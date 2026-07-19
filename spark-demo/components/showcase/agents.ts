export type Agent = {
  role: string;
  profile: string;
  special?: boolean;
};

export const agents: Agent[] = [
  {
    role: "Intake Clerk",
    profile:
      "Opens the job, parses the client request, and locks the run scope.",
  },
  {
    role: "Gatekeeper",
    profile:
      "Verifies read access to the source and write access to the target before anything runs.",
  },
  {
    role: "Scout",
    profile:
      "Crawls the classic site and snapshots every page, zone, and asset.",
  },
  {
    role: "Auditor",
    profile:
      "Classifies every asset, flags broken links and low-res images, logs pain-points.",
  },
  {
    role: "Strategist",
    profile:
      "Scores pages by reach and freshness, then tiers them so the important ones rebuild first.",
  },
  {
    role: "Liaison",
    profile: "Posts the tiered plan to Teams and waits for the operator's go-ahead.",
  },
  {
    role: "Image Handler",
    profile:
      "Migrates usable images and flags low-res ones for rewrite or SVG swap.",
  },
  {
    role: "Builder",
    profile:
      "Rebuilds interior pages and the homepage as modern web parts via Microsoft Graph.",
  },
  {
    role: "Stylist",
    profile: "Applies the theme, fonts, wallpaper, and brand voice.",
  },
  {
    role: "Inspector",
    profile:
      "The fail-closed gate: diffs built pages against source and demands copy fidelity 1.00. No agent can self-approve.",
    special: true,
  },
  {
    role: "Registrar",
    profile:
      "Stamps final migration status and exports the 3-sheet tracker workbook.",
  },
  {
    role: "Closer",
    profile:
      "Delivers the handover report, pings the operator, and closes the job.",
  },
];
