import type { ReactNode } from "react";

import { FieldFooter } from "./FieldFooter";
import { FieldGuide } from "./FieldGuide";

export function StratumChapter({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <FieldGuide>
      <section className="species-plate chapter-plate" aria-label={title}>
        <p className="plate-kicker">{kicker}</p>
        <h2>{title}</h2>
        {children}
        <FieldFooter />
      </section>
    </FieldGuide>
  );
}
