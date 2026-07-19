export type Agent = {
  id: string;
  role: string;
  profile: string;
  special?: boolean;
};

export const agents: Agent[] = [
  {
    id: "cc-intake",
    role: "Intake Clerk",
    profile:
      "Opens the job, parses the client request, and locks the run scope.",
  },
  {
    id: "cc-preflight-sp",
    role: "Gatekeeper",
    profile:
      "Verifies read access to the source and write access to the target before anything runs.",
  },
  {
    id: "cc-sp-capture",
    role: "Scout",
    profile:
      "Crawls the classic site and snapshots every page, zone, and asset.",
  },
  {
    id: "cc-sp-audit",
    role: "Auditor",
    profile:
      "Classifies every asset, flags broken links and low-res images, logs pain-points.",
  },
  {
    id: "cc-sp-score",
    role: "Strategist",
    profile:
      "Scores pages by reach and freshness, then tiers them so the important ones rebuild first.",
  },
  {
    id: "cc-notify-operator",
    role: "Liaison",
    profile: "Posts the tiered plan to Teams and waits for the operator's go-ahead.",
  },
  {
    id: "cc-sp-assets",
    role: "Image Handler",
    profile:
      "Migrates usable images and flags low-res ones for rewrite or SVG swap.",
  },
  {
    id: "cc-sp-mirror",
    role: "Builder",
    profile:
      "Rebuilds interior pages and the homepage as modern web parts via Microsoft Graph.",
  },
  {
    id: "cc-sp-theme",
    role: "Stylist",
    profile: "Applies the theme, fonts, wallpaper, and brand voice.",
  },
  {
    id: "cc-verify-sp",
    role: "Inspector",
    profile:
      "The fail-closed gate: diffs built pages against source and demands copy fidelity 1.00. No agent can self-approve.",
    special: true,
  },
  {
    id: "cc-sp-tracker",
    role: "Registrar",
    profile:
      "Stamps final migration status and exports the 3-sheet tracker workbook.",
  },
  {
    id: "cc-notify-closed",
    role: "Closer",
    profile:
      "Delivers the handover report, pings the operator, and closes the job.",
  },
];
