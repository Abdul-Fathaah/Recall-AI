const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const fileInput = document.getElementById('file-input');
const urlInput = document.getElementById('urlInput');
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : "";

if (typeof currentSessionId === 'undefined') {
    var currentSessionId = 'null';
}

document.addEventListener("DOMContentLoaded", function () {
    // Render saved bot messages from DB (marked with data-markdown)
    document.querySelectorAll('[data-markdown="true"] .msg-content').forEach(el => {
        if (window.marked && window.DOMPurify) {
            const parsed = marked.parse(el.textContent.trim());
            el.innerHTML = DOMPurify.sanitize(parsed);
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

            // Hide the meta tag during streaming
            let displayText = fullText.replace(/__META__:.*/, '');
            if (window.marked && window.DOMPurify) {
                botContentDiv.innerHTML = DOMPurify.sanitize(marked.parse(displayText));
            } else {
                botContentDiv.innerText = displayText;
            }

            scrollToBottom();
        }

        const metaMatch = fullText.match(/__META__:(\{.*?\})/);
        if (metaMatch) {
            try {
                // Try parse with single quotes replaced to double quotes
                const meta = JSON.parse(metaMatch[1].replace(/'/g, '"'));
                fullText = fullText.replace(/__META__:.*/, '').trim();
                currentSessionId = meta.session_id;
                window.history.pushState({}, '', `?session_id=${meta.session_id}`);
                const titleEl = document.querySelector('.chat-title');
                if (titleEl && meta.title) titleEl.innerText = meta.title;
                if (meta.title) location.reload();
            } catch(e) { console.warn('Meta parse error', e); }
        }

        // Final render after strip
        if (window.marked && window.DOMPurify) {
            botContentDiv.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
        } else {
            botContentDiv.innerText = fullText;
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
    }
}

function appendMessage(sender, htmlContent) {
    const div = document.createElement('div');
    div.className = `msg-container msg-container-${sender}`;
    
    let avatarHtml = '';
    if (sender === 'bot') {
        avatarHtml = `<div class="msg-avatar bot-avatar"><svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg></div>`;
    }
    
    let userAvatarHtml = '';
    if (sender === 'user') {
        userAvatarHtml = `<div class="msg-avatar user-avatar"><svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg></div>`;
    }

    div.innerHTML = `${sender === 'bot' ? avatarHtml : ''}
                     <div class="msg msg-${sender}">
                         <div class="msg-content">${htmlContent}</div>
                     </div>
                     ${sender === 'user' ? userAvatarHtml : ''}`;
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
    document.getElementById('renameForm').action = `/rename_chat/${id}/`;
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