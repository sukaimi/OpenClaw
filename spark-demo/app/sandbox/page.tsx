import type { Metadata } from "next";
import SandboxApp from "@/components/sandbox/SandboxApp";

export const metadata: Metadata = {
  title: "Sandbox — SPARK v1",
  description:
    "Interactive canned replay of a real classic→modern SharePoint rebuild — no live SharePoint, no credentials.",
};

export default function SandboxPage() {
  return <SandboxApp />;
}
