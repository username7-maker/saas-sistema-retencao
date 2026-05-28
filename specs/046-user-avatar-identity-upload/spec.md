# Feature Specification: User Avatar and Team Identity Upload

**Feature Branch**: `046-user-avatar-identity-upload`
**Created**: 2026-05-28
**Status**: Draft
**Input**: Advance Phase 4.35 after closing pilot admin surfaces. The next operational gap is making team identity feel real: avatar upload, clear job title, and separation between displayed function and access role.

## User Scenarios & Testing

### Primary User Story

As an owner or manager, I want to manage the visible identity of the team without confusing display information with access permissions.

### Acceptance Scenarios

1. **Given** an authenticated user opens Settings > Perfil, **When** they choose an image file, **Then** the avatar is uploaded and shown after refresh without needing to paste an image URL.
2. **Given** an owner or manager edits a team member, **When** they choose an image file, **Then** that team member avatar updates and the team list refreshes.
3. **Given** a user has a cargo/job title, **When** the team list and profile preview render, **Then** the cargo is shown as identity metadata and role remains the permission label.
4. **Given** an image is invalid or too large, **When** upload is attempted, **Then** the UI and API return a clear error without changing the current avatar.

## Requirements

- **REQ-01**: Avatar upload must use multipart file upload, not URL paste as the primary path.
- **REQ-02**: The current storage path may remain database-backed data URL while the pilot has no dedicated object storage or Railway volume for API uploads.
- **REQ-03**: Owner and manager can upload avatars for users they are allowed to edit; manager cannot edit owner identity.
- **REQ-04**: Audit logs must record content type and size, never raw image data.
- **REQ-05**: UI must explain that role controls permission while cargo/foto controls displayed identity.

## Out of Scope

- External object storage integration.
- New RBAC model or granular permission matrix.
- Bulk user import/update.
- Public avatar CDN.

## Risks

- Storing data URLs in `users.avatar_url` is persistent and simple, but not a long-term media architecture. Move to object storage when the product has storage infrastructure.
- Existing legacy avatar URLs must continue to render.
