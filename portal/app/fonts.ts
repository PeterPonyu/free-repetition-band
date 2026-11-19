import localFont from "next/font/local";

// Self-hosted type pair (OFL-1.1; license texts live beside the files).
// woff2 files are committed so the build never fetches fonts from the network.
export const fraunces = localFont({
  src: [
    {
      path: "./fonts/fraunces-latin-400-normal.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "./fonts/fraunces-latin-600-normal.woff2",
      weight: "600",
      style: "normal",
    },
    {
      path: "./fonts/fraunces-latin-400-italic.woff2",
      weight: "400",
      style: "italic",
    },
    {
      path: "./fonts/fraunces-latin-600-italic.woff2",
      weight: "600",
      style: "italic",
    },
  ],
  display: "swap",
  variable: "--font-display",
});

export const atkinson = localFont({
  src: [
    {
      path: "./fonts/atkinson-hyperlegible-latin-400-normal.woff2",
      weight: "400",
      style: "normal",
    },
    {
      path: "./fonts/atkinson-hyperlegible-latin-700-normal.woff2",
      weight: "700",
      style: "normal",
    },
    {
      path: "./fonts/atkinson-hyperlegible-latin-400-italic.woff2",
      weight: "400",
      style: "italic",
    },
    {
      path: "./fonts/atkinson-hyperlegible-latin-700-italic.woff2",
      weight: "700",
      style: "italic",
    },
  ],
  display: "swap",
  variable: "--font-body",
});
