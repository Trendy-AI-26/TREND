#!/usr/bin/env node
// Safer variant of i18n-codemod.mjs: only touches real React component
// files (.tsx with a JSX-returning component), never .ts data/hook files
// or module-scope objects (e.g. `metadata`), which the naive version
// corrupted (t() inserted outside any function).
// Usage: node scripts/i18n-codemod-safe.mjs [subdir ...]
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.cwd());
const ARGS = process.argv.slice(2);
const TARGET_DIRS = ARGS.length ? ARGS.map((d) => path.resolve(ROOT, d)) : [ROOT];

const SKIP_DIRS = new Set(['node_modules', '.next', '__tests__']);
const SKIP_FILES = /(^|\/)ui\//;
const SKIP_EXACT = new Set(['Trendy', 'TRENDY AI', 'OpenAI', 'Google', 'Instagram', 'Facebook', 'Twitter', 'TikTok', 'LinkedIn', 'Email', 'Password', '✓', '|', '☰', '←', '→', '·']);
const skip = (value) => {
  const s = value.trim();
  // Note: the identifier/slug check below is deliberately case-SENSITIVE.
  // Real UI copy is capitalized ("History", "Operator", "Keys"); code-like
  // tokens (slugs, env-style keys, css classes) are lowercase. Making this
  // check case-insensitive (as the original script did) accidentally
  // skipped every single-word capitalized label in the whole app.
  return !s || SKIP_EXACT.has(s) || !/[A-Za-z\u0600-\u06FF]/.test(s) || /^[a-z0-9_\-./:#@?=&%]+$/.test(s);
};
const slug = (s) => s.normalize('NFKD').replace(/[^A-Za-z0-9 ]/g, '').trim().toLowerCase().split(/\s+/).slice(0, 4).join('_') || 'text';

function walk(dir, result = []) {
  if (!fs.existsSync(dir)) return result;
  if (fs.statSync(dir).isFile()) { if (dir.endsWith('.tsx')) result.push(dir); return result; }
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory() && !SKIP_DIRS.has(entry.name)) walk(file, result);
    else if (entry.isFile() && entry.name.endsWith('.tsx') && !SKIP_FILES.test(file.replace(ROOT, ''))) result.push(file);
  }
  return result;
}

// Find the matching closing brace for the `{` at the end of `text`,
// starting the scan at `startIndex` (the position right after that `{`).
// Naive char-counter; good enough for well-formed TS/TSX source (does not
// special-case braces inside strings/templates, which is an acceptable
// approximation for this codebase's formatting style).
function findMatchingBrace(code, startIndex) {
  let depth = 1;
  for (let i = startIndex; i < code.length; i++) {
    if (code[i] === '{') depth++;
    else if (code[i] === '}') { depth--; if (depth === 0) return i; }
  }
  return code.length;
}

// A file is only eligible if it's a real component: exports a
// function/const component AND has a JSX return body ("return (" or "=> (")
// in the SAME function as the export, and is not "use client" metadata-only.
// Returns { index, text, bodyStart, bodyEnd } describing the *body span* the
// replacements are allowed to touch — never module-level code outside it.
function findComponentFunction(code) {
  const fnRe = /export default function\s+\w*\s*\([^)]*\)\s*(?::[^{]+)?\{|export (?:default )?(?:async )?function\s+\w+\s*\([^)]*\)\s*(?::[^{]+)?\{|(?:export )?(?:default )?const\s+\w+\s*(?::[^=]+)?=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>\s*\{/g;
  let m;
  const matches = [];
  while ((m = fnRe.exec(code))) matches.push({ index: m.index, text: m[0] });
  if (!matches.length) return null;
  // Prefer a match whose body contains JSX (a '<Tag' or return ( pattern)
  for (const cand of matches) {
    const bodyStart = cand.index + cand.text.length;
    const after = code.slice(bodyStart, bodyStart + 4000);
    if (/return\s*\(|return\s*</.test(after)) {
      const bodyEnd = findMatchingBrace(code, bodyStart);
      return { ...cand, bodyStart, bodyEnd };
    }
  }
  return null;
}

const enPath = path.join(ROOT, 'messages/en.json');
const en = fs.existsSync(enPath) ? JSON.parse(fs.readFileSync(enPath, 'utf8')) : {};
const extracted = {};
let changed = 0;
const changedFiles = [];

for (const dir of TARGET_DIRS) {
  for (const file of walk(dir)) {
    if (/next-intl|middleware|language-switcher/.test(file)) continue;
    let code = fs.readFileSync(file, 'utf8');
    if (/from 'next-intl'|from "next-intl"/.test(code)) continue; // already wired, don't double-declare `t`
    const original = code;
    const namespace = path.relative(ROOT, file).replace(/\.tsx?$/, '').replaceAll('/', '.');

    const comp = findComponentFunction(code);
    if (!comp) continue; // not a JSX component we can safely wire

    const used = new Set();
    const keyFor = (text) => {
      let key = slug(text), n = 2;
      while (used.has(key) || extracted[`${namespace}.${key}`]) key = `${slug(text)}${n++}`;
      used.add(key); extracted[`${namespace}.${key}`] = text; return key;
    };

    // Only rewrite text INSIDE the component's own body — never module-level
    // arrays/objects declared before or after it (that was the bug in the
    // original codemod: it inserted t() calls that were out of scope).
    const before = code.slice(0, comp.bodyStart);
    let body = code.slice(comp.bodyStart, comp.bodyEnd);
    const afterCode = code.slice(comp.bodyEnd);

    // Attribute-style strings, e.g. label: "..." (object) or aria-label="..." (JSX prop).
    body = body.replace(/\b(title|description|label|placeholder|header|helperText|emptyText|aria-label|alt):\s*['"]([^'"\n]{3,120})['"]/g, (m, prop, text) => skip(text) ? m : `${prop}: t('${keyFor(text)}')`);
    body = body.replace(/\b(label|description|header|helperText|emptyText|aria-label|alt|title|placeholder)=["']([^"'\n]{3,120})["']/g, (m, prop, text) => skip(text) ? m : `${prop}={t('${keyFor(text)}')}`);

    // Plain JSX text nodes: >Some text<. Allows the text to be wrapped onto
    // its own line (common with Prettier) by permitting embedded newlines.
    // The (?<![=\s]) guard is critical: without it this also matches stray
    // '>' characters that are actually '=>' arrows or 'a > b' comparisons
    // in plain JS/TS code elsewhere in the function, and then swallows
    // everything up to the next unrelated '<' — silently corrupting the file.
    body = body.replace(/(?<![=\s])>([ \t\n]*[A-Za-z\u0600-\u06FF][^<>{}]{0,200}?)</g, (m, rawText) => {
      const text = rawText.replace(/\s+/g, ' ').trim();
      // Extra safety net: real UI copy doesn't contain these JS/TS tokens.
      if (/[=;]|&&|\|\||=>|<=|>=|!==|===/.test(rawText)) return m;
      if (skip(text)) return m;
      return `>{t('${keyFor(text)}')}<`;
    });

    if (!/\bt\(/.test(body)) continue; // nothing eligible found in this component

    code = before + `\n  const t = useTranslations('${namespace}');` + body + afterCode;

    if (!/from 'next-intl'/.test(code)) {
      // 'use client' must remain the very first statement in the file (Next.js
      // requires this literally) — insert the import after it, not before.
      const directiveMatch = code.match(/^((?:\s*\/\/[^\n]*\n|\s*\n)*)(['"]use client['"];?)(\s*\n)/);
      if (directiveMatch) {
        const insertAt = directiveMatch[0].length;
        code = code.slice(0, insertAt) + `import { useTranslations } from 'next-intl';\n` + code.slice(insertAt);
      } else {
        code = `import { useTranslations } from 'next-intl';\n${code}`;
      }
    }

    fs.writeFileSync(file, code);
    changed++;
    changedFiles.push(path.relative(ROOT, file));
  }
}

for (const [fullKey, value] of Object.entries(extracted)) {
  const parts = fullKey.split('.'); let cursor = en;
  for (const part of parts.slice(0, -1)) cursor = cursor[part] ??= {};
  cursor[parts.at(-1)] = value;
}
fs.writeFileSync(enPath, JSON.stringify(en, null, 2) + '\n');
console.log(`✔ ${changed} files migrated, ${Object.keys(extracted).length} strings extracted`);
console.log(changedFiles.map((f) => ` - ${f}`).join('\n'));
