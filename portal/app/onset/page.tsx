import { FieldGuide } from "../FieldGuide";
import { WarehouseFooter } from "../WarehouseFooter";
import { POINTERS } from "../../lib/site";

export default function OnsetPage() {
  return (
    <FieldGuide>
      <section className="species-plate chapter-plate" aria-label="Plate II Onset">
        <p className="plate-kicker">Plate II · Onset</p>
        <h2>Onset</h2>
        <p>
          Chapter plate. Pointer: <code>{POINTERS.repeat}</code> ·{" "}
          <code>{POINTERS.repeatJson}</code> via <code>{POINTERS.index}</code>.
        </p>
        <dl className="field-notes">
          <div>
            <dt>Material</dt>
            <dd>
              <code>{POINTERS.repeat}</code>
            </dd>
          </div>
          <div>
            <dt>Rebuild</dt>
            <dd>
              <code>{POINTERS.pipeline}</code>
            </dd>
          </div>
        </dl>
        <WarehouseFooter />
      </section>
    </FieldGuide>
  );
}
