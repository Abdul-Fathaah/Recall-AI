/* static/js/dashboard.js */

// === 1. GLOBAL VARIABLES & INIT ===
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const fileInput = document.getElementById('file-input');
const urlInput = document.getElementById('urlInput'); // [NEW]
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : "";

// Fallback if not defined in template
if (typeof currentSessionId === 'undefined') {
    var currentSessionId = 'null';
}

// Initial scroll to bottom
document.addEventListener("DOMContentLoaded", function () {
    // Render existing messages with Markdown
    document.querySelectorAll('.msg-bot').forEach(msg => {
        if (!msg.innerHTML.includes('<') && window.marked && window.DOMPurify) {
            const parsed = marked.parse(msg.innerHTML.trim());
            msg.innerHTML = DOMPurify.sanitize(parsed);
        }
    });
    scrollToBottom();
});

// === 2. CHAT FUNCTIONALITY (STREAMING) ===
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // A. Add User Message to UI
    appendMessage('user', message);
    userInput.value = '';
    userInput.disabled = true; // Disable input while generating

    // B. Create Placeholder for Bot Response
    const botMessageDiv = appendMessage('bot', '<span class="typing-indicator">Thinking...</span>');
    const botContentDiv = botMessageDiv.querySelector('.msg-content');

    try {
        // C. Send Request
        const chatUrl = document.getElementById('urls').dataset.chat;
        const formData = new FormData();
        formData.append('message', message);
        formData.append('session_id', currentSessionId);
        // Important: Add CSRF Token for Django
        if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken);

        const response = await fetch(chatUrl, {
            method: 'POST',
            body: formData
        });

        // D. Handle Streaming Response
        if (!response.body) throw new Error("No response stream");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        // Clear placeholder
        botContentDiv.innerHTML = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            // Render Markdown
            if (window.marked && window.DOMPurify) {
                botContentDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
            } else {
                botContentDiv.innerText = fullText;
            }

            scrollToBottom();
        }

        // E. Update Session Metadata (if new)
        const newSessionId = response.headers.get('X-Session-ID');
        const newTitle = response.headers.get('X-Session-Title');

        if (newSessionId && currentSessionId === 'null') {
            currentSessionId = newSessionId;
            // Update URL without reloading
            window.history.pushState({}, '', `?session_id=${newSessionId}`);

            // Update Chat Title in UI if present
            const titleEl = document.querySelector('.chat-title');
            if (titleEl && newTitle) titleEl.innerText = newTitle;
        }

    } catch (error) {
        console.error("Chat Error:", error);
        botContentDiv.innerHTML = `<span style="color:var(--danger)">Error: ${error.message}</span>`;
    } finally {
        userInput.disabled = false;
        userInput.focus();
        scrollToBottom();
    }
}

// === 3. FILE UPLOAD FUNCTIONALITY ===
async function uploadFiles(files) {
    if (files.length === 0) return;

    const statusDiv = document.getElementById('upload-progress');
    const uploadUrl = document.getElementById('urls').dataset.upload;

    statusDiv.style.display = 'block';
    statusDiv.innerText = `Uploading ${files.length} file(s)...`;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    formData.append('session_id', currentSessionId);
    if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken);

    try {
        const response = await fetch(uploadUrl, { method: 'POST', body: formData });
        const data = await response.json();

        if (data.status === 'success') {
            statusDiv.innerText = "Indexing Complete!";
            handleNewSession(data.session_id);
        } else {
            statusDiv.innerText = "Error: " + data.message;
            setTimeout(() => statusDiv.style.display = 'none', 3000);
        }
    } catch (error) {
        statusDiv.innerText = "Upload Failed";
        setTimeout(() => statusDiv.style.display = 'none', 3000);
    }
}

// === 4. [NEW] URL UPLOAD FUNCTIONALITY ===
async function uploadUrl() {
    const url = document.getElementById('urlInput').value.trim();
    if (!url) return alert("Please enter a URL");

    const statusDiv = document.getElementById('upload-progress');
    const uploadEndpoint = document.getElementById('urls').dataset.upload;

    statusDiv.style.display = 'block';
    statusDiv.innerText = "Scanning URL...";

    const formData = new FormData();
    formData.append('url', url);
    formData.append('session_id', currentSessionId);
    if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken);

    try {
        const response = await fetch(uploadEndpoint, { method: 'POST', body: formData });
        const data = await response.json();

        if (data.status === 'success') {
            statusDiv.innerText = "URL Indexed!";
            document.getElementById('urlInput').value = ""; // Clear input
            handleNewSession(data.session_id);
        } else {
            statusDiv.innerText = "Error: " + data.message;
        }
    } catch (error) {
        statusDiv.innerText = "Network Error";
        console.error(error);
    }

    setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
}

// === 5. UTILITIES ===
function handleNewSession(sessionId) {
    // If a new session was created (started from null), reload to show it
    if (sessionId && currentSessionId === 'null') {
        currentSessionId = sessionId;
        window.location.href = `?session_id=${sessionId}`;
    } else {
        // Just reload to update the chat history/files list
        location.reload();
    }
}

function appendMessage(sender, htmlContent) {
    const div = document.createElement('div');
    div.className = `msg msg-${sender}`;
    div.innerHTML = `<div class="msg-content">${htmlContent}</div>`;
    chatBox.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() {
    if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
}

function handleEnter(event) {
    if (event.key === 'Enter') sendMessage();
}

// === 6. MODAL HANDLERS ===
function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'flex';
}

function showLogoutConfirmation() {
    document.getElementById('logoutConfirmModal').style.display = 'flex';
}

function openRenameModal(e, id, title) {
    e.stopPropagation();
    const modal = document.getElementById('renameModal');
    document.getElementById('newTitleInput').value = title;
    document.getElementById('renameForm').action = `/chat/rename/${id}/`;
    modal.style.display = 'flex';
}

// Close modals on click outside
window.onclick = function (e) {
    const modals = ['renameModal', 'logoutConfirmModal', 'settingsModal'];
    modals.forEach(id => {
        const modal = document.getElementById(id);
        if (e.target === modal) modal.style.display = 'none';
    });
}