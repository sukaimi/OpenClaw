import Button from "@/components/Button";

export default function Hero() {
  return (
    <section className="relative overflow-hidden py-24 text-center sm:py-28">
      {/* Soft gradient glow behind the hero */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-4 -z-10 h-[460px] w-[820px] max-w-full -translate-x-1/2 rounded-full spark-gradient-bg opacity-20 blur-3xl"
      />

      <span className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-1 text-[13px] text-body shadow-card">
        <span className="spark-gradient-bg h-2 w-2 rounded-full" />
        SPARK v1 — SharePoint Autonomous Rebuild Kit
      </span>

      <h1 className="mx-auto mt-8 max-w-[860px] text-[clamp(2.5rem,7vw,4rem)] font-light leading-[1.03] tracking-[-0.03em] text-heading">
        Rebuild any classic SharePoint site —{" "}
        <span className="spark-gradient-text">autonomously.</span>
      </h1>

      <p className="mx-auto mt-6 max-w-[640px] text-[18px] leading-[1.45] text-body">
        An autonomous agent pipeline that rebuilds legacy classic SharePoint
        intranets into modern SharePoint — capture, score, compose, and a
        fail-closed verify gate.
      </p>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
        <Button href="/sandbox" variant="gradient">
          Try the live sandbox →
        </Button>
        <Button href="#pipeline" variant="ghost">
          See how it works
        </Button>
      </div>
    </section>
  );
}
