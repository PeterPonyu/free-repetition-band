import figures from "../../public/data/figures.json";
import { StratumChapter } from "../StratumChapter";
import { GITHUB, MATERIALS, ZENODO } from "../../lib/site";

type StratumIndex = {
  figures?: { id: string }[];
};

const index = figures as StratumIndex;
const bedCount = (index.figures || []).length;

export default function ReproducePage() {
  return (
    <StratumChapter kicker="Reproduce-as-rebuild" title="Reproduce-as-rebuild">
      <p>
        Rebuild the stratum from committed runners and per-run logs. Clone,
        seed, rerun. The door does not host compiled binaries.
      </p>
      <dl className="field-notes">
        <div>
          <dt>Clone</dt>
          <dd>
            <a href={GITHUB}>{GITHUB}</a>
          </dd>
        </div>
        <div>
          <dt>Materials</dt>
          <dd>
            <code>{MATERIALS.scaleBand}</code> / <code>{MATERIALS.repeat}</code>{" "}
            / <code>{MATERIALS.capxl}</code>
          </dd>
        </div>
        <div>
          <dt>Deposit</dt>
          <dd>
            Concept <a href={`https://doi.org/${ZENODO}`}>{ZENODO}</a>
          </dd>
        </div>
        <div>
          <dt>License</dt>
          <dd>MIT (code) / CC BY 4.0 (data and figures)</dd>
        </div>
      </dl>
      <p className="index-status">
        {bedCount
          ? `stratum index ready · ${bedCount} beds`
          : "stratum index missing — rebuild from the clone"}
      </p>
    </StratumChapter>
  );
}
