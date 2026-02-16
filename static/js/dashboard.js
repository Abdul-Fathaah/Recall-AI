const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const fileInput = document.getElementById('file-input');
const urlInput = document.getElementById('urlInput');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : "";

if (typeof currentSessionId === 'undefined') {
    var currentSessionId = 'null';
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('.msg-bot').forEach(msg => {
        if (!msg.innerHTML.includes('<') && window.marked && window.DOMPurify) {
            const parsed = marked.parse(msg.innerHTML.trim());
            msg.innerHTML = DOMPurify.sanitize(parsed);
        }
    });
    scrollToBottom();
});

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    appendMessage('user', message);
    userInput.value = '';
    userInput.disabled = true;

    const botMessageDiv = appendMessage('bot', '<span class="typing-indicator">Thinking...</span>');
    const botContentDiv = botMessageDiv.querySelector('.msg-content');

    try {
        const chatUrl = document.getElementById('urls').dataset.chat;
        const formData = new FormData();
        formData.append('message', message);
        formData.append('session_id', currentSessionId);
        if (csrfToken) formData.append('csrfmiddlewaretoken', csrfToken);

        const response = await fetch(chatUrl, {
            method: 'POST',
            body: formData
        });

        if (!response.body) throw new Error("No response stream");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        botContentDiv.innerHTML = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            fullText += chunk;

            if (window.marked && window.DOMPurify) {
                botContentDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
            } else {
                botContentDiv.innerText = fullText;
            }

            scrollToBottom();
        }

        const newSessionId = response.headers.get('X-Session-ID');
        const newTitle = response.headers.get('X-Session-Title');

        if (newSessionId && currentSessionId === 'null') {
            currentSessionId = newSessionId;
            window.history.pushState({}, '', `?session_id=${newSessionId}`);
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
            document.getElementById('urlInput').value = "";
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

function handleNewSession(sessionId) {
    if (sessionId && currentSessionId === 'null') {
        currentSessionId = sessionId;
        window.location.href = `?session_id=${sessionId}`;
    } else {
        location.reload();
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
    if (!chatBox) return;

    requestAnimationFrame(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    });
}

function handleEnter(event) {
    if (event.key === 'Enter') sendMessage();
}

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

window.onclick = function (e) {
    const modals = ['renameModal', 'logoutConfirmModal', 'settingsModal'];
    modals.forEach(id => {
        const modal = document.getElementById(id);
        if (e.target === modal) modal.style.display = 'none';
    });
}

function toggleUrlInput() {
    const wrapper = document.getElementById('urlInputWrapper');
    const input = document.getElementById('urlInput');

    wrapper.classList.toggle('visible');

    if (wrapper.classList.contains('visible')) {
        input.focus();
    }
}