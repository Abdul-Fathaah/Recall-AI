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
    document.getElementById('upload-progress').innerText = "⏳ Analyzing documents (Bulk Mode)...";
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
    formData.append('session_id', currentSessionId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    fetch('/api/upload/', { method: 'POST', body: formData })
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

async function sendMessage() {
    const input = document.getElementById('user-input');
    const msg = input.value.trim();
    if (!msg) return;

    const box = document.getElementById('chat-box');

    // 1. Add User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'msg msg-user';
    userDiv.textContent = msg;
    box.appendChild(userDiv);

    input.value = '';
    scrollToBottom();

    // 2. Prepare Bot Message Container
    const botDiv = document.createElement('div');
    botDiv.className = 'msg msg-bot';
    botDiv.innerHTML = '<span class="typing-indicator">Thinking...</span>'; // You can style this class
    box.appendChild(botDiv);
    scrollToBottom();

    const formData = new FormData();
    formData.append('message', msg);
    formData.append('session_id', currentSessionId);
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    try {
        const response = await fetch('/api/chat/', { method: 'POST', body: formData });

        // 3. Update Session Info from Headers
        const newSessionId = response.headers.get('X-Session-ID');
        const newTitle = response.headers.get('X-Session-Title');

        if (currentSessionId === 'null' && newSessionId) {
            currentSessionId = newSessionId;
            window.history.replaceState({}, '', `?session_id=${newSessionId}`);
            // If we got a title, update the UI immediately (optional, or wait for reload)
            if (newTitle) {
                document.getElementById('chat-title').innerText = newTitle;
            }
        }

        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullText = "";

        // 4. Stream Loop
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            // Render Markdown on the fly
            if (window.marked && window.DOMPurify) {
                // DOMPurify might be heavy to run every chunk, but safe. 
                // For smoother typing, maybe run it less often or on end? 
                // For now, let's run it.
                botDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
            } else {
                botDiv.innerText = fullText;
            }
            scrollToBottom();
        }

    } catch (error) {
        console.error("Stream Error:", error);
        botDiv.innerText += "\n[Connection Error]";
    }
}
