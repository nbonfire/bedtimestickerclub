# Bedtime Sticker Club feature sequence

This file records the user-approved requirements and keeps five staged pull
requests aligned. Each subsequent feature branch builds on its predecessor.

## Agreed behavior

- Parents signed in as Home Assistant administrators manage profiles, schedules,
  routines, and corrections. Every backend mutation checks the caller's role.
- A shared household tablet gives children access to any active child's
  checklist and avatar. Add, reorder, archive, and restore profiles without
  erasing their records.
- Shared task defaults support per-child copies. Changing a default only affects
  children still inheriting it; customized lists can be reset to defaults.
- Parents choose whether task-list changes take effect today or tomorrow,
  defaulting to tomorrow. Tomorrow means the next local 4 am routine day.
- Morning and bedtime both run every day and earn separate stickers. Morning
  begins with dressing, breakfast, brushing teeth, and packing the school bag.
  There is no deadline or school-day exclusion.
- Cards auto-select the routine before/after a parent-set switch time (noon by
  default), with a per-card manual override that resets on reopen or the next
  routine day. The established 4 am boundary and dinner/bedtime reminders remain.
- Child avatars support emoji and local image uploads. Cards have compact,
  standard, and large presets; standard is the default.
- Calendars show the routine month only. Lifetime totals remain. Child calendars
  expand in-card and collapse on dashboard reopen. A shared calendar can show
  multiple selected children, with separate morning and bedtime stickers.
- Portable child and shared-calendar cards have visual configuration editors
  and work without the bundled dashboard or an external card dependency.

## Stored data and compatibility

Keep the existing `kid_1` through `kid_3` IDs, bedtime sensor entity IDs,
bedtime totals, saved emojis, and YAML migration support. Use ordered,
versioned migrations and preserve data before any registry cleanup. Keep the
current Home Assistant local-time 4 am boundary, durable serialized writes,
stale-action rejection, and idempotent completion. Preserve daily snapshots
when task lists or profiles change; retain only current-month detail. Do not
invent historical task completion where legacy data has no task record.

Existing bedtime sensor attributes and actions remain compatible. A missing
routine argument on a legacy action means bedtime. Routine entities expose the
selected routine's dates, task completion, reward and lifetime total; the old
bedtime entity IDs still resolve to bedtime.

## Branch order

1. `feature/parent-controls` — schema migration, profile IDs, parent controls,
   history corrections and generated native family dashboard foundation.
2. `feature/morning-routines` — separate morning state, switch time, and
   per-card routine selection.
3. `feature/avatars-and-sizing` — shared emoji/image avatars and card presets.
4. `feature/calendars` — collapsible in-card calendars and the shared calendar.
5. `feature/lovelace-editors` — visual card editors and publication polish.

Each branch is a draft pull request based on the previous feature branch. Do not
merge the stack or publish a release while implementing it.
