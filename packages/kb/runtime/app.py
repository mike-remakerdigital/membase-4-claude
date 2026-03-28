"""
Read-only web dashboard for a Membase knowledge base.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from flask import Flask, abort, g, render_template, request
except ImportError:  # pragma: no cover - import error is surfaced at runtime
    Flask = None  # type: ignore[assignment]
    abort = g = render_template = request = None  # type: ignore[assignment]

try:
    from .db import KnowledgeDB
except ImportError:  # pragma: no cover - used by copied project runtime
    from db import KnowledgeDB

BASE_DIR = Path(__file__).parent
DEFAULT_DB_PATH = BASE_DIR / "knowledge.db"


def _status_class(status: str) -> str:
    return {
        "verified": "status-verified",
        "implemented": "status-implemented",
        "specified": "status-specified",
        "retired": "status-retired",
    }.get(status, "status-unknown")


def _pass_fail_class(passed: bool | int) -> str:
    return "pass" if passed else "fail"


def create_app(db_path: str | Path | None = None):
    if Flask is None:
        raise RuntimeError(
            "Flask is required for 'membase kb serve'. Install Membase with its Python "
            "dependencies or run 'python -m pip install Flask'."
        )

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["MEMBASE_DB_PATH"] = str(Path(db_path or DEFAULT_DB_PATH).resolve())
    app.jinja_env.globals["status_class"] = _status_class
    app.jinja_env.globals["pass_fail_class"] = _pass_fail_class

    def get_db() -> KnowledgeDB:
        if "db" not in g:
            g.db = KnowledgeDB(app.config["MEMBASE_DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def close_db(exc):  # type: ignore[no-untyped-def]
        db = g.pop("db", None)
        if db is not None:
            db.close()

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
        statuses = sorted({spec["status"] for spec in all_specs})
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
        return render_template("ops.html", procedures=db.list_op_procedures())

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

    return app


def serve(
    *,
    db_path: str | Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8090,
    debug: bool = True,
) -> int:
    resolved_db = Path(db_path or DEFAULT_DB_PATH).resolve()
    if not resolved_db.exists():
        print(f"Database not found at {resolved_db}")
        print("Run 'membase kb init' and 'membase kb seed' first.")
        return 1

    app = create_app(db_path=resolved_db)
    print(f"Membase KB: http://{host}:{port}")
    print(f"Database: {resolved_db}")
    app.run(host=host, port=port, debug=debug)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the Membase KB web dashboard")
    parser.add_argument("--db", default=None, help="Explicit KB database path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--no-debug", action="store_true", help="Disable Flask debug mode")
    args = parser.parse_args(argv)
    return serve(
        db_path=args.db,
        host=args.host,
        port=args.port,
        debug=not args.no_debug,
    )


if __name__ == "__main__":
    raise SystemExit(main())
