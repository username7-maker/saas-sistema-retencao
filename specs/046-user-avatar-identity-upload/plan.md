# Implementation Plan: User Avatar and Team Identity Upload

## Technical Context

- Backend: FastAPI, SQLAlchemy `User.avatar_url`, existing `/users/me/avatar` multipart endpoint.
- Frontend: React/Vite, Settings profile form, Users administration drawer, shared `UserAvatar`.
- Planning: GSD Phase 4.35 is the execution layer; Spec Kit records the formal scope.

## Scope V1

1. Add a team avatar upload endpoint for owner/manager flows.
2. Keep avatar persistence in `users.avatar_url` as data URL for this pilot cut.
3. Remove manual URL entry as the primary user/team avatar UX.
4. Add focused backend and frontend tests.
5. Update GSD/Obsidian and publish only after validation.

## Validation

- `specify check`
- Backend focused user admin route tests.
- Frontend focused Users/Settings tests.
- `npm.cmd run lint`
- `npm.cmd run build`

## Deployment

Publish to the pilot after focused tests, lint and build pass.
