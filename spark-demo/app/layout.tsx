import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import JsonLd from "@/components/JsonLd";

const SITE_URL = "https://spark-demo.codeandcraft.ai";
const TITLE = "SPARK v1 — SharePoint Autonomous Rebuild Kit";
const DESCRIPTION =
  "An autonomous multi-agent pipeline that rebuilds legacy classic SharePoint intranets into modern SharePoint — with a fail-closed verify gate held to 1.00 copy fidelity. Live demo.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE,
    template: "%s · SPARK v1",
  },
  description: DESCRIPTION,
  applicationName: "SPARK v1",
  authors: [{ name: "Sukaimi Sukri" }],
  creator: "Sukaimi Sukri",
  keywords: [
    "classic SharePoint migration",
    "SharePoint modernization",
    "intranet migration",
    "autonomous AI agents",
    "SharePoint intranet rebuild",
    "Microsoft SharePoint",
    "agentic automation",
  ],
  alternates: {
    canonical: "/",
  },
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "SPARK v1",
    title: TITLE,
    description: DESCRIPTION,
    locale: "en_US",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "SPARK v1 — twelve AI agents rebuild your classic SharePoint",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/twitter-image"],
  },
};

// Runs before paint to apply the persisted theme and avoid a flash of
// the wrong color scheme. No network, no dependencies — inline only.
const themeScript = `
(function () {
  try {
    var t = localStorage.getItem('spark-theme');
    document.documentElement.setAttribute('data-theme', t === 'light' ? 'light' : 'dark');
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-full flex-col">
        <JsonLd />
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
