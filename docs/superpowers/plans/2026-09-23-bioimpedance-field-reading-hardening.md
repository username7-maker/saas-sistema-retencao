# Bioimpedance Field Reading Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent reference ranges, wrong labels, stale form values and inconsistent observations from entering a bioimpedance evaluation.

**Architecture:** Keep the existing camera and upload workflow. Tighten deterministic validation in the backend, improve assisted fallback selection in the frontend, and make each new OCR read replace only receipt-owned fields while preserving anthropometry.

**Tech Stack:** FastAPI/Pydantic/Pytest, React/TypeScript/Vitest.

**Spec:** `.planning/phases/09.24-ai-first-bioimpedance-reading/PLAN.md`

## Global Constraints

- Keep member context out of the vision provider request.
- Preserve anthropometry and manual profile fields.
- Do not alter persistence schema or OCR API shape.
- Preserve existing unrelated worktree changes.

## Review Focus

- A range endpoint separated by a damaged thermal-printer glyph must not become a measurement.
- A goal or control label must not be accepted as current weight.
- A missing salt or waist-hip field should trigger assisted and recovery reads.
- A second photo must not retain receipt fields from the previous photo.
- Internal inconsistencies should be surfaced without inventing replacement values.

## Tasks

- [x] Add failing backend tests for range separators, label collisions, timestamp and printed-date mismatches, and composition arithmetic.
- [x] Add failing frontend tests for assisted fallback coverage and replacement of receipt fields.
- [x] Implement narrow backend validators and recovery field selection.
- [x] Implement frontend fallback selection and safe receipt-field replacement.
- [x] Run focused tests, backend/frontend suites, lint and build; review diff and deployment readiness.
