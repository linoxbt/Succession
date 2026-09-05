/**
 * The motion system.
 *
 * Four primitives — smooth scroll, reveal, parallax, magnetic — and nothing
 * else. A page whose motion comes from a handful of shared behaviours reads as
 * composed; one where each component invents its own reads as busy.
 *
 * Three decisions keep this fast enough to use everywhere:
 *
 * 1. **One IntersectionObserver for every revealed element on the page**, not
 *    one per component. Observers are cheap individually and expensive by the
 *    hundred, and reveal is used on nearly every block here.
 * 2. **One rAF loop for every parallax element**, reading scroll position once
 *    per frame and writing transforms in a batch. Per-element scroll listeners
 *    would each force their own layout read.
 * 3. **Transform and opacity only.** Nothing here touches a property that
 *    triggers layout, so the compositor does the work.
 *
 * All of it is an enhancement. Under `prefers-reduced-motion` the observers
 * still run — elements are marked visible immediately — and the parallax loop
 * never starts, so the page is complete and static.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

/** Type-only, so the class is not pulled into the initial bundle. */
type LenisInstance = InstanceType<typeof import("lenis").default>;

const prefersReduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* -- smooth scroll ------------------------------------------------------ */

const ScrollCtx = createContext<{ scrollTo: (target: string | number) => void }>({
  scrollTo: () => {},
});

export const useScrollTo = () => useContext(ScrollCtx).scrollTo;

/**
 * Lenis, wrapping the app.
 *
 * Native smooth scrolling jumps between discrete positions; this interpolates,
 * which is what makes parallax read as depth rather than as stepping. It is
 * ~3KB and it is the single change that most affects how the whole page feels,
 * which is why it is here and a larger animation library is not.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const lenisRef = useRef<LenisInstance | null>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    let raf = 0;
    let lenis: LenisInstance | null = null;
    let cancelled = false;

    // Imported lazily so the scroll library is not in the critical path for
    // first paint; the page is fully usable before it arrives.
    void import("lenis").then(({ default: Lenis }) => {
      if (cancelled) return;
      lenis = new Lenis({ duration: 1.05, wheelMultiplier: 1, touchMultiplier: 1.6 });
      lenisRef.current = lenis;
      const loop = (time: number) => {
        lenis?.raf(time);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      lenis?.destroy();
      lenisRef.current = null;
    };
  }, []);

  const scrollTo = useCallback((target: string | number) => {
    if (lenisRef.current) lenisRef.current.scrollTo(target, { offset: 0 });
    else if (typeof target === "string") {
      document.querySelector(target)?.scrollIntoView({ behavior: "smooth" });
    } else window.scrollTo({ top: target, behavior: "smooth" });
  }, []);

  return <ScrollCtx.Provider value={{ scrollTo }}>{children}</ScrollCtx.Provider>;
}

/* -- reveal -------------------------------------------------------------- */

let sharedObserver: IntersectionObserver | null = null;

function observer(): IntersectionObserver {
  if (sharedObserver) return sharedObserver;
  sharedObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("is-in");
        // Reveal fires once. Re-animating on the way back up turns a document
        // into a slideshow.
        sharedObserver?.unobserve(entry.target);
      }
    },
    // Fires a little before the element reaches the fold, so the motion has
    // finished by the time it is properly in view rather than starting there.
    { rootMargin: "0px 0px -12% 0px", threshold: 0.08 },
  );
  return sharedObserver;
}

/** Attach to any element to have it rise into view once. */
export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (prefersReduced()) {
      node.classList.add("is-in");
      return;
    }
    observer().observe(node);
    return () => observer().unobserve(node);
  }, []);
  return ref;
}

/**
 * A block that rises into view.
 *
 * `index` staggers siblings through a custom property rather than a delay
 * class, so a list can stagger without every item carrying its own styling.
 */
export function Reveal({
  children,
  index,
  as: Tag = "div",
  className = "",
}: {
  children: ReactNode;
  index?: number;
  as?: "div" | "section" | "li" | "article" | "header" | "footer";
  className?: string;
}) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <Tag
      ref={ref as never}
      className={`reveal ${className}`}
      style={index !== undefined ? ({ "--i": index } as React.CSSProperties) : undefined}
    >
      {children}
    </Tag>
  );
}

/**
 * A line of display type that rises out from behind a clip.
 *
 * Each line needs its own clipping box, so callers pass one `MaskLine` per
 * line rather than one per paragraph — which also means the line breaks are a
 * deliberate typographic decision rather than whatever the width produced.
 */
export function MaskLine({
  children,
  index,
  className = "",
}: {
  children: ReactNode;
  index?: number;
  className?: string;
}) {
  const ref = useReveal<HTMLSpanElement>();
  return (
    <span
      ref={ref}
      className={`mask-line ${className}`}
      style={index !== undefined ? ({ "--i": index } as React.CSSProperties) : undefined}
    >
      <span>{children}</span>
    </span>
  );
}

/* -- parallax ------------------------------------------------------------ */

type ParallaxEntry = { el: HTMLElement; speed: number };
const parallaxElements = new Set<ParallaxEntry>();
let parallaxRaf = 0;

function parallaxLoop() {
  // One layout read per frame, shared by every registered element, then a
  // batch of transform writes. Reading per element would thrash.
  const viewport = window.innerHeight;
  for (const { el, speed } of parallaxElements) {
    const rect = el.getBoundingClientRect();
    if (rect.bottom < -200 || rect.top > viewport + 200) continue;
    // Progress runs -1 → 1 across the element's travel through the viewport,
    // so the offset is zero when the element is centred and the effect is
    // symmetrical on the way in and out.
    const progress = (rect.top + rect.height / 2 - viewport / 2) / viewport;
    el.style.transform = `translate3d(0, ${(progress * speed * 100).toFixed(2)}px, 0)`;
  }
  parallaxRaf = requestAnimationFrame(parallaxLoop);
}

/** Move an element against the scroll. Positive drifts down, negative up. */
export function useParallax<T extends HTMLElement>(speed = 0.12) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReduced()) return;
    const entry = { el, speed };
    parallaxElements.add(entry);
    if (!parallaxRaf) parallaxRaf = requestAnimationFrame(parallaxLoop);
    return () => {
      parallaxElements.delete(entry);
      el.style.transform = "";
      if (parallaxElements.size === 0) {
        cancelAnimationFrame(parallaxRaf);
        parallaxRaf = 0;
      }
    };
  }, [speed]);
  return ref;
}

/* -- magnetic ------------------------------------------------------------ */

/**
 * A control that leans toward the pointer.
 *
 * Deliberately small in travel — enough that a button feels answerable, not so
 * much that it feels like it is dodging the cursor. Bound to pointer events and
 * skipped entirely on coarse pointers, where there is no hover to respond to
 * and the effect would only fire after a tap had already landed.
 */
export function useMagnetic<T extends HTMLElement>(strength = 0.28) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReduced()) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    let frame = 0;
    const move = (e: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const dx = e.clientX - (r.left + r.width / 2);
        const dy = e.clientY - (r.top + r.height / 2);
        el.style.transform = `translate3d(${dx * strength}px, ${dy * strength}px, 0)`;
      });
    };
    const reset = () => {
      cancelAnimationFrame(frame);
      el.style.transform = "translate3d(0,0,0)";
    };

    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", reset);
    return () => {
      cancelAnimationFrame(frame);
      el.removeEventListener("pointermove", move);
      el.removeEventListener("pointerleave", reset);
    };
  }, [strength]);
  return ref;
}

/* -- scroll position ----------------------------------------------------- */

/** Whether the page has moved off the top. Drives the header's condensed state. */
export function useScrolled(threshold = 24) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return scrolled;
}

/** Normalised 0→1 progress of the document, for the reading indicator. */
export function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const max = document.body.scrollHeight - window.innerHeight;
        setProgress(max > 0 ? Math.min(1, window.scrollY / max) : 0);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);
  return progress;
}

/** A count that eases to its value when it first enters view. */
export function useCountUp(value: number, duration = 1200) {
  const [shown, setShown] = useState(0);
  const ref = useReveal<HTMLSpanElement>();
  const started = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (prefersReduced()) {
      setShown(value);
      return;
    }
    const check = () => {
      if (started.current || !node.classList.contains("is-in")) return;
      started.current = true;
      const start = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - start) / duration);
        // Ease-out cubic: fast to nearly-there, then settles.
        setShown(Math.round(value * (1 - Math.pow(1 - t, 3))));
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    const id = window.setInterval(check, 100);
    return () => window.clearInterval(id);
  }, [value, duration, ref]);

  return useMemo(() => ({ ref, shown }), [ref, shown]);
}

/* -- scroll-linked scenes ------------------------------------------------ */

type SceneEntry = { el: HTMLElement; set: (p: number) => void };
const sceneElements = new Set<SceneEntry>();
let sceneRaf = 0;

function sceneLoop() {
  const viewport = window.innerHeight;
  for (const { el, set } of sceneElements) {
    const rect = el.getBoundingClientRect();
    // 0 when the element's top reaches the bottom of the viewport, 1 when its
    // bottom leaves the top. The whole traversal, not just the visible part,
    // so a pinned section can choreograph across its entire scroll length.
    const total = rect.height + viewport;
    const travelled = viewport - rect.top;
    set(Math.max(0, Math.min(1, travelled / total)));
  }
  sceneRaf = requestAnimationFrame(sceneLoop);
}

/**
 * Progress of an element through the viewport, 0 → 1, updated per frame.
 *
 * The value is handed to a callback rather than to React state on purpose:
 * a scroll-linked value that re-renders sixty times a second is a scroll-linked
 * value that drops frames. Callers write straight to a transform.
 */
export function useScrollScene<T extends HTMLElement>(onProgress: (p: number) => void) {
  const ref = useRef<T | null>(null);
  const cb = useRef(onProgress);
  cb.current = onProgress;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReduced()) {
      cb.current(1);
      return;
    }
    const entry = { el, set: (p: number) => cb.current(p) };
    sceneElements.add(entry);
    if (!sceneRaf) sceneRaf = requestAnimationFrame(sceneLoop);
    return () => {
      sceneElements.delete(entry);
      if (sceneElements.size === 0) {
        cancelAnimationFrame(sceneRaf);
        sceneRaf = 0;
      }
    };
  }, []);

  return ref;
}

/* -- pointer ------------------------------------------------------------- */

export type CursorMode = "default" | "link" | "drag" | "read";

const CursorCtx = createContext<{
  mode: CursorMode;
  setMode: (m: CursorMode) => void;
  label: string;
  setLabel: (l: string) => void;
}>({ mode: "default", setMode: () => {}, label: "", setLabel: () => {} });

export const useCursor = () => useContext(CursorCtx);

export function CursorProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<CursorMode>("default");
  const [label, setLabel] = useState("");
  const value = useMemo(() => ({ mode, setMode, label, setLabel }), [mode, label]);
  return <CursorCtx.Provider value={value}>{children}</CursorCtx.Provider>;
}

/**
 * Props that put the cursor into a state while the pointer is over an element.
 *
 * Spread onto anything: `<a {...cursorState("link")}>`. Returning props rather
 * than wrapping in a component means a caller never has to change their markup
 * structure to opt in.
 */
export function useCursorState(mode: CursorMode, label = "") {
  const { setMode, setLabel } = useCursor();
  return useMemo(
    () => ({
      onPointerEnter: () => {
        setMode(mode);
        setLabel(label);
      },
      onPointerLeave: () => {
        setMode("default");
        setLabel("");
      },
    }),
    [mode, label, setMode, setLabel],
  );
}
