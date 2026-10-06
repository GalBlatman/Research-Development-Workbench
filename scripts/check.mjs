import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { inspectGit } from './publication-guard.mjs';

const inventory = inspectGit('--tracked');
if (inventory.errors.length) throw new Error(inventory.errors.join('\n'));
const preserved = new Set(JSON.parse(fs.readFileSync('docs/baselines.json', 'utf8')).documents.map((d) => d.repository_path));
// Preserve the owner-supplied standalone prompt, including Markdown spacing.
const standalonePrompt = 'docs/tools/Baseline_Plus_Research_Review_Prompt_v1.md';
const standalonePromptHash = crypto.createHash('sha256').update(fs.readFileSync(standalonePrompt)).digest('hex');
if (standalonePromptHash !== 'c913020c79eae444a4aca006c1816ee19e66531c130bf1547251fbb1d2752b3e') throw new Error('Standalone prompt source bytes changed');
preserved.add(standalonePrompt);
for (const name of inventory.names) {
  if (name.endsWith('.mjs')) execFileSync(process.execPath, ['--check', name], { stdio: 'inherit' });
  if (name.endsWith('.json')) JSON.parse(fs.readFileSync(name, 'utf8'));
  if (!preserved.has(name)) {
    const text = fs.readFileSync(name, 'utf8');
    if (/\r|[ \t]+$/m.test(text) || !text.endsWith('\n')) throw new Error('Formatting violation: ' + name);
  }
}
const ci = fs.readFileSync('.github/workflows/ci.yml', 'utf8');
for (const action of ci.matchAll(/uses:\s*([^\s]+)/g)) {
  if (!/@[a-f0-9]{40}$/.test(action[1])) throw new Error('Unpinned CI action');
}
execFileSync(process.execPath, ['--test', 'tests/bootstrap.test.mjs'], { stdio: 'inherit' });
console.log('Foundation syntax, JSON, formatting, pinned-action and publication checks PASS');
