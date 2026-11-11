import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', '')
    if len(app.secret_key) < 32:
        raise RuntimeError('Set FLASK_SECRET_KEY to a random string of at least 32 characters')
    for key in ('GEMINI_API_KEY', 'APP_PASSWORD'):
        if not os.environ.get(key):
            raise RuntimeError(f'Missing {key} environment variable')
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.environ.get('LOCAL_DEV') != '1',
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
        MAX_CONTENT_LENGTH=30_000,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    attempts = defaultdict(deque)

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-src https:; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        response.headers['Cache-Control'] = 'no-store'
        return response

    def logged_in(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get('logged_in'):
                if request.path.startswith('/api/'):
                    return jsonify(error='Login required'), 401
                return redirect(url_for('login'))
            return fn(*args, **kwargs)
        return wrapper

    @app.get('/health')
    def health():
        return jsonify(status='ok')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return redirect(url_for('index')) if session.get('logged_in') else render_template('login.html', error=None)
        ip = request.remote_addr or 'unknown'
        now = time.monotonic()
        q = attempts[ip]
        while q and now - q[0] > 600:
            q.popleft()
        if len(q) >= 10:
            return render_template('login.html', error='Too many attempts. Try again later.'), 429
        password = request.form.get('password', '')
        if not hmac.compare_digest(password, os.environ['APP_PASSWORD']):
            q.append(now)
            return render_template('login.html', error='Incorrect password'), 401
        q.clear()
        session.clear()
        session['logged_in'] = True
        session['csrf'] = secrets.token_urlsafe(24)
        session.permanent = True
        return redirect(url_for('index'))

    @app.post('/logout')
    @logged_in
    def logout():
        if request.form.get('csrf') != session.get('csrf'):
            return 'Invalid request', 403
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @logged_in
    def index():
        return render_template('index.html', csrf=session['csrf'])

    @app.post('/api/chat')
    @logged_in
    def chat():
        if request.headers.get('X-CSRF-Token') != session.get('csrf'):
            return jsonify(error='Invalid request token'), 403
        if request.mimetype != 'application/json':
            return jsonify(error='JSON required'), 415
        payload = request.get_json(silent=True) or {}
        question = payload.get('message', '')
        history = payload.get('history', [])
        if not isinstance(question, str) or not (1 <= len(question.strip()) <= 4000):
            return jsonify(error='Message must be 1–4000 characters'), 400
        if not isinstance(history, list) or len(history) > 10:
            return jsonify(error='Invalid conversation history'), 400
        contents = []
        for turn in history:
            if (not isinstance(turn, dict) or turn.get('role') not in ('user', 'model')
                    or not isinstance(turn.get('text'), str)
                    or not 1 <= len(turn['text']) <= 4000):
                return jsonify(error='Invalid conversation history'), 400
            contents.append({'role': turn['role'], 'parts': [{'text': turn['text']}]})
        contents.append({'role': 'user', 'parts': [{'text': question.strip()}]})
        model = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
        # Only permit model identifier characters; no user-controlled URLs.
        if not all(c.isalnum() or c in '-_.' for c in model):
            return jsonify(error='Invalid model configuration'), 500
        try:
            result = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                headers={'x-goog-api-key': os.environ['GEMINI_API_KEY']},
                json={'contents': contents, 'generationConfig': {'maxOutputTokens': 1200}},
                timeout=35,
            )
            if result.status_code == 429:
                return jsonify(error='Gemini rate limit reached. Try again later.'), 429
            if result.status_code in (401, 403):
                return jsonify(error='Gemini API key or permissions need attention.'), 502
            if not result.ok:
                return jsonify(error=f'Gemini service returned HTTP {result.status_code}'), 502
            data = result.json()
            parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
            answer = ''.join(p.get('text', '') for p in parts if isinstance(p, dict))
            return jsonify(answer=answer or 'No text response was returned.')
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return jsonify(error='Unable to reach Gemini right now.'), 502

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False, port=5000)
