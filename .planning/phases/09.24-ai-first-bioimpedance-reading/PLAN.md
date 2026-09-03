# Phase 09.24 - AI-first bioimpedance reading safety hotfix

## Objective

Keep the professor's existing photo workflow while making assisted vision the
first operation and preventing plausible-but-unverified demographic values from
silently affecting BMI, BMR or other calculations.

## Delivery

1. Start the assisted image request immediately from the existing CTA; run local
   OCR only as an explicit fallback after an AI failure.
2. Require field evidence from vision output and compute confidence from
   deterministic validation instead of assigning a fixed score.
3. Derive chronological age from member birthdate and assessment date, use the
   member's clinical sex, and keep profile/manual height authoritative.
4. Validate printed weight/BMI against authoritative height and flag only
   critical conflicts as save blockers.
5. Return backward-compatible field provenance, validation issues and processing
   metadata without persisting the image or logging raw OCR/PII.
6. Preserve automatic form filling for coherent reads and add one compact
   conflict-resolution card only when required.

## Safety invariants

- Physical age never becomes chronological age.
- Image suggestions never silently replace authoritative demographics.
- Positional local-OCR guesses never populate the canonical form.
- Existing evaluations and device-reported measurements are not recalculated.
- Member context is reconciled locally and is never sent to the vision provider.
- API, worker and frontend are released from the same source commit.

