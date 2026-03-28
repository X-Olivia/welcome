export class VoiceAudioPlayer {
  private audio: HTMLAudioElement | null = null;
  private objectUrl: string | null = null;
  private settle: ((error?: Error) => void) | null = null;

  async play(audioBlob: Blob): Promise<void> {
    this.stop();
    const url = URL.createObjectURL(audioBlob);
    const audio = new Audio(url);
    this.audio = audio;
    this.objectUrl = url;

    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        audio.onended = null;
        audio.onerror = null;
        this.settle = null;
      };

      this.settle = (error?: Error) => {
        cleanup();
        if (error) {
          reject(error);
          return;
        }
        resolve();
      };

      audio.onended = () => {
        this.settle?.();
      };
      audio.onerror = () => {
        this.settle?.(new Error("Audio playback failed."));
      };

      void audio.play().catch((error) => {
        this.settle?.(error instanceof Error ? error : new Error(String(error)));
      });
    });
  }

  stop() {
    if (this.audio) {
      this.audio.pause();
      this.audio.src = "";
      this.audio = null;
    }
    if (this.settle) {
      const settle = this.settle;
      this.settle = null;
      settle(new Error("Audio playback was interrupted."));
    }
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = null;
    }
  }
}
