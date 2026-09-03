import type { Metadata, Viewport } from "next";
import { Hanken_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const hanken = Hanken_Grotesk({
  subsets: ["latin"],
  variable: "--font-hanken",
  display: "swap",
});

const plex = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BizPilot AI — Decision intelligence for your business",
  description:
    "BizPilot AI turns your sales and inventory data into forecasts, anomaly alerts, and grounded, actionable recommendations.",
};

export const viewport: Viewport = {
  themeColor: "#f6f5f1",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${hanken.variable} ${plex.variable}`}>
      <body>{children}</body>
    </html>
  );
}