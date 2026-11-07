/**
 * Guide content model. Text fields support `backtick` inline code only; keep
 * formatting minimal so guides stay easy to review in pull requests.
 */
export type GuideBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: readonly string[]; ordered?: boolean }
  | { type: "code"; code: string; language: string; title?: string; caption?: string }
  | { type: "prompt"; title: string; prompt: string; note?: string }
  | { type: "checklist"; title: string; items: readonly string[] }
  | { type: "callout"; tone: "note" | "warning"; title?: string; text: string };

export type GuideSection = {
  /** Used as the in-page anchor. Must be unique within a guide. */
  id: string;
  title: string;
  blocks: readonly GuideBlock[];
};

export type Guide = {
  slug: string;
  title: string;
  /** One-sentence description used on cards and in page metadata. */
  summary: string;
  /** Which stage of the ResearchCode workflow this guide supports. */
  stage: "Specify" | "Test" | "Review" | "Reproduce";
  readingMinutes: number;
  audience: string;
  outcomes: readonly string[];
  sections: readonly GuideSection[];
};
