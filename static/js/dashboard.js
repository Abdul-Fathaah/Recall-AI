if (typeof currentSessionId === 'undefined') {
    var currentSessionId = 'null';
}

function getCsrfToken() { return document.querySelector('[name=csrfmiddlewaretoken]').value; }

// --- SETTINGS MODAL & THEME SYNC ---
function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'flex';
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const checkbox = document.getElementById('themeToggleCheckbox');
    if (checkbox) {
        checkbox.checked = (currentTheme === 'dark');
    }
}

function toggleThemeModal(checkbox) {
    const newTheme = checkbox.checked ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// --- SECURITY: BACK BUTTON TRAP ---
function showLogoutConfirmation() {
    document.getElementById('logoutConfirmModal').style.display = 'flex';
}

// Push state on load
history.pushState(null, null, location.href);

// Intercept Back Button
window.onpopstate = function () {
    history.pushState(null, null, location.href);
    showLogoutConfirmation();
};

// --- CHAT MANAGEMENT ---
function openRenameModal(event, sessionId, currentTitle) {
    event.stopPropagation();
    const modal = document.getElementById('renameModal');
    document.getElementById('renameForm').action = `/rename_chat/${sessionId}/`;
    document.getElementById('newTitleInput').value = currentTitle;
    modal.style.display = 'flex';
}

// Close Modals on Outside Click
window.onclick = function (e) {
    const renameModal = document.getElementById('renameModal');
    const logoutModal = document.getElementById('logoutConfirmModal');
    const settingsModal = document.getElementById('settingsModal');

    if (e.target == renameModal) renameModal.style.display = "none";
    if (e.target == logoutModal) logoutModal.style.display = "none";
    if (e.target == settingsModal) settingsModal.style.display = "none";
}

// --- MARKDOWN & SCROLLING ---
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.msg-bot').forEach(msg => {
        if (!msg.innerHTML.includes('<') && window.marked && window.DOMPurify) {
            const parsed = marked.parse(msg.innerHTML.trim());
            msg.innerHTML = DOMPurify.sanitize(parsed);
        }
    });
    scrollToBottom();
});

function scrollToBottom() {
    const box = document.getElementById('chat-box');
    if (box) box.scrollTop = box.scrollHeight;
}

// --- FILE UPLOAD ---
function uploadFiles(files) {
    if (!files.length) return;
    document.getElementById('upload-progress').innerText = "⏳ Analyzing documents...";
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
    formData.append('session_id', currentSessionId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    fetch('/upload_api/', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                if (data.session_id && currentSessionId === 'null') {
                    currentSessionId = data.session_id;
                    window.history.replaceState({}, '', `?session_id=${data.session_id}`);
                }
                location.reload();
            } else { document.getElementById('upload-progress').innerText = "❌ Upload Failed"; }
        });
}

function handleEnter(e) { if (e.key === 'Enter') sendMessage(); }

function sendMessage() {
    const input = document.getElementById('user-input');
    const msg = input.value.trim();
    if (!msg) return;

    const box = document.getElementById('chat-box');

    const userDiv = document.createElement('div');
    userDiv.className = 'msg msg-user';
    userDiv.textContent = msg;
    box.appendChild(userDiv);

    input.value = '';
    scrollToBottom();

    const loadingId = 'loading-' + Date.now();
    box.innerHTML += `<div id="${loadingId}" class="msg msg-bot" style="opacity:0.7;">Thinking...</div>`;
    scrollToBottom();

    const formData = new FormData();
    formData.append('message', msg);
    formData.append('session_id', currentSessionId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    fetch('/chat_api/', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            document.getElementById(loadingId).remove();
            if (currentSessionId === 'null' && data.session_id) {
                currentSessionId = data.session_id;
                window.history.replaceState({}, '', `?session_id=${data.session_id}`);
                setTimeout(() => location.reload(), 2000);
            }

            if (window.marked && window.DOMPurify) {
                const cleanHtml = DOMPurify.sanitize(marked.parse(data.response));
                box.innerHTML += `<div class="msg msg-bot">${cleanHtml}</div>`;
            } else {
                box.innerHTML += `<div class="msg msg-bot">${data.response}</div>`;
            }

            scrollToBottom();
        });
}
