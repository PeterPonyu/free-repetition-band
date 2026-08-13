import { FieldGuide } from "../FieldGuide";
import { WarehouseFooter } from "../WarehouseFooter";
import { POINTERS } from "../../lib/site";

export default function ExposurePage() {
  return (
    <FieldGuide>
      <section
        className="species-plate chapter-plate"
        aria-label="Plate IV Exposure"
      >
        <p className="plate-kicker">Plate IV · Exposure</p>
        <h2>Exposure</h2>
        <p>
          Chapter plate. Pointer: <code>E1_exposure_control</code> ·{" "}
          <code>figs/summaries/E1_exposure_control.json</code> via{" "}
          <code>{POINTERS.index}</code>.
        </p>
        <dl className="field-notes">
          <div>
            <dt>Material</dt>
            <dd>
              <code>E1_exposure_control</code>
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
