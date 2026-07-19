"use client";

import { useEffect, useRef } from "react";
import stagesData from "@/fixtures/pipeline-stages.json";
import jobSummary from "@/fixtures/job-summary.json";
import type { PipelineData } from "./types";
import { useReplayEngine } from "./useReplayEngine";
import SitePicker from "./SitePicker";
import StageStepper from "./StageStepper";
import ReplayConsole from "./ReplayConsole";
import ResultReveal from "./ResultReveal";
import TrackerViewer from "./TrackerViewer";

const pipeline = stagesData as PipelineData;
const stages = pipeline.stages;

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-5 shadow-card sm:p-6">
      {children}
    </div>
  );
}

export default function SandboxApp() {
  const engine = useReplayEngine(stages);
  const { phase } = engine;
  const started = phase !== "idle";
  const done = phase === "done";

  const replayRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  // Scroll the replay into view when a run kicks off.
  const wasIdle = useRef(true);
  useEffect(() => {
    if (started && wasIdle.current) {
      wasIdle.current = false;
      replayRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (!started) wasIdle.current = true;
  }, [started]);

  // Reveal the result once the run completes.
  const wasDone = useRef(false);
  useEffect(() => {
    if (done && !wasDone.current) {
      wasDone.current = true;
      // Let the reveal mount before scrolling.
      const t = setTimeout(
        () =>
          resultRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          }),
        120,
      );
      return () => clearTimeout(t);
    }
    if (!done) wasDone.current = false;
  }, [done]);

  const currentStage =
    engine.currentStage >= 0 ? stages[engine.currentStage] : null;

  return (
    <div className="mx-auto max-w-[1080px] px-5 py-16 sm:py-20">
      {/* Header / intro */}
      <header className="max-w-[720px]">
        <span className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-1 text-[13px] text-body shadow-card">
          <span className="spark-gradient-bg h-2 w-2 rounded-full" />
          SPARK Sandbox — canned replay
        </span>
        <h1 className="mt-6 text-[clamp(2rem,5vw,3rem)] font-light leading-[1.08] tracking-[-0.03em] text-heading">
          Watch SPARK rebuild a{" "}
          <span className="spark-gradient-text">classic SharePoint</span> site
        </h1>
        <p className="mt-5 text-[17px] leading-[1.5] text-body">
          Pick the sample source site and press{" "}
          <span className="text-heading">Rebuild</span>. SPARK replays all 13
          pipeline stages — capture, audit, score, compose, and a fail-closed
          verify gate — then reveals the before/after and the content tracker it
          produced.
        </p>
        <p className="mt-3 rounded-[var(--radius-md)] border border-border bg-surface-muted px-4 py-3 text-[13.5px] leading-[1.5] text-body">
          <span className="font-medium text-heading">
            This is a canned replay of a real Crestfield rebuild.
          </span>{" "}
          No live SharePoint, no credentials, no network calls — every stage,
          log line, and asset is loaded from static fixtures
          ({jobSummary.jobId}, verdict{" "}
          <span className="text-heading">
            copy fidelity {jobSummary.verdict.copyFidelity}
          </span>
          ).
        </p>
      </header>

      {/* 1 — Site picker */}
      <section className="mt-12">
        <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-[0.12em] text-label">
          1 · Choose a source site
        </h2>
        <SitePicker onRebuild={engine.start} disabled={phase === "running"} />
      </section>

      {/* 2 — Pipeline replay */}
      {started && (
        <section ref={replayRef} className="mt-12 scroll-mt-24">
          <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-[0.12em] text-label">
            2 · Pipeline replay
          </h2>
          <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
            <SectionCard>
              <StageStepper
                stages={stages}
                statuses={engine.statuses}
                currentStage={engine.currentStage}
              />
            </SectionCard>
            <SectionCard>
              <ReplayConsole
                phase={engine.phase}
                lines={engine.lines}
                progress={engine.progress}
                currentStage={currentStage}
                gatePassed={engine.gatePassed}
                onPause={engine.pause}
                onResume={engine.resume}
                onRestart={engine.restart}
                onSkip={engine.skip}
              />
            </SectionCard>
          </div>
        </section>
      )}

      {/* 3 — Before/After + 4 — Tracker */}
      {done && (
        <>
          <section ref={resultRef} className="mt-12 scroll-mt-24">
            <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-[0.12em] text-label">
              3 · The rebuild
            </h2>
            <SectionCard>
              <ResultReveal />
            </SectionCard>
          </section>

          <section className="mt-12">
            <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-[0.12em] text-label">
              4 · What SPARK produced
            </h2>
            <SectionCard>
              <TrackerViewer />
            </SectionCard>
          </section>
        </>
      )}
    </div>
  );
}
