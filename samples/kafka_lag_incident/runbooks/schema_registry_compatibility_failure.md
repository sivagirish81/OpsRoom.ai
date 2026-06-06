# Schema Registry Compatibility Failure

## Signals
- Avro, Protobuf, or JSON Schema deserialization errors repeat for the same topic.
- Writer and reader schema fingerprints differ.
- Consumer lag rises while consumers remain technically healthy.

## Diagnosis
Inspect the schema ID on failing messages and compare it with the consumer's generated classes.
Confirm registry compatibility mode and look for a producer rollout that emitted a backward-
incompatible field type, renamed required field, or changed a union default.

## Safe response
Stop or pause the incompatible producer rollout if it is still active. Roll back incompatible
consumers only with human approval. Restore a compatible schema, replay quarantined records, and
add a producer-consumer contract test before redeployment.

