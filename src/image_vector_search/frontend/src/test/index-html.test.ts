import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const indexHtmlPath = path.resolve(currentDir, "../../index.html");

describe("frontend html shell", () => {
  it("declares both favicon assets", () => {
    const html = readFileSync(indexHtmlPath, "utf8");

    expect(html).toContain('href="/favicon.ico"');
    expect(html).toContain('href="/favicon.png"');
  });
});
