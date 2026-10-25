#!/usr/bin/env node
// Generates messages/ar.json from the canonical English tree.
// Existing Arabic translations are preserved; uncovered strings fall back to English.
// A future AI provider can replace translateWithAI().
import fs from 'node:fs';

const en = JSON.parse(fs.readFileSync('messages/en.json', 'utf8'));
const arPath = 'messages/ar.json';
const existing = fs.existsSync(arPath) ? JSON.parse(fs.readFileSync(arPath, 'utf8')) : {};
async function translateWithAI(_text) { return null; }
function flatten(value, prefix = '') {
  return Object.entries(value).flatMap(([key, item]) => item && typeof item === 'object' ? flatten(item, `${prefix}${key}.`) : [[`${prefix}${key}`, item]]);
}
function at(tree, key) {
  return key.split('.').reduce((cursor, part) => cursor?.[part], tree);
}
const output = {};
for (const [key, value] of flatten(en)) {
  const translated = at(existing, key) ?? await translateWithAI(value) ?? value;
  let cursor = output;
  const parts = key.split('.');
  for (const part of parts.slice(0, -1)) cursor = cursor[part] ??= {};
  cursor[parts.at(-1)] = translated;
}
fs.writeFileSync(arPath, JSON.stringify(output, null, 2) + '\n');
console.log('✔ messages/ar.json generated automatically');
