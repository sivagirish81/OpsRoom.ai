# Database Connection Pool Exhaustion

## Signals
- Requests wait for database connections.
- Active connections reach the configured pool or database limit.
- Timeouts and transaction duration rise together.

## Diagnosis
Find long-running transactions, connection leaks, lock contention, and sudden concurrency changes.
Correlate with deployments and traffic changes. Raising the pool size can worsen database overload,
so verify server headroom first.

## Safe response
Roll back a leaking release with human approval, terminate only confirmed abandoned sessions, and
reduce concurrency if necessary. Add pool wait-time telemetry and leak detection before redeploy.

