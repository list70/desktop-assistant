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
    // Basic markdown replacement
    let formattedText = text
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.3);padding:2px 4px;border-radius:4px;">$1</code>');
    
    div.innerHTML = formattedText;
    
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
