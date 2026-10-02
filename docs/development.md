# Development environment

Observed 2026-10-02: Windows PowerShell, Git 2.56.0.windows.1, Node 24.19.0. Python, uv and npm unavailable on PATH; WSL access denied. One remote retry failed; origin is configured. No dependencies were installed and no application provider calls made.

Current checks use only Node built-ins. Configure the optional pre-commit hook with git config core.hooksPath .githooks. The hook checks staged blobs, including their staged content, rather than trusting the working copy. Run node scripts/check.mjs before completion.

Python prerequisites before RDW-002: install/provision Python 3.12 and uv; select exact compatible tool versions; resolve/commit uv.lock; verify a clean uv sync --locked and test/lint/type commands. Backend configuration is provisional and does not claim a deterministic dependency environment until locked. FastAPI/Pydantic dependencies belong to their implementation task.

Frontend prerequisites before UI work: provision npm or one documented package manager; choose React/TypeScript build/lint/test tools under a task decision; commit one lockfile, pin versions and verify clean install/build. No package manager or framework was substituted silently. Native Node test/syntax/style checks are sufficient for current check-script code.

Remote push and hosted Actions: PENDING_REMOTE. Do not claim these ran. Fresh local clone verifies available setup only. Deployment, authentication, model/provider, rights/retention and licensing decisions remain pending.
