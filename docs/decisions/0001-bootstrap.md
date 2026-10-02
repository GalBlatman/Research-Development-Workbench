# ADR 0001: bounded foundation

Status: accepted for RDW-001 by the owner's bootstrap/resume instructions, 2026-10-02.

Context: the canonical rubric and product specification match their supplied baselines. Git works; remote access fails. Python/uv/npm are unavailable on PATH; Node 24.19.0 works. WSL is not required.

Decision: preserve the specification's stack and modular monolith. Use a Windows checkout outside OneDrive, local main bootstrap commit and configured origin. Copy only the four explicitly approved first-party documents byte-for-byte. Use dependency-free Node checks and native test runner now. Pin Node 24.19.0; Python 3.12 is the bootstrap interpreter target, with exact patch/uv/dependency lock pending compatibility review before RDW-002.

Consequences: no application source, runtime services or provider calls; policy manifest/fixture files are deliberately non-executable scaffolds. React/TypeScript tooling and Python tests are pending environment work, not reasons to change architecture. Local CI can be checked structurally; hosted execution remains PENDING_REMOTE. Licensing remains unresolved. The initial main commit is a one-time exception; subsequent tasks use branches/review/merge.
