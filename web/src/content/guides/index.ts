import { reproducibility } from "./reproducibility";
import { reviewingAiChanges } from "./reviewing-ai-changes";
import { testingGeneratedCode } from "./testing-generated-code";
import type { Guide } from "./types";
import { writingSpecifications } from "./writing-specifications";

export type { Guide, GuideBlock, GuideSection } from "./types";

/** All guides, in the recommended reading order (which follows the workflow). */
export const guides: readonly Guide[] = [
  writingSpecifications,
  testingGeneratedCode,
  reviewingAiChanges,
  reproducibility,
];

export function getGuide(slug: string): Guide | undefined {
  return guides.find((guide) => guide.slug === slug);
}
