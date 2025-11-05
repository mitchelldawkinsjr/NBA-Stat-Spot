# NBA Prop Bet Analyzer - Development Plan

**Project Name:** NBA Prop Bet Analyzer  
**Repository:** NBA-Stat-Spot (to be refactored)  
**Objective:** Transform existing NBA stats app into a simplified, Outlier.bet-style tool focused exclusively on NBA player prop bets with transparent statistical analysis

---

## PHASE 1: PROJECT ARCHITECTURE & SETUP

### 1.1 Project Scope Definition
**Goal:** Narrow focus to NBA player prop betting analysis only

**Requirements:**
- Remove all non-NBA related functionality
- Focus exclusively on player prop bets (points, rebounds, assists, steals, blocks, 3-pointers, etc.)
- Provide transparent rationale for each suggested prop bet
- Display historical performance trends
- Show odds comparison (if available from free sources)
- Clean, minimal UI focused on actionable insights

**Out of Scope:**
- Team betting (spreads, moneylines, totals)
- Other sports leagues
- Live betting features
- Advanced arbitrage/+EV calculations (Phase 1)
- Bet slip integration with sportsbooks

---

### 1.2 Technology Stack Review
**Current Stack:**
- Backend: FastAPI (Python)
- Frontend: React + Vite (TypeScript)
- Caching: In-memory

**Keep:** All core technologies are appropriate
**Add:**
- `nba_api` (Python library for NBA stats)
- PostgreSQL or SQLite for data persistence (replace in-memory caching)
- Celery + Redis for background job processing (optional for Phase 2)

---

### 1.3 Environment Configuration
**Tasks:**
1. Update `requirements.txt` with new dependencies:
   ```
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   nba_api>=1.2.1
   pydantic>=2.5.0
   python-dotenv>=1.0.0
   sqlalchemy>=2.0.23
   alembic>=1.13.0
   pandas>=2.1.3
   numpy>=1.26.2
   httpx>=0.25.2
   redis>=5.0.1
   celery>=5.3.4
   ```

2. Create `.env.example` file:
   ```
   DATABASE_URL=sqlite:///./nba_props.db
   CACHE_TTL=3600
   API_RATE_LIMIT=100
   REDIS_URL=redis://localhost:6379/0
   ```

3. Update `.gitignore` to include:
   ```
   .env
   *.db
   *.db-journal
   __pycache__/
   .venv/
   node_modules/
   .DS_Store
   celerybeat-schedule
   ```

---

## PHASE 2: DATABASE DESIGN & MODELS

### 2.1 Database Schema Design
**Tables Required:**

**1. `players`**
- `id` (PK, Integer, from NBA API)
- `full_name` (String)
- `first_name` (String)
- `last_name` (String)
- `position` (String)
- `team_id` (Integer, FK)
- `jersey_number` (String)
- `is_active` (Boolean)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**2. `teams`**
- `id` (PK, Integer, from NBA API)
- `full_name` (String)
- `abbreviation` (String)
- `city` (String)
- `nickname` (String)
- `conference` (String)
- `division` (String)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**3. `player_game_stats`**
- `id` (PK, UUID)
- `player_id` (FK, Integer)
- `game_id` (String, from NBA API)
- `game_date` (Date)
- `opponent_team_id` (FK, Integer)
- `is_home` (Boolean)
- `minutes_played` (Float)
- `points` (Integer)
- `rebounds` (Integer)
- `assists` (Integer)
- `steals` (Integer)
- `blocks` (Integer)
- `three_pointers_made` (Integer)
- `field_goals_made` (Integer)
- `field_goals_attempted` (Integer)
- `free_throws_made` (Integer)
- `turnovers` (Integer)
- `created_at` (DateTime)

**4. `prop_suggestions`**
- `id` (PK, UUID)
- `player_id` (FK, Integer)
- `game_date` (Date)
- `prop_type` (String: 'points', 'rebounds', 'assists', etc.)
- `line_value` (Float)
- `suggestion` (String: 'over', 'under')
- `confidence_score` (Float, 0-100)
- `rationale` (JSON with supporting stats)
- `historical_hit_rate` (Float)
- `recent_form` (JSON)
- `matchup_advantage` (JSON)
- `created_at` (DateTime)

**5. `prop_bet_lines`** (for tracking odds if available)
- `id` (PK, UUID)
- `player_id` (FK, Integer)
- `game_date` (Date)
- `prop_type` (String)
- `line_value` (Float)
- `over_odds` (Float, nullable)
- `under_odds` (Float, nullable)
- `source` (String, e.g., 'manual_entry', 'oddsapi')
- `created_at` (DateTime)
- `updated_at` (DateTime)

---

### 2.2 SQLAlchemy Models Creation
**File:** `backend/app/models/__init__.py`

**Tasks:**
1. Create SQLAlchemy models for each table
2. Implement relationships:
   - Player → Team (Many-to-One)
   - Player → PlayerGameStats (One-to-Many)
   - Player → PropSuggestions (One-to-Many)
3. Add indexed fields for query optimization:
   - `player_id` in all related tables
   - `game_date` in stats and suggestions
   - `prop_type` in suggestions
4. Implement JSON fields using SQLAlchemy's JSON type for `rationale`, `recent_form`, `matchup_advantage`

---

### 2.3 Database Initialization
**File:** `backend/app/database.py`

**Tasks:**
1. Create database connection manager
2. Implement session factory
3. Create Alembic migration setup
4. Write initial migration for all tables
5. Create seed script for loading initial teams data from NBA API

**Migration Command:**
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

---

## PHASE 3: DATA INGESTION & NBA API INTEGRATION

### 3.1 NBA API Service Layer
**File:** `backend/app/services/nba_api_service.py`

**Class: `NBADataService`**

**Methods to Implement:**

1. **`fetch_all_teams()`**
   - Fetch all NBA teams
   - Update teams table
   - Return team data

2. **`fetch_active_players()`**
   - Fetch all active players
   - Update players table with team associations
   - Return player data

3. **`fetch_player_game_log(player_id: int, season: str)`**
   - Fetch game-by-game stats for a player
   - Parameters: player_id, season (e.g., '2024-25')
   - Return list of game stats

4. **`fetch_todays_games()`**
   - Get schedule for today
   - Return list of games with participating teams/players

5. **`fetch_upcoming_games(days_ahead: int = 7)`**
   - Get schedule for next N days
   - Return games by date

6. **`fetch_player_career_stats(player_id: int)`**
   - Get career averages
   - Return career statistics summary

**Error Handling:**
- Implement retry logic with exponential backoff
- Rate limiting awareness (NBA API limits)
- Cache responses for 1 hour to minimize API calls
- Graceful degradation if API is unavailable

---

### 3.2 Data Sync Service
**File:** `backend/app/services/data_sync_service.py`

**Class: `DataSyncService`**

**Methods to Implement:**

1. **`sync_teams()`**
   - Fetch and update all teams
   - Run once per week

2. **`sync_players()`**
   - Fetch and update all active players
   - Run once per day

3. **`sync_player_stats(player_id: int, lookback_days: int = 30)`**
   - Fetch recent game stats for player
   - Store in player_game_stats table
   - Avoid duplicate entries

4. **`sync_featured_players()`**
   - Sync stats for top 100-150 most popular players
   - Run daily at 6 AM EST

5. **`sync_todays_lineups()`**
   - Fetch today's games
   - Sync stats for all probable players
   - Run at 9 AM EST on game days

**Scheduling:**
- Create background tasks using Celery (or simple cron jobs initially)
- Schedule sync jobs appropriately
- Log all sync operations

---

### 3.3 Statistical Calculation Service
**File:** `backend/app/services/stats_calculator.py`

**Class: `StatsCalculator`**

**Methods to Implement:**

1. **`calculate_rolling_average(player_stats: List, stat_type: str, n_games: int = 10)`**
   - Calculate rolling average for any stat
   - Return average value

2. **`calculate_hit_rate(player_stats: List, line_value: float, stat_type: str)`**
   - Calculate historical % of games over/under line
   - Return percentage

3. **`calculate_recent_form(player_stats: List, stat_type: str, n_games: int = 5)`**
   - Last 5 games performance
   - Trending up/down indicator
   - Return form analysis

4. **`calculate_home_away_split(player_stats: List, stat_type: str)`**
   - Compare home vs away performance
   - Return differential

5. **`calculate_matchup_performance(player_stats: List, opponent_team_id: int, stat_type: str)`**
   - Historical performance against specific team
   - Return matchup stats

6. **`calculate_confidence_score(hit_rate: float, recent_form: dict, matchup_data: dict)`**
   - Proprietary scoring algorithm
   - Weight factors:
     - Historical hit rate (40%)
     - Recent form trend (30%)
     - Matchup advantage (20%)
     - Minutes consistency (10%)
   - Return 0-100 score

---

## PHASE 4: PROP SUGGESTION ENGINE

### 4.1 Prop Generation Service
**File:** `backend/app/services/prop_engine.py`

**Class: `PropBetEngine`**

**Methods to Implement:**

1. **`generate_daily_props(game_date: date = today)`**
   - For each game today
   - For each player likely to play
   - Generate prop suggestions for multiple stat types
   - Return list of PropSuggestion objects

2. **`generate_player_props(player_id: int, game_date: date, opponent_team_id: int)`**
   - Generate props for specific player
   - Calculate for: points, rebounds, assists, 3PM, steals, blocks
   - Return suggestions with confidence scores

3. **`determine_line_value(player_id: int, stat_type: str)`**
   - Use rolling 10-game average as baseline
   - Adjust based on matchup
   - Round to standard betting lines (.5 increments)
   - Return suggested line

4. **`evaluate_prop(player_id: int, stat_type: str, line_value: float, game_date: date, opponent_team_id: int)`**
   - Calculate all relevant statistics
   - Determine over/under recommendation
   - Generate confidence score
   - Compile rationale
   - Return PropSuggestion object

5. **`build_rationale(player_stats: List, calculation_results: dict)`**
   - Create human-readable explanation
   - Include key stats supporting the suggestion
   - Format as structured JSON
   - Return rationale object

**Rationale JSON Structure:**
```json
{
  "summary": "LeBron James has gone OVER 25.5 points in 8 of his last 10 games (80%)",
  "supporting_facts": [
    "Averaging 28.3 PPG in last 10 games",
    "Scored 30+ in 3 of last 5 games",
    "Averages 31.2 PPG vs. this opponent (last 3 matchups)",
    "Playing at home (26.8 PPG home avg)"
  ],
  "caution_notes": [
    "Minutes slightly down in recent games (34.2 → 32.1)"
  ]
}
```

---

### 4.2 Prop Filtering & Ranking
**File:** `backend/app/services/prop_filter.py`

**Class: `PropFilter`**

**Methods to Implement:**

1. **`filter_by_confidence(suggestions: List[PropSuggestion], min_confidence: float = 65.0)`**
   - Filter props below confidence threshold
   - Return filtered list

2. **`filter_by_prop_type(suggestions: List, prop_types: List[str])`**
   - Filter to specific stat types
   - Return filtered list

3. **`filter_by_player(suggestions: List, player_ids: List[int])`**
   - Filter to specific players
   - Return filtered list

4. **`rank_suggestions(suggestions: List, sort_by: str = 'confidence')`**
   - Sort by confidence, hit_rate, or game_time
   - Return sorted list

5. **`get_top_suggestions(suggestions: List, limit: int = 20)`**
   - Get top N suggestions by confidence
   - Return limited list

---

## PHASE 5: BACKEND API ENDPOINTS

### 5.1 Core Endpoints
**File:** `backend/app/routers/props.py`

**Endpoints to Create:**

1. **`GET /api/v1/props/daily`**
   - Query params: `date` (optional, defaults to today), `min_confidence` (optional)
   - Returns: List of top prop suggestions for the day
   - Response includes player info, prop details, confidence, rationale

2. **`GET /api/v1/props/player/{player_id}`**
   - Path param: `player_id`
   - Query params: `date` (optional), `game_id` (optional)
   - Returns: All prop suggestions for specific player

3. **`GET /api/v1/props/game/{game_id}`**
   - Path param: `game_id`
   - Returns: All props for players in specific game

4. **`GET /api/v1/props/trending`**
   - Returns: Highest confidence props from today's games
   - Limit to top 10

5. **`GET /api/v1/props/types`**
   - Returns: Available prop types (points, rebounds, assists, etc.)

---

### 5.2 Player Endpoints
**File:** `backend/app/routers/players.py`

**Endpoints to Create:**

1. **`GET /api/v1/players/search`**
   - Query param: `q` (search term)
   - Returns: List of players matching search
   - Include basic info and current team

2. **`GET /api/v1/players/{player_id}`**
   - Path param: `player_id`
   - Returns: Detailed player information
   - Include season averages

3. **`GET /api/v1/players/{player_id}/stats`**
   - Path param: `player_id`
   - Query params: `games` (last N games, default 10)
   - Returns: Recent game-by-game stats

4. **`GET /api/v1/players/{player_id}/trends`**
   - Path param: `player_id`
   - Query params: `stat_type` (points, rebounds, etc.)
   - Returns: Trend data for charting (last 20 games)

5. **`GET /api/v1/players/featured`**
   - Returns: List of featured/popular players (top 50)
   - For homepage display

---

### 5.3 Games & Schedule Endpoints
**File:** `backend/app/routers/games.py`

**Endpoints to Create:**

1. **`GET /api/v1/games/today`**
   - Returns: All NBA games scheduled for today
   - Include team info, game time

2. **`GET /api/v1/games/upcoming`**
   - Query param: `days` (default 7)
   - Returns: Games in next N days

3. **`GET /api/v1/games/{game_id}`**
   - Path param: `game_id`
   - Returns: Detailed game info
   - Include probable lineups if available

---

### 5.4 Admin/Utility Endpoints
**File:** `backend/app/routers/admin.py`

**Endpoints to Create (Protected):**

1. **`POST /api/v1/admin/sync/players`**
   - Trigger player data sync
   - Returns: Sync job status

2. **`POST /api/v1/admin/sync/stats`**
   - Trigger stats sync for featured players
   - Returns: Sync job status

3. **`POST /api/v1/admin/generate-props`**
   - Query param: `date` (optional)
   - Trigger prop generation for date
   - Returns: Number of props generated

4. **`GET /api/v1/admin/health`**
   - Health check endpoint
   - Returns: System status, database status, last sync times

---

### 5.5 Response Schemas
**File:** `backend/app/schemas/props.py`

**Pydantic Models to Create:**

1. **`PropSuggestionResponse`**
   ```python
   {
     "id": "uuid",
     "player": {
       "id": 123,
       "name": "LeBron James",
       "team": "LAL",
       "position": "F"
     },
     "game": {
       "game_id": "0022400123",
       "date": "2025-01-15",
       "opponent": "GSW",
       "is_home": true,
       "game_time": "19:30"
     },
     "prop": {
       "type": "points",
       "line": 25.5,
       "suggestion": "over",
       "confidence": 78.5
     },
     "rationale": {
       "summary": "...",
       "supporting_facts": [...],
       "caution_notes": [...]
     },
     "stats": {
       "historical_hit_rate": 0.80,
       "rolling_average": 28.3,
       "recent_form": "trending_up",
       "matchup_average": 31.2
     }
   }
   ```

2. **`PlayerResponse`**
3. **`GameResponse`**
4. **`PlayerStatsResponse`**

---

## PHASE 6: FRONTEND DEVELOPMENT

### 6.1 UI/UX Design Principles
**Design Goals:**
- Clean, minimal interface
- Mobile-responsive
- Fast loading times
- Easy navigation
- Clear data visualization

**Color Scheme:**
- Primary: NBA blue (#17408B)
- Secondary: White/light gray
- Accent: Green (for "over"), Red (for "under")
- Confidence indicator: Color gradient (red → yellow → green)

---

### 6.2 Component Architecture
**Framework:** React + TypeScript + Vite

**Component Structure:**
```
src/
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Navigation.tsx
│   ├── props/
│   │   ├── PropCard.tsx
│   │   ├── PropsList.tsx
│   │   ├── PropDetails.tsx
│   │   ├── ConfidenceMeter.tsx
│   │   └── RationaleDisplay.tsx
│   ├── players/
│   │   ├── PlayerSearch.tsx
│   │   ├── PlayerCard.tsx
│   │   ├── PlayerStatsChart.tsx
│   │   └── PlayerTrends.tsx
│   ├── games/
│   │   ├── GameCard.tsx
│   │   ├── GamesList.tsx
│   │   └── Schedule.tsx
│   └── common/
│       ├── Loading.tsx
│       ├── ErrorBoundary.tsx
│       ├── FilterBar.tsx
│       └── StatBadge.tsx
├── pages/
│   ├── HomePage.tsx
│   ├── DailyPropsPage.tsx
│   ├── PlayerDetailPage.tsx
│   ├── GameDetailPage.tsx
│   └── NotFoundPage.tsx
├── hooks/
│   ├── useProps.ts
│   ├── usePlayers.ts
│   ├── useGames.ts
│   └── useApi.ts
├── services/
│   └── api.ts
├── types/
│   └── index.ts
└── utils/
    ├── formatting.ts
    └── calculations.ts
```

---

### 6.3 Key Pages & Features

**6.3.1 Home Page**
**File:** `src/pages/HomePage.tsx`

**Features:**
- Hero section with app description
- "Today's Top Props" section (top 5-10)
- Quick player search bar
- Today's NBA games overview
- Navigation to daily props page

**Components:**
- Featured props carousel
- Quick search input
- Games schedule widget

---

**6.3.2 Daily Props Page**
**File:** `src/pages/DailyPropsPage.tsx`

**Features:**
- Full list of today's prop suggestions
- Filterable by:
  - Prop type (points, rebounds, assists, etc.)
  - Confidence level (65+, 70+, 75+, 80+)
  - Player
  - Game
- Sortable by:
  - Confidence (default)
  - Hit rate
  - Game time
- Each prop displayed as card with key info

**PropCard Component Design:**
```
┌─────────────────────────────────────────┐
│ LeBron James (LAL) vs GSW               │
│ 7:30 PM ET                              │
│                                         │
│ POINTS OVER 25.5                        │
│ Confidence: ███████░░░ 78%             │
│                                         │
│ Key Stats:                              │
│ • 8/10 games over in L10                │
│ • 28.3 PPG rolling average              │
│ • 31.2 PPG vs GSW (L3)                 │
│                                         │
│ [View Full Analysis →]                  │
└─────────────────────────────────────────┘
```

---

**6.3.3 Prop Details Modal/Page**
**File:** `src/components/props/PropDetails.tsx`

**Features:**
- Full rationale display
- Historical game log (last 10-20 games)
- Line chart showing stat trend
- Home/away splits
- Matchup history
- Injury status disclaimer

---

**6.3.4 Player Detail Page**
**File:** `src/pages/PlayerDetailPage.tsx`

**Features:**
- Player profile header (photo, team, position)
- Season statistics overview
- Current props for this player
- Recent game log (table format)
- Stat trends (interactive charts)
- Upcoming games

**Charts to Include:**
- Points trend (last 20 games)
- Rebounds trend
- Assists trend
- Selected stat type interactive chart

---

**6.3.5 Player Search**
**File:** `src/components/players/PlayerSearch.tsx`

**Features:**
- Real-time search as user types
- Dropdown with player suggestions
- Shows player name, team, position
- Navigates to player detail page on selection

---

### 6.4 State Management
**Approach:** React Context + Hooks (no Redux needed for MVP)

**Contexts to Create:**
1. **`PropsContext`** - Manage daily props state
2. **`PlayersContext`** - Manage player search state
3. **`GamesContext`** - Manage schedule state
4. **`FiltersContext`** - Manage filter selections

---

### 6.5 API Integration
**File:** `src/services/api.ts`

**API Client Setup:**
- Use Axios or Fetch
- Base URL configuration
- Error handling
- Request/response interceptors
- Type-safe API calls

**Methods:**
- `fetchDailyProps(date?, minConfidence?)`
- `fetchPlayerProps(playerId, date?)`
- `searchPlayers(query)`
- `fetchPlayerDetails(playerId)`
- `fetchPlayerStats(playerId, games?)`
- `fetchTodaysGames()`
- `fetchUpcomingGames(days?)`

---

### 6.6 Styling & UI Framework
**Approach:** Tailwind CSS (recommended) or Material-UI

**If using Tailwind:**
1. Install Tailwind: `npm install -D tailwindcss postcss autoprefixer`
2. Initialize: `npx tailwindcss init -p`
3. Configure in `tailwind.config.js`
4. Import in `src/index.css`

**Custom Theme:**
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'nba-blue': '#17408B',
        'over-green': '#10B981',
        'under-red': '#EF4444',
      }
    }
  }
}
```

---

## PHASE 7: DATA VISUALIZATION

### 7.1 Charting Library
**Recommended:** Recharts (React-native charts)

**Installation:**
```bash
npm install recharts
```

---

### 7.2 Charts to Implement

**1. Stat Trend Line Chart**
**File:** `src/components/players/PlayerStatsChart.tsx`

**Features:**
- X-axis: Last 20 games (dates)
- Y-axis: Stat value (points, rebounds, etc.)
- Line showing actual performance
- Horizontal line showing prop line value
- Shaded areas for over/under
- Hover tooltips with game details

---

**2. Confidence Meter**
**File:** `src/components/props/ConfidenceMeter.tsx`

**Features:**
- Visual bar or radial gauge
- Color-coded by confidence level:
  - 0-59%: Red (skip)
  - 60-69%: Orange (low confidence)
  - 70-79%: Yellow (medium)
  - 80-89%: Light green (good)
  - 90-100%: Dark green (strong)

---

**3. Hit Rate Indicator**
**Features:**
- Simple percentage display
- "8/10 games" format
- Visual representation (dots or bars)

---

## PHASE 8: TESTING & QUALITY ASSURANCE

### 8.1 Backend Testing
**Framework:** pytest

**Tests to Write:**

1. **Unit Tests:**
   - Test stats calculation functions
   - Test prop generation logic
   - Test confidence scoring algorithm
   - Test API service methods

2. **Integration Tests:**
   - Test database operations
   - Test API endpoints
   - Test data sync processes

3. **Test Files Structure:**
```
backend/tests/
├── test_stats_calculator.py
├── test_prop_engine.py
├── test_api_endpoints.py
└── test_nba_api_service.py
```

**Run Tests:**
```bash
pytest backend/tests/ -v
```

---

### 8.2 Frontend Testing
**Framework:** Vitest + React Testing Library

**Tests to Write:**

1. **Component Tests:**
   - PropCard rendering
   - PlayerSearch functionality
   - FilterBar interactions
   - Chart rendering

2. **Integration Tests:**
   - API calls and data flow
   - Navigation between pages
   - Filter and sort functionality

**Run Tests:**
```bash
npm run test
```

---

### 8.3 Manual Testing Checklist

**User Flows to Test:**
- [ ] Load homepage - see top props
- [ ] Navigate to daily props page
- [ ] Filter props by type
- [ ] Filter props by confidence
- [ ] Sort props by different criteria
- [ ] Click prop card to view details
- [ ] Search for player
- [ ] View player detail page
- [ ] View player stats chart
- [ ] Check mobile responsiveness
- [ ] Test error states (API down, no data)
- [ ] Test loading states

---

## PHASE 9: DEPLOYMENT

### 9.1 Deployment Architecture

**Option A: Separate Frontend/Backend Hosting**
- Frontend: Vercel, Netlify, or GitHub Pages
- Backend: Heroku, Railway, or Render
- Database: Heroku Postgres or Railway Postgres

**Option B: Single Platform Deployment**
- Platform: Render (recommended)
- Deploy both frontend and backend together
- Use Render's PostgreSQL

---

### 9.2 Backend Deployment
**Platform:** Render (example)

**Steps:**
1. Create `render.yaml` in repository root:
```yaml
services:
  - type: web
    name: nba-prop-analyzer-api
    env: python
    buildCommand: "pip install -r backend/requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: nba-props-db
          property: connectionString
      - key: PYTHON_VERSION
        value: 3.11.0

databases:
  - name: nba-props-db
    databaseName: nba_props
    user: nba_props_user
```

2. Push to GitHub
3. Connect repository to Render
4. Deploy

---

### 9.3 Frontend Deployment
**Platform:** Vercel (example)

**Steps:**
1. Create `vercel.json` in `frontend/`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "env": {
    "VITE_API_BASE_URL": "https://your-backend-url.com"
  }
}
```

2. Connect GitHub repository to Vercel
3. Configure environment variables
4. Deploy

---

### 9.4 Environment Variables

**Backend Production:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection (if using Celery)
- `ENVIRONMENT` - "production"
- `API_RATE_LIMIT` - Request rate limit

**Frontend Production:**
- `VITE_API_BASE_URL` - Backend API URL
- `VITE_ENVIRONMENT` - "production"

---

### 9.5 Database Migration for Production

**Steps:**
1. SSH into production server or use Render shell
2. Run migrations:
```bash
alembic upgrade head
```
3. Run seed scripts:
```bash
python backend/scripts/seed_teams.py
python backend/scripts/seed_featured_players.py
```

---

### 9.6 Post-Deployment Tasks

**Tasks:**
1. Test all API endpoints in production
2. Verify database connections
3. Test frontend pages
4. Run initial data sync:
   - Sync teams
   - Sync featured players
   - Sync recent stats
   - Generate today's props
5. Set up monitoring (optional: Sentry for error tracking)
6. Set up cron jobs or scheduled tasks for daily syncs

---

## PHASE 10: OPTIMIZATION & ENHANCEMENTS

### 10.1 Performance Optimization

**Backend:**
- [ ] Implement Redis caching for expensive queries
- [ ] Add database indexes on frequently queried fields
- [ ] Optimize prop generation algorithm
- [ ] Implement pagination for large result sets
- [ ] Add response compression (gzip)

**Frontend:**
- [ ] Implement lazy loading for images
- [ ] Code splitting for routes
- [ ] Memoize expensive calculations
- [ ] Virtual scrolling for long lists
- [ ] Image optimization (WebP format)

---

### 10.2 Feature Enhancements (Post-MVP)

**Phase 2 Features:**
1. **User Accounts & Tracking**
   - User registration/login
   - Track bet history
   - ROI tracking
   - Favorite players

2. **Advanced Analytics**
   - Lineup analysis (starting vs bench)
   - Rest days impact
   - Back-to-back games analysis
   - Travel schedule impact

3. **Odds Integration**
   - Integrate with Odds API (if budget allows)
   - Show live odds from sportsbooks
   - EV+ calculations
   - Odds comparison

4. **Notifications**
   - Email alerts for high-confidence props
   - Push notifications (mobile app)
   - Discord/Slack integration

5. **Social Features**
   - Share props with friends
   - Community leaderboards
   - Bet slip sharing

6. **Mobile App**
   - React Native mobile app
   - Push notifications
   - Native performance

---

### 10.3 SEO & Marketing

**SEO Tasks:**
- [ ] Add meta tags to all pages
- [ ] Create sitemap.xml
- [ ] Add structured data (JSON-LD)
- [ ] Optimize page load speed
- [ ] Create content pages (how-to guides, betting strategies)

**Marketing:**
- [ ] Create Twitter/X account for prop alerts
- [ ] Reddit posts in sports betting communities
- [ ] Write blog posts about props betting
- [ ] YouTube videos explaining the tool

---

## PHASE 11: MAINTENANCE & MONITORING

### 11.1 Monitoring Setup

**Tools to Use:**
- **Error Tracking:** Sentry
- **Uptime Monitoring:** UptimeRobot or Pingdom
- **Analytics:** Google Analytics or Plausible

**Metrics to Track:**
- API response times
- Error rates
- Daily active users
- Most viewed props
- Most searched players
- Prop suggestion accuracy (manual tracking)

---

### 11.2 Regular Maintenance Tasks

**Daily:**
- [ ] Verify data sync ran successfully
- [ ] Check for API errors
- [ ] Review generated props for quality

**Weekly:**
- [ ] Review user feedback
- [ ] Check database size and optimize if needed
- [ ] Update featured players list

**Monthly:**
- [ ] Review prop accuracy/performance
- [ ] Update algorithm if needed
- [ ] Clean up old data (archive stats older than 2 seasons)

---

### 11.3 Backup Strategy

**Database Backups:**
- Daily automated backups (most hosting platforms provide this)
- Keep last 30 days of backups
- Test restore process quarterly

---

## PHASE 12: DOCUMENTATION

### 12.1 Technical Documentation

**README.md Update:**
```markdown
# NBA Prop Bet Analyzer

A data-driven tool for analyzing NBA player prop bets with transparent statistical insights.

## Features
- Daily prop bet suggestions
- Player statistical analysis
- Historical performance tracking
- Confidence scoring
- Matchup analysis

## Tech Stack
- Backend: FastAPI + Python
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL
- Data Source: NBA Stats API

## Setup Instructions
[Detailed setup steps]

## API Documentation
[Link to API docs]

## Contributing
[Contribution guidelines]
```

---

### 12.2 API Documentation

**Tool:** FastAPI's built-in Swagger UI (available at `/docs`)

**Tasks:**
- [ ] Add detailed docstrings to all endpoints
- [ ] Include request/response examples
- [ ] Document all query parameters
- [ ] Document error responses

---

### 12.3 User Documentation

**Create help pages:**
- How to read prop suggestions
- Understanding confidence scores
- Interpreting player trends
- Betting responsibly disclaimer

---

## PROJECT TIMELINE

### Week 1-2: Foundation
- Phase 1: Architecture & Setup
- Phase 2: Database Design
- Phase 3: NBA API Integration (basic)

### Week 3-4: Core Backend
- Phase 3: Complete Data Ingestion
- Phase 4: Prop Suggestion Engine
- Phase 5: API Endpoints

### Week 5-6: Frontend
- Phase 6: UI Components
- Phase 6: Pages & Routing
- Phase 7: Data Visualization

### Week 7: Testing & Polish
- Phase 8: Testing
- Bug fixes
- UI refinements

### Week 8: Deployment
- Phase 9: Deployment
- Production setup
- Initial data sync

### Ongoing:
- Phase 10: Optimization
- Phase 11: Monitoring & Maintenance
- Phase 12: Documentation

---

## KEY DECISIONS & TRADE-OFFS

### MVP Scope
**Include:**
- NBA only (no other sports)
- Basic prop types (points, rebounds, assists, 3PM, steals, blocks)
- Historical analysis
- Confidence scoring
- Clean, simple UI

**Exclude (for now):**
- Live odds integration
- User accounts
- Bet tracking
- Advanced betting strategies (parlays, teasers)
- Mobile app
- Real-time updates during games

---

## RISKS & MITIGATIONS

**Risk 1: NBA API Rate Limiting**
- Mitigation: Aggressive caching, sync only featured players, respect rate limits

**Risk 2: Data Accuracy**
- Mitigation: Multiple data validation checks, manual review of high-confidence props

**Risk 3: Algorithm Reliability**
- Mitigation: Start conservative with confidence scores, iterate based on real-world results

**Risk 4: Server Costs**
- Mitigation: Use free tiers where possible, optimize database queries, consider caching

---

## SUCCESS METRICS

**Technical:**
- [ ] API response time < 500ms
- [ ] Uptime > 99%
- [ ] Daily data sync success rate > 95%

**Product:**
- [ ] Generate 50+ props per day
- [ ] User engagement: 100+ daily active users (after launch)
- [ ] Prop accuracy: Track and improve over time

---

## FINAL CHECKLIST

### Before Launch:
- [ ] All API endpoints tested and working
- [ ] Frontend pages rendering correctly
- [ ] Mobile responsive design verified
- [ ] Database migrations completed
- [ ] Initial data synced
- [ ] Error handling in place
- [ ] Loading states implemented
- [ ] Responsible gambling disclaimers added
- [ ] Privacy policy created
- [ ] Terms of service created
- [ ] Analytics installed
- [ ] Monitoring set up

### Launch:
- [ ] Deploy to production
- [ ] Verify all features working
- [ ] Monitor for errors
- [ ] Share with initial users
- [ ] Gather feedback

### Post-Launch:
- [ ] Fix critical bugs immediately
- [ ] Monitor performance
- [ ] Track prop accuracy
- [ ] Plan Phase 2 features
- [ ] Regular updates and improvements

---

## RESOURCES & REFERENCES

**Libraries & Tools:**
- NBA Stats API: https://github.com/swar/nba_api
- FastAPI Docs: https://fastapi.tiangolo.com
- React Docs: https://react.dev
- Recharts: https://recharts.org
- Tailwind CSS: https://tailwindcss.com

**Inspiration:**
- Outlier.bet (feature reference)
- Basketball Reference (stats reference)
- PrizePicks (prop format reference)

**Legal:**
- Review sports betting laws in your jurisdiction
- Include gambling addiction resources
- Add age verification disclaimer
- Terms of Service template

---

## CONCLUSION

This document provides a comprehensive, waterfall-style plan for transforming your NBA-Stat-Spot repository into a focused NBA prop betting analysis tool. Follow each phase sequentially, completing all tasks before moving to the next phase. Adapt as needed based on technical challenges or changing requirements, but maintain the core focus on simplicity, transparency, and statistical integrity.

**Remember:** Start simple, launch quickly, iterate based on user feedback and real-world accuracy. The goal is to provide value through clear, data-driven insights - not to be the most feature-rich app on day one.

Good luck with the build! 🏀📊
