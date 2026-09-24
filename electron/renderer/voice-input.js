export class VoiceInput {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.stream = null;
    this.maxDurationTimeout = null;
  }

  async init() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      console.error('Microphone access denied or not available', e);
    }
  }

  async startRecording() {
    if (!this.stream) await this.init();
    if (!this.stream) return;

    this.audioChunks = [];
    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: 'audio/webm;codecs=opus' });

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.start();
    this.isRecording = true;

    // Auto stop after 30 seconds
    this.maxDurationTimeout = setTimeout(() => {
      if (this.isRecording) this.stopRecording();
    }, 30000);
  }

  async stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) return null;

    return new Promise((resolve) => {
      this.mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64data = reader.result.split(',')[1];
          resolve(base64data);
        };
        reader.readAsDataURL(audioBlob);
        this.audioChunks = [];
      };

      this.mediaRecorder.stop();
      this.isRecording = false;
      if (this.maxDurationTimeout) {
        clearTimeout(this.maxDurationTimeout);
      }
    });
  }

  toggleRecording() {
    if (this.isRecording) {
      return this.stopRecording();
    } else {
      this.startRecording();
      return null;
    }
  }
}
