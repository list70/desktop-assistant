export class VoiceOutput {
  constructor() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    
    this.gainNode = this.audioContext.createGain();
    this.gainNode.connect(this.analyser);
    this.analyser.connect(this.audioContext.destination);
    
    this.currentSource = null;
    this.isPlaying = false;
  }

  base64ToArrayBuffer(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  async playAudio(base64WavData) {
    if (this.currentSource) {
      this.stop();
    }

    try {
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      const arrayBuffer = this.base64ToArrayBuffer(base64WavData);
      const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
      
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.gainNode);
      
      return new Promise((resolve) => {
        this.currentSource.onended = () => {
          this.isPlaying = false;
          resolve();
        };
        
        this.isPlaying = true;
        this.currentSource.start(0);
      });
    } catch (e) {
      console.error('Failed to play audio:', e);
      this.isPlaying = false;
    }
  }

  getVolume() {
    if (!this.isPlaying) return 0;
    
    this.analyser.getByteFrequencyData(this.dataArray);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    // Normalize to 0-1
    return sum / (this.dataArray.length * 255);
  }

  stop() {
    if (this.currentSource && this.isPlaying) {
      this.currentSource.stop();
      this.isPlaying = false;
    }
  }

  setVolume(value) {
    // value between 0.0 and 1.0
    this.gainNode.gain.value = Math.max(0, Math.min(1, value));
  }
}
