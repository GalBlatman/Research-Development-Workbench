# Intended data flow

RDW-003 implements authorized original text/Markdown -> separate private original store -> immutable source versions/anchors -> scoped admitted lexical search, plus immutable project/snapshot persistence and portable record JSON. There is no UI/model evaluation workflow.

Future: authorized user inputs -> immutable private file store/document versions -> isolated parsing -> anchored text and coverage -> server-authorized retrieval packet -> bounded workflow -> provider adapter -> anchor/semantic verification -> pure policy engine -> inspectable report and proposed actions. Structured records live in PostgreSQL behind authorized services; original files remain separate.

Acceptance creates a new revision and adoption state, never verified evidence. Evaluations freeze object/document versions plus policy/prompt/model configuration. Authorization is rechecked before context creation and output publication. An external provider receives only admitted authorized context under separate processing consent; provider choice remains pending. No arbitrary fetching or model-selected file paths.

Deletion must cover originals, parsed text, records, indexes, context/output caches, reports and backups per an accepted retention design before pilot. Logs must avoid confidential text/secrets. CI uses synthetic material only.
