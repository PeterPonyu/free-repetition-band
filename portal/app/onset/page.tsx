import { StratumChapter } from "../StratumChapter";
import { MATERIALS } from "../../lib/site";

export default function OnsetPage() {
  return (
    <StratumChapter kicker="Onset" title="Onset">
      <p>
        Memorization onset. The free-repetition band as a first-appearance
        stratum, coincident across seeds — not a late capacity effect.
      </p>
      <dl className="field-notes">
        <div>
          <dt>Object</dt>
          <dd>Onset coincidence of the free unit.</dd>
        </div>
        <div>
          <dt>Material</dt>
          <dd>
            <code>{MATERIALS.repeat}</code>
          </dd>
        </div>
      </dl>
    </StratumChapter>
  );
}
