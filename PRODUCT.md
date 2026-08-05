# Product

## Register

product

## Users

Gym staff, managers, and owners running mid-size academias (800–1,500 alunos), with
ProGym as the founding customer. They work inside the operational reality of a gym:
member churn risk, follow-ups, NPS, physical assessments, sales pipeline, compliance —
not abstract analytics. The job to be done is turning loose operational data into
practical action: who needs attention, what the next step is, whether it happened, and
what it produced. Cordex expands the same product logic to other local-business
verticals (clinics, esthetics, schools) later, so nothing in the product should assume
"gym" is a special case rather than the first vertical.

## Product Purpose

Cordex Gym OS is the first product of Cordex, an AI-first B2B SaaS that acts as the
operational and revenue layer for local businesses. For gyms specifically, it unifies
BI, CRM, predictive retention, NPS, physical assessment, WhatsApp messaging, and LGPD
compliance into one system. Success means staff spend their day acting on a queue of
owned, dated, trackable tasks generated from real signals (churn risk, inactivity,
survey sentiment) — not staring at charts.

## Brand Personality

Precise, calm, premium-technical. Anchored on the real Cordex identity: the wordmark's
orbital/atom symbol (soft blue radial glow around dark rings) and the existing
cordex-site palette — near-black navy background (`#050A12` / `#0A1628`), a single blue
accent family (`#3B82F6` core) used as a soft glow rather than a neon rainbow, off-white
text, and gentle `cubic-bezier` easing. Layered on top: a premium sports-tech feel
("Tecnofit" reference) — the sensation of high-performance athletic gear or a premium
training app, not a generic admin panel. Confidence and restraint over alarm; the
product should feel like a precision instrument, not a control room full of blinking
lights.

## Anti-references

- Generic SaaS: bland admin templates, identical card grids, Inter-everywhere,
  gradient-blob heroes — the product must read as built specifically for gym
  operations, not a reskinned admin boilerplate.
- The current `tailwind.config.js` "command center" direction (multi-neon
  cyan/blue/purple/green/red glows, alarm-style pulsing) is explicitly being moved away
  from in favor of the calmer, single-accent Cordex identity above.

## Design Principles

1. **Action over dashboard** — every insight surfaces as a task with an owner, a
   deadline, and a status. A screen that only displays data without a trackable next
   action is incomplete.
2. **Human-approved AI** — AI suggestions are always visible, explained, and require
   explicit human approval before they reach a member. Nothing acts silently on
   someone's behalf.
3. **Signal over noise** — visual emphasis (color, glow, motion) is reserved for what
   genuinely needs attention. Calm by default; alert only when it matters.
4. **Trust is visible** — the product handles sensitive member data (LGPD-protected).
   Precision and care should read in the interface itself, not just in policy docs.
5. **One product, many verticals** — nothing in the design hard-codes "gym" as special;
   language and structure should generalize to future Cordex verticals.

## Accessibility & Inclusion

WCAG AA baseline: minimum 4.5:1 text contrast, full keyboard navigation, visible focus
states (partially already present via `:focus-visible` in `index.css`). No additional
regulatory requirement known beyond LGPD data-handling rules, which are a legal/data
concern rather than an accessibility one.
