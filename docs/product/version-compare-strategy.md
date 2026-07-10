# Version Compare Strategy — Phase 19.4

## Overview

Scotch tracks every design change as an immutable `ProjectVersion` sidecar. This document defines the comparison model — what diffs mean, how they are computed, and how they are surfaced.

## Storage Model

Each version is stored as a separate file:

```
data/users/{user_id}/projects/{project_id}/versions/{version_id}.json
```

A version sidecar contains:
- `version_id` — `v-{uuid12}`
- `created_at` — UTC ISO timestamp
- `change_type` — one of `generate | regenerate | edit | option | restore`
- `summary` — human-readable description
- `snapshot` — full `ArchitectureProject` at that point

The active `project.json` is never modified retroactively. Restoring a version writes the snapshot as the new `project.json` AND appends a new `restore` sidecar — history is append-only.

## Diff Model

`GET /projects/{id}/versions/{a}/diff/{b}` returns a `VersionDiff`:

```json
{
  "version_a": "v-abc",
  "version_b": "v-def",
  "added_rooms": [{ "room_id": "...", "room_name": "...", "change": "added", "new_area": 120 }],
  "removed_rooms": [{ "room_id": "...", "room_name": "...", "change": "removed", "old_area": 90 }],
  "resized_rooms": [{ "room_id": "...", "room_name": "...", "change": "resized", "old_area": 90, "new_area": 120, "area_delta": 30 }],
  "total_area_delta": 30.0,
  "total_rooms_delta": 0
}
```

### What is compared

| Dimension | Detected | How |
|-----------|----------|-----|
| Room added | ✅ | `room_id` in B but not A |
| Room removed | ✅ | `room_id` in A but not B |
| Room resized | ✅ | Same `room_id`, `width` or `depth` changed > 0.05 ft |
| Room renamed | ❌ (not yet) | `room_id` stable, `name` differs — surfaced via summary text |
| Site dimensions | ❌ (not yet) | Planned for Phase 20 |
| Material changes | ❌ (not yet) | Planned for Phase 20 |
| Door / window changes | ❌ (not yet) | Planned for Phase 20 |

### Room identity

Rooms are matched by `room_id`. The generator assigns stable IDs per session but does not yet persist cross-session stable IDs. When a design is fully regenerated, all `room_id` values change — every room will appear as removed + added. This is correct behaviour; future work (Phase 20) could use semantic matching (room type + position proximity) to produce more useful diffs.

## UI Surface

### History panel (DataPanel › History)

- Reverse-chronological list of `ProjectVersionMeta` rows
- Each row: inline SVG thumbnail, change-type badge (colour-coded), summary, relative timestamp, room count, total area
- Restore button with two-step confirm (click once to arm, click again to execute)

### Restore flow

1. User clicks **Restore** on a version row → button enters armed state (3 s timeout)
2. User clicks **Confirm** → `POST /projects/{id}/versions/{vid}/restore`
3. Backend validates snapshot, writes it as active, appends `restore` version
4. Frontend receives `StoredProject`, updates canvas, increments `historyKey` to refresh the history list

### Diff endpoint usage (Phase 20 roadmap)

The `/diff` endpoint is ready to power a side-by-side comparison view. Planned surface:
- "Compare" button on each version row opens a modal
- Left / right columns show the two snapshots rendered as compact floor plans
- Diff overlay highlights added (green), removed (red), resized (amber) rooms
- Area delta shown per room in a summary table

## Change Types

| `change_type` | When created | UI colour |
|---------------|-------------|-----------|
| `generate` | First generation from prompt | Violet |
| `regenerate` | Parameter edit / room resize | Blue |
| `edit` | Direct PATCH with design change | Amber |
| `option` | Design option selected | Teal |
| `restore` | Version restore | Rose |

## Known Limitations (Phase 19)

1. **Room identity is session-scoped** — full regenerations show all rooms as add/remove in diffs.
2. **Thumbnail is recomputed** on every `list_versions` call (not cached in the sidecar). Acceptable for small project counts; cache in Phase 20 if list grows large.
3. **No pagination** on version list — suitable for ≤ 200 versions per project.
4. **Cloud backend stubs** — `append_version`, `list_versions`, `get_version` are `NotImplementedError` in `CloudProjectStore`. Implement with blob storage + metadata index in Phase 18 cloud work.
5. **No per-floor or per-material diff** — whole-project comparison only.
