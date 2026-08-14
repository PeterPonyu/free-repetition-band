import figures from "../public/data/figures.json";

export type StratumBed = {
  chapter: string;
  title: string;
  object: string;
  layers: string[];
  asks: string[];
};

type ScienceIndex = {
  github?: string;
  zenodo_concept_doi?: string;
  beds?: StratumBed[];
};

const index = figures as ScienceIndex;

export function allBeds(): StratumBed[] {
  return Array.isArray(index.beds) ? index.beds : [];
}

export function bedFor(chapter: string): StratumBed | undefined {
  return allBeds().find((bed) => bed.chapter === chapter);
}

export function bedCount(): number {
  return allBeds().length;
}
