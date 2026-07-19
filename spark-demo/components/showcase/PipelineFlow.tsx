import pipelineData from "@/fixtures/pipeline-stages.json";

type Stage = {
  id: string;
  label: string;
  description: string;
  agent: string;
  durationMs: number;
  logs: string[];
  isGate?: boolean;
  failClosed?: boolean;
};

const stages = pipelineData.stages as Stage[];

function chunk<T>(arr: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

function AgentTag({ agent }: { agent: string }) {
  return (
    <span className="inline-block rounded-[var(--radius-sm)] bg-surface-muted px-2 py-0.5 font-mono text-[11px] tracking-tight text-label">
      {agent}
    </span>
  );
}

function GateBadge() {
  return (
    <span className="mt-3 inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] bg-primary/10 px-2.5 py-1 text-[11px] font-normal text-primary ring-1 ring-primary/30">
      <span className="h-1.5 w-1.5 rounded-full bg-primary" />
      fail-closed · agent can&apos;t self-approve
    </span>
  );
}

/** Compact node used in the desktop horizontal flow. */
function DesktopNode({ stage, index }: { stage: Stage; index: number }) {
  const gate = stage.isGate;
  return (
    <div
      className={`flex flex-1 basis-0 flex-col rounded-[var(--radius-lg)] border p-4 ${
        gate
          ? "border-primary/50 bg-primary/[0.04] shadow-card ring-1 ring-primary/25"
          : "border-border bg-surface shadow-card"
      }`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex h-8 w-8 flex-none items-center justify-center rounded-full text-[14px] font-normal [font-feature-settings:'tnum'] ${
            gate
              ? "spark-gradient-bg text-white"
              : "border border-border-strong bg-surface-muted text-heading"
          }`}
        >
          {index + 1}
        </span>
        <h3 className="text-[15px] leading-tight tracking-[-0.01em] text-heading">
          {stage.label}
        </h3>
      </div>
      <p className="mt-2 flex-1 text-[13px] leading-[1.45] text-body">
        {stage.description}
      </p>
      <div className="mt-3">
        <AgentTag agent={stage.agent} />
      </div>
      {gate ? <GateBadge /> : null}
    </div>
  );
}

/** Row of nodes with connector arrows between adjacent nodes. */
function DesktopRow({ row, startIndex }: { row: Stage[]; startIndex: number }) {
  return (
    <div className="flex items-stretch gap-0">
      {row.map((stage, i) => (
        <div key={stage.id} className="flex flex-1 basis-0 items-stretch">
          <DesktopNode stage={stage} index={startIndex + i} />
          {i < row.length - 1 ? (
            <div className="flex w-6 flex-none items-center justify-center">
              <span aria-hidden className="text-[16px] text-border-strong">
                →
              </span>
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default function PipelineFlow() {
  const rows = chunk(stages, 4);

  return (
    <section id="pipeline" className="scroll-mt-24 py-20">
      <div className="mx-auto max-w-[640px] text-center">
        <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
          The pipeline
        </p>
        <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
          13 stages, intake to closeout
        </h2>
        <p className="mt-4 text-[16px] leading-[1.5] text-body">
          Every stage is a specialized agent. The run only completes if the
          fail-closed verify gate passes — no agent can wave its own work
          through.
        </p>
      </div>

      {/* Desktop: horizontal connected rows */}
      <div className="mt-14 hidden flex-col gap-8 lg:flex">
        {rows.map((row, r) => (
          <DesktopRow key={r} row={row} startIndex={r * 4} />
        ))}
      </div>

      {/* Mobile / tablet: vertical timeline with continuous left rail */}
      <ol className="relative mt-12 space-y-6 lg:hidden">
        <span
          aria-hidden
          className="absolute bottom-6 left-[19px] top-6 w-px bg-border"
        />
        {stages.map((stage, i) => {
          const gate = stage.isGate;
          return (
            <li key={stage.id} className="relative flex gap-4">
              <span
                className={`relative z-10 inline-flex h-10 w-10 flex-none items-center justify-center rounded-full text-[15px] font-normal [font-feature-settings:'tnum'] ${
                  gate
                    ? "spark-gradient-bg text-white shadow-card"
                    : "border border-border-strong bg-surface text-heading"
                }`}
              >
                {i + 1}
              </span>
              <div
                className={`flex-1 rounded-[var(--radius-lg)] border p-4 ${
                  gate
                    ? "border-primary/50 bg-primary/[0.04] ring-1 ring-primary/25"
                    : "border-border bg-surface"
                } shadow-card`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-[16px] leading-tight tracking-[-0.01em] text-heading">
                    {stage.label}
                  </h3>
                  <AgentTag agent={stage.agent} />
                </div>
                <p className="mt-2 text-[14px] leading-[1.45] text-body">
                  {stage.description}
                </p>
                {gate ? <GateBadge /> : null}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
