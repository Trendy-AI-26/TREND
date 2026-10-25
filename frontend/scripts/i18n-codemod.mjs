#!/usr/bin/env node
// Extracts common hard-coded UI strings into messages/en.json.
// Usage: node scripts/i18n-codemod.mjs
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.cwd());
const SKIP_DIRS = new Set(['node_modules', '.next', '__tests__']);
const SKIP_FILES = /(^|\/)ui\//;
const SKIP_EXACT = new Set(['Trendy', 'TRENDY AI', 'OpenAI', 'Google', 'Instagram', 'Facebook', 'Twitter', 'TikTok', 'LinkedIn', 'Email', 'Password', '✓', '|', '☰', '←', '→', '·']);
const skip = (value) => {
  const s = value.trim();
  return !s || SKIP_EXACT.has(s) || !/[A-Za-z\u0600-\u06FF]/.test(s) || /^[a-z0-9_\-./:#@?=&%]+$/i.test(s);
};
const slug = (s) => s.normalize('NFKD').replace(/[^A-Za-z0-9 ]/g, '').trim().toLowerCase().split(/\s+/).slice(0, 4).join('_') || 'text';
function walk(dir, result = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory() && !SKIP_DIRS.has(entry.name)) walk(file, result);
    else if (entry.isFile() && /\.tsx?$/.test(entry.name) && !SKIP_FILES.test(file.replace(ROOT, ''))) result.push(file);
  }
  return result;
}
const enPath = path.join(ROOT, 'messages/en.json');
const en = fs.existsSync(enPath) ? JSON.parse(fs.readFileSync(enPath, 'utf8')) : {};
const extracted = {};
let changed = 0;
for (const file of walk(ROOT)) {
  if (/next-intl|middleware|language-switcher/.test(file)) continue;
  let code = fs.readFileSync(file, 'utf8');
  const original = code;
  const namespace = path.relative(ROOT, file).replace(/\.tsx?$/, '').replaceAll('/', '.');
  const used = new Set();
  const keyFor = (text) => {
    let key = slug(text), n = 2;
    while (used.has(key) || extracted[`${namespace}.${key}`]) key = `${slug(text)}${n++}`;
    used.add(key); extracted[`${namespace}.${key}`] = text; return key;
  };
  code = code.replace(/\b(title|description|label|placeholder|header|helperText|emptyText):\s*['"]([^'"\n]{3,120})['"]/g, (m, prop, text) => skip(text) ? m : `${prop}: t('${keyFor(text)}')`);
  code = code.replace(/>(\s*[A-Za-z\u0600-\u06FF][^<>{}\n]{1,160}?)</g, (m, text) => skip(text) ? m : `>{t('${keyFor(text)}')}<`);
  if (code === original || !/\bt\(/.test(code)) continue;
  if (!/next-intl/.test(code)) code = `import { useTranslations } from 'next-intl';\n${code}`;
  if (!/const t = useTranslations/.test(code)) code = code.replace(/(function\s+\w+\s*\([^)]*\)\s*\{|const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{)/, `$1\n  const t = useTranslations('${namespace}');`);
  fs.writeFileSync(file, code); changed++;
}
for (const [fullKey, value] of Object.entries(extracted)) {
  const parts = fullKey.split('.'); let cursor = en;
  for (const part of parts.slice(0, -1)) cursor = cursor[part] ??= {};
  cursor[parts.at(-1)] = value;
}
fs.writeFileSync(enPath, JSON.stringify(en, null, 2) + '\n');
console.log(`✔ ${changed} files migrated, ${Object.keys(extracted).length} strings extracted`);
