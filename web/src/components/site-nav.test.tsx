import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SiteNav } from "@/components/site-nav";
import { primaryNav } from "@/content/site";

const navigation = vi.hoisted(() => ({ pathname: "/" }));
vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));

describe("SiteNav", () => {
  beforeEach(() => {
    navigation.pathname = "/";
  });

  it("links to every primary section", () => {
    render(<SiteNav />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    for (const item of primaryNav) {
      expect(within(nav).getByRole("link", { name: item.label }).getAttribute("href")).toBe(item.href);
    }
  });

  it("marks the current section, including nested pages, with aria-current", () => {
    navigation.pathname = "/guides/reproducibility";
    render(<SiteNav />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Guides" }).getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: "About" }).getAttribute("aria-current")).toBeNull();
  });

  it("opens and closes the mobile menu", () => {
    render(<SiteNav />);
    const button = screen.getByRole("button", { name: "Open menu" });
    expect(button.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    const menu = screen.getByRole("navigation", { name: "Primary mobile" });
    expect(within(menu).getByRole("link", { name: "Home" })).toBeTruthy();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(button.getAttribute("aria-expanded")).toBe("false");
  });
});
