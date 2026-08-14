import { BedField } from "./BedField";
import { FieldFooter } from "./FieldFooter";
import { FieldGuide } from "./FieldGuide";
import { StratumPlate } from "./StratumPlate";
import { bedFor } from "../lib/science";

export default function BandPage() {
  const onset = bedFor("onset");

  return (
    <FieldGuide>
      <div className="screen-band">
        <header className="masthead">
          <p className="running">Band · free-repetition · epoch stratum</p>
          <h1>
            Free-repetition <em>band</em>
          </h1>
          <p className="lede">
            The free-repetition band is an epoch stratum: a free unit between
            the unique-data floor and the overburden of diminishing returns.
          </p>
        </header>

        <div className="opening">
          <StratumPlate />
          <section className="species-plate diagnosis" aria-label="Band">
            <p className="plate-kicker">Band</p>
            <h2>Stratum</h2>
            <BedField chapter="band" />
          </section>
        </div>

        <section className="species-plate peek" aria-label="Onset peek">
          <p className="plate-kicker">Onset — next stratum</p>
          <p className="peek-body">
            {onset?.asks[0] ??
              "Memorization onset asks when the free unit first appears as a coincident bed."}
          </p>
        </section>

        <FieldFooter />
      </div>
    </FieldGuide>
  );
}
