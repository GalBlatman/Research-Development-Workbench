# Minimal React/TypeScript app

RDW-004 includes intake, pasted literature, fixed proposed interpretation and acceptance, fake evaluation, backend rubric results/traces, source inspection, edits, saved review history and exports. It is a local development slice; no full workspaces, authentication or deployment. The fake does not assess scientific text. Generated types in generated/api.ts come from the server OpenAPI; never edit them by hand.

Use Node 24.19.0 and pnpm 11.19.0. In this folder run pnpm install --frozen-lockfile, pnpm build, then pnpm dev. Start the backend first as described in docs/development.md. pnpm exec playwright install chromium installs the local test browser; pnpm test:e2e runs two real browser/backend cases with temporary synthetic storage. No mocked API in the primary flow. Playwright creates ignored test-results only. All runtime research data belongs outside Git.
