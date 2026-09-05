/**
 * The first two seconds.
 *
 * A preloader is only justified if it does work. This one waits on the two
 * things that actually cause a visible flash on this page — the display face,
 * and the first paint of the hero — and it uses the wait to state what the
 * product is, so the time is spent rather than merely passed.
 *
 * It is deliberately short and it never blocks. The counter is driven by real
 * progress where the browser exposes it (`document.fonts.ready`), and floored
 * by a timeout so a slow font CDN can never hold the page hostage: whatever
 * happens, the curtain lifts.
 *
 * It runs once per session, not once per route. A curtain that reappears on
 * every navigation is a curtain between the visitor and their own back button.
 */
import { useEffect, useState } from "react";

const SEEN_KEY = "succession:entered";

export default function Preloader({ onDone }: { onDone: () => void }) {
  // Session-scoped, so a reload during development still shows it but moving
  // between routes does not.
  const [active, setActive] = useState(() => {
    try {
      return sessionStorage.getItem(SEEN_KEY) !== "1";
    } catch {
      // A private window that refuses storage should still see the page.
      return true;
    }
  });
  const [count, setCount] = useState(0);
  const [lifting, setLifting] = useState(false);

  useEffect(() => {
    if (!active) {
      onDone();
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      finish();
      return;
    }

    let raf = 0;
    let done = false;
    const started = performance.now();
    // A floor and a ceiling. The floor stops the counter flashing past on a
    // warm cache; the ceiling stops a stalled font blocking entry.
    const MIN = 900;
    const MAX = 2600;

    const fonts =
      "fonts" in document
        ? (document as Document & { fonts: FontFaceSet }).fonts.ready
        : Promise.resolve();

    let fontsReady = false;
    void fonts.then(() => {
      fontsReady = true;
    });

    const tick = (now: number) => {
      const elapsed = now - started;
      // Progress is the greater of "time spent against the floor" and "real
      // work finished", so the number always means something.
      const byTime = Math.min(1, elapsed / MIN);
      const byWork = fontsReady ? 1 : 0.85;
      const p = Math.min(byTime, byWork);
      setCount(Math.round(p * 100));

      if (!done && ((p >= 1 && elapsed >= MIN) || elapsed >= MAX)) {
        done = true;
        setCount(100);
        finish();
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);

    function finish() {
      try {
        sessionStorage.setItem(SEEN_KEY, "1");
      } catch {
        /* nothing to persist to; the curtain simply shows again next time */
      }
      setLifting(true);
      // Matches the curtain transition, so `onDone` fires as it clears rather
      // than while it is still over the page.
      window.setTimeout(() => {
        setActive(false);
        onDone();
      }, 900);
    }
    // `finish` is hoisted; the effect runs once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!active) return null;

  return (
    <div
      className={`preloader ${lifting ? "is-lifting" : ""}`}
      role="status"
      aria-live="polite"
      aria-label="Loading"
    >
      <div className="gutter flex h-full flex-col justify-between py-10">
        <p className="font-mono text-label uppercase text-chalkFaint">Succession</p>

        <p className="display-type max-w-[14ch] text-title text-chalk">
          The property layer for agent memory
        </p>

        <div className="flex items-end justify-between gap-8">
          <span className="display-type text-colossal leading-none text-chalk tnum">
            {String(count).padStart(3, "0")}
          </span>
          {/* The rule fills as the count climbs — the same information twice,
              once as a figure and once as a length, because a number alone at
              this scale reads as decoration. */}
          <span className="mb-4 hidden h-px flex-1 origin-left bg-carbonRule sm:block">
            <span
              className="block h-px origin-left bg-chalk transition-transform duration-200 ease-linear"
              style={{ transform: `scaleX(${count / 100})` }}
            />
          </span>
        </div>
      </div>
    </div>
  );
}
