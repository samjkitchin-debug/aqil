import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Aqil",
    template: "%s · Aqil",
  },
  description:
    "Human-centred investment intelligence and long-term wealth-building.",
  applicationName: "Aqil",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "Aqil",
    statusBarStyle: "default",
  },
  icons: {
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en-GB" className="h-full">
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
