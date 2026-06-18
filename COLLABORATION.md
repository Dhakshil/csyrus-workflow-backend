# Collaboration Notes

This document captures assumptions made during development, known limitations, what would change in a production deployment, and scalability considerations.

---

## Assumptions Made

1. **Single reviewer per request.** The schema supports multiple reviewers over time (via `review_actions`), but the UI defaults to assigning one reviewer per request. If only one reviewer exists in the system, the request form auto-selects them.

2. **Role chosen at signup.** Users pick "Requester" or "Reviewer" at the Google login screen. The role is stored on the User row and cannot be changed without re-logging in with a different account or via direct DB update. This was a simplification — a real system would have an admin panel for role management.

3. **One Gmail per user.** Google's `sub` claim is the user key, not email. If a user changes their email in Google, our DB updates it on next login. But each Google account maps to exactly one User row.

4. **Dev-only OAuth consent.** The OAuth consent screen is in "Testing" mode with my own Gmail added as a test user. In production, the app would need Google's verification process.

5. **Reviewer assignment is visible.** The PDF spec required reviewer assignment as a form field. Even though there's typically one reviewer, the form shows a dropdown (auto-selected when only one reviewer exists) so the assignment is explicit.

---

## Known Limitations

1. **JWT in localStorage is XSS-vulnerable.** Any malicious JS can read it. A more secure approach uses HttpOnly cookies, but that requires same-site cookie configuration + CSRF tokens — out of scope for this assessment.

2. **No rate limiting.** Endpoints can be called without throttling. In production, add `slowapi` or a similar rate limiter, especially on `/auth/google/login` and POST endpoints.

3. **No password reset / account deletion flow.** Google handles account recovery. Account deletion is via direct DB access only.

4. **Reviewer ID shown as a dropdown, not searchable.** Works for a small number of reviewers; would need a search component for hundreds.

5. **No pagination UI.** Backend supports `skip`/`limit`, but the frontend always fetches the first 50. For large datasets, the UI would need pagination or infinite scroll.

6. **No real-time updates.** When a reviewer approves a request, the requester's dashboard doesn't update until they refresh. WebSockets or polling would fix this.

7. **No audit log beyond `review_actions`.** Edits and deletes aren't logged. A production system would have a separate audit table.

8. **Inline styles instead of CSS modules.** Faster to develop, but harder to maintain at scale. Trade-off accepted for the assessment timeline.

9. **No refresh tokens.** The JWT expires after 24 hours (`JWT_EXPIRES_MINUTES`). Users must re-login after expiry. A refresh token flow would be more user-friendly.

10. **No automated OAuth tests.** Google's servers are an external dependency. The OAuth flow is manually tested; only JWT issuance and `/auth/me` are unit-tested.

---

## What Would Change in Production

### Security
- **HttpOnly cookies** for JWT storage (instead of localStorage)
- **CSRF protection** if using cookies
- **Rate limiting** on all endpoints, especially auth
- **OAuth consent screen** moved to "In production" mode with Google verification
- **Secrets in a vault** (AWS Secrets Manager, HashiCorp Vault) instead of `.env`
- **HTTPS only** — HSTS, secure cookies
- **Refresh tokens** for long sessions without re-login
- **Audit logging** for all mutations (create/update/delete/approve/reject)

### Infrastructure
- **Alembic migrations** instead of `create_all`
- **Docker + docker-compose** for consistent dev/prod environments
- **CI/CD pipeline** (GitHub Actions) running tests on every PR
- **PostgreSQL connection pooling** (PgBouncer) for high concurrency
- **Redis** for caching user lookups (skip the DB on every request)
- **Static asset CDN** for the React frontend
- **Reverse proxy** (nginx) in front of FastAPI for TLS termination + load balancing

### Architecture
- **Background jobs** (Celery, RQ) for email notifications, async work
- **WebSocket server** for real-time dashboard updates
- **Admin panel** for role management and user administration
- **Search** (Elasticsearch) for full-text search on request descriptions
- **Metrics** (Prometheus + Grafana) for request latency, error rates, etc.

---

## Scalability Considerations

### Current bottlenecks

1. **DB connection pool size:** Engine is configured with `pool_size=5, max_overflow=10`. Fine for ~15 concurrent requests. At higher load, increase pool size or add PgBouncer.

2. **Synchronous SQLAlchemy:** Each request holds a thread. FastAPI's default threadpool handles this, but at very high concurrency (~1000 RPS+), async would scale better.

3. **Single Postgres instance:** No replication or sharding. For HA, add a read replica and route reads to it.

4. **No caching:** Every request hits the DB. Adding Redis for user lookups would cut DB load significantly.

### Horizontal scaling path

1. **Stateless backend** — JWT-based auth means any backend instance can handle any request. Add more FastAPI instances behind a load balancer.
2. **Read replicas** — Route `GET` requests to Postgres read replicas; writes go to primary.
3. **Sharding** — UUID PKs make sharding easier (consistent hash on user_id). For this app, sharding by `created_by` or `reviewer_id` would distribute load.
4. **CDN for frontend** — React build is static; serve via CloudFront/Cloudflare.

### Expected performance (single instance, dev hardware)

- Endpoints: ~200-500 RPS per FastAPI worker
- DB queries: <10ms for indexed lookups
- JWT verification: <1ms
- With 4 uvicorn workers behind gunicorn: ~1000-2000 RPS

For an internal tool with ~1000 users, this is more than enough.

---

## Final Notes

This was a 10-hour build. With more time, the highest-priority improvements would be:
1. Alembic migrations
2. HttpOnly cookies for JWT
3. Real-time updates via WebSockets
4. Frontend pagination
5. CI/CD pipeline

The architecture is intentionally simple and standard — no exotic patterns, no premature optimization. Every decision is documented in `ENGINEERING_DECISIONS.md` with rationale and trade-offs.
