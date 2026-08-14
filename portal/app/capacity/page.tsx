import { FieldGuide } from "../FieldGuide";
import { WarehouseFooter } from "../WarehouseFooter";
import { POINTERS } from "../../lib/site";

export default function CapacityPage() {
  return (
    <FieldGuide>
      <section
        className="species-plate chapter-plate"
        aria-label="Plate III Capacity"
      >
        <p className="plate-kicker">Plate III · Capacity</p>
        <h2>Capacity</h2>
        <p>
          Chapter plate. Pointer: <code>{POINTERS.capxl}</code> ·{" "}
          <code>{POINTERS.capxlJson}</code> via <code>{POINTERS.index}</code>.
        </p>
        <dl className="field-notes">
          <div>
            <dt>Material</dt>
            <dd>
              <code>{POINTERS.capxl}</code>
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
