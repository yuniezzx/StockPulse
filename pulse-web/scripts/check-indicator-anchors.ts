#!/usr/bin/env tsx
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
/// <reference types="node" />
/**
 * Validates that every anchor in indicator-doc-nav.ts has a corresponding MDX file
 * at src/content/indicator-doc/{section}/{anchor}.mdx
 *
 * Run: pnpm check:anchors
 * Integrated into: pnpm typecheck (runs first)
 */
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { indicatorDocNav } from "../src/lib/indicator-doc-nav";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const contentBase = join(scriptDir, "../src/content/indicator-doc");
let errors = 0;
let checked = 0;

for (const section of indicatorDocNav) {
  for (const item of section.items) {
    const mdxPath = join(contentBase, section.slug, `${item.anchor}.mdx`);
    checked++;
    if (!existsSync(mdxPath)) {
      console.error(
        `✗ nav anchor "${item.anchor}" → expected file: src/content/indicator-doc/${section.slug}/${item.anchor}.mdx (NOT FOUND)`,
      );
      errors++;
    }
  }
}

if (errors > 0) {
  console.error(`\n✗ ${errors}/${checked} anchor(s) missing MDX files`);
  process.exit(1);
} else {
  console.log(`✓ all ${checked} indicator anchors valid`);
}
