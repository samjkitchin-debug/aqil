#!/usr/bin/env node
/**
 * G0 guard: reject raw colour literals in app components (not in tokens.css).
 */
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const webSrc = path.join(process.cwd(), "apps", "web", "src");
const tokenFile = path.join(webSrc, "styles", "tokens.css");
const hexPattern = /#[0-9a-fA-F]{3,8}\b/;
const rgbPattern = /\b(rgb|rgba|hsl|hsla)\s*\(/;

const stylesDir = path.join(webSrc, "styles");
const allowedPaths = new Set([path.normalize(tokenFile)]);

function isAllowedStyleFile(file) {
  const normalized = path.normalize(file);
  if (allowedPaths.has(normalized)) return true;
  if (!normalized.startsWith(path.normalize(stylesDir))) return false;
  return path.basename(normalized).endsWith(".css");
}

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".next") continue;
      files.push(...(await walk(full)));
    } else if (/\.(tsx|ts|jsx|js|css)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

const violations = [];

for (const file of await walk(webSrc)) {
  if (isAllowedStyleFile(file)) continue;
  const content = await readFile(file, "utf8");
  if (file.endsWith("globals.css")) {
    continue;
  }
  const lines = content.split("\n");
  lines.forEach((line, index) => {
    if (hexPattern.test(line) || rgbPattern.test(line)) {
      violations.push(`${path.relative(process.cwd(), file)}:${index + 1}: ${line.trim()}`);
    }
  });
}

if (violations.length > 0) {
  console.error("Token styling guard failed. Use apps/web/src/styles/tokens.css only:\n");
  violations.forEach((v) => console.error(v));
  process.exit(1);
}

console.log("Token styling guard passed.");
