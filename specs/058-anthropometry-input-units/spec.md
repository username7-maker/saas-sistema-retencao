# Anthropometry input unit clarity

Every required protocol field ending in `_cm` must show `(cm)` beside its name,
including muscle circumference fields and all repeat attempt accessible labels.
Existing basic height and evolution circumference labels retain their units.
Help text distinguishes tape circumferences in cm from skinfolds in mm.

Invalid required protocol input must identify the field, its unit and the same
limits used by the calculation. Do not modify equations, plausibility limits,
stored assessments or attempt consolidation. Use existing error code support.

Acceptance: Weltman waist 21.5 cm produces a Cintura error with 30–250 cm limits,
not a generic preview failure. Valid calculations and form drafts remain intact.
