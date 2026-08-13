import { FieldGuide } from "../FieldGuide";
import { WarehouseFooter } from "../WarehouseFooter";
import { POINTERS } from "../../lib/site";

export default function ScalePage() {
  return (
    <FieldGuide>
      <section className="species-plate chapter-plate" aria-label="Plate V Scale">
        <p className="plate-kicker">Plate V · Scale</p>
        <h2>Scale</h2>
        <p>
          Chapter plate. Pointer: <code>{POINTERS.scaleBand}</code> ·{" "}
          <code>{POINTERS.scaleBandJson}</code> via <code>{POINTERS.index}</code>.
        </p>
        <dl className="field-notes">
          <div>
            <dt>Material</dt>
            <dd>
              <code>{POINTERS.scaleBand}</code>
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
