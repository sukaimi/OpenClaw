"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  before: string;
  after: string;
  beforeLabel?: string;
  afterLabel?: string;
  caption?: string;
};

/**
 * Draggable before/after wipe slider.
 *
 * Size mismatch handling: the two screenshots have different intrinsic
 * dimensions (before 1409x1093, after 1440x1000). Both are placed in a single
 * fixed-aspect container and rendered with object-cover / object-top so they
 * share identical framing. The "before" image is revealed inside a clip
 * wrapper whose width tracks the handle; the image itself is pinned to the
 * measured container width (not the clip width) so it never squishes as the
 * wipe narrows.
 */
export default function BeforeAfterSlider({
  before,
  after,
  beforeLabel = "Classic (before)",
  afterLabel = "Modern (after)",
  caption,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);
  const [pos, setPos] = useState(50);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setContainerWidth(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const setFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const next = ((clientX - rect.left) / rect.width) * 100;
    setPos(Math.min(100, Math.max(0, next)));
  }, []);

  const onPointerDown = (e: React.PointerEvent) => {
    draggingRef.current = true;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    setFromClientX(e.clientX);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (draggingRef.current) setFromClientX(e.clientX);
  };
  const stopDragging = () => {
    draggingRef.current = false;
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") {
      setPos((p) => Math.max(0, p - 2));
      e.preventDefault();
    } else if (e.key === "ArrowRight") {
      setPos((p) => Math.min(100, p + 2));
      e.preventDefault();
    } else if (e.key === "Home") {
      setPos(0);
      e.preventDefault();
    } else if (e.key === "End") {
      setPos(100);
      e.preventDefault();
    }
  };

  return (
    <figure className="m-0">
      <div
        ref={containerRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={stopDragging}
        onPointerLeave={stopDragging}
        className="relative aspect-[16/11] w-full touch-none select-none overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface-muted shadow-elevated"
      >
        {/* Base: modern rebuild */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={after}
          alt={afterLabel}
          draggable={false}
          className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover object-top"
        />

        {/* Overlay: classic (before), clipped to handle position */}
        <div
          className="pointer-events-none absolute inset-y-0 left-0 overflow-hidden"
          style={{ width: `${pos}%` }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={before}
            alt={beforeLabel}
            draggable={false}
            style={{ width: containerWidth ? `${containerWidth}px` : "100%" }}
            className="absolute inset-0 h-full max-w-none select-none object-cover object-top"
          />
        </div>

        {/* Side labels */}
        <span className="pointer-events-none absolute left-3 top-3 rounded-[var(--radius-sm)] bg-black/55 px-2.5 py-1 text-[12px] font-normal text-white backdrop-blur-sm">
          {beforeLabel}
        </span>
        <span className="pointer-events-none absolute right-3 top-3 rounded-[var(--radius-sm)] bg-black/55 px-2.5 py-1 text-[12px] font-normal text-white backdrop-blur-sm">
          {afterLabel}
        </span>

        {/* Handle */}
        <div
          className="pointer-events-none absolute inset-y-0"
          style={{ left: `${pos}%`, transform: "translateX(-50%)" }}
        >
          <div className="mx-auto h-full w-0.5 bg-white/85 shadow-[0_0_0_1px_rgba(0,0,0,0.25)]" />
          <button
            type="button"
            role="slider"
            aria-label="Reveal before or after — drag or use arrow keys"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(pos)}
            aria-valuetext={`${Math.round(pos)}% classic revealed`}
            onKeyDown={onKeyDown}
            className="pointer-events-auto absolute left-1/2 top-1/2 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 cursor-ew-resize items-center justify-center rounded-full border border-white/70 bg-white text-brand-dark shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <span aria-hidden className="text-[15px] leading-none tracking-tighter">
              ‹ ›
            </span>
          </button>
        </div>
      </div>

      {caption ? (
        <figcaption className="mt-3 text-center text-[13px] text-body">
          {caption}
        </figcaption>
      ) : null}
    </figure>
  );
}
