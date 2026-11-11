const messages = document.querySelector('#messages');
const message = document.querySelector('#message');
const form = document.querySelector('#chat-form');
const send = document.querySelector('#send');
const history = [];
function bubble(text, kind) {
  const node = document.createElement('div');
  node.className = `bubble ${kind}`;
  node.textContent = text; // Never render model output as HTML.
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = message.value.trim();
  if (!question || send.disabled) return;
  bubble(question, 'user');
  message.value = '';
  send.disabled = true;
  const pending = bubble('Thinking…', 'assistant');
  try {
    const response = await fetch('/api/chat', {
      method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': document.body.dataset.csrf},
      body: JSON.stringify({message: question, history: history.slice(-10)})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    pending.textContent = data.answer;
    history.push({role: 'user', text: question}, {role: 'model', text: data.answer});
    if (history.length > 10) history.splice(0, history.length - 10);
  } catch (err) {
    pending.textContent = `Error: ${err.message}`;
  } finally { send.disabled = false; message.focus(); }
});
document.querySelector('#clear').addEventListener('click', () => {
  history.length = 0;
  messages.replaceChildren();
  bubble('Conversation cleared.', 'assistant');
});
document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-tab]').forEach(x => x.classList.toggle('selected', x === button));
  const isPDF = button.dataset.tab === 'pdf';
  document.querySelector('#chat-panel').hidden = isPDF;
  document.querySelector('#pdf-panel').hidden = !isPDF;
}));
document.querySelector('#open-pdf').addEventListener('click', () => {
  const raw = document.querySelector('#pdf-url').value.trim();
  try {
    const url = new URL(raw);
    if (url.protocol !== 'https:') throw new Error('Use a HTTPS PDF link');
    document.querySelector('#pdf-frame').src = url.href;
    const link = document.querySelector('#pdf-tab');
    link.href = url.href;
    link.hidden = false;
  } catch (_) { alert('Enter a valid HTTPS URL.'); }
});
