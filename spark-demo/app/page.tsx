import Button from "@/components/Button";
import Hero from "@/components/showcase/Hero";
import ProblemSection from "@/components/showcase/ProblemSection";
import BeforeAfterSlider from "@/components/showcase/BeforeAfterSlider";
import ProofPanel from "@/components/showcase/ProofPanel";
import PipelineFlow from "@/components/showcase/PipelineFlow";
import AgentsSection from "@/components/showcase/AgentsSection";
import KitCards from "@/components/showcase/KitCards";
import StatsBand from "@/components/showcase/StatsBand";
import FounderNote from "@/components/showcase/FounderNote";

export default function Home() {
  return (
    <div className="mx-auto max-w-[1080px] px-5">
      <Hero />

      <ProblemSection />

      {/* Before / After */}
      <section className="py-8">
        <div className="mx-auto max-w-[640px] text-center">
          <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
            Before / after
          </p>
          <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
            Drag to see the rebuild
          </h2>
        </div>
        <div className="mx-auto mt-10 max-w-[960px]">
          <BeforeAfterSlider
            before="/crestfield/before-home.png"
            after="/crestfield/after-home.png"
            caption="A real SPARK rebuild. The sample org &lsquo;Crestfield Foods&rsquo; is fictional — the classic→modern transformation is exactly what the pipeline produced, reproducible with zero credentials."
          />
        </div>
      </section>

      <ProofPanel />

      <PipelineFlow />

      <AgentsSection />

      <KitCards />

      <StatsBand />

      <FounderNote />

      {/* Final CTA */}
      <section className="py-24 text-center">
        <div className="relative overflow-hidden rounded-[var(--radius-lg)] border border-border bg-surface px-6 py-16 shadow-elevated">
          <div
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[320px] w-[640px] max-w-full -translate-x-1/2 rounded-full spark-gradient-bg opacity-15 blur-3xl"
          />
          <h2 className="mx-auto max-w-[560px] text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
            See the pipeline run, stage by stage.
          </h2>
          <p className="mx-auto mt-4 max-w-[520px] text-[17px] leading-[1.45] text-body">
            Replay the full autonomous rebuild — capture, score, compose, and
            the fail-closed verify gate — in the live sandbox.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button href="/sandbox" variant="gradient">
              Try the sandbox →
            </Button>
            <Button
              href="https://github.com/sukaimi/OpenClaw"
              variant="ghost"
              target="_blank"
              rel="noopener noreferrer"
            >
              View the source on GitHub →
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
