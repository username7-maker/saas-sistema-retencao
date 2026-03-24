---
phase: 04
slug: import-mapper-e-reconciliacao-manual
status: approved
shadcn_initialized: false
preset: not applicable
created: 2026-03-24
---

# Phase 04 - UI Design Contract

> Visual and interaction contract for the inline import mapper/reconciliation flow inside the existing Imports page.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | custom Tailwind utilities + existing app patterns |
| Icon library | lucide-react |
| Font | `Plus Jakarta Sans` body, `Space Grotesk` heading/display |

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, inline status chips |
| sm | 8px | Compact label/value spacing |
| md | 16px | Default control spacing |
| lg | 24px | Card internals and grouped actions |
| xl | 32px | Space between import blocks |
| 2xl | 48px | Major separation between page sections |
| 3xl | 64px | Not used in mapper itself |

Exceptions: none

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.5 |
| Label | 12px | 600 | 1.4 |
| Heading | 30px | 700 | 1.15 |
| Display | 18px | 700 | 1.2 |

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `hsl(228 27% 96%)` | Page background and quiet surfaces |
| Secondary (30%) | `hsl(0 0% 100%)` | Import cards, mapper rows, modal-like emphasis blocks |
| Accent (10%) | `hsl(267 84% 64%)` | Primary validate/revalidate actions, active mapping status, focus ring |
| Destructive | `hsl(347 83% 59%)` | Blocking errors and destructive ignore confirmations only |

Accent reserved for: primary actions, active step emphasis, selected field targets, focus states. Never use accent for every border or passive label.

---

## Layout Contract

- The mapper lives inside the existing import card, below the preview summary and above the final confirm action.
- The page keeps the current three-block structure:
  - import members card
  - import check-ins card
  - export card
- The mapper is conditional:
  - hidden when preview has no unresolved columns
  - visible when there are unmapped/unrecognized/required-field issues
- The unresolved-columns experience is a stacked list of reconciliation rows, not a new table screen.
- Each reconciliation row must show:
  - source column name
  - up to 2 sample values from the uploaded file
  - current status chip: `Reconhecida`, `Precisa mapear`, `Ignorada`
  - target-field selector
  - ignore action when allowed
- Recognized columns stay in a collapsed support block; they are informative, not the main interaction target.

---

## Interaction Contract

- Operator flow stays linear:
  - select file
  - validate file
  - review preview
  - reconcile columns if needed
  - revalidate preview
  - confirm import
- Any mapper edit invalidates the previous preview and requires a new preview pass before final confirmation.
- The final commit button must remain disabled until:
  - preview exists
  - required mappings are resolved
  - latest preview matches the current mapping state
- Duplicate target-field mappings must be blocked inline with row-level error copy.
- Ignoring a column with non-empty values must require explicit confirmation copy.
- The operator must never lose the current file selection while reconciling mappings in the same card session.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Validar arquivo` / `Revalidar preview` |
| Empty state heading | `Nenhuma coluna precisa de reconciliacao` |
| Empty state body | `O arquivo ja bate com o formato esperado. Revise o impacto e confirme a importacao.` |
| Error state | `Nao foi possivel reconciliar este arquivo. Ajuste as colunas marcadas e valide novamente.` |
| Destructive confirmation | `Ignorar coluna`: `Os valores desta coluna nao serao usados nesta importacao. Deseja continuar?` |

Additional operational copy:
- Mapper section title: `Reconciliar colunas`
- Mapper helper text: `Associe colunas nao reconhecidas aos campos aceitos pelo sistema antes de confirmar.`
- Required field warning: `Este campo e obrigatorio para concluir a importacao.`
- Duplicate target warning: `Ja existe outra coluna mapeada para esse campo. Escolha outro destino ou ignore uma delas.`

---

## Component Contract

- Reuse existing rounded card surfaces:
  - `rounded-2xl border border-lovable-border bg-lovable-surface shadow-panel`
- Mapper rows should use a slightly denser inner card:
  - `rounded-xl border border-lovable-border bg-lovable-surface-soft`
- Status chips:
  - recognized -> neutral `bg-lovable-surface-soft text-lovable-ink-muted`
  - needs mapping -> warning `bg-amber-50 text-amber-950 border border-amber-300`
  - ignored -> subdued neutral with explicit label
- Sample values use muted small text and must truncate gracefully on long spreadsheet content.
- Inline errors stay row-local whenever possible; only use global error banner for file-level blocking states.

---

## Accessibility Contract

- Every mapping selector must have a visible label tied to the source column name.
- Focus order must stay inside the active import card section.
- Status cannot rely on color alone; each row needs explicit text label.
- Revalidate and confirm buttons must expose disabled intent through text and visible disabled styles, not only opacity.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| custom app patterns | import cards, status banners, compact row cards | not required |
| lucide-react | `FileUp`, `Download`, optional mapping-state icons | not required |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-03-24
