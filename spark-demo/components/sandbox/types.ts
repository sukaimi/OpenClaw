// Shared types for the SPARK sandbox. These mirror the shapes of the
// fixtures under spark-demo/fixtures/*.json. No runtime logic here.

export type PipelineStage = {
  id: string;
  label: string;
  description: string;
  agent: string;
  durationMs: number;
  logs: string[];
  isGate?: boolean;
  failClosed?: boolean;
};

export type PipelineData = {
  meta: {
    client: string;
    jobId: string;
    note: string;
    totalDurationMs: number;
  };
  stages: PipelineStage[];
};

export type StatusColor = {
  token: string;
  hex: string;
  label: string;
};

export type StatusColors = Record<string, StatusColor>;

export type ContentTrackerRow = {
  page: string;
  pageGroup: string;
  url: string;
  section: string;
  assetType: string;
  description: string;
  content: string;
  imageRef: string;
  hyperlink: string;
  reviewNotes: string;
  migrationStatus: string;
};

export type ImageIndexRow = {
  referenceId: string;
  fileName: string;
  page: string;
  section: string;
  usage: string;
  resolution: string;
  migrationAction: string;
};

export type AuditMetric = { metric: string; value: string };
export type PainPoint = { id: string; finding: string };

export type TrackerData = {
  meta: {
    client: string;
    sourceFile: string;
    derivedFrom: string;
    note: string;
    statusCounts: Record<string, number>;
  };
  statusColors: StatusColors;
  sheets: {
    contentTracker: { columns: string[]; rows: ContentTrackerRow[] };
    imageIndex: { columns: string[]; rows: ImageIndexRow[] };
    migrationSummary: { audit: AuditMetric[]; painPoints: PainPoint[] };
  };
};

// Per-stage lifecycle state used by the replay engine.
export type StageStatus = "pending" | "running" | "done";

// A single streamed console line.
export type ConsoleLine = {
  key: string;
  stageId: string;
  agent: string;
  text: string;
  isGate: boolean;
  highlight: boolean; // e.g. the "copy fidelity 1.00 — PASS" line
};

export type ReplayPhase = "idle" | "running" | "paused" | "done";
