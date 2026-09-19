const API_URL = "https://study-desk-rag-api.onrender.com/ask";

const chatArea = document.getElementById("chatArea");
const emptyState = document.getElementById("emptyState");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");

let selectedSubject = "all";

const STORAGE_KEY = "study_desk_chat_history";

function saveMessageToHistory(role, content, sources = []) {
  const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  history.push({ role, content, sources, subject: selectedSubject });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function loadChatHistory() {
  const history = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  if (history.length === 0) return;
  emptyState.style.display = "none";

  history.forEach(msg => {
    if (msg.role === "user") {
      renderUserMessage(msg.content);
    } else {
      renderAssistantMessage(msg.content, msg.sources);
    }
  });

  chatArea.scrollTop = chatArea.scrollHeight;
}

function clearChatHistory() {
  localStorage.removeItem(STORAGE_KEY);
  chatArea.innerHTML = "";
  chatArea.appendChild(emptyState);
  emptyState.style.display = "block";
}

const chips = document.querySelectorAll(".chip");
chips.forEach(chip => {
  chip.addEventListener("click", () => {
    chips.forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    selectedSubject = chip.dataset.subject;
  });
});

document.getElementById("clearChatBtn").addEventListener("click", clearChatHistory);

document.querySelectorAll(".suggestion-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    questionInput.value = btn.textContent;
    chatForm.dispatchEvent(new Event("submit"));
  });
});

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

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
  saveMessageToHistory("user", text);
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
  saveMessageToHistory("assistant", answer, sources);
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

loadChatHistory();