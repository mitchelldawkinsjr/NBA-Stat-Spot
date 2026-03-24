# Insight Generation Engine

This document describes the enhanced insight generation engine: turning raw stats into actionable matchup insights and player promotion opportunities. It extends the existing Top Picks / daily props pipeline without duplicating defensive or position-defense computation.

---

## 1. Goal

- Automatically detect **favorable matchups** using position-based defense, recent form, pace, and historical matchup.
- Generate **insight categories** (e.g. favorable scoring matchup, assist advantage, hot streak, pace-driven).
- Produce a **unified Matchup / Insight Strength Score** to rank and promote top insights.
- Surface **short narratives** and supporting metrics on the homepage and link to detailed matchup breakdowns.

---

## 2. Current State (Reuse)

- **Team defensive/offensive ranks:** `ContextCollector._calculate_defensive_ranks`, `_calculate_offensive_ranks` (cached 24h).
- **Position-based defensive ranks:** `ContextCollector._calculate_position_defensive_ranks` — PG/SG/SF/PF/C per stat (PTS, REB, AST, 3PM). Used on game prediction detail; **not yet** in Top Picks.
- **Pace ranks:** `ContextCollector._calculate_pace_ranks` (possessions per game, pace_rank). Used in game predictions; **not yet** in Top Picks.
- **Top Picks pipeline:** `BestPicksService.get_top_picks` uses **team-level** opponent def ranks only; `_scan_player` gets line + confidence via `PropBetEngine.multi_factor_confidence` (hit rate, consistency, trend, volume, home/away, opp_def_score). No position defense, no pace, no unified “matchup score.”
- **Player position:** On player objects from NBADataService; normalized to PG/SG/SF/PF/C in context_collector for position defense.
- **Frontend:** GoodBetsDashboard (Top Picks, AI Pick of the Day), PlayerProfile (opponent defense, matchup advantage), GamePredictionPage (defensive matchup insights).

---

## 3. Architecture (New Layer)

- **Position defense in best_picks:** Load position defense ranks once per run; resolve player position; for each player, opponent’s position-defense vs that position. Blend with team def rank in line/confidence.
- **Matchup / Insight Strength Score:** New module (e.g. `insight_scoring.py`) computes a 0–100 score per (player, stat, opponent) using:
  - Defense vs position (0.35)
  - Recent form (0.30)
  - Pace factor (0.15)
  - Usage (0.10) or reweight if unavailable
  - Historical matchup (0.10)
- **Insight categories and narrative:** Rule-based mapping to categories (favorable_scoring_matchup, assist_advantage, rebounding_advantage, defensive_weakness_exploit, hot_streak, pace_driven, historical_dominance, usage_spike). Template-based matchup explanation; optional LLM polish later.
- **API:** Extend top-picks (and pick-of-the-day) items with: `matchup_score`, `insight_type`, `matchup_explanation`, `opponent_abbr`, `opponent_def_rank_vs_position`, `supporting_metrics`. Backward compatible (missing = null).
- **Frontend:** Show matchup explanation and optional “Top Insights” strip by matchup_score; “View matchup” → player profile with opponent pre-filled. Optional: dedicated matchup breakdown page.

---

## 4. Frontend display (current)

The **Good Bets** dashboard shows:

- **Top Picks of the Day** – Horizontal scroll strip of best props (from `/api/v1/props/top-picks` or daily props), with tier badges (LOCK / STRONG / LEAN), direction, rationale, and “Add to tracker.”
- **Top Insights by matchup** – When any pick has `matchup_score` or `matchup_explanation`, the top 5 (by score) are shown in a separate horizontal strip above the main Top Picks. Cards show matchup explanation and “View matchup” link. The list supports both camelCase and snake_case API fields.

Layout: the Top Picks content area and the Top Insights block use `min-w-0` so horizontal scrolling works correctly in flex/grid. `SuggestionCards` in horizontal mode uses stable keys (`playerId-type-idx`) and `overflow-y-visible` so card content is not clipped.

---

## 5. Insight Strength Score Formula

```
Matchup Score =
  (Defense vs Position Rank score × 0.35) +
  (Player Recent Form score × 0.30) +
  (Pace Factor × 0.15) +
  (Usage Rate score × 0.10) +
  (Historical Matchup score × 0.10)
```

- **Defense vs position:** Opponent’s position-defense rank for that stat (1 = best D). Normalize to 0–1 so higher = easier matchup (e.g. rank 30 → 1).
- **Recent form:** Rolling avg vs season avg or existing trend score; normalize to 0–1.
- **Pace factor:** Opponent/game pace vs league avg; high pace → higher score, normalized 0–1.
- **Usage:** From game logs if available (FGA, FTA, TOV); else approximate from minutes or omit and reweight.
- **Historical matchup:** H2H avg for that stat vs this opponent vs player season avg; normalize 0–1.

Result: single **matchup_score** 0–100; rank insights across all games by this score.

---

## 6. Insight Categories

| Category | When to assign |
|----------|----------------|
| Favorable scoring matchup | Opponent allows high PTS to position; stat = PTS |
| Assist matchup advantage | Opponent allows high AST to position; stat = AST |
| Rebounding advantage | Opponent allows high REB to position; stat = REB |
| Defensive weakness exploit | Opponent position-def rank weak (e.g. ≥25) for that stat |
| Hot streak player | Recent form well above season avg |
| Pace driven opportunity | High pace; more possessions |
| Historical matchup dominance | H2H avg for stat above player’s season avg |
| Usage / minutes spike | Usage or minutes trending up (when available) |

---

## 7. Example Insight Output

**Input:** Trae Young (PG) vs Chicago Bulls.

- Chicago: Top 5 assists to PG, Top 10 points to PG (position defense).
- Trae Young: 28.4 PPG last 5, 9.8 APG last 5, high usage.

**Generated insight:**

- **insight_type:** `favorable_scoring_matchup` or `assist_advantage` (or both).
- **matchup_explanation:** “Elite matchup for Trae Young tonight. Chicago struggles defending point guards and allows high assist totals. Young is also on a strong scoring streak.”
- **supporting_metrics:** `{ recent_avg_5_pts: 28.4, recent_avg_5_ast: 9.8, opponent_def_rank_vs_position_pts: "#10", opponent_def_rank_vs_position_ast: "#5" }`.
- **matchup_score:** 0–100.

---

## 8. Implementation Order

1. **Position defense in best_picks** — Resolve player position; load pos_ranks; pass opponent position-def ranks into _scan_player; blend with team def rank in line/confidence.
2. **Matchup score + categories** — Add insight_scoring module; compute matchup_score and insight_type per pick; attach to top-picks items; add pace (and optional usage) to pipeline.
3. **Narrative** — Template-based matchup_explanation and supporting_metrics; extend API response.
4. **Frontend** — Show matchup_explanation and optional “Top Insights” by matchup_score; “View matchup” → player profile with opponent.
5. **Detail page** — Option A: extend player profile with position-defense in context. Option B: dedicated matchup page reusing player context, team-stats/ranks, position-defense/ranks, game logs.

---

## 9. Files to Touch

| Area | Files |
|------|--------|
| Position + score in pipeline | `backend/app/services/best_picks_service.py` |
| Matchup score + categories | New `backend/app/services/insight_scoring.py` (or same file) |
| Pace in pipeline | best_picks_service.py (context_collector already has pace_ranks) |
| Narrative | rationale_generator or new helper; best_picks response shape |
| API response | top-picks and pick-of-the-day (add fields) |
| Frontend cards | `frontend/src/components/SuggestionCards.tsx`, `frontend/src/components/GoodBetsDashboard.tsx` |
| Detail | `frontend/src/pages/PlayerProfile.tsx` or new matchup page |

---

## 10. Relation to Other Docs

- **Analytics engine design** ([analytics-engine-design.md](analytics-engine-design.md)): Defines raw stats, derived metrics (including Position Defense Rank, Opponent Weakness Score, Pace Impact Score), and matchup advantage formulas. This insight engine **implements** those concepts in the Top Picks pipeline and adds the unified matchup score and categories.
- **Rationale and LLM** ([rationale-and-llm.md](rationale-and-llm.md)): Optional LLM pass for polishing matchup narrative reuses the same rationale/LLM pattern as prop evaluation.
