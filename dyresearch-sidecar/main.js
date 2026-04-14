var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// main.ts
var main_exports = {};
__export(main_exports, {
  HistoryView: () => HistoryView,
  VIEW_TYPE_HISTORY: () => VIEW_TYPE_HISTORY,
  default: () => DyResearchPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var VIEW_TYPE_HISTORY = "dyresearch-history-view";
var HistoryView = class extends import_obsidian.ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }
  plugin;
  // State to track which tab is active
  activeTab = "chats";
  // Library state
  libraryOffset = 0;
  libraryLimit = 20;
  // Chat state
  chatOffset = 0;
  chatLimit = 10;
  getViewType() {
    return VIEW_TYPE_HISTORY;
  }
  getDisplayText() {
    return "DyResearch History";
  }
  async onOpen() {
    this.refreshView();
  }
  async refreshView() {
    const container = this.containerEl.children[1];
    container.empty();
    const navContainer = container.createDiv({ cls: "dy-nav-tabs" });
    const chatsTab = navContainer.createEl("button", { text: "\u{1F4AC} Chats", cls: "dy-tab-btn" });
    const libTab = navContainer.createEl("button", { text: "\u{1F4DA} Library", cls: "dy-tab-btn" });
    if (this.activeTab === "chats") chatsTab.addClass("is-active-tab");
    if (this.activeTab === "library") libTab.addClass("is-active-tab");
    chatsTab.onClickEvent(() => {
      this.activeTab = "chats";
      this.refreshView();
    });
    libTab.onClickEvent(() => {
      this.activeTab = "library";
      this.refreshView();
    });
    if (this.activeTab === "chats") {
      await this.renderChatsTab(container);
    } else {
      await this.renderLibraryTab(container);
    }
  }
  async renderChatsTab(container) {
    const header = container.createDiv({ cls: "history-header" });
    header.createEl("h4", { text: "Research Sessions" });
    const buttonContainer = header.createDiv({ cls: "history-buttons" });
    const newChatBtn = buttonContainer.createEl("button", {
      cls: "dy-new-chat-btn",
      attr: { "aria-label": "New Session" }
    });
    (0, import_obsidian.setIcon)(newChatBtn, "plus");
    newChatBtn.onClickEvent(() => {
      this.plugin.currentSessionId = `obsidian_${Date.now()}`;
      new ChatModal(this.app, this.plugin).open();
      this.refreshView();
    });
    const closeBtn = buttonContainer.createEl("button", {
      cls: "dy-close-sidebar-btn",
      attr: { "aria-label": "Close Sidebar" }
    });
    (0, import_obsidian.setIcon)(closeBtn, "x");
    closeBtn.onClickEvent(() => {
      this.app.workspace.rightSplit.collapse();
    });
    const list = container.createDiv({ cls: "history-list" });
    const footer = container.createDiv({ cls: "history-footer" });
    this.chatOffset = 0;
    const loadChats = async () => {
      const loadingText = list.createEl("p", { text: "Loading sessions...", cls: "loading-text" });
      try {
        const url = `http://localhost:8000/history/${this.plugin.userId}?limit=${this.chatLimit}&offset=${this.chatOffset}`;
        const response = await fetch(url);
        const data = await response.json();
        loadingText.remove();
        data.sessions.forEach((item) => {
          const sessionEl = list.createDiv({ cls: "history-item" });
          if (item.session_id === this.plugin.currentSessionId) sessionEl.addClass("is-active");
          const titleContainer = sessionEl.createDiv({ cls: "session-title-container" });
          const nameEl = titleContainer.createEl("div", { text: item.session_id, cls: "session-name" });
          const editBtn = titleContainer.createEl("button", { cls: "dy-edit-btn", attr: { "aria-label": "Rename Session" } });
          (0, import_obsidian.setIcon)(editBtn, "pencil");
          const deleteBtn = titleContainer.createEl("button", { cls: "dy-delete-btn", attr: { "aria-label": "Delete Session" } });
          (0, import_obsidian.setIcon)(deleteBtn, "trash");
          const date = new Date(item.last_updated).toLocaleDateString();
          sessionEl.createEl("small", { text: `Last activity: ${date}` });
          sessionEl.onClickEvent((e) => {
            if (e.target.tagName === "INPUT") return;
            this.plugin.currentSessionId = item.session_id;
            new ChatModal(this.app, this.plugin).open();
            this.refreshView();
          });
          editBtn.onClickEvent((e) => {
            e.stopPropagation();
            nameEl.empty();
            const inputField = nameEl.createEl("input", {
              type: "text",
              value: item.session_id,
              cls: "session-rename-input"
            });
            editBtn.style.display = "none";
            inputField.focus();
            inputField.addEventListener("keydown", async (keyEvent) => {
              if (keyEvent.key === "Enter") {
                const newId = inputField.value.trim();
                if (!newId || newId === item.session_id) {
                  nameEl.setText(item.session_id);
                  editBtn.style.display = "flex";
                  return;
                }
                inputField.disabled = true;
                try {
                  const response2 = await fetch(`http://localhost:8000/sessions/${item.session_id}/rename`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      new_session_id: newId,
                      user_id: this.plugin.userId
                    })
                  });
                  if (!response2.ok) throw new Error("Rename failed");
                  if (this.plugin.currentSessionId === item.session_id) {
                    this.plugin.currentSessionId = newId;
                  }
                  this.refreshView();
                  new import_obsidian.Notice("Session renamed successfully.");
                } catch (err) {
                  new import_obsidian.Notice("Failed to rename session.");
                  nameEl.setText(item.session_id);
                  editBtn.style.display = "flex";
                }
              }
              if (keyEvent.key === "Escape") {
                nameEl.setText(item.session_id);
                editBtn.style.display = "flex";
              }
            });
          });
          deleteBtn.onClickEvent(async (e) => {
            e.stopPropagation();
            const confirmDelete = confirm(`Are you sure you want to delete the session "${item.session_id}"? This cannot be undone.`);
            if (!confirmDelete) return;
            try {
              const response2 = await fetch(`http://localhost:8000/sessions/${item.session_id}?user_id=${this.plugin.userId}`, {
                method: "DELETE"
              });
              if (response2.ok) {
                if (this.plugin.currentSessionId === item.session_id) this.plugin.currentSessionId = "";
                this.refreshView();
                new import_obsidian.Notice("Session deleted.");
              }
            } catch (err) {
              new import_obsidian.Notice("Failed to delete session.");
            }
          });
        });
        this.chatOffset += data.sessions.length;
        footer.empty();
        if (this.chatOffset < data.total) {
          const loadMoreBtn = footer.createEl("button", {
            text: "Load Older Chats",
            cls: "dy-load-more-btn"
          });
          loadMoreBtn.onClickEvent(() => loadChats());
        } else if (data.total > 0) {
          footer.createEl("p", { text: "End of history", cls: "text-muted" });
        }
      } catch (err) {
        loadingText.setText("Failed to load history.");
      }
    };
    await loadChats();
  }
  async renderUploadSection(container) {
    const uploadContainer = container.createDiv({ cls: "upload-section" });
    uploadContainer.createEl("h4", { text: "Upload File(s) to Library" });
    const metadataForm = uploadContainer.createDiv({ cls: "metadata-form" });
    const subjectInput = metadataForm.createEl("input", {
      type: "text",
      placeholder: "Subject (e.g. Quantum Computing)..."
    });
    const authorsInput = metadataForm.createEl("input", {
      type: "text",
      placeholder: "Authors (e.g. John Doe)..."
    });
    const typeSelect = metadataForm.createEl("select");
    typeSelect.add(new Option("Research Paper", "paper"));
    typeSelect.add(new Option("Book / Chapter", "book"));
    typeSelect.add(new Option("Manual", "manual"));
    const fileInput = uploadContainer.createEl("input", {
      attr: { type: "file", multiple: "true", accept: ".pdf,.md,.docx,.txt" },
      cls: "hidden-file-input"
    });
    const uploadBtn = uploadContainer.createEl("button", {
      text: "\u{1F4C1} Select & Upload Docs",
      cls: "dy-upload-btn"
    });
    uploadBtn.onClickEvent(() => fileInput.click());
    fileInput.addEventListener("change", async () => {
      if (!fileInput.files || fileInput.files.length === 0) return;
      const formData = new FormData();
      for (let i = 0; i < fileInput.files.length; i++) {
        formData.append("files", fileInput.files[i]);
      }
      formData.append("subject", subjectInput.value.trim() || "General");
      formData.append("authors", authorsInput.value.trim() || "Unknown");
      formData.append("source_type", typeSelect.value);
      formData.append("metadata_json", JSON.stringify({
        uploaded_via: "obsidian_ui",
        batch_id: Date.now()
      }));
      uploadBtn.setText("\u23F3 Ingesting...");
      uploadBtn.disabled = true;
      try {
        const response = await fetch("http://localhost:8000/ingest", {
          method: "POST",
          body: formData
          // The browser automatically sets the correct multipart headers
        });
        if (!response.ok) throw new Error("Server rejected the upload");
        const result = await response.json();
        const successCount = result.results.filter((r) => r.status === "success").length;
        new import_obsidian.Notice(`Successfully ingested ${successCount} files!`);
        subjectInput.value = "";
        authorsInput.value = "";
      } catch (err) {
        console.error(err);
        new import_obsidian.Notice("Failed to upload documents. Check console for details.");
      } finally {
        uploadBtn.setText("\u{1F4C1} Select & Upload Docs");
        uploadBtn.disabled = false;
        fileInput.value = "";
      }
    });
  }
  async renderLibraryTab(container) {
    await this.renderUploadSection(container);
    container.createEl("hr", { cls: "library-divider" });
    const libContainer = container.createDiv({ cls: "library-container" });
    libContainer.createEl("h4", { text: "Files in Library" });
    const list = libContainer.createDiv({ cls: "library-list" });
    const footer = libContainer.createDiv({ cls: "library-footer" });
    this.libraryOffset = 0;
    const loadDocs = async () => {
      const loadingNotice = list.createEl("p", { text: "Loading...", cls: "loading-text" });
      try {
        const url = `http://localhost:8000/library?limit=${this.libraryLimit}&offset=${this.libraryOffset}`;
        const response = await fetch(url);
        const data = await response.json();
        loadingNotice.remove();
        data.documents.forEach((doc) => {
          const card = list.createDiv({ cls: "library-card" });
          const header = card.createDiv({ cls: "library-card-header" });
          const titleInfo = header.createDiv({ cls: "library-title-group" });
          titleInfo.createEl("strong", { text: doc.title });
          titleInfo.createEl("span", { text: doc.type, cls: "badge-type" });
          const libDeleteBtn = header.createEl("button", { cls: "dy-delete-btn-small" });
          (0, import_obsidian.setIcon)(libDeleteBtn, "trash");
          libDeleteBtn.onClickEvent(async () => {
            if (!confirm(`Delete "${doc.title}" from Knowledge Base?`)) return;
            try {
              const response2 = await fetch(`http://localhost:8000/library/${encodeURIComponent(doc.title)}`, {
                method: "DELETE"
              });
              if (response2.ok) {
                this.refreshView();
                new import_obsidian.Notice("Document removed.");
              }
            } catch (err) {
              new import_obsidian.Notice("Failed to remove document.");
            }
          });
          card.createEl("div", { text: `\u{1F464} ${doc.authors}`, cls: "library-meta" });
          card.createEl("div", { text: `\u{1F3F7}\uFE0F ${doc.subject}`, cls: "library-meta" });
          card.createEl("div", { text: `\u{1F9E9} ${doc.chunks} chunks indexed`, cls: "library-meta chunks-info" });
        });
        this.libraryOffset += data.documents.length;
        footer.empty();
        if (this.libraryOffset < data.total) {
          const loadMoreBtn = footer.createEl("button", {
            text: "Load More",
            cls: "dy-load-more-btn"
          });
          loadMoreBtn.onClickEvent(() => loadDocs());
        } else if (data.total > 0) {
          footer.createEl("p", { text: "All documents loaded.", cls: "text-muted" });
        } else {
          list.createEl("p", { text: "No documents found.", cls: "text-muted" });
        }
      } catch (err) {
        loadingNotice.setText("\u274C Error loading library.");
      }
    };
    await loadDocs();
  }
};
var DyResearchPlugin = class extends import_obsidian.Plugin {
  currentSessionId = `obsidian_${Date.now()}`;
  userId = "dyresearch_plugin_user";
  async onload() {
    this.registerView(VIEW_TYPE_HISTORY, (leaf) => new HistoryView(leaf, this));
    this.addRibbonIcon("bot", "DyResearch Chat", () => {
      new ChatModal(this.app, this).open();
    });
    this.addRibbonIcon("history", "View History", () => {
      this.activateView();
    });
  }
  async activateView() {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(VIEW_TYPE_HISTORY)[0];
    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE_HISTORY, active: true });
    }
    workspace.revealLeaf(leaf);
  }
};
var ChatModal = class extends import_obsidian.Modal {
  plugin;
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
  }
  async onOpen() {
    const { contentEl } = this;
    contentEl.addClass("dy-chat-modal");
    contentEl.createEl("h2", { text: "\u{1F916} DyResearch Assistant" });
    contentEl.createEl("p", {
      text: `Session: ${this.plugin.currentSessionId}`,
      cls: "chat-session-id"
    });
    const chatHistory = contentEl.createDiv({ cls: "chat-history" });
    try {
      const historyResponse = await fetch(`http://localhost:8000/sessions/${this.plugin.currentSessionId}/messages`);
      const messages = await historyResponse.json();
      for (const msg of messages) {
        const msgDiv = this.appendMessage(chatHistory, msg.role, "");
        await import_obsidian.MarkdownRenderer.render(this.app, msg.content, msgDiv, "", this.plugin);
      }
      chatHistory.scrollTop = chatHistory.scrollHeight;
    } catch (err) {
      console.error("Could not load session history", err);
    }
    const inputContainer = contentEl.createDiv({ cls: "chat-input-container" });
    const inputField = inputContainer.createEl("input", {
      type: "text",
      placeholder: "Type your message..."
    });
    inputField.addEventListener("keydown", async (e) => {
      var _a;
      if (e.key === "Enter" && inputField.value.trim() !== "") {
        const userQuery = inputField.value;
        inputField.value = "";
        this.appendMessage(chatHistory, "\u{1F464} You", userQuery);
        const aiMsgDiv = this.appendMessage(chatHistory, "\u{1F916} AI", "...");
        try {
          const apiResponse = await fetch("http://localhost:8000/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: userQuery,
              session_id: this.plugin.currentSessionId,
              user_id: this.plugin.userId
            })
          });
          if (!apiResponse.ok) throw new Error("Server unreachable");
          const data = await apiResponse.json();
          aiMsgDiv.empty();
          await import_obsidian.MarkdownRenderer.render(this.app, data.message, aiMsgDiv, "", this.plugin);
          const historyView = (_a = this.app.workspace.getLeavesOfType(VIEW_TYPE_HISTORY)[0]) == null ? void 0 : _a.view;
          if (historyView) historyView.refreshView();
        } catch (err) {
          aiMsgDiv.setText("\u274C Error: Could not reach Python sidecar.");
        }
        chatHistory.scrollTop = chatHistory.scrollHeight;
      }
    });
  }
  appendMessage(container, sender, text) {
    const msgWrapper = container.createDiv({ cls: "chat-msg-wrapper" });
    msgWrapper.createEl("small", { text: sender, cls: "chat-sender" });
    return msgWrapper.createDiv({ cls: "chat-msg-content", text });
  }
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  HistoryView,
  VIEW_TYPE_HISTORY
});
