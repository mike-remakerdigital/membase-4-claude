"""
Membase Reference — Read-only Web Dashboard

Strictly read-only: no forms, no POST endpoints, no edit buttons.
All writes come from the AI assistant via the Python API.
The owner uses this UI to observe, filter, and verify.

Usage:
  python reference/app.py             # start on port 8090
  python reference/app.py --port 9000  # custom port

MIT License — see LICENSE for details.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from flask import Flask, render_template, request, abort, g

# Import sibling module
sys.path.insert(0, str(Path(__file__).parent))
from db import KnowledgeDB

BASE_DIR = Path(__file__).parent
DB_PATH = str(BASE_DIR / "knowledge.db")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


# ─────────────────────────────────────────────────────────────────────
# Database (per-request to avoid SQLite threading issues)
# ─────────────────────────────────────────────────────────────────────

def get_db() -> KnowledgeDB:
    """Get a per-request KnowledgeDB instance."""
    if "db" not in g:
        g.db = KnowledgeDB(DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ─────────────────────────────────────────────────────────────────────
# Template Helpers
# ─────────────────────────────────────────────────────────────────────

def _status_class(status: str) -> str:
    """Map spec status to CSS class for color coding."""
    return {
        "verified": "status-verified",
        "implemented": "status-implemented",
        "specified": "status-specified",
        "retired": "status-retired",
    }.get(status, "status-unknown")


def _pass_fail_class(passed: bool | int) -> str:
    return "pass" if passed else "fail"


app.jinja_env.globals["status_class"] = _status_class
app.jinja_env.globals["pass_fail_class"] = _pass_fail_class


# ─────────────────────────────────────────────────────────────────────
# Routes (ALL GET — read-only)
# ─────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    db = get_db()
    summary = db.get_summary()
    recent = db.get_history(limit=20)
    return render_template("dashboard.html", summary=summary, recent=recent)


@app.route("/specs")
def specs_list():
    db = get_db()
    status = request.args.get("status")
    search = request.args.get("search")
    specs = db.list_specs(status=status, search=search)
    all_specs = db.list_specs()
    statuses = sorted(set(s["status"] for s in all_specs))
    return render_template(
        "specs.html",
        specs=specs,
        statuses=statuses,
        filters={"status": status, "search": search},
    )


@app.route("/specs/<path:spec_id>")
def spec_detail(spec_id: str):
    db = get_db()
    spec = db.get_spec(spec_id)
    if not spec:
        abort(404)
    history = db.get_spec_history(spec_id)
    assertion_run = db.get_latest_assertion_run(spec_id)
    return render_template(
        "spec_detail.html",
        spec=spec,
        history=history,
        assertion_run=assertion_run,
    )


@app.route("/assertions")
def assertions():
    db = get_db()
    runs = db.get_all_latest_assertion_runs()
    for run in runs:
        spec = db.get_spec(run["spec_id"])
        run["spec_title"] = spec["title"] if spec else "Unknown"
    return render_template("assertions.html", runs=runs)


@app.route("/ops")
def ops_list():
    db = get_db()
    procedures = db.list_op_procedures()
    return render_template("ops.html", procedures=procedures)


@app.route("/ops/<proc_id>")
def op_detail(proc_id: str):
    db = get_db()
    proc = db.get_op_procedure(proc_id)
    if not proc:
        abort(404)
    return render_template("op_detail.html", proc=proc)


@app.route("/history")
def history():
    db = get_db()
    changes = db.get_history(limit=100)
    return render_template("history.html", changes=changes)


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Membase Knowledge DB Web UI")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    port = int(os.environ.get("PORT", 0)) or args.port or 8090

    if not Path(DB_PATH).exists():
        print(f"\n  Database not found at {DB_PATH}")
        print(f"  Run 'python reference/seed.py' first to create it.\n")
        sys.exit(1)

    print(f"\n  Membase Knowledge DB: http://{args.host}:{port}")
    print(f"  Database: {DB_PATH}\n")

    app.run(host=args.host, port=port, debug=True)
