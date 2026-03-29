import { type MutableRefObject, useEffect, useRef, useState } from "react";
import { type GuideResponse, fetchSpeechAudio, postVoiceTranscribe } from "../api";
import { BrowserAudioRecorder } from "./audioRecorder";
import { VoiceAudioPlayer } from "./audioPlayer";
import { PhraseManager } from "./phraseManager";
import {
  buildResultSpeech,
  fallbackPhrases,
  greetingPhrases,
  resultOpeners,
  thinkingPhrases,
} from "./phrases";
import { type FallbackReason, type VoicePhase } from "./types";

interface UseVoiceGuideOptions {
  onGuideRequest: (message: string) => Promise<GuideResponse>;
  onTranscript?: (message: string) => void;
}

export function useVoiceGuide(options: UseVoiceGuideOptions) {
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [statusText, setStatusText] = useState("");
  const [lastTranscript, setLastTranscript] = useState("");
  const [errorText, setErrorText] = useState<string | null>(null);

  const phraseManagerRef = useRef(new PhraseManager());
  const playerRef = useRef(new VoiceAudioPlayer());
  const recorderRef = useRef<BrowserAudioRecorder | null>(null);
  const sessionIdRef = useRef(0);
  const speechNonceRef = useRef(0);

  useEffect(() => {
    return () => {
      sessionIdRef.current += 1;
      cancelSpeech(playerRef, speechNonceRef);
      void recorderRef.current?.stop();
    };
  }, []);

  async function startOrStop() {
    if (phase !== "idle" && phase !== "error") {
      await stopVoiceSession();
      return;
    }
    await startVoiceSession();
  }

  async function startVoiceSession() {
    const sessionId = ++sessionIdRef.current;
    setErrorText(null);
    setLastTranscript("");

    const greeting = phraseManagerRef.current.pick("greeting", greetingPhrases);
    setPhase("greeting");
    setStatusText(greeting);
    await speakText(greeting, sessionId, true);
    if (isStale(sessionIdRef, sessionId)) return;

    await listenAndRespond(sessionId);
  }

  async function stopVoiceSession() {
    sessionIdRef.current += 1;
    cancelSpeech(playerRef, speechNonceRef);
    await recorderRef.current?.stop();
    recorderRef.current = null;
    setPhase("idle");
    setStatusText("Voice mode has stopped. Tap again when you are ready.");
  }

  async function listenAndRespond(sessionId: number) {
    setPhase("listening");
    setStatusText("I am listening. Pause after speaking and I will start processing automatically.");

    const recorder = new BrowserAudioRecorder();
    recorderRef.current = recorder;

    let capture;
    try {
      capture = await recorder.recordUntilSilence();
    } catch (error) {
      await handleFallback("transcribe_failed", sessionId, error);
      return;
    } finally {
      recorderRef.current = null;
    }

    if (isStale(sessionIdRef, sessionId)) return;
    if (!capture.speechDetected || capture.blob.size < 1200) {
      await handleFallback("no_speech", sessionId);
      return;
    }

    setPhase("transcribing");
    setStatusText("Turning your speech into text...");

    let transcriptText = "";
    try {
      const transcript = await transcribeWithRetry(capture.blob, inferLanguageHint());
      transcriptText = transcript.text.trim();
    } catch (error) {
      await handleFallback("transcribe_failed", sessionId, error);
      return;
    }

    if (isStale(sessionIdRef, sessionId)) return;
    if (!transcriptText) {
      await handleFallback("no_speech", sessionId);
      return;
    }

    setLastTranscript(transcriptText);
    options.onTranscript?.(transcriptText);

    const thinking = phraseManagerRef.current.pick("thinking", thinkingPhrases);
    setPhase("thinking");
    setStatusText(thinking);
    void speakText(thinking, sessionId, false);

    let result: GuideResponse;
    try {
      result = await options.onGuideRequest(transcriptText);
    } catch (error) {
      await handleFallback("guide_failed", sessionId, error);
      return;
    }

    if (isStale(sessionIdRef, sessionId)) return;
    cancelSpeech(playerRef, speechNonceRef);

    const needsClarification = result.intent === "clarification" || result.places.length === 0;
    if (needsClarification) {
      await handleFallback("clarification", sessionId, result.reply_zh);
      return;
    }

    const opener = phraseManagerRef.current.pick("result", resultOpeners);
    const speech = buildResultSpeech(result, opener);
    setPhase("speaking_result");
    setStatusText("Your route is ready. I will give you a quick overview.");
    await speakText(speech, sessionId, true);

    if (isStale(sessionIdRef, sessionId)) return;
    setPhase("idle");
    setStatusText("The route is now on the map. You can start another voice request any time.");
  }

  async function handleFallback(reason: FallbackReason, sessionId: number, error?: unknown) {
    if (isStale(sessionIdRef, sessionId)) return;

    cancelSpeech(playerRef, speechNonceRef);
    const phrases = fallbackPhrases(reason);
    const fallback = phraseManagerRef.current.pick("fallback", phrases);
    setPhase("error");
    setErrorText(typeof error === "string" ? error : error instanceof Error ? error.message : null);
    setStatusText(fallback);
    await speakText(fallback, sessionId, true);

    if (isStale(sessionIdRef, sessionId)) return;
    setPhase("idle");
  }

  return {
    phase,
    statusText,
    lastTranscript,
    errorText,
    isActive: phase !== "idle" && phase !== "error",
    startOrStop,
    stopVoiceSession,
  };

  async function speakText(text: string, sessionId: number, waitUntilEnded: boolean) {
    const nonce = ++speechNonceRef.current;
    try {
      const audioBlob = await fetchSpeechAudio(text);
      if (isStale(sessionIdRef, sessionId) || nonce !== speechNonceRef.current) return;
      const playPromise = playerRef.current.play(audioBlob);
      if (waitUntilEnded) {
        await playPromise;
      } else {
        void playPromise.catch(() => undefined);
      }
    } catch {
      // Voice should never block the main guide flow. Fail silently here.
    }
  }
}

function isStale(sessionIdRef: MutableRefObject<number>, sessionId: number): boolean {
  return sessionIdRef.current !== sessionId;
}

function cancelSpeech(
  playerRef: MutableRefObject<VoiceAudioPlayer>,
  speechNonceRef: MutableRefObject<number>,
) {
  speechNonceRef.current += 1;
  playerRef.current.stop();
}

function inferLanguageHint(): string | undefined {
  const locale = navigator.language.toLowerCase();
  if (locale.startsWith("zh")) return "zh";
  if (locale.startsWith("en")) return "en";
  return undefined;
}

async function transcribeWithRetry(audio: Blob, language?: string) {
  try {
    return await postVoiceTranscribe(audio, { language });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!/timed out/i.test(message)) {
      throw error;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1200));
    return await postVoiceTranscribe(audio, { language });
  }
}
