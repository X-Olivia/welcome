import { type GuideResponse } from "../api";
import { type FallbackReason } from "./types";

export const greetingPhrases = [
  "Where would you like to explore first? Say the word and I will map it out for you.",
  "What would you like to see today? I can turn that into a route right away.",
  "If you already have a building or topic in mind, you can tell me now.",
  "Would you like to see engineering, student life, or a specific place?",
  "Tell me how you would like to explore the campus today.",
  "First time at UNNC? Tell me what you want to see and I will guide you.",
  "You can name a place directly, or describe the kind of area that interests you.",
  "Would you like to start with the library, engineering, or student life?",
  "Tell me where you want to go and I will plan the route straight away.",
  "If you are not sure yet, just say: recommend a route for me.",
];

export const thinkingPhrases = [
  "Alright, let me work that out for you.",
  "Give me a moment while I plan the route.",
  "I am finding a route that flows well across the campus.",
  "Let me think about the best way to guide you around.",
  "I am putting together the route and key stops now.",
  "I am checking which places make the best first stops for you.",
  "Almost there. I am generating your guide now.",
  "I am matching your request to a campus route.",
  "Just a moment while I arrange the stops in order.",
  "I am using the campus map to shape the route.",
];

export const resultOpeners = [
  "Your route is ready.",
  "I have planned it for you.",
  "This route is now prepared.",
  "Your guided route is ready to go.",
  "I have generated the result for you.",
  "I have arranged the route for you.",
  "The guide is ready and we can begin.",
  "You can set off now. I have marked the route on the map.",
];

const fallbackPhrasesByReason: Record<FallbackReason, string[]> = {
  no_speech: [
    "I did not catch that clearly. Could you say it again?",
    "I only heard part of that. Please try once more.",
    "You can tell me a destination, or the kind of area you want to explore.",
    "A shorter request can help, for example: how do I get to the library?",
    "You can also say something like: I want to explore the engineering area.",
    "I am ready to listen again whenever you are.",
  ],
  transcribe_failed: [
    "That audio did not turn into text properly. Let us try again.",
    "The recording was a little unstable just now. Please say it once more.",
    "The speech recognition did not catch that. Let us restart.",
    "I did not get the whole sentence this time. You can try another wording.",
    "Please say it once more, or just name a place directly.",
    "If it is noisy around you, moving a little closer may help.",
  ],
  guide_failed: [
    "I could not generate the route just now. Please try again.",
    "The route did not come through this time. Let us try once more.",
    "I am resetting the request. You can say what you need again.",
    "I could not return a result yet, but we can try again right away.",
    "If you name a specific place, it will be easier for me to plan the route.",
    "I stalled for a moment there. You can say it again now.",
  ],
  clarification: [
    "I mostly understand, but I still need a little more detail.",
    "You can tell me the place name directly, or the theme you want to explore.",
    "Requests like how do I get to the library or I want to see engineering are easier for me to plan.",
    "A little more detail is enough for me to generate the route.",
    "You can name a building, or a theme like AI, robotics, or student life.",
    "That is still a bit vague. One more detail and I can continue.",
  ],
};

export function fallbackPhrases(reason: FallbackReason): string[] {
  return fallbackPhrasesByReason[reason];
}

export function buildResultSpeech(result: GuideResponse, opener: string): string {
  const placeNames = result.places.map((place) => place.name_zh).filter(Boolean);
  const trimmedSummary = trimForSpeech(result.route_summary_zh || result.reply_zh || "");

  if (result.intent === "clarification") {
    return trimmedSummary || `${opener} I still need a little more detail from you.`;
  }

  if (result.intent === "route" && placeNames[0]) {
    return `${opener} I recommend starting with ${placeNames[0]}. The map already shows the direction for you.`;
  }

  if (placeNames.length >= 2) {
    const sequence = placeNames.slice(0, 3).join(", ");
    return `${opener} I recommend visiting ${sequence} in that order. ${trimmedSummary}`;
  }

  if (trimmedSummary) {
    return `${opener} ${trimmedSummary}`;
  }

  return `${opener} The map and route are updated, so you can begin following the highlighted path.`;
}

function trimForSpeech(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  if (normalized.length <= 70) return normalized;
  return `${normalized.slice(0, 68)}…`;
}
