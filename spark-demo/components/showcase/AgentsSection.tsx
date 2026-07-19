import { agents, type Agent } from "@/components/showcase/agents";

function AgentCard({ agent }: { agent: Agent }) {
  const special = agent.special;
  return (
    <div
      className={`flex flex-col rounded-[var(--radius-lg)] border p-5 ${
        special
          ? "border-primary/50 bg-primary/[0.04] shadow-card ring-1 ring-primary/25"
          : "border-border bg-surface shadow-card"
      }`}
    >
      {special ? (
        <div className="flex items-center justify-end gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-[var(--radius-sm)] bg-primary/10 px-2 py-0.5 text-[11px] font-normal text-primary ring-1 ring-primary/30">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            verify gate
          </span>
        </div>
      ) : null}
      <h3 className="mt-3 text-[17px] font-semibold leading-tight tracking-[-0.01em] text-heading">
        {agent.role}
      </h3>
      <p className="mt-2 flex-1 text-[14px] leading-[1.45] text-body">
        {agent.profile}
      </p>
    </div>
  );
}

export default function AgentsSection() {
  return (
    <section id="agents" className="scroll-mt-24 py-20">
      <div className="mx-auto max-w-[640px] text-center">
        <p className="text-[13px] font-normal uppercase tracking-[0.14em] text-primary">
          The agents
        </p>
        <h2 className="mt-3 text-[clamp(1.75rem,4vw,2.5rem)] font-light leading-[1.1] tracking-[-0.02em] text-heading">
          Twelve specialists, one assembly line
        </h2>
        <p className="mt-4 text-[16px] leading-[1.5] text-body">
          Twelve agents across thirteen stages — the Builder runs two. Every
          stage has a dedicated owner, and no agent can self-approve its own
          work.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-2 gap-4 sm:gap-5 md:grid-cols-3 lg:grid-cols-4">
        {agents.map((agent) => (
          <AgentCard key={agent.role} agent={agent} />
        ))}
      </div>
    </section>
  );
}
