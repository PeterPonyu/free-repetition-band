import { StratumChapter } from "../StratumChapter";
import { MATERIALS } from "../../lib/site";

export default function ScalePage() {
  return (
    <StratumChapter kicker="Scale" title="Scale">
      <p>
        Scale overlay. The same free unit on landscape and real-byte strata.
      </p>
      <dl className="field-notes">
        <div>
          <dt>Object</dt>
          <dd>Scale invariance of the free-repetition band.</dd>
        </div>
        <div>
          <dt>Material</dt>
          <dd>
            <code>{MATERIALS.scaleBand}</code>
          </dd>
        </div>
      </dl>
    </StratumChapter>
  );
}
