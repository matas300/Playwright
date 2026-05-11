"""Flask app: dashboard + config + scan API."""
import threading
from flask import Flask, render_template, request, jsonify

from src.config import load_config, save_config
from src.db import init_db, get_posts, mark_ignored, get_latest_scan_run
from src.scan_job import start_scan, get_state, is_running
from src.scanner import Scanner
from src.paths import get_auth_state_path


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    init_db()

    @app.route("/")
    def index():
        latest = get_latest_scan_run()
        session_present = get_auth_state_path().exists()
        return render_template("index.html",
                               latest_scan=latest,
                               session_present=session_present)

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        if start_scan():
            return jsonify({"started": True})
        return jsonify({"started": False, "reason": "already running"}), 409

    @app.route("/api/status")
    def api_status():
        return jsonify(get_state())

    @app.route("/api/posts")
    def api_posts():
        tiers = request.args.get("tiers", "S,A,B,C,D,E,over_budget").split(",")
        include_ignored = request.args.get("include_ignored") == "true"
        posts = get_posts(tiers=tiers, include_ignored=include_ignored)
        return jsonify([{
            "id": p.id,
            "group_id": p.group_id,
            "url": p.url,
            "author_name": p.author_name,
            "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            "text_original": p.text_original,
            "text_translated": p.text_translated,
            "language": p.language,
            "price_eur": p.price_eur,
            "date_start": p.date_start.isoformat() if p.date_start else None,
            "date_end": p.date_end.isoformat() if p.date_end else None,
            "neighborhood": p.neighborhood,
            "neighborhood_tier": p.neighborhood_tier,
            "tier": p.tier,
            "match_reasons": p.match_reasons,
            "photo_urls": p.photo_urls,
            "is_ignored": p.is_ignored,
        } for p in posts])

    @app.route("/api/posts/<post_id>/ignore", methods=["POST"])
    def api_post_ignore(post_id):
        mark_ignored(post_id)
        return jsonify({"ok": True})

    @app.route("/config")
    def config_page():
        return render_template("config_page.html", config=load_config())

    @app.route("/api/config", methods=["GET", "POST"])
    def api_config():
        if request.method == "POST":
            save_config(request.json)
            return jsonify({"ok": True})
        return jsonify(load_config())

    @app.route("/api/login", methods=["POST"])
    def api_login():
        if is_running():
            return jsonify({"ok": False, "reason": "scan running"}), 409
        def _login():
            with Scanner() as scanner:
                scanner.interactive_login()
        t = threading.Thread(target=_login, daemon=True)
        t.start()
        return jsonify({"ok": True, "message": "Apertura browser per login..."})

    return app


if __name__ == "__main__":
    app = create_app()
    print("FB Bot Scan attivo su http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
