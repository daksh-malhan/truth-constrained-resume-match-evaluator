import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Truth-Constrained Resume Match Evaluator",
  description: "Evidence-based resume-job matching with RAG, citations, partial scoring, and truth-constrained projected improvements."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

