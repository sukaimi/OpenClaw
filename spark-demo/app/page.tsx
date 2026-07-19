import Button from "@/components/Button";
import Card, { CardTitle, CardBody } from "@/components/Card";

const features = [
  {
    title: "Capture",
    body: "Point SPARK at any classic SharePoint site. It reads structure, content, and layout — no manual export.",
  },
  {
    title: "Rebuild",
    body: "Autonomous agents regenerate a modern, pixel-faithful site with verified content parity.",
  },
  {
    title: "Deliver",
    body: "A completeness gate closes the job only when the rebuild matches the source. No silent misses.",
  },
];

export default function Home() {
  return (
    <div className="mx-auto max-w-[1080px] px-5">
      {/* Hero */}
      <section className="relative overflow-hidden py-24 text-center sm:py-32">
        {/* Soft gradient glow behind the hero */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[420px] w-[720px] max-w-full -translate-x-1/2 rounded-full opacity-20 blur-3xl spark-gradient-bg"
        />

        <span className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-1 text-[13px] text-body shadow-card">
          <span className="spark-gradient-bg h-2 w-2 rounded-full" />
          SPARK v1 — Hackathon Preview
        </span>

        <h1 className="mx-auto mt-8 max-w-[820px] text-[clamp(2.25rem,6vw,3.5rem)] font-light leading-[1.05] tracking-[-0.03em] text-heading">
          SPARK v1 —{" "}
          <span className="spark-gradient-text">
            SharePoint Autonomous Rebuild Kit
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-[560px] text-[18px] leading-[1.4] text-body">
          Rebuild any classic SharePoint site — autonomously.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Button href="/sandbox" variant="gradient">
            Open the Sandbox
          </Button>
          <Button href="/sandbox" variant="ghost">
            See how it works
          </Button>
        </div>
      </section>

      {/* Feature cards */}
      <section className="grid gap-5 pb-24 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <Card key={f.title}>
            <CardTitle>{f.title}</CardTitle>
            <CardBody>{f.body}</CardBody>
          </Card>
        ))}
      </section>
    </div>
  );
}
