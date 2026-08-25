export type Agent = {
  role: string;
  profile: string;
  special?: boolean;
};

export const agents: Agent[] = [
  {
    role: "Delivery Lead",
    profile:
      "Single entry point and orchestrator. Decomposes the job, sequences the team, runs the client gates, and delivers. The only seat that spawns other agents.",
  },
  {
    role: "Product Manager",
    profile:
      "Turns the request into a testable spec and runs the content audit, producing the migration tracker. Defines what and why, never how.",
  },
  {
    role: "Architect",
    profile:
      "Owns content architecture and technical design. Decides how it gets built — boring and proven over clever.",
  },
  {
    role: "UX Designer",
    profile:
      "Wireframes, then hi-fi designs as hosted, commentable previews. SharePoint-honest layouts only — nothing the platform can't actually render.",
  },
  {
    role: "SharePoint Engineer",
    profile:
      "Rebuilds pages and the homepage as modern native web parts via Microsoft Graph. Supervises the coding engine and owns the tests.",
  },
  {
    role: "Code Reviewer",
    profile:
      "Blocking internal quality gate. Reviews against the diff and returns approve or block — never a maybe.",
  },
  {
    role: "QA Engineer",
    profile:
      "The fail-closed gate: diffs every built page against the captured source and demands copy fidelity. No agent can self-approve.",
    special: true,
  },
  {
    role: "Security & Governance",
    profile:
      "Always-on gate across the whole run: M365 permissions, data governance, PDPA, and pre-ship package security.",
  },
  {
    role: "DevOps Deploy",
    profile:
      "Packages, deploys, and rolls back. Staging first, production only after sign-off. Reversible-first, least-privilege.",
  },
  {
    role: "Technical Writer",
    profile:
      "Turns the shipped site into runbooks, governance docs, and user guides — documenting what actually shipped, verified live.",
  },
];
