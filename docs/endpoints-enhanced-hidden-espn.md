# 🏀 ESPN Hidden NBA API Endpoints (Unofficial)

These are community-discovered ESPN endpoints for NBA data. Use with caution — they are undocumented and may change.

| Purpose | Endpoint | Notes |
|----------|-----------|-------|
| **Scoreboard (all games)** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard` | Includes live and completed games; add `?dates=YYYYMMDD` for specific date |
| **Box Score / Summary (per game)** | `https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={GAME_ID}` | Replace `{GAME_ID}` with event id from scoreboard response |
| **Play-by-Play** | `https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/playbyplay?event={GAME_ID}` | Returns sequence of plays, scores, etc. |
| **Gamecast Data (advanced)** | `https://cdn.espn.com/core/nba/gamecast?gameId={GAME_ID}&xhr=1` | Used internally for Gamecast UI |
| **Teams List** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams` | Returns all NBA teams with metadata |
| **Team Info** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{TEAM_ID}` | Replace `{TEAM_ID}` with team slug (e.g., `lal`, `bos`) |
| **Team Roster** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{TEAM_ID}/roster` | Player info for each team |
| **Team Schedule** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{TEAM_ID}/schedule` | Upcoming and past games |
| **Player Info** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/players/{PLAYER_ID}` | Individual player profile |
| **Standings** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings` | League and conference standings |
| **News Feed** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/news` | General NBA news |
| **Injuries** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries` | Returns injury reports per team |
| **Transactions** | `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/transactions` | Recent trades and signings |

---

### ⚙️ Usage Notes
- Replace placeholders: `{GAME_ID}`, `{TEAM_ID}`, `{PLAYER_ID}`
- Add parameters like `?dates=YYYYMMDD` where applicable.
- Responses are JSON and can be parsed directly.
- Not officially supported by ESPN; subject to change or blocking.
