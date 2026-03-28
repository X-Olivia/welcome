export interface VoiceRecordingResult {
  blob: Blob;
  durationMs: number;
  speechDetected: boolean;
}

interface RecordOptions {
  maxDurationMs?: number;
  silenceMs?: number;
  threshold?: number;
}

export class BrowserAudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private analyser: AnalyserNode | null = null;
  private rafId: number | null = null;
  private stopTimer: number | null = null;

  async recordUntilSilence(options: RecordOptions = {}): Promise<VoiceRecordingResult> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("This browser does not support microphone recording.");
    }
    if (typeof MediaRecorder === "undefined") {
      throw new Error("This browser does not support MediaRecorder.");
    }

    const maxDurationMs = options.maxDurationMs ?? 9000;
    const silenceMs = options.silenceMs ?? 1400;
    const threshold = options.threshold ?? 0.018;

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    this.audioContext = new AudioContext();
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 2048;
    this.source.connect(this.analyser);

    const mimeType = pickSupportedMimeType();
    const chunks: BlobPart[] = [];
    const startedAt = Date.now();
    let speechDetected = false;
    let lastVoiceAt = startedAt;

    this.mediaRecorder = mimeType
      ? new MediaRecorder(this.stream, { mimeType })
      : new MediaRecorder(this.stream);

    return await new Promise<VoiceRecordingResult>((resolve, reject) => {
      const stopRecording = () => {
        if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
          this.mediaRecorder.stop();
        }
      };

      const loop = () => {
        if (!this.analyser) return;
        const samples = new Float32Array(this.analyser.fftSize);
        this.analyser.getFloatTimeDomainData(samples);
        let sum = 0;
        for (const sample of samples) sum += sample * sample;
        const rms = Math.sqrt(sum / samples.length);
        const now = Date.now();

        if (rms >= threshold) {
          speechDetected = true;
          lastVoiceAt = now;
        }

        if (speechDetected && now - lastVoiceAt >= silenceMs) {
          stopRecording();
          return;
        }
        this.rafId = window.requestAnimationFrame(loop);
      };

      this.mediaRecorder!.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };

      this.mediaRecorder!.onstop = async () => {
        const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
        const durationMs = Date.now() - startedAt;
        await this.cleanup();
        resolve({ blob, durationMs, speechDetected });
      };

      this.mediaRecorder!.onerror = async () => {
        await this.cleanup();
        reject(new Error("Recording failed."));
      };

      this.stopTimer = window.setTimeout(stopRecording, maxDurationMs);
      this.mediaRecorder!.start();
      loop();
    });
  }

  async stop(): Promise<void> {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
      return;
    }
    await this.cleanup();
  }

  private async cleanup(): Promise<void> {
    if (this.rafId !== null) {
      window.cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.stopTimer !== null) {
      window.clearTimeout(this.stopTimer);
      this.stopTimer = null;
    }
    this.source?.disconnect();
    this.analyser?.disconnect();
    this.stream?.getTracks().forEach((track) => track.stop());
    this.source = null;
    this.analyser = null;
    this.stream = null;
    this.mediaRecorder = null;
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
  }
}

function pickSupportedMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate));
}
