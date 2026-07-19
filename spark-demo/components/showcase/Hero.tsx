import Button from "@/components/Button";

export default function Hero() {
  return (
    <section className="relative overflow-hidden py-20 sm:py-24">
      {/* Soft gradient glow behind the hero (stronger in light mode) */}
      <div
        aria-hidden
        style={{ opacity: "var(--hero-glow-opacity)" }}
        className="pointer-events-none absolute left-1/2 top-4 -z-10 h-[460px] w-[820px] max-w-full -translate-x-1/2 rounded-full spark-gradient-bg blur-3xl"
      />

      <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.08fr)] lg:gap-14">
        {/* Left: copy */}
        <div className="text-center lg:text-left">
          <span className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] border border-border bg-surface px-3 py-1 text-[13px] text-body shadow-card">
            <span className="spark-gradient-bg h-2 w-2 rounded-full" />
            SPARK v1 — SharePoint Autonomous Rebuild Kit
          </span>

          <h1 className="mx-auto mt-8 max-w-[640px] text-[clamp(2.25rem,5.5vw,3.5rem)] font-light leading-[1.05] tracking-[-0.03em] text-heading lg:mx-0">
            Twelve AI agents rebuild your classic SharePoint —{" "}
            <span className="spark-gradient-text">start to finish.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-[560px] text-[18px] leading-[1.45] text-body lg:mx-0">
            An autonomous pipeline captures the old site, scores every page, and
            composes a modern SharePoint replica — held to{" "}
            <span className="text-heading">1.00 copy fidelity</span> by a verify
            gate no agent can cheat.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3 lg:justify-start">
            <Button href="/sandbox" variant="gradient">
              Watch the full rebuild replay →
            </Button>
            <Button href="#pipeline" variant="ghost">
              See the 13 stages
            </Button>
          </div>
        </div>

        {/* Right: framed browser-style mockup of the modern rebuild */}
        <div className="relative mx-auto w-full max-w-[560px] lg:mx-0">
          <div className="overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface shadow-elevated">
            {/* window chrome */}
            <div className="flex items-center gap-2 border-b border-border bg-surface-muted px-4 py-3">
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: "var(--accent-ruby)" }}
              />
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: "var(--warn)" }}
              />
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: "var(--success)" }}
              />
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/crestfield/after-home.png"
              alt="A modern SharePoint communication site rebuilt by the SPARK pipeline"
              className="block w-full"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
