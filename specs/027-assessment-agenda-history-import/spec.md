# Spec 027 - Assessment Agenda History Import

## Summary

Create an operational assessment agenda/history layer for the gym's Excel spreadsheets without creating technical `Assessment` records from non-technical data.

## Requirements

- Import spreadsheet rows as `AssessmentAppointment`.
- Preserve scheduled date/time, attendance, payment, evaluator name, notes and source.
- Link evaluator to trainer user when possible.
- Treat attended/completed appointments as historical assessment coverage.
- Do not trigger post-assessment technical ladder from imported operational history.
- Create operational tasks for no-show and pending payment.
