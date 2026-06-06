# Kafka Consumer Lag After a Bad Deployment

## Signals
- Consumer lag begins within minutes of a consumer deployment.
- Throughput falls while incoming message rate remains steady.
- Consumer logs show repeatable processing failures.

## Diagnosis
Compare the incident start time with the deployment stream. Check whether the new consumer
changed deserializers, schema versions, partition assignment, or retry behavior. A poison-message
loop often creates rapidly compounding lag because offsets never commit.

## Safe response
Pause further rollout. Request human approval to roll back the consumer. After rollback, verify
that offsets advance, lag drains, and dead-letter volume remains bounded. Preserve failing payload
metadata for a compatibility test before redeployment.

