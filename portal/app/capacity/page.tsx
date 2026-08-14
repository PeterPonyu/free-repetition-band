import { StratumChapter } from "../StratumChapter";
import { MATERIALS } from "../../lib/site";

export default function CapacityPage() {
  return (
    <StratumChapter kicker="Capacity" title="Capacity">
      <p>
        Capacity–entropy bed. Asks whether the free unit is a capacity artifact
        when width and entropy change.
      </p>
      <dl className="field-notes">
        <div>
          <dt>Object</dt>
          <dd>Capacity–entropy test of the free-repetition band.</dd>
        </div>
        <div>
          <dt>Material</dt>
          <dd>
            <code>{MATERIALS.capxl}</code>
          </dd>
        </div>
      </dl>
    </StratumChapter>
  );
}
