# NBA Analytics Engine Design

A stat-driven NBA insights engine for player prop opportunities, team matchup advantages, defensive rankings, and pace-of-play indicators. This document defines raw stats, derived metrics, formulas, and visualization ideas.

---

## 1. Key Raw Stats Needed from NBA Data Feeds

| Category | Raw stat | Use |
|----------|----------|-----|
| **Scoring** | Points (PTS), FGA, FGM, 3PA, 3PM, FTA, FTM | Efficiency, volume, prop lines |
| **Rebounding** | REB, OREB, DREB | Rebounding advantage, second-chance |
| **Playmaking** | AST, turnovers (TOV) | Assist props, ball security |
| **Defense** | STL, BLK | Defensive pressure, steal/block props |
| **Team / Opponent** | Opponent PTS, Opponent FG%, Opponent 3P%, Opponent FGA | Defensive rating, matchup strength |
| **Pace & Possessions** | Team FGA, Team FTA, Team TOV, Team OREB | Possessions, pace, environment |
| **Rating-style** | Defensive Rating, Offensive Rating (or components) | High-level team strength |

**Minimum viable set for current app:**  
PTS, REB, AST, 3PM, STL, BLK, TOV, OREB, DREB, opponent points allowed, opponent FG%/3P%, game logs with matchup and opponent team.

---

## 2. Derived Analytics Metrics

| Metric | Formula / logic | Purpose |
|--------|------------------|---------|
| **Defensive Pressure Score** | Weighted: STL/g, BLK/g, opponent TOV%, opponent FG% allowed | How much a team disrupts offense |
| **Rebounding Advantage Index** | (OREB% − Opponent OREB%) or (REB allowed vs league avg) | Second-chance and board control |
| **Pace Impact Score** | (Team pace − League avg pace) / League std | Fast/slow environment for props |
| **Opponent Weakness Score** | Rank-based: how much opponent allows above league avg for a stat | "Soft" matchup for that stat |
| **Prop Opportunity Index** | Player avg vs opponent allowed for that stat, normalized | Single number: over/under opportunity |
| **Turnover Creation Rate** | Opponent TOV% when facing this team | Steal props, ball-handler pressure |
| **Position Defense Rank** | Rank teams by points/reb/ast allowed to PG/SG/SF/PF/C | Position-specific matchup |

---

## 3. Defensive Ranking Formulas

**Team Defensive Score (composite):**

```
Defensive Score = w1·(30 - rank_opp_pts)
                + w2·(30 - rank_opp_fg_pct)
                + w3·rank_steals_per_game
                + w4·rank_blocks_per_game
                + w5·(30 - rank_opp_3pt_pct)
                + w6·rank_turnovers_forced
                - w7·pace_factor   (optional: penalize fast pace that inflates counting stats)
```

**Per-stat defensive rank (current approach):**  
Rank 1 = team that allows the *fewest* of that stat (best defense).  
- Opponent PTS allowed → rank 1–30  
- Opponent REB/AST/3PM allowed → same.  
Sources: opponent game logs (what players scored vs this team) or box-score aggregates.

**Pace-adjusted defensive rating (advanced):**  
Defensive rating = (Opponent PTS / Possessions) × 100. Rank teams by this so pace doesn’t distort “good defense.”

---

## 4. Pace of Play Calculations

**Possessions (approximate):**

```
Possessions = FGA + 0.44·FTA + TOV − OREB
```

(Use team totals; 0.44 approximates FTA that end possession.)

**Pace:**

```
Pace = Possessions per 48 minutes (or per game length).
```

**Use in insights:**

- **Fast games:** Pace > league avg by ~2+ → more FGA, PTS, REB; favor over props in high-pace matchups.
- **Slow / defensive:** Low pace + low opponent PPG → tough scoring environment; be cautious on over PTS.
- **Inflated stat environment:** High pace + weak defense → “prop-friendly” opponent.

---

## 5. Matchup Insight Logic

**Examples the engine can derive:**

1. **“Opponent allows the 3rd most rebounds to centers”**  
   Position-level ranks: e.g. REB allowed to C only → rank 28/30 → center reb over is favorable.

2. **“Opponent allows high steal rates against guards”**  
   STL allowed to PG/SG vs league avg or rank → “high steal opportunity.”

3. **“Team plays top 5 fastest pace”**  
   Pace rank 1–5 → “boosts scoring props,” more possessions.

4. **“Elite at limiting points, weak vs 3PM”**  
   Def rank PTS top 5, def rank 3PM bottom 10 → “3PT over friendly, PTS under lean.”

5. **“Prop friendly opponent”**  
   Composite: allows above-avg PTS/REB/AST/3PM and/or high pace → badge for prop opportunity.

**Implementation:** Store per-team, per-stat (and optionally per-position) “allowed” averages; rank vs league; expose as short insight strings and numeric advantage scores.

---

## 6. Position-Based Defensive Rankings

Rank teams by what they *allow* to each position:

| Position | Stats to rank | Example output |
|----------|----------------|----------------|
| PG | PTS, AST, STL allowed | “#2 vs PG assists” |
| SG | PTS, 3PM allowed | “#28 vs SG 3PM” |
| SF | PTS, REB allowed | “#15 vs SF scoring” |
| PF | REB, PTS allowed | “#8 vs PF rebounds” |
| C | REB, BLK, PTS allowed | “#3 most REB to centers” |

**Data need:** Game logs with position (or primary position) and opponent team; aggregate by (opponent_team_id, position, stat).

---

## 7. Matchup Advantage Score

**Formula:**

```
Advantage(stat) = Player_avg(stat) − Opponent_allowed(stat)
```

Example: Player avg REB = 9.5, opponent allows to centers = 13.2 → **+3.7** (favorable rebounding matchup).

**Display:**

- **Positive:** Over opportunity (e.g. “+3.7 REB vs avg”).
- **Near zero:** Neutral.
- **Negative:** Under lean or tough matchup.

**Variants:**

- **Pace-adjusted:** Use per-possession rates then multiply by expected possessions.
- **vs position:** Opponent allowed to *centers* (or primary position) for REB, not just team avg.

---

## 8. Example Insight Outputs for the App

- “Elite rebound matchup” (advantage score > threshold, e.g. +2)
- “High steal opportunity” (opponent STL rank or rate vs guards)
- “Fast pace game environment” (pace rank top 5)
- “Strong defensive matchup” (opponent def rank PTS top 8)
- “Prop friendly opponent” (composite: high allowed + high pace)
- “Tough vs points, soft vs 3PM” (split defense insight)
- “#3 in limiting assists” (def rank AST)
- “Over-friendly for rebounds” (REB advantage score + pace)

---

## 9. Visualization Ideas

| Idea | Description |
|------|-------------|
| **Heat maps** | Team × stat (def rank or allowed avg); color = favorable/unfavorable. |
| **Matchup badges** | “Elite reb matchup,” “Fast pace,” “Tough D” on player/team cards. |
| **Defensive ranking tables** | Sortable table: team, def rank PTS/REB/AST/3PM, optional composite. |
| **Advantage bars** | Horizontal bar: player avg vs opponent allowed; green = over, red = under. |
| **Prop probability indicators** | Simple “over/under lean” or confidence from advantage + pace. |
| **Radar / bar charts** | Defense vs offense by stat (current); add “vs league avg” or “allowed” view. |
| **Rank distribution** | Where this team sits (e.g. “Top 5 defense”) with a small distribution curve. |

---

## 10. Advanced Analytics (Future)

- **Regression models for stat projections:** Use opponent def rank, pace, home/away, rest, position to predict PTS/REB/AST/3PM.
- **Matchup similarity clustering:** “This matchup is similar to games where player went over 70%.”
- **Pace-adjusted stat forecasting:** Project in per-possession terms then multiply by expected possessions.
- **Bayesian updates:** Prior (season avg) + likelihood (recent games, opponent) → posterior projection.
- **Injury/lineup adjustments:** Reduce opponent allowed stats when key defenders are out.

---

## 11. Insight Generation Engine (Planned)

The **Insight Generation Engine** extends the Top Picks pipeline to automatically surface high-value matchups and narrative insights. It reuses all existing data (team and position defensive ranks, pace, player context, game logs) and adds:

- **Position-based matchup scoring** — Use opponent's position-defense (e.g. "allows 3rd most PTS to PG") in addition to team-level def rank when generating lines and confidence.
- **Unified Matchup / Insight Strength Score** — Weighted combination: defense vs position (0.35), recent form (0.30), pace (0.15), usage (0.10), historical matchup (0.10). Rank insights by this score.
- **Insight categories** — Tag picks as e.g. favorable_scoring_matchup, assist_advantage, rebounding_advantage, defensive_weakness_exploit, hot_streak, pace_driven, historical_dominance.
- **Short narratives** — Template- or LLM-generated explanation (e.g. "Elite matchup for X. Opponent allows … X is averaging …").
- **Homepage promotion** — Show matchup explanation and optional "Top Insights" strip; "View matchup" links to player profile with opponent context.

Full design, formula, and implementation order: **[insight-generation-engine.md](insight-generation-engine.md)**.

---

## Implementation Notes (Current Codebase)

- **Defensive ranks:** `ContextCollector._calculate_defensive_ranks()` builds PTS/REB/AST/3PM ranks from opponent game logs; cached 24h. Refresh via Admin “Refresh defensive ranks.”
- **Team stats/ranks:** `GET /api/v1/teams/team-stats/ranks` returns def/off ranks plus pace (possessions per game, pace_rank) for all teams.
- **Pace:** `ContextCollector._calculate_pace_ranks()` computes possessions per game (FGA + 0.44·FTA + TOV − OREB from game logs); rank 1 = fastest. Cached 24h; refresh via Admin “Refresh pace ranks.”
- **Position defense:** `ContextCollector._calculate_position_defensive_ranks()` ranks teams by PTS/REB/AST/3PM allowed per position (PG/SG/SF/PF/C). Refresh via Admin “Refresh position defense ranks.”
- **Player context:** `GET /api/v1/players/{id}/context` includes `opponent_defense`, `matchup_advantage` (player avg − opponent allowed), rest, injury, H2H.
- **Matchup advantage:** Shown on player profile; formula: player season avg − opponent’s avg allowed per stat.
