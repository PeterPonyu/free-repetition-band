import { bedFor } from "../lib/science";

export function BedField({ chapter }: { chapter: string }) {
  const bed = bedFor(chapter);
  if (!bed) {
    return (
      <p className="index-status">
        Stratum bed missing — rebuild from the clone.
      </p>
    );
  }

  return (
    <div className="bed-field">
      <dl className="field-notes">
        <div>
          <dt>Object</dt>
          <dd>{bed.object}</dd>
        </div>
        {bed.layers.length > 0 ? (
          <div>
            <dt>Layers</dt>
            <dd>
              <ol className="layer-list">
                {bed.layers.map((layer) => (
                  <li key={layer}>{layer}</li>
                ))}
              </ol>
            </dd>
          </div>
        ) : null}
      </dl>
      {bed.asks.length > 0 ? (
        <ol className="ask-list" aria-label={`${bed.title} asks`}>
          {bed.asks.map((ask) => (
            <li key={ask}>{ask}</li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
