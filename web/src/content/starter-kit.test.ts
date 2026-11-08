import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { site } from "@/content/site";
import {
  checkCommands,
  copyCommands,
  dailyCommands,
  exampleCommand,
  starterComponents,
  starterDirectory,
  starterSourceUrl,
  starterTree,
  starterVersion,
} from "@/content/starter-kit";

// The starter lives next to the website in the monorepo: ResearchCode/scientific-starter.
// (Built with node:path; Vite would treat `new URL(template, import.meta.url)` as an asset import.)
const starterRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..", starterDirectory);
const starterFile = (path: string) => join(starterRoot, path);
const readme = readFileSync(starterFile("README.md"), "utf8");

/** Command lines from a shell snippet, without trailing comments. */
function commandLines(snippet: string): string[] {
  return snippet
    .split("\n")
    .map((line) => line.replace(/\s+#.*$/, "").trim())
    .filter(Boolean);
}

describe("starter kit page matches the implementation", () => {
  it("finds the starter directory", () => {
    expect(existsSync(starterFile("pyproject.toml"))).toBe(true);
  });

  it.each(starterComponents.flatMap((c) => c.paths.map((path) => [c.name, path])))(
    "%s: %s exists",
    (_, path) => {
      expect(existsSync(starterFile(path)), `missing ${starterDirectory}/${path}`).toBe(true);
    },
  );

  it.each(starterTree.filter((entry) => entry.path).map((entry) => [entry.path!]))(
    "directory tree entry %s exists",
    (path) => {
      expect(existsSync(starterFile(path)), `missing ${starterDirectory}/${path}`).toBe(true);
    },
  );

  it("shows the version declared in pyproject.toml", () => {
    const pyproject = readFileSync(starterFile("pyproject.toml"), "utf8");
    expect(pyproject).toContain(`version = "${starterVersion}"`);
  });

  it.each(commandLines([copyCommands, checkCommands, exampleCommand, dailyCommands].join("\n")).map((c) => [c]))(
    "the starter README documents `%s`",
    (command) => {
      expect(readme).toContain(command);
    },
  );

  it("links to the starter inside this project's repository", () => {
    expect(starterSourceUrl).toBe(`${site.repository}/tree/main/${starterDirectory}`);
    expect(readme).toContain(site.repository);
  });
});
