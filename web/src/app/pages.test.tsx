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
  it("starter kit states that nothing is downloadable yet", () => {
    const { container } = render(<StarterKitPage />);
    expect(container.textContent).toMatch(/Not yet available for download/);
    expect(container.textContent).toMatch(/Planned/);
  });

  it("evaluation page presents a design with no results", () => {
    const { container } = render(<EvaluationPage />);
    expect(container.textContent).toMatch(/no data collected yet/i);
    expect(container.textContent).toMatch(/No results yet/);
  });

  it("example page labels its data as synthetic and illustrative", () => {
    const { container } = render(<ExamplePage />);
    expect(container.textContent).toMatch(/All data on this page is illustrative/);
    expect(container.textContent).toMatch(/synthetic/i);
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
