import type { Metadata } from "next";
import Button from "@/components/Button";
import Card from "@/components/Card";

export const metadata: Metadata = {
  title: "Sandbox — SPARK v1",
  description: "Interactive sandbox for the SharePoint Autonomous Rebuild Kit.",
};

export default function Sandbox() {
  return (
    <div className="mx-auto max-w-[1080px] px-5 py-24">
      <div className="mx-auto max-w-[640px] text-center">
        <span className="text-[13px] uppercase tracking-[0.12em] text-body">
          Sandbox
        </span>
        <h1 className="mt-3 text-[clamp(2rem,5vw,3rem)] font-light leading-[1.1] tracking-[-0.03em] text-heading">
          Interactive sandbox{" "}
          <span className="spark-gradient-text">coming</span>
        </h1>
        <p className="mx-auto mt-5 max-w-[480px] text-[18px] leading-[1.4] text-body">
          This is where you&apos;ll paste a classic SharePoint URL and watch
          SPARK rebuild it live. The interactive flow lands in a later phase.
        </p>
      </div>

      <Card elevated className="mx-auto mt-12 max-w-[720px]">
        <div className="flex flex-col items-center justify-center gap-4 rounded-[var(--radius-md)] border border-dashed border-border-strong px-6 py-16 text-center">
          <span className="spark-gradient-bg inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] text-[22px] text-white">
            ⚡
          </span>
          <p className="text-[16px] text-body">
            Sandbox controls will appear here.
          </p>
          <Button href="/" variant="ghost">
            Back to Showcase
          </Button>
        </div>
      </Card>
    </div>
  );
}
