/**
 * Dashboard Logic
 * Handles Chat interactions, File Uploads, and Modals.
 */

// Global State
// currentSessionId is declared in home.html via inline script
if (typeof currentSessionId === 'undefined') {
    var currentSessionId = 'null';
}

function getCsrfToken() { return document.querySelector('[name=csrfmiddlewaretoken]').value; }

// --- SETTINGS MODAL & THEME SYNC ---
function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'flex';
    // Sync checkbox with current theme
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
    // Push state again so they stay on the page
    history.pushState(null, null, location.href);
    // Show the modal
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
    // Initialize currentSessionId from global variable or data attribute if present
    // Note: Inline script defines currentSessionId, but we moved it. 
    // We expect the template to define a global 'currentSessionId' or we handle it in setup.
    // Ideally, pass it via data attribute on body or a specific element, but for now we rely on the global var if set separately,
    // or we need to initialize it.
    // FIX: logic below assumes currentSessionId is available. 

    document.querySelectorAll('.msg-bot').forEach(msg => {
        // [SECURE] Sanitize parsed Markdown before setting innerHTML
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

    // NOTE: Django URL {% url "upload_api" %} cannot be used in JS file directly.
    // We should use a hardcoded path or pass it via data attributes.
    // For this refactor, I will use the relative path '/upload_api/' which matches the typical Django url pattern.
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

// --- MESSAGING ---
function handleEnter(e) { if (e.key === 'Enter') sendMessage(); }

function sendMessage() {
    const input = document.getElementById('user-input');
    const msg = input.value.trim();
    if (!msg) return;

    const box = document.getElementById('chat-box');

    const userDiv = document.createElement('div');
    userDiv.className = 'msg msg-user';
    userDiv.textContent = msg; // [SECURE] Prevents HTML injection
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

    // NOTE: Using '/chat_api/' instead of {% url "chat_api" %}
    fetch('/chat_api/', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            document.getElementById(loadingId).remove();
            if (currentSessionId === 'null' && data.session_id) {
                currentSessionId = data.session_id;
                window.history.replaceState({}, '', `?session_id=${data.session_id}`);
                setTimeout(() => location.reload(), 2000);
            }

            // [SECURE] Sanitize the LLM response
            if (window.marked && window.DOMPurify) {
                const cleanHtml = DOMPurify.sanitize(marked.parse(data.response));
                box.innerHTML += `<div class="msg msg-bot">${cleanHtml}</div>`;
            } else {
                box.innerHTML += `<div class="msg msg-bot">${data.response}</div>`;
            }

            scrollToBottom();
        });
}
