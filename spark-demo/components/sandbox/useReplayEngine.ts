"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ConsoleLine,
  PipelineStage,
  ReplayPhase,
  StageStatus,
} from "./types";

// Map a real stage duration (≈1.3s–6.8s) into a snappy demo slot so the
// whole 13-stage replay lands around ~22s instead of the real ~47s.
// Linear map with a hard clamp to [1200ms, 2500ms] per the brief.
function scaledDurationMs(durationMs: number): number {
  const REAL_MIN = 1300;
  const REAL_MAX = 6800;
  const OUT_MIN = 1200;
  const OUT_MAX = 2500;
  const t = (durationMs - REAL_MIN) / (REAL_MAX - REAL_MIN);
  const scaled = OUT_MIN + t * (OUT_MAX - OUT_MIN);
  return Math.max(OUT_MIN, Math.min(OUT_MAX, scaled));
}

function isHighlight(text: string): boolean {
  return /copy fidelity 1\.00/i.test(text) || /gate open/i.test(text);
}

type Ctrl = { cancelled: boolean; paused: boolean };

export type ReplayEngine = {
  phase: ReplayPhase;
  currentStage: number;
  statuses: StageStatus[];
  lines: ConsoleLine[];
  progress: number; // 0..100
  gatePassed: boolean;
  start: () => void;
  pause: () => void;
  resume: () => void;
  restart: () => void;
  skip: () => void;
};

export function useReplayEngine(stages: PipelineStage[]): ReplayEngine {
  const total = stages.length;
  const [phase, setPhase] = useState<ReplayPhase>("idle");
  const [currentStage, setCurrentStage] = useState(-1);
  const [statuses, setStatuses] = useState<StageStatus[]>(() =>
    stages.map(() => "pending"),
  );
  const [lines, setLines] = useState<ConsoleLine[]>([]);
  const [progress, setProgress] = useState(0);
  const [gatePassed, setGatePassed] = useState(false);

  const ctrlRef = useRef<Ctrl>({ cancelled: true, paused: false });

  // Pause-aware, cancellable sleep. Resolves after `ms` of *unpaused* time.
  const sleep = useCallback((ms: number, ctrl: Ctrl) => {
    return new Promise<void>((resolve) => {
      if (ms <= 0) return resolve();
      let remaining = ms;
      const tick = 40;
      const id = setInterval(() => {
        if (ctrl.cancelled) {
          clearInterval(id);
          resolve();
          return;
        }
        if (ctrl.paused) return;
        remaining -= tick;
        if (remaining <= 0) {
          clearInterval(id);
          resolve();
        }
      }, tick);
    });
  }, []);

  const resetState = useCallback(() => {
    setStatuses(stages.map(() => "pending"));
    setLines([]);
    setProgress(0);
    setGatePassed(false);
    setCurrentStage(-1);
  }, [stages]);

  // Fill everything instantly — used by "Skip to result".
  const fillComplete = useCallback(() => {
    setStatuses(stages.map(() => "done"));
    const allLines: ConsoleLine[] = [];
    stages.forEach((stage) => {
      stage.logs.forEach((text, li) => {
        allLines.push({
          key: `${stage.id}-${li}`,
          stageId: stage.id,
          agent: stage.agent,
          text,
          isGate: Boolean(stage.isGate),
          highlight: isHighlight(text),
        });
      });
    });
    setLines(allLines);
    setProgress(100);
    setGatePassed(true);
    setCurrentStage(total - 1);
    setPhase("done");
  }, [stages, total]);

  const run = useCallback(
    async (ctrl: Ctrl) => {
      for (let i = 0; i < total; i++) {
        if (ctrl.cancelled) return;
        const stage = stages[i];
        setCurrentStage(i);
        setStatuses((prev) => {
          const next = [...prev];
          next[i] = "running";
          return next;
        });

        const slot = scaledDurationMs(stage.durationMs);
        const logs = stage.logs;
        const perLine = slot / (logs.length + 1);

        await sleep(perLine * 0.6, ctrl); // brief lead-in

        for (let li = 0; li < logs.length; li++) {
          if (ctrl.cancelled) return;
          const text = logs[li];
          const key = `${stage.id}-${li}`;
          const highlight = isHighlight(text);

          // Seed an empty line, then typewriter it in.
          setLines((prev) => [
            ...prev,
            {
              key,
              stageId: stage.id,
              agent: stage.agent,
              text: "",
              isGate: Boolean(stage.isGate),
              highlight,
            },
          ]);

          const typeBudget = perLine * 0.7;
          const charDelay = Math.max(
            8,
            Math.min(28, typeBudget / Math.max(text.length, 1)),
          );
          for (let c = 1; c <= text.length; c++) {
            if (ctrl.cancelled) return;
            const partial = text.slice(0, c);
            setLines((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last && last.key === key) {
                next[next.length - 1] = { ...last, text: partial };
              }
              return next;
            });
            // Type a few chars per tick to stay within budget.
            if (c % 3 === 0) await sleep(charDelay, ctrl);
          }
          await sleep(perLine * 0.35, ctrl);
        }

        if (ctrl.cancelled) return;
        setStatuses((prev) => {
          const next = [...prev];
          next[i] = "done";
          return next;
        });
        if (stage.isGate) setGatePassed(true);
        setProgress(Math.round(((i + 1) / total) * 100));
      }

      if (!ctrl.cancelled) setPhase("done");
    },
    [sleep, stages, total],
  );

  const start = useCallback(() => {
    ctrlRef.current.cancelled = true; // cancel any prior run
    const ctrl: Ctrl = { cancelled: false, paused: false };
    ctrlRef.current = ctrl;
    resetState();
    setPhase("running");
    void run(ctrl);
  }, [resetState, run]);

  const pause = useCallback(() => {
    if (phase !== "running") return;
    ctrlRef.current.paused = true;
    setPhase("paused");
  }, [phase]);

  const resume = useCallback(() => {
    if (phase !== "paused") return;
    ctrlRef.current.paused = false;
    setPhase("running");
  }, [phase]);

  const restart = useCallback(() => {
    start();
  }, [start]);

  const skip = useCallback(() => {
    ctrlRef.current.cancelled = true;
    ctrlRef.current.paused = false;
    fillComplete();
  }, [fillComplete]);

  // Cancel the running loop if the component unmounts.
  useEffect(() => {
    return () => {
      ctrlRef.current.cancelled = true;
    };
  }, []);

  return {
    phase,
    currentStage,
    statuses,
    lines,
    progress,
    gatePassed,
    start,
    pause,
    resume,
    restart,
    skip,
  };
}
