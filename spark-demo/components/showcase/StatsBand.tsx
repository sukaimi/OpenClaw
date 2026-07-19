import pipelineData from "@/fixtures/pipeline-stages.json";
import jobSummary from "@/fixtures/job-summary.json";

const stats = [
  { value: String(pipelineData.stages.length), label: "pipeline stages" },
  { value: jobSummary.verdict.copyFidelity, label: "copy fidelity" },
  { value: String(jobSummary.assets.inventoried), label: "assets inventoried" },
  { value: "100%", label: "autonomous" },
];

export default function StatsBand() {
  return (
    <section className="py-6">
      <div className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface shadow-card">
        <dl className="grid grid-cols-2 divide-y divide-border sm:grid-cols-4 sm:divide-x sm:divide-y-0">
          {stats.map((s) => (
            <div
              key={s.label}
              className="flex flex-col items-center gap-1 px-4 py-8 text-center"
            >
              <dt className="order-2 text-[13px] uppercase tracking-[0.1em] text-body">
                {s.label}
              </dt>
              <dd className="order-1 text-[clamp(2rem,5vw,2.75rem)] font-light leading-none tracking-[-0.02em] spark-gradient-text [font-feature-settings:'tnum']">
                {s.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
