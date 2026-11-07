import { describe, expect, it } from "vitest";
import { getGuide, guides } from "@/content/guides";

describe("guide content", () => {
  it("has at least three guides with unique, URL-safe slugs", () => {
    expect(guides.length).toBeGreaterThanOrEqual(3);
    const slugs = guides.map((g) => g.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const slug of slugs) expect(slug).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
  });

  it.each(guides.map((g) => [g.slug, g] as const))("%s has a checklist, a copyable prompt, and unique section ids", (_, guide) => {
    const blocks = guide.sections.flatMap((s) => s.blocks);
    expect(blocks.some((b) => b.type === "checklist")).toBe(true);
    expect(blocks.some((b) => b.type === "prompt")).toBe(true);
    const ids = guide.sections.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(guide.outcomes.length).toBeGreaterThan(0);
  });

  it("looks up guides by slug", () => {
    expect(getGuide("reproducibility")?.title).toMatch(/reproducible/i);
    expect(getGuide("does-not-exist")).toBeUndefined();
  });
});
