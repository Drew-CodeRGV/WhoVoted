/* llm-chat.js — LLM-Powered Query Assistant
 * Natural language interface for querying voter data
 */

(function () {
    'use strict';

    class LLMChat {
        constructor() {
            this.chatHistory = [];
            this.isProcessing = false;
            this.checkAvailability();
        }

        async checkAvailability() {
            try {
                const resp = await fetch('/api/llm/status');
                const status = await resp.json();
                
                if (status.available) {
                    this.initUI();
                } else {
                    console.warn('[LLM Chat] Not available:', status.error || 'Service unavailable');
                }
            } catch (e) {
                console.warn('[LLM Chat] Status check failed:', e.message || e);
            }
        }

        initUI() {
            // Add chat button to toolbar
            const chatBtn = document.createElement('button');
            chatBtn.id = 'llmChatBtn';
            chatBtn.className = 'panel-icon-btn';
            chatBtn.innerHTML = '🤖';
            chatBtn.title = 'Ask Questions (AI Assistant)';
            chatBtn.onclick = () => this.openChat();
            
            const panelIcons = document.querySelector('.panel-icons');
            if (panelIcons) {
                panelIcons.appendChild(chatBtn);
            }
        }

        openChat() {
            // Remove existing modal
            const existing = document.getElementById('llmChatModal');
            if (existing) {
                existing.remove();
                return;
            }

            const modal = document.createElement('div');
            modal.id = 'llmChatModal';
            modal.className = 'llm-chat-modal';
            modal.innerHTML = `
                <div class="llm-chat-backdrop"></div>
                <div class="llm-chat-container">
                    <div class="llm-chat-header">
                        <div class="llm-chat-header-content">
                            <span class="llm-chat-icon">🤖</span>
                            <div>
                                <h3>AI Query Assistant</h3>
                                <p>Ask questions about your voter data in plain English</p>
                            </div>
                        </div>
                        <button class="llm-chat-close">&times;</button>
                    </div>
                    <div class="llm-chat-messages" id="llmChatMessages">
                        <div class="llm-welcome-message">
                            <p><strong>Welcome!</strong> I can help you query voter data using natural language.</p>
                            <p><strong>Try asking:</strong></p>
                            <ul>
                                <li>"Show me voters in TX-15 who voted in 2024 but not 2026"</li>
                                <li>"What's the turnout rate by age group in Hidalgo County?"</li>
                                <li>"Find new voters who are registered Democrats"</li>
                                <li>"How many voters switched from Republican to Democratic?"</li>
                            </ul>
                        </div>
                    </div>
                    <div class="llm-chat-input-container">
                        <input type="text" 
                               id="llmChatInput" 
                               class="llm-chat-input"
                               placeholder="Ask a question about voter data..."
                               autocomplete="off">
                        <button id="llmChatSend" class="llm-chat-send-btn">
                            <span class="llm-send-icon">➤</span>
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Event listeners
            modal.querySelector('.llm-chat-backdrop').onclick = () => this.closeChat();
            modal.querySelector('.llm-chat-close').onclick = () => this.closeChat();
            modal.querySelector('#llmChatSend').onclick = () => this.sendMessage();
            
            const input = modal.querySelector('#llmChatInput');
            input.onkeypress = (e) => {
                if (e.key === 'Enter' && !this.isProcessing) {
                    this.sendMessage();
                }
            };
            
            // Focus input
            setTimeout(() => input.focus(), 100);
        }

        closeChat() {
            const modal = document.getElementById('llmChatModal');
            if (modal) modal.remove();
        }

        async sendMessage() {
            if (this.isProcessing) return;

            const input = document.getElementById('llmChatInput');
            const question = input.value.trim();
            
            if (!question) return;

            // Add user message
            this.addMessage('user', question);
            input.value = '';
            this.isProcessing = true;

            // Show loading
            const loadingId = this.addMessage('assistant', 'Thinking...', true);

            try {
                const resp = await fetch('/api/llm/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ 
                        question,
                        context: this.getContext()
                    })
                });

                const data = await resp.json();

                // Remove loading message
                this.removeMessage(loadingId);

                if (data.success) {
                    // Show SQL query (collapsible)
                    this.addSQLMessage(data.sql);

                    // Show results
                    if (data.count > 0) {
                        this.addTableMessage(data.results, data.columns, data.count);
                        
                        // Show explanation
                        if (data.explanation) {
                            this.addMessage('assistant', data.explanation);
                        }

                        // Show suggestions
                        if (data.suggestions && data.suggestions.length > 0) {
                            this.addSuggestionsMessage(data.suggestions);
                        }
                    } else {
                        this.addMessage('assistant', 'No results found for your query.');
                    }
                } else {
                    this.addMessage('assistant', `❌ Error: ${data.error}`, false, 'error');
                    if (data.sql) {
                        this.addSQLMessage(data.sql);
                    }
                }
            } catch (e) {
                this.removeMessage(loadingId);
                this.addMessage('assistant', `❌ Request failed: ${e.message}`, false, 'error');
            } finally {
                this.isProcessing = false;
            }
        }

        getContext() {
            // Get current map context (district, county, etc.)
            const context = {};
            
            // Check if user is viewing a specific district
            if (window.activeDistrict) {
                context.district = window.activeDistrict.properties.district_id;
            }
            
            // Check if user has a county filter
            if (window.currentCounty) {
                context.county = window.currentCounty;
            }
            
            return context;
        }

        addMessage(role, content, loading = false, type = 'normal') {
            const messages = document.getElementById('llmChatMessages');
            const msg = document.createElement('div');
            const msgId = 'msg-' + Date.now();
            msg.id = msgId;
            msg.className = `llm-message llm-message-${role}${loading ? ' llm-message-loading' : ''}${type === 'error' ? ' llm-message-error' : ''}`;
            
            const bubble = document.createElement('div');
            bubble.className = 'llm-message-bubble';
            bubble.textContent = content;
            msg.appendChild(bubble);
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
            
            return msgId;
        }

        removeMessage(msgId) {
            const msg = document.getElementById(msgId);
            if (msg) msg.remove();
        }

        addSQLMessage(sql) {
            const messages = document.getElementById('llmChatMessages');
            const msg = document.createElement('div');
            msg.className = 'llm-message llm-message-sql';
            
            msg.innerHTML = `
                <div class="llm-sql-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <span class="llm-sql-icon">📝</span>
                    <span>Generated SQL Query</span>
                    <span class="llm-sql-toggle">▼</span>
                </div>
                <pre class="llm-sql-code"><code>${this.escapeHtml(sql)}</code></pre>
            `;
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }

        addTableMessage(rows, columns, totalCount) {
            const messages = document.getElementById('llmChatMessages');
            const msg = document.createElement('div');
            msg.className = 'llm-message llm-message-table';
            
            const table = document.createElement('table');
            table.className = 'llm-results-table';
            
            // Header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Body (show first 50 rows)
            const tbody = document.createElement('tbody');
            const displayRows = rows.slice(0, 50);
            displayRows.forEach(row => {
                const tr = document.createElement('tr');
                columns.forEach(col => {
                    const td = document.createElement('td');
                    const val = row[col];
                    td.textContent = val !== null && val !== undefined ? val : '';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            
            const container = document.createElement('div');
            container.className = 'llm-table-container';
            
            if (totalCount > 50) {
                const notice = document.createElement('div');
                notice.className = 'llm-table-notice';
                notice.textContent = `Showing first 50 of ${totalCount} results`;
                container.appendChild(notice);
            }
            
            container.appendChild(table);
            msg.appendChild(container);
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }

        addSuggestionsMessage(suggestions) {
            const messages = document.getElementById('llmChatMessages');
            const msg = document.createElement('div');
            msg.className = 'llm-message llm-message-suggestions';
            
            const header = document.createElement('div');
            header.className = 'llm-suggestions-header';
            header.textContent = '💡 You might also ask:';
            msg.appendChild(header);
            
            suggestions.forEach(suggestion => {
                const btn = document.createElement('button');
                btn.className = 'llm-suggestion-btn';
                btn.textContent = suggestion;
                btn.onclick = () => {
                    document.getElementById('llmChatInput').value = suggestion;
                    this.sendMessage();
                };
                msg.appendChild(btn);
            });
            
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
        window.llmChat = new LLMChat();
    });

})();
