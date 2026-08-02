# CI Configs

These JSON configs are designed to run in the CI pipeline (`.github/workflows/process.yml`)
using paths relative to the repo root. They mirror the example configs in `src/`
but with adjusted paths for the `ubuntu-latest` runner working directory.

| File | Pipeline Stage | Based On |
|---|---|---|
| `preprocess-covid19.json` | `preprocess` job | `src/preprocesador/preprocesador_example_covid19.json` |
| `process-covid19.json` | `process` job | `src/procesador/procesador_example_covid19.json` |
