import { GITHUB, ZENODO } from "../lib/site";

export function FieldFooter() {
  return (
    <footer className="provenance">
      <p>
        Concept DOI{" "}
        <a href={`https://doi.org/${ZENODO}`}>{ZENODO}</a>
        {" · "}
        <a href={GITHUB}>github.com/PeterPonyu/free-repetition-band</a>
        {" · "}
        MIT (code) / CC BY 4.0 (data and figures)
      </p>
    </footer>
  );
}
