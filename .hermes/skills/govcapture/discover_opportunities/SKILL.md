---
name: discover_opportunities
description: Capture Lead procedure for finding candidate federal opportunities. Parses goal into criteria, searches SAM.gov live, falls back to cached then seeded fixtures per PRD §5.4. Used exactly once per agent run.
version: 1.0.0
metadata:
  hermes:
    tags: [govcapture, discovery, sam, capture-lead]
    category: gov
    requires_toolsets: [gov_discovery]
---

# Discover Opportunities

Capture Lead procedure for finding and ranking candidate federal contracting opportunities.

## When to Use

- The Capture Lead has a parsed user profile and goal.
- You need to identify which opportunities exist that match the goal.
- Use **once per agent run.** Do not re-search.

## Procedure

1. **Parse the goal:**
   ```
   criteria = parse_goal(user_goal, profile)
   ```
   Returns structured criteria: `{keywords, naics_hints, set_aside_preference, deadline_window_days, place_of_performance_states, agency_filter, opportunity_size_hint}`.

2. **Try live SAM.gov search:**
   ```
   try:
     candidates = search_sam_opportunities(criteria)
   except RateLimited or ServerError:
     candidates = None
   ```

3. **If live failed OR `DEMO_USE_SEEDED_ONLY=true` is set in env, use seeded:**
   ```
   if candidates is None or env.DEMO_USE_SEEDED_ONLY:
     candidates = load_seeded_opportunities(criteria)
   ```

4. **Rank candidates deterministically:**
   ```
   ranked = rank_opportunities(candidates, criteria, profile)  # returns list with relevance_score
   top_n = ranked[:3]   # default N=3; reduce if budget tight
   ```

5. **Return top_n** to your delegate-fan-out step (see `analyze_opportunity_e2e` SKILL).

## Pitfalls

- **Re-searching wastes budget.** If you've already searched, use the result. Refine via filtering, not re-querying.
- **Live SAM is unreliable during demos.** Default to seeded path when `DEMO_USE_SEEDED_ONLY=true`. This is non-negotiable for stage runs.
- **Empty results from both paths.** If both live and seeded return zero, escalate to `request_human_review` with the criteria so the user can adjust the goal.
- **Fallback loop.** Never call `search_sam_opportunities` after a `load_seeded_opportunities` fallback succeeded — the planner may try; resist.

## Verification

- `criteria` has at least one of: keywords (≥1 string), naics_hints (≥1 NAICS), or set_aside_preference set.
- Result list has between 1 and 50 opportunities; if 0, you escalated to needs_human.
- After ranking, top-N opportunities each have `relevance_score` populated (0–100).
- The seeded fallback path emits `step_completed.status = degraded` (not failed) — degraded is expected behavior, not an error.
