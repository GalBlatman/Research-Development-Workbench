# Pure domain and v4 policy

domain/models.py contains frozen typed research records, independent states, source-version references and immutable evaluation snapshots. policy_engine accepts a validated manifest plus explicitly supported semantic findings and manually assessed ratings; it returns exact scores, availability states, gates and structured rule trace. It reads no files and calls no network/model/database service.

From this directory: uv sync --locked; uv run --locked pytest -q; uv run --locked ruff check .; uv run --locked ruff format --check .; uv run --locked mypy domain policy_engine. Tests use synthetic inputs only. Caller loads the manifest explicitly and supplies its canonical policy hash; engine does not inspect documents or verify scientific truth.

Pydantic contracts roundtrip JSON with null/status preserved. Calculation results are immutable Python value objects containing exact Fraction values; display fields must never be fed back into calculations. No server or persistence is implemented.
