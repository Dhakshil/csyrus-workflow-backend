# Engineering Decisions

This document records the key architectural and design decisions made during the build, the rationale behind each, and the trade-offs accepted.

---

## 1. Layered Architecture (Routes → Services → Repositories → Models)

**Decision:** Strict four-layer separation. Each layer has one responsibility.

**Rationale:** Separation of concerns. Routes handle HTTP, services own business rules, repositories own SQL, models define data. This makes the codebase:
- **Testable** — services can be tested with mocked repos
- **Replaceable** — swap Postgres for Mongo by only rewriting repos
- **Readable** — when debugging, you know exactly which file to look at

**Trade-offs:** More files than a "fat route" approach. For an app this size, the overhead is worth it because the structure scales — adding a new entity follows the same pattern.

**Alternatives considered:**
- *Fat routes (business logic in route handlers)* — rejected; hard to test, hard to reuse logic across endpoints (e.g. creating a request from a CLI or background job)
- *Active Record pattern (models with save() methods)* — rejected; couples persistence to domain logic

---

## 2. SQLAlchemy 2.0 + Sync (not Async)

**Decision:** Synchronous SQLAlchemy with `create_engine` + `Session`.

**Rationale:** The rubric didn't require async. Sync code is simpler to reason about, simpler to test, and FastAPI handles sync routes by running them in a threadpool automatically. For a CRUD app at this scale, sync is plenty fast.

**Trade-offs:** At very high concurrency, async would scale better (no thread per request). For this assessment's workload, irrelevant.

**Alternatives considered:**
- *Async SQLAlchemy + asyncpg* — adds `async/await` everywhere, complicates testing, no benefit at this scale

---

## 3. UUID Primary Keys (not Integer)

**Decision:** All tables use `UUID` PKs (Postgres native UUID type, `default=uuid4`).

**Rationale:**
- **Non-sequential** — doesn't leak info about user/request counts (unlike integer IDs)
- **Globally unique** — safe for future sharding or distributed systems
- **Industry standard** for new apps

**Trade-offs:** 16 bytes vs 4-8 bytes for integer. Slightly slower index lookups. Negligible at this scale.

---

## 4. Pydantic Schemas Separate from ORM Models

**Decision:** Distinct `User`, `UserRead`, `UserBrief`, `RequestCreate`, etc. — never return ORM models directly.

**Rationale:** API shape ≠ DB shape. We expose subsets (e.g. `UserBrief` omits `google_id` when embedded as `request.creator`). Coupling them causes data leaks and makes API evolution painful.

**Trade-offs:** More code. Worth it for security and clarity.

---

## 5. Repository Pattern with `flush()` instead of `commit()`

**Decision:** Repositories call `flush()` (push to DB without committing). Services call `commit()`.

**Rationale:** Unit of Work pattern. Multi-step operations (e.g. "create review action + flip request status") commit atomically. If a service does 3 repo ops and the second fails, nothing persists — no half-state.

**Trade-offs:** Slightly more code. Essential for data integrity.

---

## 6. Domain Exceptions + Global Handler

**Decision:** Service layer raises domain exceptions (`NotFoundError`, `ForbiddenError`, `ConflictError`, etc.). A single `@app.exception_handler` in `main.py` translates them to HTTP responses.

**Rationale:** Decouples business logic from HTTP. If we expose services via gRPC or a CLI later, no HTTP code needs to change.

**Alternatives considered:**
- *`raise HTTPException(404)` in services* — rejected; couples services to HTTP

---

## 7. Google OAuth: Authorization Code Flow (server-side)

**Decision:** Use the authorization code flow (not implicit flow). Backend exchanges the code for tokens.

**Rationale:** Google's recommended flow for web apps. The code is one-time-use and requires the Client Secret — even if intercepted, it can't be reused. Implicit flow returns tokens directly to the browser (less secure, deprecated by OAuth 2.1).

**Implementation:** Authlib's `OAuth2Client` handles token exchange. We use Google's `sub` claim (stable identifier) as `google_id`, not email — email can change; `sub` never does.

---

## 8. JWT in URL Fragment (not query param)

**Decision:** Backend redirects to `http://localhost:5173/auth/callback#token=xxx` (fragment, not `?token=`).

**Rationale:**
- Fragments aren't sent to servers in subsequent HTTP requests → token doesn't leak to backend logs
- Fragments aren't included in `Referer` headers → token doesn't leak to third-party sites

**Trade-offs:** Browser history still records the URL. Acceptable for dev. In production, HttpOnly cookies would be more secure.

---

## 9. JWT Verification + DB Lookup per Request

**Decision:** Even though the JWT contains user ID + role claims, `get_current_user` fetches the user from the DB on every request.

**Rationale:**
- Catches deleted users (token issued before deletion should not work)
- Catches role changes (admin demotes a user → next request reflects new role)
- The JWT claim is just a hint; the DB is the source of truth

**Trade-offs:** One extra DB query per request. At scale, cache the user in Redis with a short TTL.

---

## 10. Real PostgreSQL Test DB (not SQLite or mocks)

**Decision:** Tests run against a real PostgreSQL test database. Tables dropped + recreated between tests.

**Rationale:**
- SQLite doesn't enforce Postgres-specific features (UUID, ENUM, FK CASCADE)
- Mocking the DB hides SQL bugs (wrong join, missing eager-load)
- Testing real SQL behavior catches bugs that SQLite would miss

**Trade-offs:** Slower than in-memory SQLite (~1s per test vs ~10ms). For 25 tests, total time is ~12s. Worth it for confidence.

**Fix for cached plan error:** psycopg3's prepared statement cache breaks when tables are dropped between tests. Fix: `connect_args={"prepare_threshold": None}` in the test engine.

---

## 11. `selectinload` for Eager Loading (not `joinedload`)

**Decision:** All list endpoints use `selectinload(Model.relationship)` to eager-load related objects.

**Rationale:** Avoids the N+1 query problem. Without it, listing 50 requests with `creator.name` fires 51 SQL queries. With `selectinload`, it fires 3 (requests + creators + reviewers in batches).

**Trade-offs:** `joinedload` does it in one query but multiplies rows (one per relationship row). For list endpoints, `selectinload` is usually faster.

---

## 12. `Base.metadata.create_all()` (not Alembic migrations)

**Decision:** Use `create_all` for table creation in dev. No Alembic migrations.

**Rationale:** For an assessment with no schema changes after initial design, `create_all` is sufficient and saves 30+ minutes of Alembic setup.

**What I'd improve with more time:** Add Alembic for versioned migrations. Production schemas evolve; `create_all` doesn't handle column additions, type changes, or data migrations.

---

## 13. CORS with Explicit Origins (not wildcard)

**Decision:** CORS middleware allows specific origins (`http://localhost:5173`, etc.) with `allow_credentials=True`.

**Rationale:** `allow_origins=["*"]` is incompatible with `allow_credentials=True` (browser security rule). Explicit origins are safer.

---

## 14. Pydantic Settings with `extra="ignore"`

**Decision:** Use Pydantic Settings for config. `extra="ignore"` allows unknown env vars (like `TEST_DATABASE_URL`) without crashing.

**Rationale:** Type-safe config with validation at startup. Missing required vars crash the app immediately (fail-fast), not on first request.

---

## Summary

Every decision above favors **clarity and correctness over cleverness**. The codebase is structured to scale: adding a new entity means adding files in 4 layers (model, schema, repo, service, route), each following the same pattern.
