import { CharacterManager } from './character.js';
import { ChatManager } from './chat.js';
import { VoiceInput } from './voice-input.js';
import { VoiceOutput } from './voice-output.js';

export default class App {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    
    this.chat = new ChatManager();
    this.character = new CharacterManager();
    this.voiceInput = new VoiceInput();
    this.voiceOutput = new VoiceOutput();
    
    this.init();
  }
  
  async init() {
    // Setup UI handlers
    document.getElementById('minimize-btn').addEventListener('click', () => {
      window.electronAPI.minimizeWindow();
    });
    
    document.getElementById('settings-btn').addEventListener('click', () => {
      if (window.electronAPI && window.electronAPI.openDevTools) {
        window.electronAPI.openDevTools();
        this.chat.addSystemMessage('⚙ 開発者ツール (DevTools) を開きました。ログを確認できます。');
      }
    });

    // F12 key to open DevTools
    document.addEventListener('keydown', (e) => {
      if (e.key === 'F12' && window.electronAPI && window.electronAPI.openDevTools) {
        window.electronAPI.openDevTools();
      }
    });

    const sendBtn = document.getElementById('send-btn');
    const msgInput = document.getElementById('message-input');
    
    sendBtn.addEventListener('click', () => this.sendMessage());
    msgInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage();
    });
    
    const micBtn = document.getElementById('mic-btn');
    micBtn.addEventListener('click', async () => {
      if (this.voiceInput.isRecording) {
        const audioBase64 = await this.voiceInput.stopRecording();
        micBtn.classList.remove('recording');
        if (audioBase64) {
          this.sendAudioMessage(audioBase64);
        }
      } else {
        await this.voiceInput.startRecording();
        micBtn.classList.add('recording');
      }
    });

    // Hold space to talk
    document.addEventListener('keydown', async (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && !this.voiceInput.isRecording) {
        await this.voiceInput.startRecording();
        micBtn.classList.add('recording');
      }
    });
    
    document.addEventListener('keyup', async (e) => {
      if (e.code === 'Space' && this.voiceInput.isRecording) {
        const audioBase64 = await this.voiceInput.stopRecording();
        micBtn.classList.remove('recording');
        if (audioBase64) {
          this.sendAudioMessage(audioBase64);
        }
      }
    });

    // Init modules
    await this.character.init(document.getElementById('character-canvas'));
    await this.voiceInput.init();
    
    // Connect WebSocket
    this.connectWebSocket();
    
    // Start render loop for lipsync
    this.startAudioSyncLoop();
  }
  
  startAudioSyncLoop() {
    const loop = () => {
      if (this.voiceOutput.isPlaying) {
        const vol = this.voiceOutput.getVolume();
        this.character.startLipSync(vol);
      } else {
        this.character.stopLipSync();
      }
      requestAnimationFrame(loop);
    };
    loop();
  }
  
  connectWebSocket() {
    this.updateStatus(false, '接続中...');
    
    try {
      this.ws = new WebSocket('ws://localhost:8765/ws');
      
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateStatus(true, 'オンライン');
        this.chat.addSystemMessage('サーバーに接続しました。');
      };
      
      this.ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleServerMessage(data);
        } catch (e) {
          console.error('Failed to parse message', e);
        }
      };
      
      this.ws.onclose = () => {
        this.updateStatus(false, 'オフライン');
        this.scheduleReconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }
  
  scheduleReconnect() {
    const delay = Math.min(30000, Math.pow(1.5, this.reconnectAttempts) * 1000);
    this.reconnectAttempts++;
    this.chat.addSystemMessage(`${Math.round(delay/1000)}秒後に再接続します...`);
    setTimeout(() => this.connectWebSocket(), delay);
  }
  
  updateStatus(online, text) {
    const dot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    
    if (online) {
      dot.classList.remove('offline');
      dot.classList.add('online');
    } else {
      dot.classList.remove('online');
      dot.classList.add('offline');
    }
    statusText.textContent = text;
  }
  
  handleServerMessage(data) {
    if (data.type === 'response') {
      this.chat.hideThinking();
      this.chat.addAssistantMessage(data.content);
      if (data.emotion) {
        this.character.setEmotion(data.emotion);
      }
      if (data.audio) {
        this.voiceOutput.playAudio(data.audio);
      }
    } else if (data.type === 'transcription') {
      this.chat.addUserMessage(data.content);
    } else if (data.type === 'thinking') {
      this.chat.showThinking();
    } else if (data.type === 'error') {
      this.chat.hideThinking();
      this.chat.addSystemMessage('エラー: ' + data.content);
    }
  }
  
  sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text) return;
    
    this.chat.addUserMessage(text);
    input.value = '';
    
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'text', content: text }));
      this.chat.showThinking();
      this.character.setEmotion('thinking');
    } else {
      this.chat.addSystemMessage('エラー：サーバーに接続されていません。');
    }
  }
  
  sendAudioMessage(base64) {
    this.chat.addUserMessage('🎤 [音声入力]');
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'audio', data: base64 }));
      this.chat.showThinking();
      this.character.setEmotion('thinking');
    } else {
      this.chat.addSystemMessage('エラー：サーバーに接続されていません。');
    }
  }
}

// Instantiate
window.appInstance = new App();
