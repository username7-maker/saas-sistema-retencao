# Spec 057 - Antropometria Actuar Core

## Status

Spike preflight executed on 2026-07-16. Implementation is NO-GO until a live Actuar test passes the matrix in `ACTUAR-SPIKE.md`.

No Actuar sync is part of Spec 056, and no anthropometric Actuar sync is authorized by this Spec 057 result yet.

## Required spike before implementation

Before implementing the pipeline, run a controlled technical proof in Actuar with a designated test student and capture evidence in `ACTUAR-SPIKE.md`.

Validation matrix:

1. required fields;
2. whether muscle mass can be empty;
3. whether date, weight, height and body fat are enough to save;
4. whether Actuar differentiates physical assessment, anthropometry and bioimpedance;
5. how to capture `external_assessment_id`;
6. how the assessment appears in Actuar history/report;
7. whether previous creation can be detected by search/key/marker;
8. behavior after save, update and page close;
9. behavior after timeout following final click.

## Go/no-go

If Actuar requires muscle mass or does not expose a safe way to recover the created external ID:

- V1.1 does not advance;
- the local V1 remains published;
- UI must show that Actuar sending is not available for anthropometry.

Current preflight result:

- muscle-mass-empty save is unverified;
- minimum payload save is unverified;
- current backend/bridge contract does not yet persist a created assessment id as `external_assessment_id`;
- therefore Actuar Core implementation remains blocked.

## Conditional implementation after PASS

- Create `assessment_push`.
- Reuse existing `ActuarSyncJob`, attempts, member binding, bridge, extension, logs and status.
- Create a separate anthropometric mapper.
- Send only date, weight, height and official body fat percentage.
- Do not send skinfolds, perimeters or muscle mass.
- Require `external_assessment_id`.
- Start with ProGym allowlist only.

## Idempotency

- `UNIQUE (gym_id, assessment_id, job_type)`
- `UNIQUE (gym_id, external_assessment_id)`

The PostgreSQL job row is the transactional outbox. No Actuar access happens inside the HTTP transaction.
