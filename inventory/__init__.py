from pathlib import Path
import secrets
import sqlite3
from flask import Flask, jsonify, render_template, session, request
from .db import init_db, get_db, close_db
from .routes import api

def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(DATABASE=str(Path(app.instance_path) / 'inventory.sqlite'), MAX_CONTENT_LENGTH=32768,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict')
    if config:
        app.config.update(config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    key = Path(app.config['DATABASE']).parent / 'session.key'
    if not key.exists():
        try:
            with key.open('x') as handle:
                handle.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    app.config['SECRET_KEY'] = key.read_text()
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
    app.register_blueprint(api)

    @app.before_request
    def csrf():
        if request.method in ('POST', 'PUT', 'DELETE'):
            token = session.get('csrf', '')
            if not token or not secrets.compare_digest(token, request.headers.get('X-CSRF-Token', '')):
                return jsonify(error='Sesi formulir tidak valid. Muat ulang halaman.'), 403

    @app.get('/')
    def index():
        session.setdefault('csrf', secrets.token_urlsafe(32))
        return render_template('index.html', csrf=session['csrf'])

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity(_error):
        return jsonify(error='Kode/nama sudah digunakan atau data masih memiliki relasi. Periksa kembali.'), 409

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'"
        response.headers['Cache-Control'] = 'no-store'
        return response
    return app
