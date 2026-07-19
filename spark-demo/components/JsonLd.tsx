const SITE_URL = "https://spark-demo.codeandcraft.ai";

const graph = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "SoftwareApplication",
      name: "SPARK v1 — SharePoint Autonomous Rebuild Kit",
      applicationCategory: "BusinessApplication",
      operatingSystem: "Web",
      url: SITE_URL,
      description:
        "An autonomous multi-agent pipeline that rebuilds legacy classic SharePoint intranets into modern SharePoint, with a fail-closed verify gate held to 1.00 copy fidelity.",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
        description: "Live interactive demo",
      },
      creator: {
        "@type": "Person",
        name: "Sukaimi Sukri",
      },
      publisher: {
        "@type": "Organization",
        name: "Code & Craft",
      },
    },
    {
      "@type": "Organization",
      name: "Code & Craft",
      url: SITE_URL,
      parentOrganization: {
        "@type": "Organization",
        name: "Code & Canvas",
        url: "https://codeandcanvas.io",
      },
    },
    {
      "@type": "Person",
      name: "Sukaimi Sukri",
      jobTitle: "Founder",
      worksFor: {
        "@type": "Organization",
        name: "Code & Craft",
      },
    },
  ],
};

export default function JsonLd() {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }}
    />
  );
}
