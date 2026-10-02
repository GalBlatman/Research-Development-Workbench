import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { inspectGit } from './publication-guard.mjs';

const inventory = inspectGit('--tracked');
if (inventory.errors.length) throw new Error(inventory.errors.join('\n'));
const preserved = new Set(JSON.parse(fs.readFileSync('docs/baselines.json', 'utf8')).documents.map((d) => d.repository_path));
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
