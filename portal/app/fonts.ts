import { Atkinson_Hyperlegible, Fraunces } from "next/font/google";

export const fraunces = Fraunces({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["400", "600"],
  style: ["normal", "italic"],
});

export const atkinson = Atkinson_Hyperlegible({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body",
  weight: ["400", "700"],
  style: ["normal", "italic"],
});
