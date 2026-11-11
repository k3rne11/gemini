import os
from unittest.mock import patch
os.environ.setdefault('GEMINI_API_KEY', 'test-key')
os.environ.setdefault('APP_PASSWORD', 'local-test-password')
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-for-testing-that-is-long-enough')
os.environ.setdefault('LOCAL_DEV', '1')
from app import create_app

def test_auth_and_chat():
    a = create_app()
    a.testing = True
    c = a.test_client()
    assert c.get('/health').status_code == 200
    assert c.get('/').status_code == 302
    assert c.post('/api/chat', json={'message': 'hi'}).status_code == 401
    assert c.post('/login', data={'password':'wrong'}).status_code == 401
    assert c.post('/login', data={'password':'local-test-password'}).status_code == 302
    page = c.get('/')
    assert page.status_code == 200
    with c.session_transaction() as s:
        csrf = s['csrf']
    assert c.post('/api/chat', json={'message':'hello'}).status_code == 403
    with patch('app.requests.post') as send:
        send.return_value.status_code = 200
        send.return_value.ok = True
        send.return_value.json.return_value = {'candidates':[{'content':{'parts':[{'text':'Hello back'}]}}]}
        response = c.post('/api/chat', json={'message':'hello'}, headers={'X-CSRF-Token':csrf})
        assert response.status_code == 200
        assert response.json['answer'] == 'Hello back'
    assert c.post('/logout', data={'csrf':csrf}).status_code == 302
    assert c.get('/').status_code == 302


def test_image_upload_and_validation():
    import io
    from PIL import Image
    a = create_app()
    a.testing = True
    c = a.test_client()
    c.post('/login', data={'password': 'local-test-password'})
    with c.session_transaction() as s:
        csrf = s['csrf']
    im = Image.new('RGB', (24, 24), 'white')
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    buf.seek(0)
    with patch('app.requests.post') as send:
        send.return_value.status_code = 200
        send.return_value.ok = True
        send.return_value.json.return_value = {'candidates': [{'content': {'parts': [{'text': 'A white square'}]}}]}
        r = c.post('/api/chat', data={
            'message': 'Describe this image',
            'history': '[]',
            'image': (buf, 'photo.png', 'image/png'),
        }, headers={'X-CSRF-Token': csrf})
        assert r.status_code == 200
        assert r.json['answer'] == 'A white square'
        sent = send.call_args.kwargs['json']['contents'][-1]['parts']
        assert sent[1]['inline_data']['mime_type'] == 'image/jpeg'
        assert len(sent[1]['inline_data']['data']) > 10
    r = c.post('/api/chat', data={
        'message': '', 'history': '[]',
        'image': (io.BytesIO(b'not an image'), 'bad.png', 'image/png')
    }, headers={'X-CSRF-Token': csrf})
    assert r.status_code == 400
