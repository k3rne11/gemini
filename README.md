# Gemini Study Popup — Render-ready

Private, password-protected Gemini study assistant with a standalone popup window for Moodle. Includes a simple PDF URL viewer. **Use only if AI assistance is allowed under your exam rules.**

## Features

- Server-side Gemini key (never exposed in Moodle HTML or the browser)
- Password login, secure HttpOnly cookies, CSRF protection for the API, conservative CSP
- Small chat history (last five exchanges) while the page remains open
- Separate browser popup (not an iframe)
- PDF viewer for direct HTTPS URLs, with fallback link
- No database and no chat persistence
- `/health` endpoint for Render

## 1. Get credentials

- Gemini API key: https://aistudio.google.com/apikey
- Choose a long, unique `APP_PASSWORD` for the private assistant.
- **Do not put either credential in the Moodle HTML. Do not share the real API key in chat or commit it to Git.**

## 2. Deploy to Render

1. Unzip this folder and push its contents to a **private** GitHub repository (or another Git provider supported by Render).
2. In Render choose **New → Blueprint** and connect the repository containing `render.yaml`.
3. When prompted, set `GEMINI_API_KEY` and `APP_PASSWORD`. `FLASK_SECRET_KEY` is generated automatically.
4. Deploy and open `https://YOUR-SERVICE.onrender.com/`. Log in with the configured password.
5. If you deploy using **New → Web Service** rather than Blueprint, use:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
   - Env vars: `GEMINI_API_KEY`, `APP_PASSWORD`, and a random `FLASK_SECRET_KEY` at least 32 characters long.
6. The free Render plan can sleep when idle and take time to wake up; a paid always-on plan avoids that limitation.

## 3. Add the Moodle popup button

Open `moodle-block.html`, replace BOTH occurrences of `YOUR-SERVICE.onrender.com` with your Render hostname, and paste the HTML into **your own** Moodle HTML block in HTML/source mode. Save and click **Open study popup**. Chrome may open a normal tab if popup behavior is constrained. The button must be clicked by the user; popups may otherwise be blocked.

This block lives on `/my/`; it won't automatically appear inside quizzes. If the browser forbids using other windows, the popup approach will not override that restriction.

## 4. Local test (optional)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set variables from .env.example in your shell; the app does not auto-load .env
python app.py
```

Visit `http://127.0.0.1:5000/login`. Local development requires `LOCAL_DEV=1` to permit cookies over HTTP. Do not enable `LOCAL_DEV` in Render.

## Notes and limitations

- The PDF viewer is URL-based. Moodle protected PDF links may not render in a separate Render window because of authentication or frame restrictions. Use the `Open in tab` link or publicly accessible documents that you have permission to use.
- No PDF upload, server-side PDF parsing, or chat persistence is included.
- Keep service password private. The in-memory login attempt limiter is per instance and is not a substitute for a gateway/WAF on a public app.
- API use may incur Google charges or quotas. The model identifier is set by `GEMINI_MODEL`; verify model availability on your Google account.
- Do not send confidential student data or exam materials to third-party AI without permission.
