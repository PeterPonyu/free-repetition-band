import type { Metadata } from "next";

import { atkinson, fraunces } from "./fonts";
import "./globals.css";

export const metadata: Metadata = {
  title: "Free-repetition band — epoch stratum field",
  description:
    "Epoch stratum field for the free-repetition band: Band, Onset, Capacity, Exposure, Scale, Reproduce-as-rebuild.",
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
