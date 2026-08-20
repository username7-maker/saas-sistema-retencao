# Feature Specification: Cordex Method OS V1

**Feature Branch**: `047-cordex-method-os-v1`
**Created**: 2026-06-03
**Status**: Draft
**Input**: Build the first internal Cordex Method OS layer over the existing Cordex Gym OS stack, keeping `Gym` as the physical tenant table while exposing horizontal Method OS APIs and UI.

## User Scenarios & Testing

### Primary User Story

As a Cordex operator, I want to configure a client, load a segment playbook, register operational events, generate tasks, prepare supervised messages, record human actions and measure outcomes so Cordex can replicate the method across segments without rebuilding the product.

### Acceptance Scenarios

1. **Given** a Cordex client has a segment, **When** the operator opens Method OS, **Then** the segment playbook and active pillars are visible.
2. **Given** an event is registered for acquisition, sales or post-sale, **When** a task is generated, **Then** it includes a responsible role, priority, suggested message, optional `wa.me` link and human approval metadata.
3. **Given** a human completes a task, **When** they record an action and outcome, **Then** the dashboard and weekly report include that result.
4. **Given** a new segment is needed, **When** a playbook is configured, **Then** no core schema change is needed for channels, questions, signals, templates or metrics.

## Requirements

- **REQ-01**: Add horizontal entities for segments, playbooks, client method config, people, operational events, operational tasks, human actions, outcomes and Method reports.
- **REQ-02**: Preserve tenant isolation by backing `cordex_client_id` with the existing `gyms.id` / `gym_id` tenant model.
- **REQ-03**: Seed playbooks for academia, clinica, estetica, escola_curso, consorcio and servico_b2b_local.
- **REQ-04**: Generate tasks from events for acquisition, sales and post-sale without automatic external sends.
- **REQ-05**: Generate `wa.me` links only for valid Brazilian phone numbers and editable suggested messages.
- **REQ-06**: Provide deterministic AI fallback functions that always require human review.
- **REQ-07**: Expose Method OS endpoints under `/api/v1/method-os`.
- **REQ-08**: Add one internal UI page at `/method-os` for configuration, dashboard, task execution and weekly report preview.
- **REQ-09**: Provide a minimal generic import foundation for people and events using preview/mapping semantics.

## Out of Scope

- Full SaaS rebuild, broad schema rename, CRM replacement, BI suite, PDF report generation, autonomous agents, automatic WhatsApp sending, deep integrations, object storage and segment-specific custom modules.

## Success Criteria

- A client can be associated with a seeded segment and configured with active pillars.
- A person, event, generated task, human action and outcome can be created through the Method OS API.
- The dashboard and weekly report aggregate tasks, actions and outcomes for the active client.
- The frontend page supports the V1 workflow without changing existing gym-centric screens.

## Assumptions

- The physical tenant table remains `gyms`.
- Method OS APIs use `cordex_client_id` naming where user-facing or API-facing.
- Reports are JSON/Markdown in V1.
- AI is template/deterministic unless an existing safe provider is available.
