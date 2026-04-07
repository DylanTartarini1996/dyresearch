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
  getViewType() {
    return VIEW_TYPE_HISTORY;
  }
  getDisplayText() {
    return "DyResearch History";
  }
  async onOpen() {
    this.refreshHistory();
  }
  async refreshHistory() {
    const container = this.containerEl.children[1];
    container.empty();
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
      this.refreshHistory();
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
    try {
      const response = await fetch(`http://localhost:8000/history/${this.plugin.userId}`);
      const history = await response.json();
      history.forEach((item) => {
        const sessionEl = list.createDiv({ cls: "history-item" });
        if (item.session_id === this.plugin.currentSessionId) sessionEl.addClass("is-active");
        const date = new Date(item.last_updated).toLocaleDateString();
        sessionEl.createEl("div", { text: item.session_id, cls: "session-name" });
        sessionEl.createEl("small", { text: `Last activity: ${date}` });
        sessionEl.onClickEvent(() => {
          this.plugin.currentSessionId = item.session_id;
          new ChatModal(this.app, this.plugin).open();
          this.refreshHistory();
        });
      });
    } catch (err) {
      list.createEl("p", { text: "Failed to load history." });
    }
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
    typeSelect.add(new Option("Personal Notes", "notes"));
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
          if (historyView) historyView.refreshHistory();
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
