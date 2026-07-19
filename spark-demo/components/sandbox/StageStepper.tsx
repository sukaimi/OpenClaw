"use client";

import type { PipelineStage, StageStatus } from "./types";

type StageStepperProps = {
  stages: PipelineStage[];
  statuses: StageStatus[];
  currentStage: number;
};

function Dot({ status, isGate }: { status: StageStatus; isGate?: boolean }) {
  if (status === "done") {
    return (
      <span
        className={`flex h-6 w-6 items-center justify-center rounded-full text-[13px] text-white ${
          isGate ? "bg-emerald-500" : "spark-gradient-bg"
        }`}
        aria-hidden
      >
        ✓
      </span>
    );
  }
  if (status === "running") {
    return (
      <span
        className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-primary"
        aria-hidden
      >
        <span className="h-2 w-2 animate-ping rounded-full bg-primary" />
      </span>
    );
  }
  return (
    <span
      className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-surface-muted"
      aria-hidden
    />
  );
}

export default function StageStepper({
  stages,
  statuses,
  currentStage,
}: StageStepperProps) {
  return (
    <ol className="flex flex-col gap-0.5" aria-label="Pipeline stages">
      {stages.map((stage, i) => {
        const status = statuses[i] ?? "pending";
        const active = i === currentStage && status === "running";
        return (
          <li
            key={stage.id}
            aria-current={active ? "step" : undefined}
            className={`relative flex items-start gap-3 rounded-[var(--radius-md)] px-2 py-2 transition-colors ${
              active
                ? "bg-primary/5"
                : status === "done"
                  ? ""
                  : "opacity-70"
            } ${stage.isGate ? "ring-1 ring-emerald-500/30" : ""}`}
          >
            <div className="flex flex-col items-center">
              <Dot status={status} isGate={stage.isGate} />
              {i < stages.length - 1 && (
                <span
                  className={`mt-0.5 h-5 w-px ${
                    status === "done" ? "bg-primary/40" : "bg-border"
                  }`}
                  aria-hidden
                />
              )}
            </div>
            <div className="min-w-0 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`text-[14px] ${
                    active || status === "done"
                      ? "text-heading"
                      : "text-body"
                  }`}
                >
                  {stage.label}
                </span>
                {stage.isGate && (
                  <span className="rounded-[var(--radius-sm)] bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-success">
                    Gate · fail-closed
                  </span>
                )}
              </div>
              {active && (
                <p className="mt-0.5 text-[12.5px] leading-snug text-body">
                  {stage.description}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
