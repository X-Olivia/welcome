import { type PhraseCategory } from "./types";

export class PhraseManager {
  private lastIndexes = new Map<PhraseCategory, number>();

  pick(category: PhraseCategory, phrases: string[]): string {
    if (phrases.length === 0) return "";
    if (phrases.length === 1) return phrases[0];

    const lastIndex = this.lastIndexes.get(category);
    let nextIndex = Math.floor(Math.random() * phrases.length);
    if (phrases.length > 1 && nextIndex === lastIndex) {
      nextIndex = (nextIndex + 1) % phrases.length;
    }
    this.lastIndexes.set(category, nextIndex);
    return phrases[nextIndex];
  }
}
