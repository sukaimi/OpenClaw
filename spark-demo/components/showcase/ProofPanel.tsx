import Card from "@/components/Card";
import Button from "@/components/Button";
import jobSummary from "@/fixtures/job-summary.json";

const jobId = jobSummary.jobId;
const copyFidelity = jobSummary.verdict.copyFidelity;
const pagesMatched = jobSummary.pages.composed;

export default function ProofPanel() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-[640px] text-center">
        <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
          The proof
        </p>
        <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
          Verified, not claimed.
        </h2>
      </div>

      <div className="mx-auto mt-12 max-w-[720px]">
        <Card elevated className="relative overflow-hidden text-center">
          <div
            aria-hidden
            style={{ opacity: "var(--hero-glow-opacity)" }}
            className="pointer-events-none absolute left-1/2 top-0 -z-10 h-[220px] w-[520px] max-w-full -translate-x-1/2 rounded-full spark-gradient-bg blur-3xl"
          />

          <span className="inline-flex items-center gap-2 rounded-[var(--radius-sm)] bg-primary/10 px-2.5 py-1 text-[11px] font-normal text-primary ring-1 ring-primary/30">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            verify gate · PASS
          </span>

          <p className="mt-5 text-[clamp(1.75rem,4.5vw,2.5rem)] font-light leading-none tracking-[-0.02em] text-heading">
            <span className="font-mono text-[0.7em] tracking-tight text-body">
              {jobId}
            </span>
            <span className="mx-3 text-border-strong">·</span>
            copy fidelity{" "}
            <span className="spark-gradient-text [font-feature-settings:'tnum']">
              {copyFidelity}
            </span>
          </p>

          <p className="mt-4 text-[15px] leading-[1.5] text-label [font-feature-settings:'tnum']">
            {pagesMatched}/{pagesMatched} pages matched · 0 missing zones · 0
            dropped assets
          </p>

          <p className="mx-auto mt-6 max-w-[520px] text-[16px] leading-[1.55] text-body">
            The fail-closed verify gate diffed every rebuilt page against the
            source and opened only on a full content match.
          </p>

          <div className="mt-8 flex justify-center">
            <Button href="/sandbox" variant="ghost">
              Replay the full evidence in the sandbox →
            </Button>
          </div>
        </Card>
      </div>
    </section>
  );
}
