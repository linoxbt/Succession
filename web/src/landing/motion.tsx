/**
 * Scroll motion, without a motion library.
 *
 * Everything here is an IntersectionObserver plus a CSS class. A physics
 * library would add ~50kb of runtime to animate things that only ever move
 * once, in one direction, on entry — and on a page whose argument is
 * restraint, weight is the wrong trade.
 *
 * Every effect checks `prefers-reduced-motion` and degrades to "already
 * visible" rather than to "invisible", so a reader who asks for less motion
 * gets the whole page immediately instead of an empty one.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** True once the element has entered the viewport. Never flips back. */
export function useInView<T extends HTMLElement>(threshold = 0.25) {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(() => prefersReducedMotion());

  useEffect(() => {
    if (seen || !ref.current) return;
    const node = ref.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(node);

    // The observer is an enhancement, never the only way content appears.
    // It can legitimately never fire — a viewport resized past the element, a
    // print or screenshot pass, a browser that throttles observers in a
    // background tab — and content that is hidden until an animation triggers
    // is content that can be lost. This guarantees it shows regardless.
    const failsafe = window.setTimeout(() => {
      setSeen(true);
      observer.disconnect();
    }, 2500);

    return () => {
      observer.disconnect();
      window.clearTimeout(failsafe);
    };
  }, [seen, threshold]);

  return { ref, seen };
}

/** Fade and rise on entry. `delay` staggers siblings. */
export function Reveal({
  children,
  delay = 0,
  as: Tag = "div",
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  as?: "div" | "section" | "li" | "p" | "h2";
  className?: string;
}) {
  const { ref, seen } = useInView<HTMLDivElement>(0.15);
  return (
    <Tag
      ref={ref as never}
      className={`reveal ${seen ? "is-in" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Tag>
  );
}

/**
 * A number that counts up once, on entry.
 *
 * Eased rather than linear, and it always lands exactly on the target — a
 * counter that stops at 419 because the last frame was dropped undermines the
 * one thing a number on a landing page is for.
 */
export function CountUp({
  to,
  duration = 1100,
  decimals = 0,
  prefix = "",
  suffix = "",
}: {
  to: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
}) {
  const { ref, seen } = useInView<HTMLSpanElement>(0.4);
  const [value, setValue] = useState(() => (prefersReducedMotion() ? to : 0));

  useEffect(() => {
    if (!seen || prefersReducedMotion()) {
      setValue(to);
      return;
    }
    let raf = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(t === 1 ? to : to * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [seen, to, duration]);

  return (
    <span ref={ref} className="tnum">
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}

/**
 * A hash that scrambles into place.
 *
 * Hex characters cycle before settling, left to right. It is the one piece of
 * decoration on the page that is also an explanation: it makes visible that a
 * hash is derived rather than declared.
 */
export function ScrambleHash({
  value,
  active,
  duration = 900,
  className = "",
}: {
  value: string;
  active: boolean;
  duration?: number;
  className?: string;
}) {
  const [shown, setShown] = useState(value);

  useEffect(() => {
    if (!active || prefersReducedMotion()) {
      setShown(value);
      return;
    }
    const chars = "0123456789abcdef";
    let raf = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - started) / duration, 1);
      const settled = Math.floor(value.length * t);
      setShown(
        value
          .split("")
          .map((c, i) =>
            i < settled || c === "x" || c === "0"
              ? c
              : chars[Math.floor(Math.random() * chars.length)],
          )
          .join(""),
      );
      if (t < 1) raf = requestAnimationFrame(tick);
      else setShown(value);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, value, duration]);

  return <span className={className}>{shown}</span>;
}
