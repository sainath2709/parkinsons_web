const API_BASE = '';
let authToken = localStorage.getItem('token');
let username = localStorage.getItem('username');

const authView = document.getElementById('auth-view');
const appView = document.getElementById('app-view');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const authError = document.getElementById('auth-error');
const userDisplay = document.getElementById('welcome-user');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultCard = document.getElementById('result-card');
const resultText = document.getElementById('result-text');
const historyBody = document.getElementById('history-body');
const resultCamImg = document.getElementById('result-cam-img');
const imageModal = document.getElementById('image-modal');
const modalOrig = document.getElementById('modal-orig');
const modalCam = document.getElementById('modal-cam');

// Init
if (authToken) {
    showApp();
} else {
    showAuth();
}

function showAuth() {
    authView.style.display = 'flex';
    appView.style.display = 'none';
}

function showApp() {
    authView.style.display = 'none';
    appView.style.display = 'flex';
    userDisplay.innerText = username;
    fetchHistory();
}

function switchAuth(type) {
    if (authError) authError.innerText = '';
    if (type === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
    } else {
        registerForm.style.display = 'block';
        loginForm.style.display = 'none';
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    authToken = null;
    username = null;
    
    // Reset DOM state so the next user doesn't see old data
    if (chatMessages) {
        chatMessages.innerHTML = '<div class="message bot-message">Hello! I am your NeuroCare medical assistant. How can I help you regarding Parkinson\'s disease today?</div>';
    }
    if (resultCard) resultCard.style.display = 'none';
    if (historyBody) historyBody.innerHTML = '';
    
    showAuth();
}

// Auth Handlers
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const u = document.getElementById('l-username').value;
    const p = document.getElementById('l-password').value;
    
    try {
        const res = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, password: p})
        });
        const data = await res.json();
        if (res.ok) {
            authToken = data.token;
            username = data.username;
            localStorage.setItem('token', authToken);
            localStorage.setItem('username', username);
            showApp();
            loginForm.reset();
            authError.innerText = '';
        } else {
            authError.innerText = data.error;
            authError.style.color = 'var(--danger)';
        }
    } catch(err) { authError.innerText = 'Network error'; }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const u = document.getElementById('r-username').value;
    const email = document.getElementById('r-email').value;
    const p = document.getElementById('r-password').value;
    
    try {
        const res = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: u, email: email, password: p})
        });
        const data = await res.json();
        if (res.ok) {
            switchAuth('login');
            authError.innerText = 'Registration successful. Please login.';
            authError.style.color = 'var(--success)';
            registerForm.reset();
        } else {
            authError.innerText = data.error;
            authError.style.color = 'var(--danger)';
        }
    } catch(err) { authError.innerText = 'Network error'; }
});

// Drag & Drop
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleUpload(e.dataTransfer.files[0]);
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) handleUpload(fileInput.files[0]);
});

async function handleUpload(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file');
        return;
    }
    
    const formData = new FormData();
    formData.append('image', file);
    
    dropZone.innerHTML = '<div class="loader"></div><p style="margin-top: 1rem">Analyzing Scan...</p>';
    
    try {
        const res = await fetch(`${API_BASE}/predict`, {
            method: 'POST',
            headers: {'Authorization': `Bearer ${authToken}`},
            body: formData
        });
        const data = await res.json();
        
        dropZone.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i><p>Drag & Drop your MRI (.jpg, .png)</p><p class="text-sm">or click to browse</p>';
        fileInput.value = '';
        
        if (res.ok) {
            displayResult(data.result, data.confidence, data.heatmap_path);
            fetchHistory(); // Refresh history
        } else {
            if (res.status === 401) { logout(); }
            alert(data.error || 'Upload failed');
        }
    } catch (err) {
        dropZone.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i><p>Drag & Drop your MRI (.jpg, .png)</p><p class="text-sm">or click to browse</p>';
        alert('Network error during upload');
    }
}

function displayResult(result, confidence, camPath) {
    const isHealthy = result === "Healthy";
    resultText.innerHTML = `<i class="fas ${isHealthy ? 'fa-check-circle' : 'fa-exclamation-triangle'}"></i> Analysis: <strong>${result}</strong>`;
    resultText.className = 'result-header ' + (isHealthy ? 'healthy' : 'parkinsons');
    
    // Animate the confidence bar
    const fill = document.getElementById('confidence-fill');
    const label = document.getElementById('confidence-text');
    fill.style.width = '0%';
    
    setTimeout(() => {
        fill.style.width = confidence;
        fill.style.background = isHealthy ? 'linear-gradient(90deg, #10b981, #34d399)' : 'linear-gradient(90deg, #f43f5e, #fb7185)';
        label.innerText = `Model Confidence: ${confidence}`;
    }, 100);
    
    resultCard.style.display = 'block';
    if (camPath) {
        resultCamImg.src = camPath;
        resultCamImg.style.display = 'block';
    } else {
        resultCamImg.style.display = 'none';
    }
    
    if (result === "Parkinson's") {
        resultCard.style.borderLeft = '4px solid var(--danger)';
    } else {
        resultCard.style.borderLeft = '4px solid var(--success)';
    }
}

async function fetchHistory() {
    try {
        const res = await fetch(`${API_BASE}/history`, {
            headers: {'Authorization': `Bearer ${authToken}`}
        });
        
        if (res.status === 401) { logout(); return; }
        
        const data = await res.json();
        if (res.ok) {
            historyBody.innerHTML = '';
            data.history.forEach(scan => {
                const date = new Date(scan.timestamp).toLocaleString();
                const badgeClass = scan.result === "Parkinson's" ? 'badge-parkinsons' : 'badge-healthy';
                const percent = (scan.confidence * 100).toFixed(1) + '%';
                
                const tr = document.createElement('tr');
                tr.className = 'clickable-row';
                tr.onclick = () => openModal(scan.image_path, scan.heatmap_path);
                tr.innerHTML = `
                    <td>${date}</td>
                    <td><span class="history-badge ${badgeClass}">${scan.result}</span></td>
                    <td>${percent}</td>
                    <td><i class="fa-solid fa-image" style="color: var(--primary);"></i> View</td>
                `;
                historyBody.appendChild(tr);
            });
        }
    } catch(err) { console.error('Failed to fetch history', err); }
}

// Modal functionality
function openModal(origPath, camPath) {
    if (!origPath || !camPath) {
        alert("Images cannot be displayed for this record because it was processed before the visual Grad-CAM history feature was added to the database!");
        return; 
    }
    modalOrig.src = origPath;
    modalCam.src = camPath;
    imageModal.style.display = 'flex';
}

function closeModal() {
    imageModal.style.display = 'none';
}

// Chatbot functionality
const chatPanel = document.getElementById('chat-panel');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');

function toggleChat() {
    if (chatPanel) {
        chatPanel.classList.toggle('active');
        if (chatPanel.classList.contains('active')) chatInput.focus();
    }
}

chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    // Add user message
    appendMessage(text, 'user-message');
    chatInput.value = '';
    
    // Add loader
    const loaderId = 'loader-' + Date.now();
    appendMessage('<div class="loader" style="width:1rem;height:1rem;border-width:2px;border-top-color:var(--primary);"></div>', 'bot-message', loaderId);
    
    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({message: text})
        });
        
        const loaderElem = document.getElementById(loaderId);
        if (loaderElem) loaderElem.remove();
        
        if (res.status === 401) {
            appendMessage("Please login to use the chat assistant.", 'bot-message');
            logout();
            return;
        }
        
        const data = await res.json();
        if (res.ok) {
            let formattedResponse = data.response
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
            appendMessage(formattedResponse, 'bot-message');
        } else {
            appendMessage("Error: " + (data.error || "Failed to get response"), 'bot-message');
        }
    } catch(err) {
        const loaderElem = document.getElementById(loaderId);
        if (loaderElem) loaderElem.remove();
        appendMessage("Network error communicating with medical assistant.", 'bot-message');
    }
}

function appendMessage(htmlContent, className, id = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ' + className;
    if (id) msgDiv.id = id;
    msgDiv.innerHTML = htmlContent;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
