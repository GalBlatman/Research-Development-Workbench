# Scoped persistence adapters

PostgreSQL is canonical; SQLite supports lightweight local tests against the same Pydantic contracts and repository implementation. Provision a private PostgreSQL database with a restricted service account, call Database.postgres(dsn), then Database.initialize() explicitly. Never supply credentials to policy/model code. No deployment or database provisioning service is configured here.

Pass a server-authenticated AccessScope to every repository operation. Register the owner workspace, create a revision-one Project, append sequential revisions/source versions and freeze StoredSnapshot records. SourceService operates on original UTF-8 text/Markdown and a separate private OriginalFileStore root. Source text is admitted explicitly; search requests specify document versions. File metadata stays in SQL while original bytes stay in private files.

Raw Database SQL is infrastructure, not a public application API. Repository checks ownership and composite scope; triggers protect immutable history even against accidental direct updates/deletes. Reuse connections only in their owning service/thread. No source-selection/model text may become SQL or credentials. Later production identity/RLS, retention/deletion, backups and orphan-file cleanup need their own tasks.

Export omits source text by default. include_source_text=True explicitly exports admitted extracted text but never original file bytes. Import into an empty project identity preserves history; it never merges over an existing project. External original/text availability remains explicit.
