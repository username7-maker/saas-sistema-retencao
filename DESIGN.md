---
name: Cordex Gym OS
description: Precision operations console for gym retention, CRM, and BI — calm dark UI, one accent, action over decoration.
colors:
  carbon: "#0A0B0F"
  sidebar: "#0C0E14"
  surface: "#0E1018"
  surface-elevated: "#101320"
  border: "#202329"
  border-strong: "#266BD9"
  ink: "#F2F3F5"
  ink-muted: "#8B8E96"
  orbit-blue: "#3B82F6"
  orbit-blue-soft: "#021431"
  success: "#10B981"
  warning: "#F59E0B"
  danger: "#FF3B3B"
  ai-violet: "#8B5CF6"
typography:
  display:
    fontFamily: "'Barlow Condensed', 'Space Grotesk', sans-serif"
    fontWeight: 700
    letterSpacing: "-0.01em"
  body:
    fontFamily: "'Inter', 'Barlow', 'Plus Jakarta Sans', sans-serif"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'Inter', 'Barlow', sans-serif"
    fontWeight: 600
    letterSpacing: "0.01em"
  numeric:
    fontFamily: "'JetBrains Mono', ui-monospace, monospace"
    fontFeature: "tabular-nums"
    letterSpacing: "-0.02em"
rounded:
  sm: "8px"
  lg: "12px"
  card: "24px"
components:
  button-primary:
    backgroundColor: "{colors.orbit-blue}"
    textColor: "#04121F"
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "40px"
  button-secondary:
    backgroundColor: "{colors.surface-elevated}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "40px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "40px"
  card-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "20px"
---

# Design System: Cordex Gym OS

## 1. Overview

**Creative North Star: "The Quiet Nucleus"**

The Cordex mark replaces the O in CORDEX with an orbit around a soft glowing core — two
rings crossing at an angle around a single point of light. That's the system: one calm
point of focus (the blue accent), everything else in disciplined near-black orbit
around it. The interface is a precision instrument for gym operators managing churn
risk, follow-ups, and revenue — not a control room. It earns trust through restraint,
not through blinking lights.

This explicitly rejects: generic SaaS scaffolding (Inter-everywhere, identical card
grids, gradient-blob heroes) and the "command center" over-decoration still present as
dead weight in `tailwind.config.js` — a `command`/`pi` neon layer (cyan, purple, green,
red, orange glows, alarm-style pulses) that turned out to be almost entirely unused in
the actual UI (0 files reference the `command-*` classes; only one uses the `pi-*`
glow/pulse utilities). The real, live system — the `lovable-*` dark tokens used across
115 components — is already this calm single-accent identity; it just needs the leftover
neon config formally retired rather than treated as available vocabulary.

**Key Characteristics:**
- Near-black navy depth (four flat layers, no pure black, no drop-shadowed skeuomorphism)
- One accent color (`orbit-blue`) carrying focus, interactivity, and brand identity
- Status colors (success/warning/danger/ai) reserved strictly for state, never decoration
- Condensed display type for headings, tabular monospace for every metric/KPI number
- Motion is a confirmation, not a performance — short, purposeful, respects reduced-motion

## 2. Colors

A single accent on a four-step near-black depth scale. Status colors exist purely to
report state; nothing outside `orbit-blue` should recur as a "brand" color.

### Primary
- **Orbit Blue** (`#3B82F6`): the one accent. Primary buttons, active nav state, links,
  focus rings, chart emphasis, the logo's core glow. Used deliberately, not decoratively
  — if a screen has more than one dominant blue element competing for attention, that's
  a sign color discipline has slipped.

### Neutral
- **Carbon** (`#0A0B0F`): base app background.
- **Sidebar Carbon** (`#0C0E14`): sidebar/topbar, one step darker than content.
- **Surface** (`#0E1018`): card and panel background.
- **Surface Elevated** (`#101320`): modals, popovers, anything raised above a card.
- **Hairline Border** (`#202329`): default 1px borders — visually ~7% white over carbon.
- **Border Strong** (`#266BD9`): only on focus/active/hover states, never at rest.
- **Ink** (`#F2F3F5`): primary text.
- **Ink Muted** (`#8B8E96`): secondary text, labels, timestamps. Never below 4.5:1 against
  its background — check this specifically on `surface-elevated`.

### Status (use only for state, never as accents)
- **Success** (`#10B981`): retention win, task completed, positive trend.
- **Warning** (`#F59E0B`): needs attention soon, approaching a threshold.
- **Danger** (`#FF3B3B`): churn risk, overdue task, failed action.
- **AI Violet** (`#8B5CF6`): exclusively marks AI-generated content (a suggestion, a
  sentiment score, an automation) so users always know what came from the model.

### Named Rules
**The One Nucleus Rule.** `orbit-blue` is the only color allowed to carry brand
identity. Status colors report state; they never substitute as a second "brand" accent.
If a screen needs a second color to feel finished, the layout — not the palette — is the
problem.

**The Retired Neon Rule.** `command-*` and `pi-*` colors/glows in `tailwind.config.js`
(cyan `#00c8ff`, purple `#8b5cf6` used decoratively, green/red/orange glow shadows,
`pi-pulse` animations) are legacy and not part of this system. Do not reach for them in
new work; plan to remove the dead config and the one remaining consumer
(`components/ui2/command/StatusPill.tsx`).

## 3. Typography

**Display Font:** Barlow Condensed (fallback Space Grotesk, sans-serif)
**Body Font:** Inter (fallback Barlow, Plus Jakarta Sans, sans-serif)
**Label/Mono Font:** JetBrains Mono (fallback ui-monospace)

**Character:** A condensed, athletic display face against a neutral, highly-legible body
face — confident headlines, quiet reading text. Every number that matters (KPIs, MRR,
churn %, scores) renders in tabular monospace so figures align and read as data, not
decoration.

### Hierarchy
- **Display** (700, `clamp(1.5rem, 1.1rem + 1.5vw, 2.25rem)`, tight leading): page titles,
  dashboard section headers. Barlow Condensed.
- **Title** (700, 18px, 1.3 line-height): card titles (`CardTitle`).
- **Body** (400, 14–16px, 1.5 line-height): all prose and UI copy. Cap at 65–75ch for any
  long-form text (help text, empty states).
- **Label** (600, 12–13px, +0.01em tracking): form labels, table headers, nav items.
- **Numeric** (JetBrains Mono, tabular-nums, −0.02em tracking): every KPI, currency, and
  metric value. The `.num` utility class already exists in `index.css` — use it, don't
  reinvent it inline.

### Named Rules
**The Tabular Truth Rule.** Any number a user might compare across rows or over time
(MRR, churn %, scores, counts) uses `.num` (JetBrains Mono, tabular-nums). Proportional
figures next to monospace ones is the fastest way to make a dashboard look unfinished.

## 4. Elevation

Flat by default, layered through background steps rather than heavy drop shadows —
depth comes from `carbon → sidebar → surface → surface-elevated`, not from shadow size.
Shadows are short and tight; they confirm a raised state, they don't announce it.

### Shadow Vocabulary
- **Card** (`0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)`): default
  resting shadow for any card/panel, paired with a 1px top inner highlight for glass
  edge.
- **Panel (raised)** (`0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)`
  at rest; larger `0 30px 120px -52px rgba(0,0,0,0.96), 0 14px 44px -28px rgba(59,130,246,0.22)`
  for modals/popovers): the blue-tinted long shadow is the *only* place a colored glow is
  allowed, and only on the top-most, most-important layer.
- **Focus glow** (`0 0 12px rgba(59,130,246,0.28)`): visible focus ring companion on
  interactive elements — restrained, not the aggressive pulsing glows in the retired
  neon layer.

### Named Rules
**The One Glow Rule.** Only `orbit-blue` gets a glow, and only on the single most
elevated surface on screen (a modal, a popover, a focused input) — never on a resting
card, never in more than one color at once, never animated into a pulse.

## 5. Components

### Buttons
- **Shape:** `rounded-lg` (8px) for `sm`, `rounded-xl` (12px) for `md`/`lg`.
- **Primary:** gradient `orbit-blue → info-blue` background, near-black text (`#04121F`)
  for contrast against the bright fill, blue-tinted shadow, hover lifts `-2px` with a
  slight brightness increase. This is the only button variant allowed a gradient.
- **Secondary:** bordered, `surface-soft` background, `ink` text — the default choice
  when primary isn't warranted.
- **Ghost:** transparent, `ink-muted` text, fills to `surface-soft` on hover — for
  low-emphasis actions inside toolbars and tables.
- **Danger:** `danger`-tinted border and background wash, `danger` text — destructive
  actions only.
- **Focus:** every variant gets a 2px `orbit-blue`/`danger`-toned ring with 2px offset;
  never a variant without a visible focus state.

### Cards
- **Corner Style:** `rounded-[24px]` — noticeably softer than buttons; this is the
  system's most generous radius and it's reserved for cards only.
- **Background:** subtle diagonal gradient between `surface` and `surface-soft`
  (145deg), not a flat fill — gives cards faint depth without a heavy shadow.
- **Border:** 1px hairline (`border`).
- **Top edge:** a 64px-tall, near-invisible white gradient (`rgba(255,255,255,0.04)` to
  transparent) simulating a glass top-edge highlight in dark mode only.
- **Internal Padding:** header/content/footer each at 20px horizontal, header adds a
  4px title/description gap.

### Inputs
- **Style:** bordered, `surface-soft` background, 8–12px radius consistent with buttons.
- **Focus:** border shifts to `border-strong`, plus the focus glow token — never just a
  color change alone.

### Status Pills
- **Style:** small rounded-full chip, background = status color at low opacity, text =
  full-strength status color. Currently the only surviving consumer of the legacy
  `pi-*` tokens (`StatusPill.tsx`) — migrate this to the `success`/`warning`/`danger`
  tokens above rather than `pi-green`/`pi-red` when next touched.

## 6. Do's and Don'ts

### Do:
- **Do** treat `orbit-blue` (`#3B82F6`) as the only brand accent; everything else is
  neutral or status.
- **Do** use the four-step neutral depth scale (`carbon` → `sidebar` → `surface` →
  `surface-elevated`) to convey hierarchy instead of stacking shadows.
- **Do** render every KPI/metric number in `.num` (JetBrains Mono, tabular-nums).
- **Do** reserve glow effects for the single most-elevated element on screen, in blue
  only.
- **Do** keep motion short and purposeful (150–450ms), always with a
  `prefers-reduced-motion` fallback — see the existing `stagger-*` and `pi-count-in`
  utilities in `lovable-theme.css` for the calibration to match.
- **Do** show AI-origin content in `ai-violet` so users can always tell what the model
  suggested versus what a human entered.

### Don't:
- **Don't** introduce the `command-*` Tailwind color group (cyan/blue/purple "command
  center" palette) in new components — it's legacy, unused config.
- **Don't** use `pi-*` glow/pulse utilities (`pi-glow-green`, `pi-glow-red`,
  `pi-glow-cyan`, `pi-glow-orange`, `pi-pulse`) — alarm-style pulsing contradicts the
  calm-precision direction; reserve any pulsing state for a true, rare, time-critical
  alert, and even then keep it to the `danger` token, not a rainbow of options.
- **Don't** use gray text on a colored background — bump toward `ink` when contrast is
  close, especially `ink-muted` on `surface-elevated`.
- **Don't** nest cards inside cards, or default to a card when a plain list/row would
  read better (member lists, task queues).
- **Don't** use `border-left`/`border-right` colored stripes as a callout accent —
  they're not part of this system's vocabulary; use the surface/border scale or a status
  icon instead.
- **Don't** let a screen ship with only a dashboard and no actionable task — every
  insight needs an owner, a deadline, and a status per PRODUCT.md's core principle.
