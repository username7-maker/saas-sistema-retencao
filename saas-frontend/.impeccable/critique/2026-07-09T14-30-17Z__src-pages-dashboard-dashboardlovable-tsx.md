---
target: src/pages/dashboard/DashboardLovable.tsx
total_score: 15
p0_count: 1
p1_count: 4
timestamp: 2026-07-09T14-30-17Z
slug: src-pages-dashboard-dashboardlovable-tsx
---
Method: dual-agent (A: general-purpose design-review agent · B: general-purpose detector/browser-evidence agent)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 2 | Skeletons exist for metric cards, but the "Hoje" panel fails to a permanent, unrecoverable error state with no explanation |
| 2 | Match System / Real World | 2 | Domain language is right, but raw `[SEED100_FULL_V1]` fixture strings leak into member names shown to the user |
| 3 | User Control and Freedom | 2 | No dismiss/snooze/filter on alerts or the action queue; a hard reload on this route silently bounces to `/login` |
| 4 | Consistency and Standards | 1 | Card radius diverges from spec (`Card.tsx`=24px vs. the actually-used `CommandCard.tsx`=18px); two parallel status-color systems coexist |
| 5 | Error Prevention | 2 | Zero-value metrics ("Novos alunos: 0") render in the same bold treatment as populated ones — reads as a possible bug |
| 6 | Recognition Rather Than Recall | 3 | Icons are consistently text-labeled; sidebar active state is clear |
| 7 | Flexibility and Efficiency of Use | 1 | No shortcuts, no bulk actions on a 13-item critical queue, no saved views |
| 8 | Aesthetic and Minimalist Design | 1 | Directly contradicts the project's own "One Nucleus Rule" — 5 competing accent colors on first paint |
| 9 | Error Recovery | 1 | "Tentar de novo" is the entire recovery path — no explanation, no fallback content |
| 10 | Help and Documentation | 0 | No help affordance anywhere on the screen |
| **Total** | | **15/40** | **Poor — significant improvements needed before users are happy** |

## Anti-Patterns Verdict

**Start here: yes, this reads as AI-generated**, and it's now triple-confirmed — independent LLM design review, static source scan, and live rendered-DOM overlay all converged on the same core tells.

**LLM assessment (Assessment A):** Gradient text on the hero H1 ("IA de risco em tempo real"), the hero-metric template (big gradient headline + eyebrow + stat pills) wrapping it, a tiny-uppercase-tracked eyebrow ("PERFORMANCE INTELLIGENCE"), 8 near-identical metric cards with no hierarchy, and five competing accent colors (blue/green/amber/rose/violet) all live on first paint — the last one a direct violation of this project's *own* committed DESIGN.md "One Nucleus Rule." The component folder is even still named `ui2/command/` — a `CommandCard` — despite DESIGN.md explicitly retiring the "command center" direction by name.

**Deterministic scan (Assessment B):** Static `detect.mjs` confirmed the gradient-text hit at `DashboardLovable.tsx:105` exactly where the LLM flagged it — and found the *same pattern repeated across all four other dashboard pages* (Commercial, Financial, Operational, Retention: `CommercialDashboardPage.tsx:97`, `FinancialDashboardPage.tsx:160`, `OperationalDashboardPage.tsx:107`, `RetentionDashboardPage.tsx:804,827`). This isn't a one-off on the page reviewed — it's a systemic pattern across the whole dashboard section. Plus 4 more "design-system-color" advisories (undocumented `rgba()` values bypassing DESIGN.md tokens) in `DashboardLovable.tsx`, `ThemedToaster.tsx`, and `LineSeriesChart.tsx`.

**Visual overlays (live, user-visible right now):** the live-DOM detector found **57 findings across 44 elements** on the rendered page — far more than the static scan, because it measures computed styles, not source regex. Breakdown: **nested-cards ×19** (the single largest category — a direct hit against DESIGN.md's own "Don't nest cards inside cards" rule and SKILL.md's absolute-ban framing of nested cards), **dark-glow ×11** (against the "One Glow Rule" — glow is supposed to be reserved for one elevated surface, not eleven), **low-contrast ×9** (accessibility), **gpt-thin-border-wide-shadow ×6**, **line-length ×3**, **clipped-overflow-container ×2**, **hero-eyebrow-chip ×2**, **gradient-text ×2**, plus one each of ai-color-palette, overused-font, and codex-grid-background. These overlays are live right now in your browser in the tab titled **"IMPECCABLE-PREFLIGHT-B"** — yellow outlines with labels directly on the dashboard.

No false positives identified in either scan — every flagged snippet was manually verified against source.

## Overall Impression

The information architecture instinct is right — lead with "what do I do today," not a chart wall — and the calm-dark-plus-one-accent system is the correct call for a retention tool per this project's own brief. But the execution contradicts the very design system that documents it, in ways both cosmetic (gradient hero, 19 nested-card instances, 5 competing accents) and functional (the page's stated primary feature — the daily action panel — is completely broken against real data, not stylistically rough but structurally non-functional). The single biggest opportunity: fix the 404s powering the "Hoje" panel first, since everything else is polish on top of a feature that currently doesn't work at all.

## What's Working

1. **The metric tone system is legitimately state-driven, not decorative.** `MetricCard`'s color mapping (danger/success/warning/info) tracks real state, and the `.num` JetBrains Mono tabular treatment — DESIGN.md's one explicitly named "Tabular Truth Rule" — is implemented correctly everywhere it was checked. The idea is sound even where the palette overuses it.
2. **Focus states are genuinely good.** Tabbing through interactive elements produces a clean, visible blue focus ring with proper offset — rare to get right, and it directly serves this project's stated WCAG AA commitment.
3. **Zero console errors, clean API contract everywhere except two endpoints.** Of ~11 API calls the page makes, only 2 fail (both 404s, both tied to the same broken panel) — the rest of the data layer is solid, which narrows the P0 fix to a specific, bounded problem rather than a systemic one.

## Priority Issues

**[P0] The "Hoje" panel — the page's stated primary feature — is broken by a real backend contract mismatch, confirmed via network evidence.**
Why it matters: this project's own PRODUCT.md principle #1 is "action over dashboard... a screen that only displays data without a trackable next action is incomplete," and the component built specifically to deliver that (`TodayBlock`) is the first thing users see, and it's non-functional. Network capture confirms this isn't a loading-state design gap — `GET /api/v1/cockpit/daily` and `GET /api/v1/cockpit/weekly-funnel` both return **404**, reproduced identically across two separate sessions. The frontend is calling endpoints that don't exist on the backend.
Fix: This is a backend routing/contract bug, not a design fix — confirm the correct endpoint paths and either fix the route or the frontend's call. Once data flows, still design a real empty/error state (not a bare "tentar de novo") for whenever this legitimately has nothing to show.
Suggested command: `/impeccable harden`

**[P1] Nested cards, 19 instances — the single most common issue found, and a direct violation of the project's own DESIGN.md rule.**
Why it matters: DESIGN.md explicitly says "don't nest cards inside cards, or default to a card when a plain list/row would read better (member lists, task queues)" — and the live overlay found 19 nested-card instances on exactly the surfaces that rule calls out (the action queue, the risk matrix). This is the highest-volume, most systemic issue on the page.
Fix: Flatten the action-queue and risk-matrix items into rows/list treatments per DESIGN.md's own guidance, reserving the card shape for the outer container only.
Suggested command: `/impeccable layout`

**[P1] Gradient hero headline + hero-metric template, repeated across all 5 dashboard pages.**
Why it matters: triple-confirmed (manual review, static scan, live overlay) as both a universal AI-slop tell and a violation of this project's own "One Glow Rule" (glow/color reserved for one elevated surface, never headline type). Confirmed not isolated to this page — the identical pattern exists in Commercial, Financial, Operational, and Retention dashboards too.
Fix: Replace the gradient span with solid `ink` or a single deliberate `orbit-blue` use; let the strong insight copy underneath carry the section instead of decorative type. Apply the same fix across all 5 dashboard pages, not just this one.
Suggested command: `/impeccable quieter`

**[P1] Color discipline: 5 competing accents + 11 dark-glow instances + the retired `pi-*` neon tokens are still live in `StatusPill.tsx`.**
Why it matters: DESIGN.md names `StatusPill.tsx` by filename as the one remaining consumer of the legacy `pi-green`/`pi-red`/`pi-pulse` tokens that needs migrating — it hasn't been. Combined with `MetricCard`'s 5-tone palette and the overlay's 11 dark-glow hits (against a rule that reserves glow for exactly one surface), this is the project's own committed spec being violated by its own shipped code, not a generic style critique.
Fix: Migrate `StatusPill.tsx` onto `success`/`warning`/`danger`/`ai-violet` tokens; audit `MetricCard` so only 1-2 tones read as "hot" per view.
Suggested command: `/impeccable colorize`

**[P1] Chart tooltip shows the wrong label for real data — a confirmed code bug, not a style issue.**
Why it matters: hovering the "Churn e NPS" chart shows *two* lines both labeled "NPS médio" (one the real NPS value, one actually the churn rate). Root-caused in source: the tooltip formatter checks `if (key === "churn_rate")` but the callback's second argument is the series `name` prop, not its `dataKey`, so that branch is dead code and churn always falls through to the NPS label. For a product whose principle #4 is "trust is visible," a manager reading the wrong metric off a chart while making retention decisions is a real data-integrity problem, not polish.
Fix: Correct the formatter to match on the actual `name`/`dataKey` Recharts passes, not a string that's never equal to it.
Suggested command: `/impeccable harden`

**[P2] Low contrast, 9 instances (accessibility) + dead space/layout imbalance + raw seed artifacts in copy.**
Why it matters: 9 low-contrast hits from the live overlay corroborate the Sam-persona accessibility concerns below. Separately, the left content column runs out of content ~300-400px before the right rail does, reading as a layout bug rather than intentional space. And every action-queue item displays `[SEED100_FULL_V1]` ahead of the member's real name — a data-hygiene miss that undercuts trust at the exact moment the tool is asking a manager to trust an AI risk score.
Fix: Run a contrast pass against DESIGN.md's 4.5:1 baseline; equalize or internally-scroll the shorter dashboard column; strip/sanitize fixture prefixes from any display name regardless of data source.
Suggested command: `/impeccable audit`, then `/impeccable layout`

## Persona Red Flags

**Alex (Power User / gym manager, daily user for months)**
- No keyboard shortcuts for the core loop (open a specific at-risk member, mark a task done) — every action is a full mouse trip to "Abrir."
- No bulk action on the queue — 13 critical-risk members require 13 individual clicks, the textbook "one-item-at-a-time where batch would be natural" red flag.
- The broken "Hoje" panel with only a generic retry button is a direct abandonment trigger for a daily user — hit it once, lose trust, go back to a spreadsheet.
- Zero customization: no saved views, no reordering or hiding metric cards.

**Sam (Accessibility-dependent, keyboard/screen-reader user)**
- Focus states are genuinely good — a real strength, not a flag.
- 9 low-contrast instances found live on this exact page (overlay-confirmed) — meaning meets color contrast isn't consistently true across the surface, despite the project's stated WCAG AA commitment.
- The confirmed chart-tooltip bug is worse for Sam than a cosmetic glitch: a screen-reader user relying on the tooltip announcement to distinguish churn from NPS would be told the wrong metric outright.
- No `aria-live` region evident for the two failed "Hoje" panels — a screen-reader user gets no announced heads-up that data failed to load.

**Riley (Deliberate stress tester)**
- "Novos alunos: 0" renders in the same bold 5xl treatment as every populated metric — indistinguishable from a bug at a glance.
- `[SEED100_FULL_V1]` fixture strings rendering as real member-facing copy is exactly the "feature that appears to work but exposes internal implementation detail" Riley is built to catch.
- A hard reload on `/dashboard/executive` silently bounces to `/login` rather than preserving session/route — reproduced once; worth confirming intent vs. bug.

## Minor Observations

- `SectionHeader`'s eyebrow prop is applied inconsistently — some sections get it, most don't; pick one system.
- The connecting-line "flow" visual in "Mapa de Inteligência Operacional" only renders at the `xl:` breakpoint and silently disappears below it, undermining the section's own premise below that width.
- 3 line-length overlay hits and 2 clipped-overflow-container hits (likely tooltip/dropdown content escaping a scroll container) — both worth a pass under `/impeccable adapt`.
- "FLUXO DE DECISÃO" / "RETENÇÃO" are used as static section-tag pills wearing `StatusPill` styling meant for actual state — blurs the component's semantic purpose.
- Currency formatting truncates to 0 decimal places (`maximumFractionDigits: 0`) — fine for MRR at this scale, worth confirming it doesn't misrepresent smaller deltas elsewhere.

## Questions to Consider

1. DESIGN.md names the exact file (`StatusPill.tsx`) and exact rule (nested cards, one-glow) being violated — is there a missing enforcement step between "design system documented" and "design system shipped," like a lint pass tied to this detector?
2. The panel embodying this product's entire stated thesis ("action over dashboard") is the one that's structurally broken against real data — what does that suggest about how this surface got tested before shipping?
3. If only the single worst problem on this page got visual weight and everything else went quiet, would that change what staff act on first — or just make the page calmer to look at?
