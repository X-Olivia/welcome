export type VoicePhase =
  | "idle"
  | "greeting"
  | "listening"
  | "transcribing"
  | "thinking"
  | "speaking_result"
  | "error";

export type PhraseCategory = "greeting" | "thinking" | "result" | "fallback";

export type FallbackReason = "no_speech" | "transcribe_failed" | "guide_failed" | "clarification";
