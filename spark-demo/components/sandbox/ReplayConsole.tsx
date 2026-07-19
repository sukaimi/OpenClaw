"use client";

import { useEffect, useRef } from "react";
import type { ConsoleLine, PipelineStage, ReplayPhase } from "./types";

type ReplayConsoleProps = {
  phase: ReplayPhase;
  lines: ConsoleLine[];
  progress: number;
  currentStage: PipelineStage | null;
  gatePassed: boolean;
  onPause: () => void;
  onResume: () => void;
  onRestart: () => void;
  onSkip: () => void;
};

export default function ReplayConsole({
  phase,
  lines,
  progress,
  currentStage,
  gatePassed,
  onPause,
  onResume,
  onRestart,
  onSkip,
}: ReplayConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the newest line as it streams in.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const running = phase === "running";
  const paused = phase === "paused";
  const done = phase === "done";
  const onGateStage = Boolean(currentStage?.isGate);

  return (
    <div className="flex flex-col gap-3">
      {/* Progress + agent tag row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {currentStage ? (
            <span
              className={`inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] border px-2 py-1 font-mono text-[12px] ${
                onGateStage
                  ? "border-emerald-500/40 bg-emerald-500/10 text-success"
                  : "border-border bg-surface-muted text-body"
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  running ? "animate-pulse bg-primary" : "bg-body/50"
                }`}
              />
              {currentStage.agent}
            </span>
          ) : (
            <span className="font-mono text-[12px] text-body">idle</span>
          )}
          <span className="text-[12.5px] text-body">
            {currentStage ? currentStage.label : "Ready"}
          </span>
        </div>
        <span className="font-mono text-[12px] tabular-nums text-body">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-border"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="spark-gradient-bg h-full rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Console */}
      <div
        ref={scrollRef}
        className="h-[300px] overflow-y-auto rounded-[var(--radius-md)] border border-border bg-[#0a1020] p-4 font-mono text-[12.5px] leading-[1.7] text-slate-300"
        aria-label="Pipeline console output"
        aria-live="polite"
      >
        {lines.length === 0 && (
          <p className="text-slate-500">
            $ waiting for run to start…
          </p>
        )}
        {lines.map((line, i) => {
          const isLast = i === lines.length - 1;
          return (
            <div
              key={line.key}
              className={`whitespace-pre-wrap break-words ${
                line.highlight
                  ? "font-semibold text-emerald-400"
                  : line.isGate
                    ? "text-emerald-300/90"
                    : ""
              }`}
            >
              <span className="select-none text-slate-600">
                {line.agent}&nbsp;›&nbsp;
              </span>
              {line.text}
              {isLast && running && (
                <span className="ml-0.5 inline-block h-3.5 w-2 animate-pulse bg-slate-300 align-middle" />
              )}
            </div>
          );
        })}
      </div>

      {/* Verify-gate climax banner */}
      {gatePassed && (
        <div className="flex items-start gap-3 rounded-[var(--radius-md)] border border-emerald-500/40 bg-emerald-500/10 px-4 py-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[15px] text-white">
            ✓
          </span>
          <div>
            <p className="text-[15px] font-semibold text-success-strong">
              copy fidelity 1.00 — PASS
            </p>
            <p className="mt-0.5 text-[13px] text-body">
              Fail-closed verify gate: the agent cannot self-approve. The gate
              diffed all 16 rebuilt pages against the source and opened only on a
              full content match.
            </p>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        {running && (
          <button
            type="button"
            onClick={onPause}
            className="rounded-[var(--radius-sm)] border border-border-strong bg-transparent px-3 py-1.5 text-[13px] text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            ⏸ Pause
          </button>
        )}
        {paused && (
          <button
            type="button"
            onClick={onResume}
            className="rounded-[var(--radius-sm)] border border-border-strong bg-transparent px-3 py-1.5 text-[13px] text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            ▶ Resume
          </button>
        )}
        <button
          type="button"
          onClick={onRestart}
          className="rounded-[var(--radius-sm)] border border-border-strong bg-transparent px-3 py-1.5 text-[13px] text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          ↻ Restart
        </button>
        {!done && (
          <button
            type="button"
            onClick={onSkip}
            className="rounded-[var(--radius-sm)] border border-border bg-surface-muted px-3 py-1.5 text-[13px] text-body transition-colors hover:text-heading focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Skip to result »
          </button>
        )}
      </div>
    </div>
  );
}
