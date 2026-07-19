import Card, { CardTitle, CardBody } from "@/components/Card";
import pipelineData from "@/fixtures/pipeline-stages.json";
import jobSummary from "@/fixtures/job-summary.json";
import contentTracker from "@/fixtures/content-tracker.json";

const stageCount = pipelineData.stages.length;
const agentCount = new Set(pipelineData.stages.map((s) => s.agent)).size;
const statusCounts = contentTracker.meta.statusCounts;
const auditedAssets = Object.values(statusCounts).reduce((a, b) => a + b, 0);
const statusCount = Object.keys(statusCounts).length;
const copyFidelity = jobSummary.verdict.copyFidelity;

const cards = [
  {
    title: "Autonomous multi-agent pipeline",
    body: `${stageCount} stages driven by ${agentCount} specialized agents — from intake to closeout, with no human at the keyboard.`,
  },
  {
    title: "Fail-closed verify gate",
    body: `The agent can't self-approve. A content-zone diff must reach copy fidelity ${copyFidelity} before the job is allowed to close.`,
  },
  {
    title: "Content tracker",
    body: `${auditedAssets} assets audited and classified across ${statusCount} migration statuses — Migrate, Rewrite, Review, and Archive.`,
  },
  {
    title: "Zero-touch handover",
    body: "A Teams-native handover report and closeout ping fire automatically the moment the verify gate opens.",
  },
];

export default function KitCards() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-[640px] text-center">
        <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
          What&apos;s in the kit
        </p>
        <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
          Everything the rebuild needs
        </h2>
      </div>

      <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.title} className="flex flex-col">
            <CardTitle>{c.title}</CardTitle>
            <CardBody>{c.body}</CardBody>
          </Card>
        ))}
      </div>
    </section>
  );
}
