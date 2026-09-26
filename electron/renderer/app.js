import { CharacterManager } from './character.js';
import { ChatManager } from './chat.js';
import { VoiceInput } from './voice-input.js';
import { VoiceOutput } from './voice-output.js';

const API_BASE = 'http://127.0.0.1:8765';

export default class App {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.currentModel = '';
    
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
    
    this.initSettings();

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
    this.voiceInput.onAutoStop = (audioBase64) => {
      micBtn.classList.remove('recording');
      if (audioBase64) this.sendAudioMessage(audioBase64);
    };
    micBtn.addEventListener('click', async () => {
      try {
        if (this.voiceInput.isRecording) {
          const audioBase64 = await this.voiceInput.stopRecording();
          micBtn.classList.remove('recording');
          if (audioBase64) this.sendAudioMessage(audioBase64);
        } else {
          const started = await this.voiceInput.startRecording();
          micBtn.classList.toggle('recording', started);
          if (!started) this.chat.addSystemMessage('マイクを利用できません。権限とデバイスを確認してください。');
        }
      } catch (error) {
        micBtn.classList.remove('recording');
        this.chat.addSystemMessage(`録音を開始できません: ${error.message}`);
      }
    });

    // Hold space to talk
    document.addEventListener('keydown', async (e) => {
      if (e.code !== 'Space' || e.repeat || e.target.closest('input, textarea, select, button') || this.voiceInput.isRecording) return;
      e.preventDefault();
      try {
        const started = await this.voiceInput.startRecording();
        micBtn.classList.toggle('recording', started);
        if (!started) this.chat.addSystemMessage('マイクを利用できません。権限とデバイスを確認してください。');
      } catch (error) {
        micBtn.classList.remove('recording');
        this.chat.addSystemMessage(`録音を開始できません: ${error.message}`);
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

    // Init modules. Microphone permission is requested only after the user starts recording.
    await this.character.init(document.getElementById('character-canvas'));
    
    // Connect WebSocket
    this.connectWebSocket();
    
    // Start render loop for lipsync
    this.startAudioSyncLoop();
  }

  initSettings() {
    this.settingsModal = document.getElementById('settings-modal');
    this.modelSelect = document.getElementById('llm-model-select');
    this.settingsStatus = document.getElementById('settings-status');
    this.saveSettingsButton = document.getElementById('settings-save-btn');

    document.getElementById('settings-btn').addEventListener('click', () => this.openSettings());
    document.getElementById('refresh-models-btn').addEventListener('click', () => this.refreshOllamaModels());
    this.modelSelect.addEventListener('change', () => {
      this.saveSettingsButton.disabled = !this.modelSelect.value || this.modelSelect.value === this.currentModel;
    });
    this.saveSettingsButton.addEventListener('click', () => this.saveSettings());
    document.getElementById('settings-close-btn').addEventListener('click', () => this.closeSettings());
    document.getElementById('settings-cancel-btn').addEventListener('click', () => this.closeSettings());
    this.settingsModal.addEventListener('click', (event) => {
      if (event.target === this.settingsModal) this.closeSettings();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !this.settingsModal.hidden) this.closeSettings();
    });
  }

  async openSettings() {
    this.settingsModal.hidden = false;
    this.settingsModal.setAttribute('aria-hidden', 'false');
    document.getElementById('llm-model-select').focus();
    await this.refreshOllamaModels();
  }

  closeSettings() {
    this.settingsModal.hidden = true;
    this.settingsModal.setAttribute('aria-hidden', 'true');
    document.getElementById('settings-btn').focus();
  }

  async refreshOllamaModels() {
    const refreshButton = document.getElementById('refresh-models-btn');
    refreshButton.disabled = true;
    this.modelSelect.disabled = true;
    this.saveSettingsButton.disabled = true;
    this.settingsStatus.classList.remove('error');
    this.settingsStatus.textContent = 'Ollamaのモデル一覧を取得しています…';
    try {
      const configResponse = await fetch(`${API_BASE}/config`);
      if (!configResponse.ok) throw new Error('設定を読み込めません。バックエンドの状態を確認してください。');
      const currentConfig = await configResponse.json();
      const response = await fetch(`${API_BASE}/ollama/models`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Ollamaに接続できません。');

      const models = Array.isArray(result.models) ? result.models : [];
      this.currentModel = currentConfig.llm_model || '';
      this.modelSelect.replaceChildren();
      for (const model of models) {
        const option = document.createElement('option');
        option.value = model.name;
        option.textContent = model.size ? `${model.name} (${this.formatModelSize(model.size)})` : model.name;
        this.modelSelect.appendChild(option);
      }
      this.modelSelect.disabled = models.length === 0;
      if (models.some((model) => model.name === this.currentModel)) {
        this.modelSelect.value = this.currentModel;
        this.settingsStatus.textContent = `${models.length}個のインストール済みモデルが見つかりました。`;
      } else if (models.length > 0) {
        this.modelSelect.selectedIndex = 0;
        this.settingsStatus.textContent = `現在のモデル「${this.currentModel}」は未インストールです。利用可能なモデルを選んでください。`;
        this.saveSettingsButton.disabled = false;
      } else {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'インストール済みモデルがありません';
        this.modelSelect.appendChild(option);
        this.settingsStatus.textContent = 'Ollamaでモデルをダウンロードしてから一覧を更新してください。';
      }
    } catch (error) {
      this.modelSelect.replaceChildren();
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'モデル一覧を取得できません';
      this.modelSelect.appendChild(option);
      this.settingsStatus.textContent = error.message;
      this.settingsStatus.classList.add('error');
    } finally {
      refreshButton.disabled = false;
    }
  }

  formatModelSize(size) {
    if (!Number.isFinite(size) || size <= 0) return '';
    const gib = size / (1024 ** 3);
    return gib >= 1 ? `${gib.toFixed(1)} GB` : `${(size / (1024 ** 2)).toFixed(0)} MB`;
  }

  async saveSettings() {
    const model = this.modelSelect.value;
    if (!model) return;
    this.saveSettingsButton.disabled = true;
    this.settingsStatus.classList.remove('error');
    this.settingsStatus.textContent = 'モデルを切り替えています…';
    try {
      const response = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ llm_model: model })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'モデルを保存できませんでした。');
      this.currentModel = result.llm_model;
      this.settingsStatus.textContent = `使用モデルを「${this.currentModel}」に切り替えました。`;
      this.chat.addSystemMessage(`Ollamaモデルを ${this.currentModel} に切り替えました。`);
    } catch (error) {
      this.settingsStatus.textContent = error.message;
      this.settingsStatus.classList.add('error');
      this.saveSettingsButton.disabled = false;
    }
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
      this.ws = new WebSocket('ws://127.0.0.1:8765/ws');
      
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
