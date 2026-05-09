# Standup Log

Append-only daily log. Both devs write entries. Async-friendly so this works across timezones/shifts.

**Format:** one section per dev per day. Don't edit prior entries.

**Template (copy-paste, fill in):**

```markdown
## YYYY-MM-DD — Dev N (Track A|B)

**Done since last entry:**
- [ ] task ID — one-line outcome
- [ ] task ID — one-line outcome

**Doing next:**
- task ID — what specifically

**Blocked on:**
- (nothing) OR (task ID, waiting for X from other track, ETA)

**Decisions / questions for the other dev:**
- (none) OR (specific question; tag the other dev's name)

**Notes for posterity:**
- (anything surprising; non-obvious; corrections to prior plans)
```

---

## Sync-checkpoint sign-offs

When a sync checkpoint completes (S1–S5 from `../INTERFERENCE_MAP.md §3`), both devs sign off here:

```markdown
### Sync S<n> — YYYY-MM-DD HH:MM
- ✅ Dev 1: <one-line confirm>
- ✅ Dev 2: <one-line confirm>
- Notes: <anything that surfaced; followup tasks>
```

---

## Entries

<!-- Append below this line. -->
