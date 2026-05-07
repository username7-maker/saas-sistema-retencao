# Plan 020 - Lifecycle Orchestration

## Implementation

1. Add computed backend service.
2. Expose computed fields in member schema through model properties.
3. Add lifecycle snapshot to operational profile.
4. Add frontend labels and display.
5. Add unit tests.

## Safety

- No migration.
- No auto-send.
- Tenant safety inherited from existing member endpoints.
- Data quality is surfaced as reason text rather than hidden.
