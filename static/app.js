const messages = document.querySelector('#messages');
const message = document.querySelector('#message');
const form = document.querySelector('#chat-form');
const send = document.querySelector('#send');
const imageInput = document.querySelector('#image-input');
const preview = document.querySelector('#image-preview');
const attachment = document.querySelector('#attachment');
const imageName = document.querySelector('#image-name');
let selectedImage = null;
let previewURL = null;
const history = [];
function bubble(text, kind) {
  const node = document.createElement('div');
  node.className = `bubble ${kind}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
  return node;
}
function clearImage() {
  selectedImage = null;
  imageInput.value = '';
  attachment.hidden = true;
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = null;
  preview.removeAttribute('src');
}
function setImage(file) {
  if (!file) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    alert('Choose a JPG, PNG or WebP image.'); return;
  }
  if (file.size > 6 * 1024 * 1024) {
    alert('Image must be under 6 MB.'); return;
  }
  clearImage();
  selectedImage = file;
  previewURL = URL.createObjectURL(file);
  preview.src = previewURL;
  imageName.textContent = file.name || 'Pasted screenshot';
  attachment.hidden = false;
}
document.querySelector('#attach-image').addEventListener('click', () => imageInput.click());
imageInput.addEventListener('change', () => setImage(imageInput.files[0]));
document.querySelector('#remove-image').addEventListener('click', clearImage);
document.addEventListener('paste', (e) => {
  if (document.querySelector('#chat-panel').hidden) return;
  const item = [...(e.clipboardData?.items || [])].find(x => x.kind === 'file' && x.type.startsWith('image/'));
  if (item) { e.preventDefault(); setImage(item.getAsFile()); }
});
form.addEventListener('dragover', e => { e.preventDefault(); form.classList.add('dragover'); });
form.addEventListener('dragleave', () => form.classList.remove('dragover'));
form.addEventListener('drop', e => {
  e.preventDefault(); form.classList.remove('dragover');
  const file = [...e.dataTransfer.files].find(x => x.type.startsWith('image/'));
  if (file) setImage(file);
});
form.addEventListener('submit', async e => {
  e.preventDefault();
  const question = message.value.trim();
  if ((!question && !selectedImage) || send.disabled) return;
  const hadImage = Boolean(selectedImage);
  bubble((hadImage ? '📷 Image attached' + (question ? '\n' : '') : '') + question, 'user');
  send.disabled = true;
  const pending = bubble('Thinking…', 'assistant');
  const body = new FormData();
  body.append('message', question);
  body.append('history', JSON.stringify(history.slice(-10)));
  if (selectedImage) body.append('image', selectedImage, selectedImage.name || 'screenshot.png');
  message.value = '';
  clearImage();
  try {
    const response = await fetch('/api/chat', {
      method: 'POST', credentials: 'same-origin',
      headers: {'X-CSRF-Token': document.body.dataset.csrf},
      body
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    pending.textContent = data.answer;
    // Image bytes are not retained in history; the text summary stays in this tab only.
    history.push({role: 'user', text: hadImage ? '[Image attached] ' + (question || 'Describe this image') : question},
                 {role: 'model', text: data.answer});
    if (history.length > 10) history.splice(0, history.length - 10);
  } catch (err) {
    pending.textContent = `Error: ${err.message}`;
  } finally { send.disabled = false; message.focus(); }
});
document.querySelector('#clear').addEventListener('click', () => {
  history.length = 0; clearImage(); messages.replaceChildren();
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
    link.href = url.href; link.hidden = false;
  } catch (_) { alert('Enter a valid HTTPS URL.'); }
});
