import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SentinelFlow AI - Autonomous SecOps Monitor",
  description: "AI-powered automated Kubernetes incident response and safety envelope guardrails",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="bg-[#0a0e17] text-[#e2e8f0] min-h-screen">
        {children}
      </body>
    </html>
  );
}
