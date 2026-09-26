export class VoiceInput {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.stream = null;
    this.maxDurationTimeout = null;
    this.onAutoStop = null;
    this.stopPromise = null;
  }

  async init() {
    if (this.stream) return true;
    if (!navigator.mediaDevices?.getUserMedia) return false;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      return true;
    } catch (e) {
      console.error('Microphone access denied or not available', e);
      return false;
    }
  }

  async startRecording() {
    if (this.stopPromise) await this.stopPromise;
    if (this.isRecording) return true;
    if (!this.stream && !(await this.init())) return false;
    if (typeof MediaRecorder === 'undefined') return false;

    this.audioChunks = [];
    const supportedTypes = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
    const mimeType = typeof MediaRecorder.isTypeSupported === 'function'
      ? supportedTypes.find((type) => MediaRecorder.isTypeSupported(type))
      : undefined;
    const recorder = mimeType
      ? new MediaRecorder(this.stream, { mimeType })
      : new MediaRecorder(this.stream);
    this.mediaRecorder = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    try {
      recorder.start();
    } catch (error) {
      this.mediaRecorder = null;
      throw error;
    }
    this.isRecording = true;

    // Auto stop after 30 seconds
    this.maxDurationTimeout = setTimeout(async () => {
      if (!this.isRecording) return;
      const audioBase64 = await this.stopRecording();
      if (this.onAutoStop) this.onAutoStop(audioBase64);
    }, 30000);
    return true;
  }

  async stopRecording() {
    if (this.stopPromise) return this.stopPromise;
    if (!this.isRecording || !this.mediaRecorder) return null;
    const recorder = this.mediaRecorder;
    this.isRecording = false;
    if (this.maxDurationTimeout) {
      clearTimeout(this.maxDurationTimeout);
      this.maxDurationTimeout = null;
    }

    this.stopPromise = new Promise((resolve) => {
      recorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: recorder.mimeType || 'audio/webm' });
        const reader = new FileReader();
        reader.onerror = () => resolve(null);
        reader.onloadend = () => {
          const base64data = typeof reader.result === 'string' ? reader.result.split(',')[1] : null;
          resolve(base64data);
        };
        reader.readAsDataURL(audioBlob);
        this.audioChunks = [];
        if (this.mediaRecorder === recorder) this.mediaRecorder = null;
      };

      recorder.onerror = () => resolve(null);
      try {
        recorder.stop();
      } catch {
        if (this.mediaRecorder === recorder) this.mediaRecorder = null;
        resolve(null);
      }
    });
    try {
      return await this.stopPromise;
    } finally {
      this.stopPromise = null;
    }
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
