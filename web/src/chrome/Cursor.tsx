/**
 * The pointer.
 *
 * A custom cursor earns its place only if it carries information the native one
 * cannot. This one does two things: it reports what the thing under it *is*,
 * a link, a draggable rail, a block of reading, and it lags fractionally
 * behind the pointer, which is what makes the page feel like it has weight
 * rather than like it is tracking a mouse.
 *
 * Three rules keep it from becoming a gimmick:
 *
 *   It never replaces the native cursor over anything a person needs precision
 *   for. Inputs and textareas keep their I-beam; the ring simply hides.
 *
 *   It is desktop-only, gated on `(hover: hover) and (pointer: fine)`. On a
 *   touch screen there is no pointer to follow and the element would only ever
 *   appear after a tap had already landed.
 *
 *   It runs entirely outside React. Position is written to a transform in a rAF
 *   loop; a cursor that re-rendered a component on every pointer move would be
 *   the single most expensive thing on the page.
 */
import { useEffect, useRef } from "react";

import { useCursor } from "../motion";

export default function Cursor() {
  const dot = useRef<HTMLDivElement | null>(null);
  const ring = useRef<HTMLDivElement | null>(null);
  const { mode, label } = useCursor();

  useEffect(() => {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;
    let rx = x;
    let ry = y;
    let visible = false;

    const onMove = (e: PointerEvent) => {
      x = e.clientX;
      y = e.clientY;
      if (!visible) {
        visible = true;
        dot.current?.style.setProperty("opacity", "1");
        ring.current?.style.setProperty("opacity", "1");
      }
    };
    const onLeave = () => {
      visible = false;
      dot.current?.style.setProperty("opacity", "0");
      ring.current?.style.setProperty("opacity", "0");
    };

    const loop = () => {
      // The ring eases toward the pointer while the dot tracks it exactly. The
      // gap between them under fast movement is the whole effect: it reads as
      // inertia, which is the same physics the scroll already has.
      rx += (x - rx) * 0.16;
      ry += (y - ry) * 0.16;
      if (dot.current) dot.current.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (ring.current) ring.current.style.transform = `translate3d(${rx}px, ${ry}px, 0)`;
      raf = requestAnimationFrame(loop);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
    };
  }, []);

  return (
    <div aria-hidden="true" className="cursor-layer">
      <div ref={dot} className="cursor-dot" data-mode={mode} />
      <div ref={ring} className="cursor-ring" data-mode={mode}>
        {label ? <span className="cursor-label">{label}</span> : null}
      </div>
    </div>
  );
}
