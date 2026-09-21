const API_URL = "https://study-desk-rag-api.onrender.com/ask";
const STORAGE_KEY = "study_desk_conversations";

const chatArea = document.getElementById("chatArea");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const conversationList = document.getElementById("conversationList");
const newChatBtn = document.getElementById("newChatBtn");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");

const UPLOAD_URL = "https://study-desk-rag-api.onrender.com/upload";
const uploadToggle = document.getElementById("uploadToggle");
const uploadForm = document.getElementById("uploadForm");
const pdfFileInput = document.getElementById("pdfFileInput");
const uploadSubject = document.getElementById("uploadSubject");
const uploadSubmitBtn = document.getElementById("uploadSubmitBtn");
const uploadStatus = document.getElementById("uploadStatus");

let selectedSubject = "all";
let currentConversationId = null;

// ---------- Storage helpers ----------

function loadAllConversations() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveAllConversations(conversations) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

function getCurrentConversation(conversations) {
  return conversations.find(c => c.id === currentConversationId);
}

function createNewConversationId() {
  return "conv_" + Date.now() + "_" + Math.random().toString(36).slice(2, 8);
}

// Adds a message to the current conversation, creating the conversation
// on first message if it doesn't exist yet.
function persistMessage(role, content, sources = []) {
  const conversations = loadAllConversations();
  let convo = getCurrentConversation(conversations);

  if (!convo) {
    convo = {
      id: currentConversationId,
      title: role === "user" ? content.slice(0, 40) : "New conversation",
      messages: [],
      updatedAt: Date.now()
    };
    conversations.unshift(convo);
  }

  convo.messages.push({ role, content, sources });
  convo.updatedAt = Date.now();

  // Title the conversation after the first user message
  if (role === "user" && convo.messages.filter(m => m.role === "user").length === 1) {
    convo.title = content.slice(0, 40) + (content.length > 40 ? "…" : "");
  }

  saveAllConversations(conversations);
  renderSidebar();
}

// ---------- Sidebar rendering ----------

function renderSidebar() {
  const conversations = loadAllConversations().sort((a, b) => b.updatedAt - a.updatedAt);
  conversationList.innerHTML = "";

  if (conversations.length === 0) {
    conversationList.innerHTML = `<div class="sidebar-empty">No past conversations yet. Ask something to start one.</div>`;
    return;
  }

  conversations.forEach(convo => {
    const item = document.createElement("div");
    item.className = "conversation-item" + (convo.id === currentConversationId ? " active" : "");
    item.innerHTML = `
      <span class="conversation-title"></span>
      <button class="conversation-delete" title="Delete">✕</button>
    `;
    item.querySelector(".conversation-title").textContent = convo.title || "New conversation";

    item.addEventListener("click", (e) => {
      if (e.target.closest(".conversation-delete")) return;
      loadConversation(convo.id);
    });

    item.querySelector(".conversation-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteConversation(convo.id);
    });

    conversationList.appendChild(item);
  });
}

function deleteConversation(id) {
  let conversations = loadAllConversations();
  conversations = conversations.filter(c => c.id !== id);
  saveAllConversations(conversations);

  if (id === currentConversationId) {
    startNewChat();
  } else {
    renderSidebar();
  }
}

// ---------- Loading / starting conversations ----------

function loadConversation(id) {
  const conversations = loadAllConversations();
  const convo = conversations.find(c => c.id === id);
  if (!convo) return;

  currentConversationId = id;
  chatArea.innerHTML = "";
  chatArea.appendChild(emptyState);
  emptyState.style.display = "none";

  convo.messages.forEach(msg => {
    if (msg.role === "user") {
      renderUserMessage(msg.content);
    } else {
      renderAssistantMessage(msg.content, msg.sources);
    }
  });

  chatArea.scrollTop = chatArea.scrollHeight;
  renderSidebar();
  closeSidebarOnMobile();
}

function startNewChat() {
  currentConversationId = createNewConversationId();
  chatArea.innerHTML = "";
  chatArea.appendChild(emptyState);
  emptyState.style.display = "block";
  renderSidebar();
  closeSidebarOnMobile();
}

function closeSidebarOnMobile() {
  sidebar.classList.remove("open");
}

// ---------- Subject chips ----------

const chips = document.querySelectorAll(".chip");
chips.forEach(chip => {
  chip.addEventListener("click", () => {
    chips.forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    selectedSubject = chip.dataset.subject;
  });
});

// ---------- Sidebar toggle (mobile) ----------

sidebarToggle.addEventListener("click", () => {
  sidebar.classList.toggle("open");
});

newChatBtn.addEventListener("click", startNewChat);

uploadToggle.addEventListener("click", () => {
  const isHidden = uploadForm.style.display === "none";
  uploadForm.style.display = isHidden ? "flex" : "none";
  uploadStatus.textContent = "";
});

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const file = pdfFileInput.files[0];
  const subject = uploadSubject.value;

  if (!file || !subject) return;

  uploadSubmitBtn.disabled = true;
  uploadStatus.className = "upload-status";
  uploadStatus.textContent = "Uploading and processing...";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("subject", subject);

  try {
    const response = await fetch(UPLOAD_URL, {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.error) {
      uploadStatus.className = "upload-status error";
      uploadStatus.textContent = data.error;
    } else {
      uploadStatus.className = "upload-status success";
      uploadStatus.textContent = `${data.message} (${data.chunks_added} chunks added). Note: won't persist across server restarts.`;
      uploadForm.reset();
    }
  } catch (err) {
    uploadStatus.className = "upload-status error";
    uploadStatus.textContent = "Upload failed. Check your connection and try again.";
    console.error(err);
  } finally {
    uploadSubmitBtn.disabled = false;
  }
});

// ---------- Suggestions ----------

document.querySelectorAll(".suggestion-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    questionInput.value = btn.textContent;
    chatForm.dispatchEvent(new Event("submit"));
  });
});

// ---------- Chat submission ----------

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  if (!currentConversationId) {
    currentConversationId = createNewConversationId();
  }

  if (emptyState) emptyState.style.display = "none";

  addUserMessage(question);
  questionInput.value = "";
  sendBtn.disabled = true;

  const loadingCard = addLoadingCard();

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, subject: selectedSubject })
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const data = await response.json();
    loadingCard.remove();
    addAssistantMessage(data.answer, data.sources);
  } catch (err) {
    loadingCard.remove();
    addErrorMessage("Couldn't reach the study assistant. Make sure the backend server is running.");
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    chatArea.scrollTop = chatArea.scrollHeight;
  }
});

// ---------- Rendering helpers ----------

function renderUserMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `<div class="bubble-user"></div>`;
  row.querySelector(".bubble-user").textContent = text;
  chatArea.appendChild(row);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addUserMessage(text) {
  renderUserMessage(text);
  persistMessage("user", text);
}

function addLoadingCard() {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="assistant-avatar">S</div>
    <div class="card-assistant loading-card">
      Searching your notes
      <span class="typing-dots"><span></span><span></span><span></span></span>
    </div>
  `;
  chatArea.appendChild(row);
  chatArea.scrollTop = chatArea.scrollHeight;
  return row;
}

function renderAssistantMessage(answer, sources) {
  const subjectClass = sources.some(s => s.startsWith("dbms")) &&
                        !sources.some(s => s.startsWith("os"))
                        ? "subject-dbms" : "";

  const row = document.createElement("div");
  row.className = "message-row assistant";

  const sourceTags = sources.map(s => `<span class="source-tag">${s}</span>`).join("");

  row.innerHTML = `
    <div class="assistant-avatar">S</div>
    <div class="card-assistant ${subjectClass}">
      <div class="answer-text"></div>
      <div class="sources">
        <span class="sources-label">SOURCES</span>
        ${sourceTags}
      </div>
    </div>
  `;
  row.querySelector(".answer-text").textContent = answer;
  chatArea.appendChild(row);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addAssistantMessage(answer, sources) {
  renderAssistantMessage(answer, sources);
  persistMessage("assistant", answer, sources);
}

function addErrorMessage(text) {
  const row = document.createElement("div");
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="assistant-avatar">S</div>
    <div class="card-assistant" style="border-color:#e05b5b;"></div>
  `;
  row.querySelector(".card-assistant").textContent = text;
  chatArea.appendChild(row);
}

// ---------- Init ----------

renderSidebar();
startNewChat();

// Default the sidebar open on wider screens, closed on mobile
if (window.innerWidth > 768) {
  sidebar.classList.add("open");
}