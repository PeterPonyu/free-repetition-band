import { BedField } from "../BedField";
import { StratumChapter } from "../StratumChapter";

export default function ExposurePage() {
  return (
    <StratumChapter kicker="Exposure" title="Exposure">
      <p>
        Exposure-matched bed. Asks whether the free unit holds when exposure is
        controlled.
      </p>
      <BedField chapter="exposure" />
    </StratumChapter>
  );
}
