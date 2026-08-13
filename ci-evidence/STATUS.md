# E1 warehouse CI evidence (PeterPonyu/free-repetition-band)

- **Remote:** https://github.com/PeterPonyu/free-repetition-band
- **Default branch:** `main` (unprotected; this work is on `ci/comprehensive`, not merged)
- **Pages:** not enabled (`gh api repos/PeterPonyu/free-repetition-band/pages` → 404)
- **TDD:** `ci-evidence/RED.log` (tests before stubs) → `ci-evidence/GREEN.log` (39 passed)

## Workflows

| Path | Jobs | Required? | Notes |
|---|---|---|---|
| `.github/workflows/ci.yml` | `required-contract-tests` | **required** | pytest + `portal/build.sh` |
| `.github/workflows/pages.yml` | `validate-and-copy` (runs) / `deploy` (`if: false`) | sketch; deploy optional/gated | path filters; `pages: write` + `github-pages` env declared; **does not enable Pages** |
| `.github/workflows/visual-pixel.yml` | `visual-ralph-pixel` (`if: false`) | **optional / gated** | must not fail required CI until `reference.png` is approved |

## Local verification

```
python3 -m pytest tests   # 39 passed
bash portal/build.sh      # copy+validate; no TeX
```
