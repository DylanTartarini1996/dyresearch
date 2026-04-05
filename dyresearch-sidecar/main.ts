import { App, Plugin, Modal, MarkdownRenderer, ItemView, WorkspaceLeaf, setIcon } from 'obsidian';

export const VIEW_TYPE_HISTORY = "dyresearch-history-view";

interface ChatResponse {
    message: string; 
}

interface SessionInfo {
    session_id: string;
    last_updated: string;
}

export class HistoryView extends ItemView {
    constructor(leaf: WorkspaceLeaf, private plugin: DyResearchPlugin) {
        super(leaf);
    }

    getViewType() { return VIEW_TYPE_HISTORY; }
    getDisplayText() { return "DyResearch History"; }

    async onOpen() {
        this.refreshHistory();
    }

    async refreshHistory() {
        const container = this.containerEl.children[1];
        container.empty();
        
        // --- Header with New Chat Button ---
        const header = container.createDiv({ cls: 'history-header' });
        header.createEl("h4", { text: "Research Sessions" });
        
        const buttonContainer = header.createDiv({ cls: 'history-buttons' });

        const newChatBtn = buttonContainer.createEl("button", { 
            cls: 'dy-new-chat-btn',
            attr: { "aria-label": "New Session" } 
        });
        setIcon(newChatBtn, 'plus');
        newChatBtn.onClickEvent(() => {
            this.plugin.currentSessionId = `obsidian_${Date.now()}`;
            new ChatModal(this.app, this.plugin).open();
            this.refreshHistory();
        });

        const closeBtn = buttonContainer.createEl("button", { 
            cls: 'dy-close-sidebar-btn',
            attr: { "aria-label": "Close Sidebar" } 
        });
        setIcon(closeBtn, 'x'); // Uses Obsidian's native 'x' icon
        closeBtn.onClickEvent(() => {
            this.app.workspace.rightSplit.collapse();
        });

        // --- Session List ---
        const list = container.createDiv({ cls: "history-list" });

        try {
            const response = await fetch(`http://localhost:8000/history/${this.plugin.userId}`);
            const history: SessionInfo[] = await response.json();

            history.forEach(item => {
                const sessionEl = list.createDiv({ cls: "history-item" });
                if (item.session_id === this.plugin.currentSessionId) sessionEl.addClass('is-active');

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
    }
}

export default class DyResearchPlugin extends Plugin {
    public currentSessionId: string = `obsidian_${Date.now()}`;
    public userId: string = 'dyresearch_plugin_user';

    async onload() {
        this.registerView(VIEW_TYPE_HISTORY, (leaf) => new HistoryView(leaf, this));

        this.addRibbonIcon('bot', 'DyResearch Chat', () => {
            new ChatModal(this.app, this).open();
        });

        this.addRibbonIcon('history', 'View History', () => {
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
}

class ChatModal extends Modal {
    plugin: DyResearchPlugin;

    constructor(app: App, plugin: DyResearchPlugin) {
        super(app);
        this.plugin = plugin;
    }

    async onOpen() {
        const { contentEl } = this;
        contentEl.addClass('dy-chat-modal');
        
        contentEl.createEl('h2', { text: '🤖 DyResearch Assistant' });
        contentEl.createEl('p', { 
            text: `Session: ${this.plugin.currentSessionId}`, 
            cls: 'chat-session-id' 
        });

        const chatHistory = contentEl.createDiv({ cls: 'chat-history' });
        
        try {
            const historyResponse = await fetch(`http://localhost:8000/sessions/${this.plugin.currentSessionId}/messages`);
            const messages = await historyResponse.json();
            
            for (const msg of messages) {
                const msgDiv = this.appendMessage(chatHistory, msg.role, '');
                // Render as Markdown so old code blocks/bolding look right
                await MarkdownRenderer.render(this.app, msg.content, msgDiv, '', this.plugin);
            }
            // Scroll to the bottom after loading
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } catch (err) {
            console.error("Could not load session history", err);
        }
        
        const inputContainer = contentEl.createDiv({ cls: 'chat-input-container' });
        const inputField = inputContainer.createEl('input', { 
            type: 'text', 
            placeholder: 'Type your message...' 
        });

        inputField.addEventListener('keydown', async (e: KeyboardEvent) => {
            if (e.key === 'Enter' && inputField.value.trim() !== '') {
                const userQuery = inputField.value;
                inputField.value = '';

                this.appendMessage(chatHistory, '👤 You', userQuery);
                const aiMsgDiv = this.appendMessage(chatHistory, '🤖 AI', '...');
                
                try {
                    const apiResponse = await fetch('http://localhost:8000/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            message: userQuery,
                            session_id: this.plugin.currentSessionId,
                            user_id: this.plugin.userId
                        })
                    });

                    if (!apiResponse.ok) throw new Error('Server unreachable');
                    const data: ChatResponse = await apiResponse.json();

                    aiMsgDiv.empty(); 
                    await MarkdownRenderer.render(this.app, data.message, aiMsgDiv, '', this.plugin);

                    // Refresh history sidebar to update timestamps
                    const historyView = this.app.workspace.getLeavesOfType(VIEW_TYPE_HISTORY)[0]?.view as HistoryView;
                    if (historyView) historyView.refreshHistory();

                } catch (err) {
                    aiMsgDiv.setText('❌ Error: Could not reach Python sidecar.');
                }
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
        });
    }

    appendMessage(container: HTMLElement, sender: string, text: string): HTMLElement {
        const msgWrapper = container.createDiv({ cls: 'chat-msg-wrapper' });
        msgWrapper.createEl('small', { text: sender, cls: 'chat-sender' });
        return msgWrapper.createDiv({ cls: 'chat-msg-content', text: text });
    }
}