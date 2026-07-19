import { ImageResponse } from "next/og";

export const alt =
  "SPARK v1 — twelve AI agents rebuild your classic SharePoint";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#0a1224",
          position: "relative",
          fontFamily: "sans-serif",
        }}
      >
        {/* soft brand-gradient glow */}
        <div
          style={{
            position: "absolute",
            top: "-260px",
            right: "-200px",
            width: "760px",
            height: "760px",
            borderRadius: "9999px",
            background:
              "radial-gradient(circle at center, rgba(109,91,255,0.55), rgba(34,211,238,0.18) 45%, rgba(10,18,36,0) 70%)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-300px",
            left: "-160px",
            width: "620px",
            height: "620px",
            borderRadius: "9999px",
            background:
              "radial-gradient(circle at center, rgba(83,58,253,0.4), rgba(10,18,36,0) 70%)",
          }}
        />

        {/* monogram */}
        <div style={{ display: "flex" }}>
          <div
            style={{
              width: "112px",
              height: "112px",
              borderRadius: "28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background:
                "linear-gradient(135deg, #533afd 0%, #6d5bff 50%, #22d3ee 100%)",
              color: "#ffffff",
              fontSize: "72px",
              fontWeight: 700,
            }}
          >
            S
          </div>
        </div>

        {/* headline + subline */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              color: "#ffffff",
              fontSize: "64px",
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-1px",
              maxWidth: "1000px",
            }}
          >
            Twelve AI agents rebuild your classic SharePoint.
          </div>
          <div
            style={{
              marginTop: "28px",
              color: "#9fb0d0",
              fontSize: "30px",
              fontWeight: 400,
            }}
          >
            Autonomous SharePoint modernization · fail-closed verify gate · 1.00
            copy fidelity
          </div>
        </div>

        {/* footer url */}
        <div
          style={{
            display: "flex",
            color: "#6d7a99",
            fontSize: "24px",
            fontWeight: 500,
          }}
        >
          spark-demo.codeandcraft.ai
        </div>
      </div>
    ),
    { ...size }
  );
}
