import os
import hmac
import hashlib
import requests
from flask import Flask, request, render_template, redirect, url_for, abort, session, flash
from auth import login_required, verify_credentials
from storage import add_webhook, get_webhook, get_all_webhooks, delete_webhook, append_history


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))


@app.route("/")
@login_required
def index():
    return render_template("index.html", webhooks=list(get_all_webhooks().items()))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if verify_credentials(username, password):
            session["user"] = username
            next_url = session.pop("next", None)
            return redirect(next_url or url_for("index"))
        flash("Ungültige Zugangsdaten.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/add", methods=["POST"])
@login_required
def add():
    discord_url = request.form.get("discord_url")
    if not discord_url:
        return redirect(url_for("index"))
    wid, _secret = add_webhook(discord_url)
    return redirect(url_for("show", wid=wid))


@app.route("/webhook/<wid>")
@login_required
def show(wid):
    wh = get_webhook(wid)
    if not wh:
        abort(404)
    webhook_url = request.url_root.rstrip("/") + f"/hook/{wid}"
    return render_template(
        "show.html",
        wid=wid,
        webhook_url=webhook_url,
        discord_url=wh["discord_url"],
        secret=wh.get("secret", ""),
        history=(wh.get("history") or [])[::-1]
    )


def _validate_github_signature(secret_value: str, payload_bytes: bytes, signature_header: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    provided_sig_hex = signature_header.split("=", 1)[1].strip()
    mac = hmac.new(secret_value.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    expected_sig_hex = mac.hexdigest()
    try:
        return hmac.compare_digest(provided_sig_hex, expected_sig_hex)
    except Exception:
        return False


@app.route("/hook/<wid>", methods=["POST"])
def hook(wid):
    wh = get_webhook(wid)
    if not wh:
        abort(404)

    signature = request.headers.get("X-Hub-Signature-256", "")
    raw = request.get_data() or b""
    if not _validate_github_signature(wh.get("secret", ""), raw, signature):
        abort(401)

    payload = request.json or {}
    repo = payload.get("repository", {}).get("full_name", "Unbekanntes Repository")
    commits = payload.get("commits", [])
    lines = [f"{repo}: neue Commits"]
    for c in commits:
        message = c.get("message")
        author = (c.get("author") or {}).get("name")
        lines.append(f"- {message} — {author}")
    content = "\n".join(lines) if lines else "Update"

    status = "sent"
    try:
        resp = requests.post(wh["discord_url"], json={"content": content}, timeout=10)
        if not (200 <= resp.status_code < 300):
            status = f"discord_status_{resp.status_code}"
    except Exception:
        status = "discord_error"
    finally:
        try:
            append_history(wid, payload, content, status)
        except Exception:
            pass
    return {"status": "ok"}


@app.route("/webhook/<wid>/delete", methods=["POST"])
@login_required
def delete_wid(wid):
    if not get_webhook(wid):
        abort(404)
    if delete_webhook(wid):
        flash("Webhook gelöscht.", "success")
    else:
        flash("Webhook konnte nicht gelöscht werden.", "danger")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
