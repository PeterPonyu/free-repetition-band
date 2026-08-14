import { StratumChapter } from "../StratumChapter";
import { MATERIALS } from "../../lib/site";

export default function ExposurePage() {
  return (
    <StratumChapter kicker="Exposure" title="Exposure">
      <p>
        Exposure-matched bed. Asks whether the free unit holds when exposure is
        controlled.
      </p>
      <dl className="field-notes">
        <div>
          <dt>Object</dt>
          <dd>Exposure control of the free-repetition band.</dd>
        </div>
        <div>
          <dt>Material</dt>
          <dd>
            <code>{MATERIALS.exposure}</code>
          </dd>
        </div>
      </dl>
    </StratumChapter>
  );
}
