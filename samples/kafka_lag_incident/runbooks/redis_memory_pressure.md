# Redis Memory Pressure Incident

## Signals
- Redis used memory approaches maxmemory.
- Evictions, latency, blocked clients, or replication lag increase.
- Application errors mention OOM or command timeouts.

## Diagnosis
Inspect memory by keyspace, eviction policy, fragmentation ratio, and big keys. Confirm whether a
new workload introduced unbounded streams, hashes, or vector documents. Check persistence and
replica health before changing policy.

## Safe response
Trim bounded streams, remove confirmed disposable keys, and scale capacity through the approved
change process. Never flush the database during incident response. Add retention limits and memory
alerts after recovery.

