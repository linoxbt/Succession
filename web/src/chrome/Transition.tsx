/**
 * Movement between destinations.
 *
 * The console swaps views in place rather than loading documents, so there is
 * no navigation event to hang a transition on and no unload to cover. What
 * there *is* is a moment where one screen's content is replaced by another's,
 * and doing that instantly makes the app feel like a set of tabs.
 *
 * So: a short outgoing settle, a swap while nothing is on screen, and an
 * incoming rise. Deliberately brief, around a third of a second each way. A
 * transition a person notices twice is a transition they resent by the tenth
 * time, and this is an application people will move through repeatedly rather
 * than a site they will visit once.
 *
 * The scroll position resets with the swap, because arriving halfway down a
 * screen you have not seen is disorienting in a way no amount of easing fixes.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

const OUT = 260;
const IN = 420;

export default function Transition({
  routeKey,
  children,
}: {
  /** Changing this triggers the swap. */
  routeKey: string;
  children: ReactNode;
}) {
  const [shown, setShown] = useState(children);
  const [phase, setPhase] = useState<"in" | "out">("in");
  const current = useRef(routeKey);

  useEffect(() => {
    if (current.current === routeKey) {
      // Same destination, new content, the screen refreshed under itself, so
      // update in place. Animating here would flash on every data refresh.
      setShown(children);
      return;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      current.current = routeKey;
      setShown(children);
      window.scrollTo(0, 0);
      return;
    }

    setPhase("out");
    const timer = window.setTimeout(() => {
      current.current = routeKey;
      setShown(children);
      window.scrollTo(0, 0);
      setPhase("in");
    }, OUT);

    return () => window.clearTimeout(timer);
  }, [routeKey, children]);

  return (
    <div
      className="route"
      data-phase={phase}
      style={
        {
          "--route-out": `${OUT}ms`,
          "--route-in": `${IN}ms`,
        } as React.CSSProperties
      }
    >
      {shown}
    </div>
  );
}
