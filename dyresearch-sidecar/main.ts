import { App, Plugin, Modal, MarkdownRenderer, setIcon } from 'obsidian';

// 1. Define an Interface for our API response
interface ChatResponse {
    response: string;
}

export default class DyResearchPlugin extends Plugin {
    async onload() {
        this.addRibbonIcon('bot', 'DyResearch Chat', () => {
            new ChatModal(this.app, this).open();
        });
    }
}

class ChatModal extends Modal {
    plugin: Plugin;

    constructor(app: App, plugin: Plugin) {
        super(app);
        this.plugin = plugin;
    }

    private sessionId: string = `obsidian_${Date.now()}`;
    private userId: string = 'dyresearch_plugin_user'

    onOpen() {
        const { contentEl } = this;
        contentEl.addClass('dy-chat-modal');
        
        contentEl.createEl('h2', { text: '🤖 DyResearch Assistant' });

        // Container for the conversation
        const chatHistory = contentEl.createDiv({ cls: 'chat-history' });
        
        // Input Area
        const inputContainer = contentEl.createDiv({ cls: 'chat-input-container' });
        const inputField = inputContainer.createEl('input', { 
            type: 'text', 
            placeholder: 'Type your command (e.g. "Create a note on Physics")...' 
        });

        // The "Send" logic
        inputField.addEventListener('keydown', async (e: KeyboardEvent) => {
            if (e.key === 'Enter' && inputField.value.trim() !== '') {
                const userQuery = inputField.value;
                inputField.value = '';

                // Add User Message to UI
                this.appendMessage(chatHistory, '👤 You', userQuery);

                // Add "Thinking" placeholder
                const aiMsgDiv = this.appendMessage(chatHistory, '🤖 AI', '...');
                
                try {
                    const apiResponse = await fetch('http://localhost:8000/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            message: userQuery,
                            session_id: this.sessionId,
                            user_id: this.userId
                        })
                    });

                    if (!apiResponse.ok) throw new Error('Server unreachable');

                    const data: ChatResponse = await apiResponse.json();

                    // Clear "..." and render the real Markdown
                    aiMsgDiv.empty(); 
                    
                    // 2. THE MAGIC: Use Obsidian's Markdown Engine
                    // This renders bold, lists, and code blocks perfectly.
                    await MarkdownRenderer.render(
                        this.app, 
                        data.response, 
                        aiMsgDiv, 
                        '', 
                        this.plugin
                    );

                } catch (err) {
                    aiMsgDiv.setText('❌ Error: Could not reach the Python sidecar.');
                }
                
                // Scroll to bottom
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }
        });
    }

    // Helper function to create message bubbles
    appendMessage(container: HTMLElement, sender: string, text: string): HTMLElement {
        const msgWrapper = container.createDiv({ cls: 'chat-msg-wrapper' });
        msgWrapper.createEl('small', { text: sender, cls: 'chat-sender' });
        return msgWrapper.createDiv({ cls: 'chat-msg-content', text: text });
    }
}