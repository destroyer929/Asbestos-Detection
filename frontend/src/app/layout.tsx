import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alfred | Asbestos Analysis & Blueprint Diagnostics Platform",
  description:
    "Built on Japanese Precision. Reimagined for India. Automated MLIT / JIS A 1481 compliance, PaddleOCR CJK extraction, and Tier-5 LLM regulatory arbitration for Alfred Co., Ltd.",
  icons: {
    icon: "/brand/bird.png",
    shortcut: "/brand/bird.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-[#f7fbf6] text-slate-800 antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col bg-[#f7fbf6] text-slate-800 font-sans">
        {children}
      </body>
    </html>
  );
}
