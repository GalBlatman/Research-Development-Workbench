import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { inspectFile, inspectGit } from '../scripts/publication-guard.mjs';

test('governing copies retain recorded source bytes', () => {
  const baseline = JSON.parse(fs.readFileSync('docs/baselines.json', 'utf8'));
  assert.equal(baseline.documents.length, 4);
  for (const doc of baseline.documents) {
    const actual = crypto.createHash('sha256').update(fs.readFileSync(doc.repository_path)).digest('hex');
    assert.equal(actual, doc.source_sha256);
    assert.equal(actual, doc.repository_sha256);
  }
});

test('implemented policy and golden fixtures match the canonical baseline', () => {
  const manifest = JSON.parse(fs.readFileSync('policies/rubric-v4.manifest.json', 'utf8'));
  assert.equal(manifest.executable, true);
  assert.equal(manifest.status, 'implemented');
  assert.ok(manifest.rules.length >= 27);
  const baseline = JSON.parse(fs.readFileSync('docs/baselines.json', 'utf8'));
  assert.equal(manifest.canonical_sha256, baseline.documents[0].source_sha256);
  const fixtures = JSON.parse(fs.readFileSync('policies/rubric-v4.test-fixtures.json', 'utf8'));
  assert.equal(fixtures.synthetic_only, true);
  assert.equal(fixtures.cases.length, 16);
});

test('guard rejects obvious private categories and synthetic credentials', () => {
  for (const name of ['Sources/article.md', 'Research Ideas Rubric/note.md', 'Sources/Aguinis Guantlet/export.json', 'theory-contribution-builder-export 1.json', '.env.local', 'uploads/draft.md', 'runtime/project.json', 'reports/review.md', 'paper.pdf', 'screenshot.png', 'cache.db', 'credential.pem']) {
    assert.ok(inspectFile(name, Buffer.from('synthetic')).length, name);
  }
  const fakeKey = 'sk-' + 'a'.repeat(30);
  assert.ok(inspectFile('example.md', Buffer.from(fakeKey)).length);
  assert.deepEqual(inspectFile('tests/synthetic.json', Buffer.from('{"synthetic":true}')), []);
});

test('staged guard inspects index bytes even after working copy is cleaned', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'rdw-guard-'));
  const git = (...args) => execFileSync('git', args, { cwd: temp, stdio: 'pipe' });
  try {
    git('init');
    const filename = path.join(temp, 'sample.md');
    fs.writeFileSync(filename, 'sk-' + 'a'.repeat(30));
    git('add', '--', 'sample.md');
    fs.writeFileSync(filename, 'safe synthetic text');
    assert.ok(inspectGit('--staged', temp).errors.some((e) => e.includes('possible credential')));
    git('add', '--', 'sample.md');
    assert.deepEqual(inspectGit('--staged', temp).errors, []);
    fs.writeFileSync(path.join(temp, 'paper.pdf'), 'synthetic PDF placeholder');
    git('add', '--', 'paper.pdf');
    assert.ok(inspectGit('--staged', temp).errors.some((e) => e.includes('forbidden publication category')));
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});

test('reviewed benchmark Python module retains publication restrictions', () => {
  assert.deepEqual(inspectFile('backend/benchmarks/evaluator.py', Buffer.from('"""Synthetic module."""\n')), []);
  for (const name of ['backend/benchmarks/runtime/gold.json', 'backend/benchmarks/uploads/paper.md', 'backend/benchmarks/paper.pdf', 'backend/benchmarks/output.sqlite']) {
    assert.ok(inspectFile(name, Buffer.from('synthetic')).includes('forbidden publication category'));
  }
  const syntheticCredential = 'sk-' + 'a'.repeat(30);
  assert.ok(inspectFile('backend/benchmarks/evaluator.py', Buffer.from(syntheticCredential)).includes('possible credential'));
});
