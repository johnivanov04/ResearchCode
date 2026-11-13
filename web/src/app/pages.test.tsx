import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import AboutPage from "@/app/about/page";
import EvaluationPage from "@/app/evaluation/page";
import ExamplePage from "@/app/example/page";
import GuidePage from "@/app/guides/[slug]/page";
import GuidesPage from "@/app/guides/page";
import NotFound from "@/app/not-found";
import HomePage from "@/app/page";
import StarterKitPage from "@/app/starter-kit/page";
import { guides } from "@/content/guides";
import { primaryNav } from "@/content/site";
import { protocolUrl } from "@/content/evaluation";
import { appSourceUrl } from "@/content/growth-analysis";
import { starterSourceUrl } from "@/content/starter-kit";

const knownRoutes = new Set(["/", ...primaryNav.map((item) => item.href), ...guides.map((g) => `/guides/${g.slug}`)]);

async function renderGuide(slug: string) {
  return render(await GuidePage({ params: Promise.resolve({ slug }) }));
}

const staticPages: [string, () => ReactElement][] = [
  ["/", HomePage],
  ["/guides", GuidesPage],
  ["/starter-kit", StarterKitPage],
  ["/example", ExamplePage],
  ["/evaluation", EvaluationPage],
  ["/about", AboutPage],
];

function expectWellFormed(container: HTMLElement) {
  // Exactly one h1 per page.
  expect(container.querySelectorAll("h1")).toHaveLength(1);

  // Every internal link points at a real route, and every in-page anchor at a real id.
  for (const anchor of container.querySelectorAll<HTMLAnchorElement>("a[href]")) {
    const href = anchor.getAttribute("href")!;
    if (href.startsWith("#")) {
      expect(container.querySelector(href), `missing anchor target ${href}`).not.toBeNull();
    } else if (href.startsWith("/")) {
      expect(knownRoutes.has(href.split("#")[0]), `broken link ${href}`).toBe(true);
    }
  }

  // No download links until downloadable artifacts actually exist.
  expect(container.querySelectorAll("a[download]")).toHaveLength(0);

  // aria-labelledby must reference elements that exist.
  for (const element of container.querySelectorAll("[aria-labelledby]")) {
    const id = element.getAttribute("aria-labelledby")!;
    expect(container.ownerDocument.getElementById(id), `missing label ${id}`).not.toBeNull();
  }
}

describe("static pages", () => {
  it.each(staticPages)("%s renders with valid structure and links", (_, Page) => {
    const { container } = render(<Page />);
    expectWellFormed(container);
  });

  it("home page carries the project headline", () => {
    const { container } = render(<HomePage />);
    expect(container.querySelector("h1")?.textContent).toBe("Build research software with AI. Trust the results.");
  });

  it("guides index links to every guide", () => {
    const { container } = render(<GuidesPage />);
    for (const guide of guides) {
      expect(container.querySelector(`a[href="/guides/${guide.slug}"]`)).not.toBeNull();
    }
  });
});

describe("honesty requirements", () => {
  it("starter kit explains that it is a monorepo folder, not a template or download", () => {
    const { container } = render(<StarterKitPage />);
    expect(container.textContent).toMatch(/not a separate GitHub template repository/);
    expect(container.textContent).toMatch(/no download package/);
    expect(container.querySelector(`a[href="${starterSourceUrl}"]`)).not.toBeNull();
    // Scope limits stay visible: the starter's own example is small, and the full analysis is
    // a separate application that the page links to.
    expect(container.textContent).toMatch(/covers two readings only/);
    expect(container.querySelector('a[href="/example#application"]')).not.toBeNull();
  });

  it("evaluation page presents the implemented framework with no results", () => {
    const { container } = render(<EvaluationPage />);
    expect(container.textContent).toMatch(/Framework implemented; results pending/);
    expect(container.textContent).toMatch(/No AI trials have\s+been run/);
    expect(container.textContent).toMatch(/No results yet/);
    expect(container.textContent).toMatch(/not experimental results/);
    expect(container.textContent).toMatch(/Claude Pro subscription/);
    expect(container.textContent).toMatch(/\$0 additional spending/);
    expect(container.textContent).not.toMatch(/API key is used|of model use/);
    expect(container.querySelector(`a[href="${protocolUrl}"]`)).not.toBeNull();
    // Results are never shown before trials exist: no percentage other than the reference checks.
    expect(container.querySelector("#results")?.textContent).not.toMatch(/\d+%/);
  });

  it("example page labels its data as synthetic and illustrative", () => {
    const { container } = render(<ExamplePage />);
    expect(container.textContent).toMatch(/All data on this page is illustrative/);
    expect(container.textContent).toMatch(/synthetic/i);
    expect(container.textContent).toMatch(/none\s+of the numbers below is an experimental finding/);
  });

  it("example page presents the application as available, with its source and honest comparison", () => {
    const { container } = render(<ExamplePage />);
    expect(container.querySelector(`a[href="${appSourceUrl}"]`)).not.toBeNull();
    expect(container.textContent).toMatch(/Available/);
    expect(container.textContent).not.toMatch(/Planned/);
    // The estimate is explained as differing from the intrinsic rate, not presented as 1.2.
    expect(container.textContent).toMatch(/That is expected, not an error/);
    // Known bias and the synthetic-only validation are stated, not hidden.
    expect(container.textContent).toMatch(/7\.4% too high/);
    expect(container.textContent).toMatch(/validated on synthetic data\s+only, not on real experimental measurements/);
    // Every figure has descriptive alternative text.
    const images = container.querySelectorAll("img");
    expect(images.length).toBe(3);
    for (const image of images) {
      expect(image.getAttribute("alt")?.length ?? 0).toBeGreaterThan(40);
    }
  });
});

describe("guide pages", () => {
  it.each(guides.map((g) => [g.slug]))("/guides/%s renders", async (slug) => {
    const { container } = await renderGuide(slug);
    expectWellFormed(container);
    expect(container.querySelector("h1")?.textContent).toBe(guides.find((g) => g.slug === slug)?.title);
  });

  it("unknown slugs trigger a 404", async () => {
    await expect(GuidePage({ params: Promise.resolve({ slug: "missing" }) })).rejects.toThrow();
  });

  it("not-found page offers a way back", () => {
    const { container } = render(<NotFound />);
    expect(container.querySelector('a[href="/"]')).not.toBeNull();
  });
});
