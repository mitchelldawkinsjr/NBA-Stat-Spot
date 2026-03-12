"""
NBA Stat Spot — Centralized LLM Prompt Builder
===============================================
All prompts fed to the LLM are constructed here.
Goals:
  - Analyst persona locked in at the top of every prompt
  - Only data the model needs, structured as labeled key-value pairs
  - Explicit output contract: format, length, tone
  - No ambiguity that causes hallucination or fluff
  - Works for both chat (system + user) and single-prompt (Ollama/LlamaCpp)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# System prompts (used by chat-based models: OpenAI)
# ─────────────────────────────────────────────────────────────────────────────

PROP_SYSTEM_PROMPT = """You are a sharp NBA statistical analyst for a data-driven prop-betting platform.
Your job: produce concise, factual rationales backed by the numbers provided.
Rules:
- Use only the data given. Never invent statistics.
- 2 sentences maximum. No bullet points. No preamble (e.g. don't start with "Rationale:" or "Sure,").
- Sentence 1: the single strongest statistical reason supporting the pick.
- Sentence 2: the most important risk factor or confirming context signal.
- Write in present tense, analytical tone. No hype, no gambling encouragement."""

GAME_OUTLOOK_SYSTEM_PROMPT = """You are a senior NBA game analyst writing pre-game outlooks for a betting intelligence platform.
Rules:
- Use only the statistics and context provided. Never invent numbers.
- Write exactly 3 sentences. No bullet points. No preamble.
- Sentence 1: why the model's predicted winner is favored (cite specific metrics or matchup edges).
- Sentence 2: which player's form or matchup most influences the outcome.
- Sentence 3: the main risk factor or scenario where the underdog could win.
- Analytical tone. Real numbers. No hedging phrases."""

GAME_SUMMARY_SYSTEM_PROMPT = """You are an NBA analyst. Write exactly ONE concise sentence (under 20 words) explaining why the predicted winner is favored today. Output the sentence only — no prefix, no label."""

OVER_UNDER_SYSTEM_PROMPT = """You are an expert NBA live-betting analyst specializing in game totals.
Rules:
- Use only the data given. Never invent statistics.
- 2 sentences maximum. No bullet points. No preamble.
- Sentence 1: why the projection favors this recommendation (cite the numbers).
- Sentence 2: the single most important live factor driving this call.
- Precise, analytical tone. Output the rationale only."""

BEST_MATCH_SYSTEM_PROMPT = """You are an expert NBA betting analyst selecting the game of the day.
Respond in this exact format and nothing else:
MATCHUP: {AWAY} @ {HOME}
WHY: [exactly 2 sentences on why this game has the highest combined betting and entertainment value]
FACTORS: [3-5 comma-separated factors]"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _direction_vs_line_signal(avg: float, line: float, direction: str) -> str:
    """State clearly how the average compares to the line."""
    diff = avg - line
    if direction == "over":
        if diff >= 2:
            return f"season avg {avg:.1f} is {diff:+.1f} vs line {line} — positive edge"
        if diff >= 0:
            return f"season avg {avg:.1f} just above line {line}"
        return f"season avg {avg:.1f} is {diff:.1f} below line {line} — risk signal"
    else:
        if diff <= -2:
            return f"season avg {avg:.1f} is {abs(diff):.1f} below line {line} — positive under edge"
        if diff <= 0:
            return f"season avg {avg:.1f} just below line {line}"
        return f"season avg {avg:.1f} is {diff:+.1f} above line {line} — risk signal"


def _trend_label(trend: str, recent_avg: float, line: float, direction: str) -> str:
    """Human-readable trend + streak signal."""
    arrow = {"up": "↑ hot", "down": "↓ cooling", "flat": "→ steady"}.get(trend, trend)
    diff = recent_avg - line
    signal = f"last-N avg {recent_avg:.1f}"
    if direction == "over" and diff > 0:
        signal += f" ({diff:+.1f} vs line)"
    elif direction == "under" and diff < 0:
        signal += f" ({diff:+.1f} vs line)"
    return f"{arrow} | {signal}"


def _hit_rate_label(hr: float) -> str:
    if hr >= 0.72:
        return f"{hr:.0%} ✓ strong"
    if hr >= 0.55:
        return f"{hr:.0%} ✓ above average"
    if hr >= 0.45:
        return f"{hr:.0%} ≈ coin-flip"
    return f"{hr:.0%} ✗ weak"


def _context_lines(context: Optional[Dict[str, Any]], espn_context: Optional[Dict[str, Any]]) -> str:
    parts: List[str] = []
    if context:
        rest = context.get("rest_days")
        if rest is not None:
            if rest == 0:
                parts.append("• Back-to-back — fatigue risk")
            elif rest == 1:
                parts.append("• 1 rest day")
            elif rest >= 3:
                parts.append(f"• Well-rested ({rest} days off)")
            else:
                parts.append(f"• {rest} rest days")
        if context.get("is_home_game"):
            parts.append("• Home game")
        else:
            parts.append("• Road game")
        opp_rank = context.get("opponent_def_rank")
        if opp_rank:
            tier = "elite" if opp_rank <= 5 else ("tough" if opp_rank <= 12 else ("average" if opp_rank <= 20 else "weak"))
            parts.append(f"• Opponent def rank: #{opp_rank}/30 ({tier} defense)")
        h2h = context.get("h2h_avg")
        if h2h:
            parts.append(f"• H2H avg vs this opponent: {h2h:.1f}")
        pace = context.get("game_pace") or context.get("opponent_pace")
        if pace:
            tier = "fast" if pace > 102 else ("slow" if pace < 97 else "average")
            parts.append(f"• Game pace: {pace:.1f} possessions ({tier})")
    if espn_context:
        inj = espn_context.get("injury_status")
        if inj:
            flag = {"out": "⛔ OUT", "doubtful": "⚠️ DOUBTFUL", "questionable": "⚠️ QUESTIONABLE", "probable": "✓ PROBABLE"}.get(str(inj).lower(), str(inj).upper())
            parts.append(f"• Injury status: {flag}")
        cr = espn_context.get("conference_rank")
        if cr:
            tier = "playoff contender" if cr <= 6 else ("bubble" if cr <= 10 else "lottery")
            parts.append(f"• Conference rank: #{cr} ({tier})")
        sent = espn_context.get("news_sentiment")
        if sent is not None and abs(float(sent)) > 0.2:
            label = "positive" if float(sent) > 0 else "negative"
            parts.append(f"• Recent news sentiment: {label} ({float(sent):+.2f})")
    return "\n".join(parts) if parts else "  (no additional context)"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Prop Bet Rationale
# ─────────────────────────────────────────────────────────────────────────────

def build_prop_rationale_prompt(
    player_name: str,
    prop_type: str,
    line_value: float,
    direction: str,
    confidence: float,
    ml_confidence: Optional[float],
    stats: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    espn_context: Optional[Dict[str, Any]] = None,
    for_chat_api: bool = True,
) -> str:
    """
    Build the user-facing prompt for a single prop-bet rationale.
    `for_chat_api=True` → used as the `user` message (system prompt provided separately).
    `for_chat_api=False` → includes the analyst persona inline (Ollama/LlamaCpp).
    """
    hit_rate = float(stats.get("hit_rate") or 0)
    hit_rate_over = float(stats.get("hit_rate_over") or 0)
    recent = stats.get("recent") or {}
    trend = recent.get("trend") or "flat"
    recent_avg = float(recent.get("avg") or 0)
    season_avg = float(stats.get("season_avg") or recent_avg or 0)
    last_n_hits = stats.get("last_n_hits")
    last_n_total = stats.get("last_n_total")
    recent_games_stats = stats.get("recent_games") or []

    dir_upper = direction.upper()
    prop_display = f"{prop_type} {dir_upper} {line_value}"

    ml_str = f" | ML: {ml_confidence:.0f}%" if ml_confidence else ""
    conf_tier = "LOCK" if confidence >= 78 else ("STRONG" if confidence >= 62 else "LEAN")

    # Season avg vs line signal
    if season_avg:
        avg_signal = _direction_vs_line_signal(season_avg, line_value, direction)
    else:
        avg_signal = f"line: {line_value}"

    # Recent form
    trend_str = _trend_label(trend, recent_avg, line_value, direction)

    # Hit rates
    hit_str = _hit_rate_label(hit_rate)
    season_over_str = _hit_rate_label(hit_rate_over)

    # Last-N games hit streak
    streak_str = ""
    if last_n_hits is not None and last_n_total:
        streak_str = f"Hit {last_n_hits}/{last_n_total} of last {last_n_total} games {dir_upper} {line_value}"

    # Context block
    ctx_block = _context_lines(context, espn_context)

    # Injury — surface at the top if present
    inj_warning = ""
    if espn_context and espn_context.get("injury_status") in ("out", "doubtful"):
        flag = "⛔ PLAYER IS OUT" if espn_context["injury_status"] == "out" else "⚠️ PLAYER IS DOUBTFUL"
        inj_warning = f"\n{flag} — this strongly affects the recommendation.\n"

    # Recent game line (last 3 values) for local Ollama context
    recent_log_str = ""
    if recent_games_stats:
        vals = [str(g.get(prop_type.lower(), g.get("pts", "?"))) for g in recent_games_stats[:3]]
        recent_log_str = f"\n• Last 3 game values ({prop_type}): {', '.join(vals)}"

    body = f"""{inj_warning}
PROP: {player_name} — {prop_display}
CONFIDENCE: {confidence:.0f}% [{conf_tier}]{ml_str}

STATISTICAL EVIDENCE:
• Season hit rate ({dir_upper}): {hit_str}
• Season average vs line: {avg_signal}
• Recent form: {trend_str}{recent_log_str}
• Season hit rate (OVER): {season_over_str}
{f"• Streak: {streak_str}" if streak_str else ""}
GAME CONTEXT:
{ctx_block}"""

    if for_chat_api:
        # Clean prompt for chat API — instructions already in system prompt
        return body.strip()

    # Inline persona for single-prompt models (Ollama, LlamaCpp)
    return f"""You are a sharp NBA statistical analyst. Write exactly 2 analytical sentences explaining why this prop bet makes sense. Sentence 1: the strongest statistical reason. Sentence 2: key risk or confirming factor. No preamble. No bullet points.

{body.strip()}

Analysis:"""


# ─────────────────────────────────────────────────────────────────────────────
# 2. Over/Under (Live Game Totals)
# ─────────────────────────────────────────────────────────────────────────────

def build_over_under_prompt(
    home_team: str,
    away_team: str,
    current_total: int,
    projected_total: float,
    live_line: Optional[float],
    recommendation: str,
    confidence: str,
    key_factors: List[str],
    game_context: Optional[Dict[str, Any]] = None,
    for_chat_api: bool = True,
) -> str:
    """Build prompt for live over/under recommendation."""
    quarter = (game_context or {}).get("quarter") or "?"
    time_rem = (game_context or {}).get("time_remaining") or "?"
    home_score = (game_context or {}).get("home_score")
    away_score = (game_context or {}).get("away_score")

    score_str = ""
    if home_score is not None and away_score is not None:
        score_str = f"{away_team} {away_score} — {home_team} {home_score} | "

    edge_str = ""
    if live_line:
        diff = projected_total - live_line
        if abs(diff) >= 1:
            edge_str = f"\n• Model edge: {abs(diff):.1f} pts {'above' if diff > 0 else 'below'} live line → supports {recommendation}"

    factors_text = "\n".join(f"• {f}" for f in key_factors) if key_factors else "• (no specific factors identified)"

    body = f"""
GAME: {away_team} @ {home_team}
LIVE SCORE: {score_str}Q{quarter} — {time_rem} remaining | Combined: {current_total} pts
PROJECTED FINAL: {projected_total:.1f} pts{f" (live line: {live_line})" if live_line else ""}{edge_str}

RECOMMENDATION: {recommendation} ({confidence} confidence)

KEY DRIVERS:
{factors_text}"""

    if for_chat_api:
        return body.strip()

    return f"""You are an expert NBA live-betting analyst specializing in game totals. Write exactly 2 sentences: (1) why the projection supports {recommendation} using the numbers, (2) the single most important live factor driving this call. No preamble.

{body.strip()}

Analysis:"""


# ─────────────────────────────────────────────────────────────────────────────
# 3. Game Prediction Summary (short, for list view)
# ─────────────────────────────────────────────────────────────────────────────

def build_game_summary_prompt(
    home_abbr: str,
    away_abbr: str,
    winner_abbr: str,
    win_pct: int,
    key_advantage: str,
    home_ppg: float,
    away_ppg: float,
    home_pace: float,
    away_pace: float,
    for_chat_api: bool = True,
) -> str:
    """One-sentence game prediction summary for the games list view."""
    underdog = away_abbr if winner_abbr == home_abbr else home_abbr
    venue = "at home" if winner_abbr == home_abbr else "on the road"
    ppg_edge = home_ppg - away_ppg if winner_abbr == home_abbr else away_ppg - home_ppg
    ppg_signal = f"{abs(ppg_edge):.1f} PPG edge" if abs(ppg_edge) >= 1 else "similar scoring"

    body = f"""Game: {away_abbr} @ {home_abbr}
Predicted winner: {winner_abbr} {venue} — {win_pct}% probability
PPG: {home_abbr} {home_ppg:.1f} vs {away_abbr} {away_ppg:.1f} ({ppg_signal})
Pace: {home_abbr} {home_pace:.1f} / {away_abbr} {away_pace:.1f}
Model edge: {key_advantage}"""

    if for_chat_api:
        return body.strip()

    return f"""NBA analyst task: Write ONE sentence (under 20 words) explaining why {winner_abbr} is favored against {underdog} today. Use the numbers. Output the sentence only, no prefix.

{body.strip()}

One-sentence reason:"""


# ─────────────────────────────────────────────────────────────────────────────
# 4. Game Outlook (detail page — rich, 3-sentence paragraph)
# ─────────────────────────────────────────────────────────────────────────────

def build_game_outlook_prompt(
    home_abbr: str,
    away_abbr: str,
    winner_abbr: str,
    win_pct: float,
    key_advantage: str,
    home_ppg: Optional[float],
    away_ppg: Optional[float],
    home_pace: Optional[float],
    away_pace: Optional[float],
    home_off_pts: Optional[int],
    home_def_pts: Optional[int],
    away_off_pts: Optional[int],
    away_def_pts: Optional[int],
    key_players_text: Optional[str] = None,
    for_chat_api: bool = True,
) -> str:
    """Rich game outlook for the game detail page."""
    underdog = away_abbr if winner_abbr == home_abbr else home_abbr
    win_edge = "narrow" if abs(win_pct - 50) < 8 else ("moderate" if abs(win_pct - 50) < 18 else "clear")

    def _rank(v: Optional[int]) -> str:
        return f"#{v}" if v is not None else "N/A"

    team_table = (
        f"           {home_abbr:<8}  {away_abbr}\n"
        f"PPG:       {(f'{home_ppg:.1f}'):<8}  {(f'{away_ppg:.1f}') if away_ppg else 'N/A'}\n"
        f"Pace:      {(f'{home_pace:.1f}'):<8}  {(f'{away_pace:.1f}') if away_pace else 'N/A'}\n"
        f"Off rank:  {_rank(home_off_pts):<8}  {_rank(away_off_pts)}\n"
        f"Def rank:  {_rank(home_def_pts):<8}  {_rank(away_def_pts)}"
    )

    players_block = ""
    if key_players_text:
        players_block = f"\nSTANDOUT PLAYERS (season avg | last-5 trend):\n{key_players_text}"

    body = f"""GAME: {away_abbr} @ {home_abbr}
MODEL PREDICTION: {winner_abbr} wins — {win_pct:.0f}% probability ({win_edge} edge)
KEY EDGE: {key_advantage}

TEAM METRICS:
{team_table}{players_block}"""

    if for_chat_api:
        return body.strip()

    return f"""You are a senior NBA game analyst. Write exactly 3 sentences: (1) why {winner_abbr} is favored — cite specific metrics or matchup edges, (2) which player's form or matchup most influences the outcome, (3) the main risk or underdog scenario. Factual, analytical, no hedging. No bullet points.

{body.strip()}

Analysis:"""


# ─────────────────────────────────────────────────────────────────────────────
# 5. Best Match of the Day
# ─────────────────────────────────────────────────────────────────────────────

def build_best_match_prompt(
    predictions: List[Dict[str, Any]],
    for_chat_api: bool = True,
) -> str:
    """Build prompt to select the single best game of the day from today's slate."""
    game_lines: List[str] = []
    for i, p in enumerate(predictions, 1):
        home = p.get("home") or ""
        away = p.get("away") or ""
        winner = p.get("predicted_winner") or ""
        win_pct = p.get("win_probability_home") if winner == home else p.get("win_probability_away")
        win_pct = win_pct if win_pct is not None else 50.0
        spread_closeness = abs(float(win_pct) - 50)
        competitiveness = "⚡ tight" if spread_closeness < 6 else ("→ slight edge" if spread_closeness < 15 else "→ clear favorite")
        key_adv = p.get("key_advantage_summary") or "balanced matchup"
        home_ppg = p.get("home_ppg")
        away_ppg = p.get("away_ppg")
        home_pace = p.get("home_pace")
        away_pace = p.get("away_pace")
        combined_ppg = (home_ppg + away_ppg) if home_ppg and away_ppg else None
        avg_pace = ((home_pace + away_pace) / 2) if home_pace and away_pace else None
        stat_parts = []
        if combined_ppg:
            stat_parts.append(f"combined PPG {combined_ppg:.0f}")
        if avg_pace:
            stat_parts.append(f"avg pace {avg_pace:.0f}")
        stat_str = " | " + ", ".join(stat_parts) if stat_parts else ""
        game_lines.append(
            f"{i}. {away} @ {home}: {winner} {win_pct:.0f}% {competitiveness}{stat_str} | edge: {key_adv}"
        )

    games_block = "\n".join(game_lines)

    body = f"""SCORING CRITERIA (priority order):
1. Competitive balance — closest to 50/50 = most uncertain, highest betting value
2. Offensive firepower — high combined PPG = exciting, high-scoring
3. Statistical edge — clear matchup advantage creates a strong betting angle
4. Pace — high pace = more possessions = prop and total opportunity

TODAY'S GAMES:
{games_block}

Select the single BEST MATCH OF THE DAY. Be decisive. Use the criteria above."""

    if for_chat_api:
        return body.strip()

    return f"""You are an expert NBA betting analyst. Select the single BEST MATCH OF THE DAY from the games below and reply in this exact format:
MATCHUP: {{AWAY}} @ {{HOME}}
WHY: [2 sentences on why this game has the highest betting and entertainment value]
FACTORS: [3-5 comma-separated factors]

{body.strip()}

Response:"""
