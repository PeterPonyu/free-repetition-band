"use client";

import { useEffect, useState } from "react";

import { FieldGuide } from "../FieldGuide";
import { WarehouseFooter } from "../WarehouseFooter";
import { BASE_PATH, GITHUB, POINTERS, ZENODO } from "../../lib/site";

export default function ReproducePage() {
  const [status, setStatus] = useState("loading FIGURE-INDEX…");

  useEffect(() => {
    fetch(`${BASE_PATH}/data/figures.json`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("missing");
        }
        return response.json();
      })
      .then((index: { figures?: { id: string }[] }) => {
        const ids = (index.figures || []).map((fig) => fig.id);
        setStatus(
          ids.length
            ? `FIGURE-INDEX loaded · ${ids.length} plates`
            : "summary missing — see PIPELINE.md",
        );
      })
      .catch(() => {
        setStatus("summary missing — see PIPELINE.md");
      });
  }, []);

  return (
    <FieldGuide>
      <section
        className="species-plate chapter-plate"
        aria-label="Plate VI Reproduce"
      >
        <p className="plate-kicker">Plate VI · Reproduce</p>
        <h2>Reproduce</h2>
        <p>
          This door reads <code>{POINTERS.index}</code> (copied to{" "}
          <code>{POINTERS.figuresJson}</code>). It does not host journal PDFs.
        </p>
        <dl className="field-notes">
          <div>
            <dt>Clone</dt>
            <dd>
              <a href={GITHUB}>{GITHUB}</a>
            </dd>
          </div>
          <div>
            <dt>Pipeline</dt>
            <dd>
              <code>{POINTERS.pipeline}</code>
            </dd>
          </div>
          <div>
            <dt>Index</dt>
            <dd>
              <code>{POINTERS.index}</code> · <code>{POINTERS.scaleBand}</code> /{" "}
              <code>{POINTERS.repeat}</code> / <code>{POINTERS.capxl}</code>
            </dd>
          </div>
          <div>
            <dt>Zenodo</dt>
            <dd>
              Concept <a href={`https://doi.org/${ZENODO}`}>{ZENODO}</a>
            </dd>
          </div>
          <div>
            <dt>License</dt>
            <dd>MIT (code) / CC BY 4.0 (data and figures)</dd>
          </div>
        </dl>
        <p className="index-status">{status}</p>
        <WarehouseFooter />
      </section>
    </FieldGuide>
  );
}
