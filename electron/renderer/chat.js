export class ChatManager {
  constructor() {
    this.messagesContainer = document.getElementById('chat-messages');
    this.thinkingIndicator = document.getElementById('thinking-indicator');
    this.history = [];
  }

  addUserMessage(text) {
    this.history.push({ role: 'user', content: text });
    this.createMessageBubble(text, 'user');
    this.scrollToBottom();
  }

  addAssistantMessage(text) {
    this.history.push({ role: 'assistant', content: text });
    this.createMessageBubble(text, 'assistant');
    this.scrollToBottom();
  }

  addSystemMessage(text) {
    this.createMessageBubble(text, 'system');
    this.scrollToBottom();
  }

  createMessageBubble(text, type) {
    const div = document.createElement('div');
    div.classList.add('message', type);
    // Render the small markdown subset with text nodes so model output cannot inject HTML.
    const parts = String(text ?? '').split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\n)/g);
    for (const part of parts) {
      if (part === '\n') {
        div.appendChild(document.createElement('br'));
      } else if (part.startsWith('**') && part.endsWith('**')) {
        const strong = document.createElement('strong');
        strong.textContent = part.slice(2, -2);
        div.appendChild(strong);
      } else if (part.startsWith('*') && part.endsWith('*')) {
        const emphasis = document.createElement('em');
        emphasis.textContent = part.slice(1, -1);
        div.appendChild(emphasis);
      } else if (part.startsWith('`') && part.endsWith('`')) {
        const code = document.createElement('code');
        code.textContent = part.slice(1, -1);
        div.appendChild(code);
      } else if (part) {
        div.appendChild(document.createTextNode(part));
      }
    }
    
    // Insert before thinking indicator if it exists
    if (this.thinkingIndicator.parentNode === this.messagesContainer) {
      this.messagesContainer.insertBefore(div, this.thinkingIndicator);
    } else {
      this.messagesContainer.appendChild(div);
    }
  }

  showThinking() {
    this.thinkingIndicator.style.display = 'flex';
    this.messagesContainer.appendChild(this.thinkingIndicator);
    this.scrollToBottom();
  }

  hideThinking() {
    this.thinkingIndicator.style.display = 'none';
  }

  clearMessages() {
    const msgs = this.messagesContainer.querySelectorAll('.message');
    msgs.forEach(m => m.remove());
    this.history = [];
  }

  scrollToBottom() {
    this.messagesContainer.scrollTo({
      top: this.messagesContainer.scrollHeight,
      behavior: 'smooth'
    });
  }

  getHistory() {
    return this.history;
  }
}
