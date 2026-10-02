import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export function inspectFile(name, bytes) {
  const normalized = name.replaceAll('\\', '/').toLowerCase();
  const errors = [];
  if (/(^|\/)(sources|research ideas rubric|ag(u|ui)nis[^/]*|uploads|runtime|private|reports|extracted|model-outputs|node_modules|\.venv|__pycache__|\.cache)(\/|$)/.test(normalized)
      || /builder-export/.test(normalized)
      || /(^|\/)\.env($|\.)/.test(normalized)
      || /\.(pdf|docx?|pptx?|epub|png|jpe?g|gif|webp|zip|sqlite\d*|db|log|pem|key|p12|pfx)$/.test(normalized)) errors.push('forbidden publication category');
  const permitted = /\.(md|json|toml|mjs|ya?ml|html)$/.test(normalized)
    || (/^backend\/(domain|policy_engine|tests)\/.+\.py$/.test(normalized))
    || ['.gitignore', '.gitattributes', '.node-version', 'backend/.python-version', 'backend/uv.lock', '.githooks/pre-commit'].includes(normalized);
  if (!permitted) errors.push('unreviewed file type; explicit safety review required');
  if (normalized.endsWith('.html') && normalized !== 'docs/reference/interface-wireframe.html') errors.push('unapproved HTML');
  if (bytes.includes(0)) errors.push('binary content');
  const text = bytes.toString('utf8');
  if (/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(text)
      || /\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{20,})\b/.test(text)
      || /(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*["']?[A-Za-z0-9_\-/+]{16,}/i.test(text)) errors.push('possible credential');
  return errors;
}

export function inspectGit(mode = '--tracked', cwd = process.cwd()) {
  const git = (args) => execFileSync('git', args, { cwd, maxBuffer: 20 * 1024 * 1024 });
  const args = mode === '--staged' ? ['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'] : ['ls-files', '-z'];
  const names = git(args).toString('utf8').split('\0').filter(Boolean);
  const errors = [];
  for (const name of names) {
    const entries = git(['ls-files', '--stage', '--', name]).toString('utf8');
    if (/^(120000|160000) /m.test(entries)) errors.push(name + ': symlink/submodule not allowed');
    const staged = git(['show', ':' + name]);
    for (const error of inspectFile(name, staged)) errors.push(name + ': ' + error);
    if (mode === '--tracked') {
      const target = path.join(cwd, name);
      if (fs.existsSync(target)) for (const error of inspectFile(name, fs.readFileSync(target))) errors.push(name + ' (working copy): ' + error);
    }
  }
  return { names, errors };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const mode = process.argv[2] || '--tracked';
  if (!['--tracked', '--staged'].includes(mode)) throw new Error('Use --tracked or --staged');
  const result = inspectGit(mode);
  if (result.errors.length) {
    console.error(result.errors.join('\n'));
    process.exitCode = 1;
  } else console.log('Publication guard PASS: ' + result.names.length + ' ' + mode.slice(2) + ' files');
}
