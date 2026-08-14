export const BASE_PATH = "/free-repetition-band";

export const CHAPTERS = [
  { href: "/", id: "band", roman: "I", label: "Band" },
  { href: "/onset/", id: "onset", roman: "II", label: "Onset" },
  { href: "/capacity/", id: "capacity", roman: "III", label: "Capacity" },
  { href: "/exposure/", id: "exposure", roman: "IV", label: "Exposure" },
  { href: "/scale/", id: "scale", roman: "V", label: "Scale" },
  { href: "/reproduce/", id: "reproduce", roman: "VI", label: "Reproduce-as-rebuild" },
] as const;

export const MATERIALS = {
  figuresJson: "data/figures.json",
  scaleBand: "E1_scale_band",
  repeat: "E1_repeat",
  capxl: "E1_capxl",
  exposure: "E1_exposure_control",
} as const;

export const ZENODO = "10.5281/zenodo.21020378";
export const GITHUB = "https://github.com/PeterPonyu/free-repetition-band";
