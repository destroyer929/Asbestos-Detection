import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DrawingScan | AI Asbestos Identification in Engineering Drawings",
  description:
    "Automated bilingual OCR, Finish Schedule table parsing, and 4-tier MLIT regulatory cross-matching for Alfred Company Ltd. (Hamamatsu, Japan).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full bg-slate-950 text-slate-100 antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 font-sans">
        {children}
      </body>
    </html>
  );
}
