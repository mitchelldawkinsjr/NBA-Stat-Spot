# Rookie merge data

## rookie_merge.json

Lists players who are on NBA/ESPN rosters but not yet in `nba_api` static data (e.g. new rookies). They are merged into the app’s player list so they appear in search, team rosters, and props.

**Format:** JSON array of objects:

- `full_name` – Display name (e.g. `"Kon Knueppel"`)
- `nba_id` – NBA person ID from [nba.com/player/ID/name](https://www.nba.com/player/1642851/kon-knueppel)
- `team_abbr` – Current team abbreviation: ATL, BOS, CHA, CHI, CLE, DAL, DEN, DET, GSW, HOU, IND, LAC, LAL, MEM, MIA, MIL, MIN, NOP, NYK, OKC, ORL, PHI, PHX, POR, SAC, SAS, TOR, UTA, WAS, BKN.

**Finding missing players:** Call `GET /api/v1/admin/players/missing-from-espn` to list names on ESPN rosters that aren’t in the app. Look up each player on NBA.com to get their `nba_id`, then add an entry here.
