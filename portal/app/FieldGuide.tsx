import type { ReactNode } from "react";

import { ChapterNav } from "./ChapterNav";

export function FieldGuide({ children }: { children: ReactNode }) {
  return (
    <article
      className="field-guide"
      data-ia="field-guide"
      data-layout="field-guide"
    >
      <ChapterNav />
      <div className="folio">{children}</div>
    </article>
  );
}
