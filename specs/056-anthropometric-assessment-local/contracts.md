# API Contracts - Spec 056

## GET /api/v1/assessments/anthropometry/protocols

Returns supported protocols only.

Each protocol includes:

- key;
- label;
- formula version;
- supported sex;
- age range;
- required fields;
- optional fields;
- references;
- status.

## POST /api/v1/assessments/members/{member_id}/anthropometry/preview

Calculates a non-persisted preview.

Required body:

- assessment date;
- height;
- weight;
- sex used by formula;
- protocol key;
- measurements and attempts;
- optional observations.

Response includes:

- calculated results;
- indicator origins;
- unavailable metrics;
- warnings/flags;
- calculation hash;
- normalized snapshot preview.

## POST /api/v1/assessments/members/{member_id}/anthropometry

Creates a final anthropometric assessment.

Required header:

```text
Idempotency-Key: UUID
```

Repeated calls with the same key and gym return the already-created assessment.

## GET /api/v1/assessments/members/{member_id}/{assessment_id}/pdf

Generates the premium anthropometric PDF for one local anthropometric assessment.

The PDF identifies:

- modality;
- protocol;
- formula version;
- origin of indicators;
- metric cards only when data exists.
