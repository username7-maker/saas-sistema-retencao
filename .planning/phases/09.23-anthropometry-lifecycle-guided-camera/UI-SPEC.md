# UI Spec - 09.23

## Anthropometry history

- Render valid Brazilian date/time for date-only and full ISO values.
- Show `Relatorio`, `Editar`, `Excluir` and `Abrir PDF premium`.
- Editing reopens the existing protocol form with every recorded attempt.
- Deletion requires confirmation and explains that the record is recoverable.
- Updated/deleted records that need external reconciliation create a visible Actuar
  follow-up task instead of claiming automatic synchronization.

## Premium presentation

- Use the existing clinical report language and layout.
- Label the method as `Antropometria - sem bioimpedancia`.
- Show only metrics available or valid for the modality.
- Compare against the previous manual anthropometry record only.
- Keep PDF and browser print actions.

## Guided scanner

- Prefer the rear camera and high resolution without hard failing on older devices.
- Show a document frame, camera selector and supported torch/zoom controls.
- Review supports crop, 90-degree rotation, retake and confirm.
- Quality checks warn about blur, darkness, glare, small framing and low resolution.
- Only empty/unusable frames are blocked; warnings may be explicitly accepted.
- File upload remains available when camera access is absent or denied.

