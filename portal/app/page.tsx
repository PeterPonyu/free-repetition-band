import { FieldGuide } from "./FieldGuide";
import { StratumPlate } from "./StratumPlate";
import { WarehouseFooter } from "./WarehouseFooter";
import { POINTERS } from "../lib/site";

export default function BandPage() {
  return (
    <FieldGuide>
      <div className="screen-band">
        <header className="masthead">
          <p className="running">Plate I · Band · PeterPonyu/free-repetition-band</p>
          <h1>
            Field <em>guide</em>
          </h1>
          <p className="lede">
            A door to the warehouse figure index. Chapters name scientific
            structure. Plates cite summary filenames, not findings.
          </p>
        </header>

        <div className="opening">
          <StratumPlate />
          <section className="species-plate diagnosis" aria-label="Plate I Band">
            <p className="plate-kicker">Plate I · Band</p>
            <h2>Stratum</h2>
            <dl className="field-notes">
              <div>
                <dt>Chapter</dt>
                <dd>Band — opening plate of the field guide.</dd>
              </div>
              <div>
                <dt>Pointer</dt>
                <dd>
                  <code>{POINTERS.scaleBand}</code> ·{" "}
                  <code>{POINTERS.scaleBandJson}</code>
                </dd>
              </div>
              <div>
                <dt>Index</dt>
                <dd>
                  <code>{POINTERS.index}</code> (copied to{" "}
                  <code>{POINTERS.figuresJson}</code>)
                </dd>
              </div>
              <div>
                <dt>Rebuild</dt>
                <dd>
                  <code>{POINTERS.pipeline}</code>
                </dd>
              </div>
            </dl>
          </section>
        </div>

        <section className="species-plate peek" aria-label="Plate II peek">
          <p className="plate-kicker">Plate II · Onset — next chapter</p>
          <p className="peek-body">
            Pointer: <code>{POINTERS.repeatJson}</code>.
          </p>
        </section>

        <WarehouseFooter />
      </div>
    </FieldGuide>
  );
}
