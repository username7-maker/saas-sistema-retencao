# Retention PostgreSQL integration checks

Run from `saas-backend` against an isolated local PostgreSQL database whose name ends in `_test`:

```powershell
$env:RETENTION_TEST_DATABASE_URL='postgresql+psycopg2://postgres@127.0.0.1:55439/cordex_retention_test'
python -m pytest tests/test_retention_postgresql_integration.py -q
```

The suite creates a random schema per test, seeds synthetic gyms/members/alerts, and drops only that schema in teardown. It refuses non-local hosts and non-test database names. Without the explicit URL these three tests are skipped by the ordinary suite.

Coverage: real SQL row locking, simultaneous batches (one success and one 409), rollback after a flushed row/audit event, per-alert and batch audit persistence, episode and actor fields, and isolation between gyms. Cache invalidation is stubbed so this suite never calls external cache services.

Verified locally on 2026-09-18 with PostgreSQL 18.4: all three scenarios passed. No production database or member data was used.

Related UI fixes: failed photography now offers retry; rejected photos resume live analysis with fresh stability; uncertain bulk-response failures refresh retention and no longer claim that zero alerts changed; invalid legacy measurement entries are ignored and measurement rendering failures are contained within the section. No backend runtime behavior or schema migration changed in this delivery.
