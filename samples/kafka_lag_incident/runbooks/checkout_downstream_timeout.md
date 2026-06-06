# Checkout Latency Caused by a Downstream Timeout

## Signals
- Checkout p95 latency rises with dependency timeout counters.
- Worker concurrency saturates while request throughput falls.
- Logs identify a payment, inventory, tax, or fraud dependency.

## Diagnosis
Break latency down by dependency and compare timeout rates with connection pool utilization.
Determine whether retries amplify load. Kafka lag may be secondary if the consumer synchronously
calls the affected dependency.

## Safe response
Reduce retry amplification, enable the documented circuit breaker, and coordinate with the
dependency owner. Do not assume a deploy is causal unless timing and logs support it.

