"use client";

import { useCallback, useRef, useState } from "react";

type Mode = "slider" | "sideBySide";

export default function ResultReveal() {
  const [pos, setPos] = useState(50); // 0..100 — reveal split
  const [mode, setMode] = useState<Mode>("slider");
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const setFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPos(Math.max(0, Math.min(100, pct)));
  }, []);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      draggingRef.current = true;
      (e.target as Element).setPointerCapture?.(e.pointerId);
      setFromClientX(e.clientX);
    },
    [setFromClientX],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!draggingRef.current) return;
      setFromClientX(e.clientX);
    },
    [setFromClientX],
  );

  const onPointerUp = useCallback(() => {
    draggingRef.current = false;
  }, []);

  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft") setPos((p) => Math.max(0, p - 4));
    if (e.key === "ArrowRight") setPos((p) => Math.min(100, p + 4));
  }, []);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-[19px] text-heading">Before / After</h3>
          <p className="text-[13px] text-body">
            Classic source vs. the modern rebuild — drag to compare.
          </p>
        </div>
        <div className="inline-flex rounded-[var(--radius-sm)] border border-border p-0.5">
          <button
            type="button"
            onClick={() => setMode("slider")}
            className={`rounded-[calc(var(--radius-sm)-1px)] px-3 py-1 text-[13px] transition-colors ${
              mode === "slider"
                ? "bg-primary text-white"
                : "text-body hover:text-heading"
            }`}
          >
            Slider
          </button>
          <button
            type="button"
            onClick={() => setMode("sideBySide")}
            className={`rounded-[calc(var(--radius-sm)-1px)] px-3 py-1 text-[13px] transition-colors ${
              mode === "sideBySide"
                ? "bg-primary text-white"
                : "text-body hover:text-heading"
            }`}
          >
            Side by side
          </button>
        </div>
      </div>

      {mode === "slider" ? (
        <div
          ref={containerRef}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
          className="relative aspect-[3/4] w-full touch-none select-none overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface-muted shadow-card sm:aspect-[16/10]"
        >
          {/* After (base layer) */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/crestfield/after-home.png"
            alt="Crestfield Foods modern rebuilt homepage"
            draggable={false}
            className="absolute inset-0 h-full w-full object-cover object-top"
          />
          {/* Before (clipped overlay). clip-path keeps the image at full
              container size and just hides the right portion — no reflow. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/crestfield/before-home.png"
            alt="Crestfield Foods classic intranet homepage"
            draggable={false}
            style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
            className="absolute inset-0 h-full w-full object-cover object-top"
          />

          {/* Labels */}
          <span className="pointer-events-none absolute left-3 top-3 rounded-[var(--radius-sm)] bg-black/60 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-white">
            Before · Classic
          </span>
          <span className="pointer-events-none absolute right-3 top-3 rounded-[var(--radius-sm)] bg-primary/85 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-white">
            After · Modern
          </span>

          {/* Handle */}
          <div
            role="slider"
            tabIndex={0}
            aria-label="Comparison slider position"
            aria-valuenow={Math.round(pos)}
            aria-valuemin={0}
            aria-valuemax={100}
            onPointerDown={onPointerDown}
            onKeyDown={onKeyDown}
            className="absolute top-0 bottom-0 z-10 flex w-8 -translate-x-1/2 cursor-ew-resize items-center justify-center focus-visible:outline-none"
            style={{ left: `${pos}%` }}
          >
            <span className="absolute inset-y-0 left-1/2 w-0.5 -translate-x-1/2 bg-white/90" />
            <span className="relative flex h-8 w-8 items-center justify-center rounded-full bg-white text-[12px] text-slate-700 shadow-elevated ring-2 ring-primary/40">
              ⟷
            </span>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <figure>
            <div className="aspect-[3/4] w-full overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface-muted shadow-card sm:aspect-[16/10]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/crestfield/before-home.png"
                alt="Crestfield Foods classic intranet homepage"
                className="h-full w-full object-cover object-top"
              />
            </div>
            <figcaption className="mt-2 text-[12.5px] text-body">
              Before — classic intranet
            </figcaption>
          </figure>
          <figure>
            <div className="aspect-[3/4] w-full overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface-muted shadow-card sm:aspect-[16/10]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/crestfield/after-home.png"
                alt="Crestfield Foods modern rebuilt homepage"
                className="h-full w-full object-cover object-top"
              />
            </div>
            <figcaption className="mt-2 text-[12.5px] text-body">
              After — modern rebuild
            </figcaption>
          </figure>
        </div>
      )}
    </div>
  );
}
