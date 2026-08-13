import type { Metadata } from "next";

import { atkinson, fraunces } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "Field guide — PeterPonyu/free-repetition-band",
  description:
    "Warehouse door: chapter structure and figure-index pointers. No journal PDFs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${fraunces.variable} ${atkinson.variable}`}>
      <body>{children}</body>
    </html>
  );
}
