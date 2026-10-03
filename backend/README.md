# Backend

Pydantic domain/source/application contracts, pure v4 policy, scoped PostgreSQL/SQLite persistence, source service and RDW-004 FastAPI/workflow/fake-adapter boundary. The fake adapter has no network/model/database access. Policy calculations remain independent of HTTP, models and persistence. See docs/development.md for locked setup, loopback runtime and complete checks. No real provider, authentication, durable worker or deployment is implemented.
