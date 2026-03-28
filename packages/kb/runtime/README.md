# Knowledge DB Runtime

This directory is managed by GroundTruth and is the project-local knowledge base
runtime copied from the upstream platform.

Managed files:

- `db.py`
- `assertions.py`
- `seed.py`
- `app.py`
- `templates/`
- `static/`

Typical workflow:

1. `membase kb init --path .`
2. `membase kb seed --path .`
3. `membase kb verify --path .`
4. `membase kb serve --path .`

Project-specific KB content belongs in `knowledge.db`. The runtime code above is
platform-managed and should be refreshed from GroundTruth updates rather than edited
in place.
