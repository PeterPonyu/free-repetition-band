import { BedField } from "../BedField";
import { StratumChapter } from "../StratumChapter";

export default function CapacityPage() {
  return (
    <StratumChapter kicker="Capacity" title="Capacity">
      <p>
        Capacity–entropy bed. Asks whether the free unit is a capacity artifact
        when width and entropy change.
      </p>
      <BedField chapter="capacity" />
    </StratumChapter>
  );
}
