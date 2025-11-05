# NBA Player Profile Interface - Technical Specification & Design Document

## Executive Summary

A comprehensive, data-driven interface for analyzing NBA player statistics to inform prop betting decisions. The system provides historical performance analysis, trend visualization, matchup intelligence, and betting recommendations through an intuitive, visually-rich dashboard.

---

## Table of Contents

1. [Overview & Objectives](#overview--objectives)
2. [User Stories](#user-stories)
3. [System Architecture](#system-architecture)
4. [Data Models & Structures](#data-models--structures)
5. [Component Hierarchy](#component-hierarchy)
6. [UI/UX Design Specifications](#uiux-design-specifications)
7. [Feature Requirements](#feature-requirements)
8. [Technical Stack](#technical-stack)
9. [Implementation Phases](#implementation-phases)
10. [API Requirements](#api-requirements)
11. [Performance Requirements](#performance-requirements)
12. [Testing Strategy](#testing-strategy)

---

## 1. Overview & Objectives

### Primary Goal
Create an intuitive, visually compelling interface that helps users make informed prop betting decisions by surfacing relevant player statistics, trends, and contextual factors.

### Key Objectives
- **Data Clarity**: Present complex statistical data in easily digestible formats
- **Visual Hierarchy**: Guide users to high-confidence betting opportunities
- **Contextual Intelligence**: Surface matchup-specific insights automatically
- **Decision Support**: Provide confidence scores and risk assessments
- **Responsive Design**: Work seamlessly across desktop, tablet, and mobile

### Target Users
- Sports bettors (casual to professional)
- Fantasy sports players
- Sports analysts
- NBA fans interested in player performance

---

## 2. User Stories

### Core User Stories

**US-001: Quick Prop Assessment**
```
As a bettor
I want to see prop lines with confidence indicators at a glance
So that I can quickly identify high-value betting opportunities
```

**US-002: Historical Performance Analysis**
```
As a bettor
I want to view a player's recent performance trends
So that I can identify hot/cold streaks and patterns
```

**US-003: Matchup Context**
```
As a bettor
I want to understand how opponent defense affects player performance
So that I can adjust my expectations for tonight's game
```

**US-004: Split Analysis**
```
As a bettor
I want to see how a player performs in different scenarios (home/away, rest days, etc.)
So that I can factor in contextual variables
```

**US-005: Odds Comparison**
```
As a bettor
I want to compare odds across multiple sportsbooks
So that I can find the best value for my bets
```

**US-006: Parlay Building**
```
As a bettor
I want to see suggested parlays with calculated payouts
So that I can make informed multi-leg betting decisions
```

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Player Header│  │  Prop Cards  │  │ Chart Panels │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Stats Tables │  │ Matchup Cards│  │Parlay Builder│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Confidence    │  │ Trend        │  │ Correlation  │      │
│  │Calculator    │  │ Analyzer     │  │ Engine       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Player Stats │  │ Odds Data    │  │ Team Defense │      │
│  │ API          │  │ API          │  │ Stats API    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Flow

```
App Container
│
├── PlayerProfileHeader
│   ├── PlayerAvatar
│   ├── PlayerInfo
│   └── GameContext
│
├── PropHighlightsSection
│   └── PropCard[] (6 cards)
│       ├── PropValue
│       ├── TrendIndicator
│       └── ConfidenceBar
│
├── PerformanceTrendsSection
│   ├── PointsTrendChart
│   └── AssistsTrendChart
│
├── StatisticalSplitsSection
│   └── SplitsTable
│       └── StatRow[]
│
├── MatchupAnalysisSection
│   └── MatchupCard[] (4 cards)
│
├── ShotDistributionSection
│   ├── PieChart (Shot Types)
│   └── BarChart (Quarter Scoring)
│
├── HistoricalPropSection
│   └── PropHistoryRow[] (6 rows)
│
├── LiveOddsSection
│   └── OddsCard[] (2+ cards)
│
├── AdvancedMetricsSection
│   ├── UsageRateCard
│   ├── CorrelationsCard
│   └── DefensiveMatchupCard
│
├── ParlayBuilderSection
│   ├── ParlayLegsList
│   └── PayoutCalculator
│
└── BettingRecommendationSection
    ├── HighConfidencePlays
    ├── RiskFactors
    └── Tags
```

---

## 4. Data Models & Structures

### Core Data Types

```typescript
// Player Information
interface Player {
  id: string;
  name: string;
  team: string;
  number: string;
  position: string;
  avatar?: string;
}

// Game Context
interface GameContext {
  opponent: string;
  date: string;
  time: string;
  location: 'home' | 'away';
  venue?: string;
}

// Prop Line
interface PropLine {
  id: string;
  type: 'points' | 'assists' | 'rebounds' | 'threes' | 'pra' | 'double-double';
  line: number | string;
  overUnder: 'over' | 'under';
  confidence: number; // 0-100
  trend: 'up' | 'down' | 'neutral';
  recentAverage: number;
  differential: number;
}

// Game Statistics
interface GameStats {
  gameId: string;
  date: string;
  opponent: string;
  minutes: number;
  points: number;
  assists: number;
  rebounds: number;
  threesMade: number;
  fieldGoalsMade: number;
  fieldGoalsAttempted: number;
  freeThrowsMade: number;
  freeThrowsAttempted: number;
  turnovers: number;
  steals: number;
  blocks: number;
  plusMinus: number;
}

// Statistical Split
interface StatSplit {
  category: string;
  games: number;
  points: number;
  assists: number;
  rebounds: number;
  threesMade: number;
  pra: number;
}

// Matchup Data
interface MatchupData {
  opponentDefenseRank: {
    pointsAllowed: number;
    assistsAllowed: number;
    reboundsAllowed: number;
  };
  pace: number;
  expectedPossessions: number;
  primaryDefender?: string;
  defenderRating?: number;
}

// Odds Entry
interface OddsEntry {
  sportsbook: string;
  propType: string;
  line: number;
  overOdds: string;
  underOdds: string;
  lastUpdated: string;
}

// Prop History
interface PropHistory {
  propType: string;
  hitRate: number; // 0-100
  recentResults: boolean[]; // Last 5-10 games
  averageMargin: number;
  trend: 'hot' | 'cold' | 'neutral' | 'fire';
}

// Parlay Leg
interface ParlayLeg {
  id: string;
  player: string;
  propType: string;
  line: number;
  selection: 'over' | 'under';
  odds: string;
  confidence: number;
}

// Parlay
interface Parlay {
  legs: ParlayLeg[];
  combinedOdds: string;
  risk: number;
  toWin: number;
  totalPayout: number;
  probability: number;
}
```

### Calculated Metrics

```typescript
// Confidence Score Calculation
interface ConfidenceFactors {
  recentPerformance: number;      // 30% weight
  historicalVsOpponent: number;   // 25% weight
  homeAwayFactor: number;         // 15% weight
  restDaysFactor: number;         // 10% weight
  usageRateTrend: number;         // 10% weight
  matchupRating: number;          // 10% weight
}

// Advanced Metrics
interface AdvancedMetrics {
  usageRate: number;
  trueShootingPercentage: number;
  assistPercentage: number;
  reboundPercentage: number;
  playerEfficiencyRating: number;
}

// Correlations
interface PropCorrelations {
  pointsToAssists: number;    // -1 to 1
  pointsToRebounds: number;
  assistsToRebounds: number;
}
```

---

## 5. Component Hierarchy

### Component Breakdown

#### 5.1 PlayerProfileHeader
**Purpose**: Display player identity and game context
**Props**:
```typescript
interface PlayerProfileHeaderProps {
  player: Player;
  gameContext: GameContext;
}
```
**Features**:
- Player avatar/initials
- Full name
- Team, number, position
- Opponent and game time
- Home/away indicator

#### 5.2 PropCard
**Purpose**: Display individual prop line with confidence
**Props**:
```typescript
interface PropCardProps {
  label: string;
  value: string | number;
  trend: 'up' | 'down' | 'neutral';
  trendText: string;
  confidence: number;
  recommendation: string;
}
```
**Features**:
- Large value display
- Trend arrow and text
- Confidence bar (0-100%)
- Visual hierarchy based on confidence
- Hover effects

#### 5.3 TrendChart
**Purpose**: Visualize performance over recent games
**Props**:
```typescript
interface TrendChartProps {
  data: Array<{
    game: string;
    value: number;
    line: number;
  }>;
  title: string;
  yAxisLabel: string;
  minValue: number;
  maxValue: number;
}
```
**Features**:
- Line chart with actual values
- Dashed line for prop line
- Color coding (green above line, red below)
- Tooltips on hover
- Legend

#### 5.4 SplitsTable
**Purpose**: Display statistical splits across scenarios
**Props**:
```typescript
interface SplitsTableProps {
  splits: StatSplit[];
  propLines: {
    points: number;
    assists: number;
    rebounds: number;
    threes: number;
    pra: number;
  };
}
```
**Features**:
- Color-coded indicators (green/yellow/red dots)
- Highlight rows (Last 5, Home Games, vs Opponent)
- Responsive layout
- Hover states

#### 5.5 MatchupCard
**Purpose**: Display contextual matchup information
**Props**:
```typescript
interface MatchupCardProps {
  title: string;
  stats: Array<{
    label: string;
    value: string;
    valueColor?: string;
  }>;
  tags?: string[];
}
```
**Features**:
- Clean card layout
- Label-value pairs
- Optional tags for streaks
- Hover shadow effect

#### 5.6 OddsCard
**Purpose**: Compare odds across sportsbooks
**Props**:
```typescript
interface OddsCardProps {
  title: string;
  propLine: number;
  odds: Array<{
    sportsbook: string;
    over: string;
    under: string;
  }>;
  bestOver: string;
  bestUnder: string;
}
```
**Features**:
- Header with prop description
- Row per sportsbook
- Highlight best odds
- Last updated timestamp

#### 5.7 ParlayBuilder
**Purpose**: Suggest and calculate parlays
**Props**:
```typescript
interface ParlayBuilderProps {
  suggestedLegs: ParlayLeg[];
  onRemoveLeg: (legId: string) => void;
  onPlaceBet: () => void;
}
```
**Features**:
- List of parlay legs
- Remove leg functionality
- Payout calculator
- Combined odds display
- Probability estimate
- CTA button

---

## 6. UI/UX Design Specifications

### 6.1 Color Palette

```css
/* Primary Colors */
--color-primary-900: #1e3a8a;      /* Dark blue - headers, emphasis */
--color-primary-600: #2563eb;      /* Blue - links, accents */
--color-primary-100: #dbeafe;      /* Light blue - backgrounds */

/* Secondary Colors */
--color-purple-600: #9333ea;       /* Purple - gradients */
--color-purple-100: #f3e8ff;       /* Light purple - backgrounds */

/* Status Colors */
--color-green-600: #16a34a;        /* Positive trends, above line */
--color-green-500: #22c55e;        /* Confidence bars */
--color-green-100: #dcfce7;        /* Light green backgrounds */

--color-yellow-600: #ca8a04;       /* Neutral trends, warnings */
--color-yellow-500: #eab308;       /* Near line indicators */
--color-yellow-100: #fef9c3;       /* Light yellow backgrounds */

--color-red-600: #dc2626;          /* Negative trends, below line */
--color-red-500: #ef4444;          /* Cold streaks */
--color-red-100: #fee2e2;          /* Light red backgrounds */

/* Neutral Colors */
--color-gray-900: #111827;         /* Primary text */
--color-gray-700: #374151;         /* Secondary text */
--color-gray-500: #6b7280;         /* Tertiary text */
--color-gray-200: #e5e7eb;         /* Borders */
--color-gray-100: #f3f4f6;         /* Backgrounds */
--color-gray-50: #f9fafb;          /* Light backgrounds */
```

### 6.2 Typography

```css
/* Font Family */
--font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;

/* Font Sizes */
--text-xs: 0.75rem;      /* 12px - labels, tags */
--text-sm: 0.875rem;     /* 14px - body, descriptions */
--text-base: 1rem;       /* 16px - base text */
--text-lg: 1.125rem;     /* 18px - card titles */
--text-xl: 1.25rem;      /* 20px - section titles */
--text-2xl: 1.5rem;      /* 24px - large headings */
--text-3xl: 1.875rem;    /* 30px - section headers */
--text-4xl: 2.25rem;     /* 36px - main title */
--text-5xl: 3rem;        /* 48px - prop values */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-extrabold: 800;
```

### 6.3 Spacing Scale

```css
--spacing-1: 0.25rem;    /* 4px */
--spacing-2: 0.5rem;     /* 8px */
--spacing-3: 0.75rem;    /* 12px */
--spacing-4: 1rem;       /* 16px */
--spacing-5: 1.25rem;    /* 20px */
--spacing-6: 1.5rem;     /* 24px */
--spacing-8: 2rem;       /* 32px */
--spacing-10: 2.5rem;    /* 40px */
--spacing-12: 3rem;      /* 48px */
```

### 6.4 Border Radius

```css
--radius-sm: 0.375rem;   /* 6px - small elements */
--radius-md: 0.5rem;     /* 8px - buttons, inputs */
--radius-lg: 0.75rem;    /* 12px - cards */
--radius-xl: 1rem;       /* 16px - large cards */
--radius-2xl: 1.5rem;    /* 24px - major containers */
--radius-3xl: 1.75rem;   /* 28px - page container */
--radius-full: 9999px;   /* Full rounded */
```

### 6.5 Shadows

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
```

### 6.6 Layout Grid

```
Desktop (>1024px):
┌────────────────────────────────────────────────┐
│  [3 columns for prop cards]                    │
│  [2 columns for charts]                        │
│  [4 columns for matchup cards]                 │
│  [Full width table]                            │
└────────────────────────────────────────────────┘

Tablet (768px-1023px):
┌────────────────────────────────────────────────┐
│  [2 columns for prop cards]                    │
│  [1 column for charts, stacked]                │
│  [2 columns for matchup cards]                 │
│  [Scrollable table]                            │
└────────────────────────────────────────────────┘

Mobile (<767px):
┌────────────────────────────────────────────────┐
│  [1 column, all stacked]                       │
│  [Swipeable prop cards]                        │
│  [Stacked charts]                              │
│  [Scrollable table]                            │
└────────────────────────────────────────────────┘
```

---

## 7. Feature Requirements

### 7.1 Prop Highlights (PRIORITY: HIGH)

**Requirements**:
- Display 6 key prop bets at top of interface
- Show prop line, recent average, and differential
- Display confidence percentage (0-100%)
- Visual confidence bar
- Trend indicator (up/down/neutral arrow)
- Color coding based on confidence level

**Calculations**:
```typescript
function calculateConfidence(
  recentGames: GameStats[],
  historicalVsOpponent: GameStats[],
  splitData: StatSplit[],
  propLine: number
): number {
  const weights = {
    recentPerformance: 0.30,
    vsOpponent: 0.25,
    homeAway: 0.15,
    rest: 0.10,
    usage: 0.10,
    matchup: 0.10
  };
  
  // Calculate each factor (0-100)
  const recentScore = calculateRecentPerformance(recentGames, propLine);
  const opponentScore = calculateOpponentHistory(historicalVsOpponent, propLine);
  const homeAwayScore = calculateHomeAwayFactor(splitData, propLine);
  const restScore = calculateRestFactor(gameContext);
  const usageScore = calculateUsageTrend(recentGames);
  const matchupScore = calculateMatchupRating(matchupData);
  
  // Weighted sum
  return (
    recentScore * weights.recentPerformance +
    opponentScore * weights.vsOpponent +
    homeAwayScore * weights.homeAway +
    restScore * weights.rest +
    usageScore * weights.usage +
    matchupScore * weights.matchup
  );
}
```

### 7.2 Performance Trends (PRIORITY: HIGH)

**Requirements**:
- Line charts showing last 10-15 games
- Plot actual performance vs prop line
- Different charts for points, assists, rebounds, etc.
- Tooltips showing exact values on hover
- Responsive sizing
- Legend explaining lines

**Chart Configuration**:
```typescript
const chartConfig = {
  width: '100%',
  height: 280,
  margin: { top: 10, right: 30, left: 0, bottom: 0 },
  grid: {
    strokeDasharray: '3 3',
    stroke: '#e5e7eb'
  },
  line: {
    actual: {
      stroke: '#3b82f6',
      strokeWidth: 3,
      dot: { fill: '#3b82f6', r: 5 }
    },
    propLine: {
      stroke: '#ef4444',
      strokeDasharray: '8 4',
      strokeWidth: 2
    }
  }
};
```

### 7.3 Statistical Splits (PRIORITY: HIGH)

**Requirements**:
- Table showing performance across different scenarios
- Color-coded indicators (green dot = above line, yellow = near, red = below)
- Highlight important rows (Last 5, Home Games, vs Opponent)
- Mobile-responsive (horizontal scroll if needed)
- Sortable columns (optional)

**Split Categories**:
1. Season Average
2. Last 10 Games
3. Last 5 Games
4. Home Games
5. Away Games
6. vs Opponent (last 3 meetings)
7. With 1 Day Rest
8. Back-to-Back Games
9. Days Rest = 2+
10. First Half of Season
11. Second Half of Season

### 7.4 Matchup Analysis (PRIORITY: MEDIUM)

**Requirements**:
- 4 card layout showing contextual factors
- Opponent defense rankings
- Pace and style metrics
- Recent form and streaks
- Game context (rest, injuries, minutes)

**Data Points**:
- Opponent's points allowed to position (rank)
- Opponent's assists allowed (rank)
- Opponent's rebounds allowed (rank)
- Expected game pace
- Expected possessions
- Primary defender stats
- Rest days
- Injury report
- Recent minutes trend

### 7.5 Historical Prop Performance (PRIORITY: HIGH)

**Requirements**:
- Table showing how often each prop hits
- Visual representation of last 5 games (✓/✗)
- Hit rate percentage
- Average margin of victory/defeat
- Trend label (Hot/Cold/Neutral/Fire)

**Display Format**:
```
┌────────────┬──────────┬─────────────┬────────────┬────────┐
│ Prop Type  │ Hit Rate │   Last 5    │ Avg Margin │ Trend  │
├────────────┼──────────┼─────────────┼────────────┼────────┤
│ Over 25.5  │ 14/20    │ ✓ ✓ ✓ ✓ ✗  │   +1.8 pts │ 📈 Hot │
│ PTS        │ (70%)    │             │            │        │
└────────────┴──────────┴─────────────┴────────────┴────────┘
```

### 7.6 Live Odds Comparison (PRIORITY: MEDIUM)

**Requirements**:
- Display odds from 3+ sportsbooks
- Show over/under odds for each
- Highlight best available odds with star icon
- Update timestamp
- Color coding for best value

**Sportsbooks to Include**:
1. DraftKings
2. FanDuel
3. BetMGM
4. Caesars
5. PointsBet

### 7.7 Advanced Metrics (PRIORITY: LOW)

**Requirements**:
- 3 cards showing advanced analytics
- Usage rate analysis (trending up/down)
- Prop correlations (which props move together)
- Defensive matchup intel

**Metrics**:
- Usage Rate %
- True Shooting %
- Assist %
- Rebound %
- PER (Player Efficiency Rating)
- Correlations between stats

### 7.8 Parlay Builder (PRIORITY: MEDIUM)

**Requirements**:
- Suggested 3-leg parlay based on high confidence props
- Individual leg details (prop, odds, confidence)
- Combined odds calculator
- Risk/reward display
- Payout calculation
- Probability estimate
- Remove leg functionality
- CTA button to place bet

**Calculations**:
```typescript
function calculateParlayOdds(legs: ParlayLeg[]): {
  combinedOdds: string;
  decimalOdds: number;
  probability: number;
} {
  let totalDecimalOdds = 1;
  let combinedProbability = 1;
  
  legs.forEach(leg => {
    const decimalOdds = americanToDecimal(leg.odds);
    totalDecimalOdds *= decimalOdds;
    combinedProbability *= (leg.confidence / 100);
  });
  
  return {
    combinedOdds: decimalToAmerican(totalDecimalOdds),
    decimalOdds: totalDecimalOdds,
    probability: combinedProbability * 100
  };
}
```

### 7.9 Betting Recommendation (PRIORITY: HIGH)

**Requirements**:
- Summary card at bottom of page
- High confidence plays (top 3)
- Risk factors to consider
- Tags for player status (Hot Streak, Favorable Matchup, etc.)
- Plain language explanations

**Content Structure**:
```markdown
## High Confidence Plays
1. [Prop] ([Confidence]%) - [Reasoning]
2. [Prop] ([Confidence]%) - [Reasoning]
3. [Prop] ([Confidence]%) - [Reasoning]

## Risk Factors
- [Risk 1]
- [Risk 2]
- [Risk 3]

Tags: [Tag1] [Tag2] [Tag3]
```

---

## 8. Technical Stack

### Required Technologies

**Frontend Framework**:
- React 18+ with TypeScript
- Functional components with hooks

**Styling**:
- Tailwind CSS 3.x
- No custom CSS files (use Tailwind utilities only)

**Charts**:
- Recharts 2.x (React-specific charting library)
- Components: LineChart, BarChart, PieChart

**State Management** (Optional):
- React Context for global state
- Or Zustand for simple state management
- Redux if complex state required

**Data Fetching**:
- React Query (TanStack Query) for API calls
- Axios or Fetch API

**Type Safety**:
- TypeScript 5.x
- Strict mode enabled
- Interface definitions for all data structures

**Build Tools**:
- Vite (recommended) or Create React App
- ESLint + Prettier for code quality

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Setup and basic structure

**Tasks**:
1. Initialize React + TypeScript project with Vite
2. Configure Tailwind CSS
3. Define all TypeScript interfaces
4. Create folder structure:
   ```
   src/
   ├── components/
   │   ├── PlayerHeader/
   │   ├── PropCard/
   │   ├── TrendChart/
   │   ├── SplitsTable/
   │   ├── MatchupCard/
   │   ├── OddsCard/
   │   ├── ParlayBuilder/
   │   └── BettingRecommendation/
   ├── hooks/
   ├── utils/
   ├── types/
   ├── constants/
   └── App.tsx
   ```
5. Setup mock data for development
6. Create PlayerProfileHeader component

**Deliverables**:
- Working dev environment
- Type definitions file
- Header component rendering

### Phase 2: Core Components (Week 2)
**Goal**: Build primary UI components

**Tasks**:
1. Build PropCard component with all features
2. Implement TrendChart component
3. Create SplitsTable component
4. Build MatchupCard component
5. Test responsiveness on all components

**Deliverables**:
- 4 core components completed
- Storybook stories for each (optional)
- Mobile-responsive design verified

### Phase 3: Data Visualization (Week 3)
**Goal**: Implement all charts and data displays

**Tasks**:
1. Integrate Recharts
2. Build LineChart for trends
3. Build PieChart for shot distribution
4. Build BarChart for quarter scoring
5. Add tooltips and legends
6. Implement historical prop performance display

**Deliverables**:
- All charts rendering with mock data
- Interactive features working
- Performance optimized

### Phase 4: Advanced Features (Week 4)
**Goal**: Add betting-specific features

**Tasks**:
1. Build OddsCard component
2. Implement ParlayBuilder
3. Create parlay odds calculator
4. Build BettingRecommendation component
5. Add advanced metrics section

**Deliverables**:
- Parlay builder functional
- Odds comparison working
- Recommendations generating

### Phase 5: Integration & Polish (Week 5)
**Goal**: Connect to real APIs and polish UI

**Tasks**:
1. Replace mock data with API calls
2. Implement loading states
3. Add error handling
4. Optimize performance
5. Add animations and transitions
6. Comprehensive testing
7. Documentation

**Deliverables**:
- Fully functional application
- Real data flowing through
- Production-ready code
- Documentation complete

---

## 10. API Requirements

### 10.1 Player Stats API

**Endpoint**: `GET /api/players/{playerId}/stats`

**Required Data**:
```json
{
  "player": {
    "id": "string",
    "name": "string",
    "team": "string",
    "position": "string",
    "number": "string"
  },
  "seasonStats": {
    "gamesPlayed": "number",
    "pointsPerGame": "number",
    "assistsPerGame": "number",
    "reboundsPerGame": "number",
    // ... other stats
  },
  "recentGames": [
    {
      "gameId": "string",
      "date": "string",
      "opponent": "string",
      "points": "number",
      "assists": "number",
      "rebounds": "number",
      // ... other stats
    }
  ],
  "splits": [
    {
      "category": "string",
      "games": "number",
      "stats": { /* ... */ }
    }
  ]
}
```

### 10.2 Odds API

**Endpoint**: `GET /api/odds/props/{playerId}`

**Required Data**:
```json
{
  "props": [
    {
      "propType": "string",
      "line": "number",
      "sportsbooks": [
        {
          "name": "string",
          "overOdds": "string",
          "underOdds": "string",
          "lastUpdated": "string"
        }
      ]
    }
  ]
}
```

### 10.3 Matchup API

**Endpoint**: `GET /api/matchups/{gameId}`

**Required Data**:
```json
{
  "game": {
    "id": "string",
    "date": "string",
    "homeTeam": "string",
    "awayTeam": "string"
  },
  "defenseStats": {
    "pointsAllowedRank": "number",
    "assistsAllowedRank": "number",
    "reboundsAllowedRank": "number"
  },
  "pace": "number",
  "injuries": []
}
```

### 10.4 Error Handling

**Standard Error Response**:
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object"
  }
}
```

**Status Codes**:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 429: Rate Limit Exceeded
- 500: Server Error

---

## 11. Performance Requirements

### 11.1 Load Time
- Initial page load: < 2 seconds
- Component render: < 100ms
- Chart render: < 200ms

### 11.2 Bundle Size
- Total JS bundle: < 500KB (gzipped)
- CSS bundle: < 50KB (gzipped)
- Lazy load non-critical components

### 11.3 Optimization Strategies
1. Code splitting by route/section
2. Lazy load charts below fold
3. Memoize expensive calculations
4. Use React.memo for pure components
5. Implement virtual scrolling for large tables
6. Optimize images (WebP, lazy loading)
7. Cache API responses

### 11.4 Accessibility
- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader friendly
- Proper ARIA labels
- Color contrast ratio > 4.5:1

---

## 12. Testing Strategy

### 12.1 Unit Tests
**Framework**: Jest + React Testing Library

**Coverage Target**: 80%+

**Test Categories**:
1. Component rendering
2. User interactions
3. Calculations (confidence, odds, payouts)
4. Data transformations
5. Utility functions

**Example Tests**:
```typescript
describe('PropCard', () => {
  it('renders prop value correctly', () => {});
  it('shows correct trend arrow based on trend prop', () => {});
  it('displays confidence bar with correct width', () => {});
  it('applies correct color classes based on confidence level', () => {});
});

describe('calculateConfidence', () => {
  it('returns value between 0-100', () => {});
  it('weights recent performance heavily', () => {});
  it('factors in home/away split', () => {});
});
```

### 12.2 Integration Tests
**Framework**: Cypress or Playwright

**Test Scenarios**:
1. Full user flow (landing → view stats → build parlay)
2. Data loading and error states
3. Responsive design on different viewports
4. Chart interactions
5. Odds comparison functionality

### 12.3 Visual Regression Tests
**Tool**: Percy or Chromatic

**Test Cases**:
1. Component visual consistency
2. Responsive breakpoints
3. Theme variations
4. Loading states
5. Error states

### 12.4 Performance Tests
**Tools**: Lighthouse, WebPageTest

**Metrics to Monitor**:
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time to Interactive (TTI)
- Cumulative Layout Shift (CLS)

---

## 13. Future Enhancements

### Phase 2 Features (Post-MVP)

1. **Multi-Player Comparison**
   - Compare 2-3 players side-by-side
   - Highlight differentiators

2. **Custom Prop Builder**
   - User creates their own prop lines
   - System provides confidence score

3. **Bet Tracking**
   - Log placed bets
   - Track win/loss record
   - ROI calculator

4. **Alerts & Notifications**
   - Line movement alerts
   - Injury news alerts
   - Hot streak notifications

5. **Historical Archive**
   - View past games
   - Analyze prop performance over time
   - Export data

6. **Social Features**
   - Share parlays
   - Follow other users
   - Community picks

7. **Machine Learning Integration**
   - AI-powered confidence scores
   - Pattern recognition
   - Predictive modeling

---

## 14. Deployment & DevOps

### 14.1 Hosting Options
- Vercel (recommended for Next.js/React)
- Netlify
- AWS Amplify
- AWS S3 + CloudFront

### 14.2 CI/CD Pipeline
```yaml
# GitHub Actions example
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: npm install
      - name: Run tests
        run: npm test
      - name: Build
        run: npm run build
      - name: Deploy
        run: npm run deploy
```

### 14.3 Monitoring
- Error tracking: Sentry
- Analytics: Google Analytics 4
- Performance: Vercel Analytics or New Relic
- Uptime: Pingdom or UptimeRobot

---

## 15. Glossary

**Prop Bet**: Proposition bet on a specific player statistic (e.g., "Will LeBron score over 25.5 points?")

**PRA**: Points + Rebounds + Assists combined total

**Line**: The threshold value for a prop bet (e.g., 25.5 points)

**Over/Under**: Betting on whether actual result will be above or below the line

**Confidence Score**: Calculated probability (0-100%) that a prop will hit

**Hit Rate**: Percentage of times a prop bet has won historically

**Parlay**: Combination bet with multiple legs (all must win)

**American Odds**: Betting odds format (e.g., -110, +150)

**Split**: Statistical breakdown by category (home/away, rest days, etc.)

**Usage Rate**: Percentage of team plays that involve the player

**True Shooting %**: Shooting efficiency metric accounting for 2PT, 3PT, and FT

---

## 16. Success Metrics

### Key Performance Indicators (KPIs)

1. **User Engagement**
   - Average session duration: > 5 minutes
   - Pages per session: > 3
   - Return visitor rate: > 40%

2. **Feature Adoption**
   - % users viewing splits table: > 70%
   - % users interacting with charts: > 60%
   - % users checking odds comparison: > 50%
   - % users using parlay builder: > 30%

3. **Technical Performance**
   - Page load time: < 2 seconds
   - Error rate: < 1%
   - Uptime: > 99.5%

4. **Business Metrics** (if applicable)
   - Bet placement conversion: Track if users place bets
   - Premium feature adoption: If monetized
   - Referral rate: Measure sharing

---

## 17. Contact & Support

**Product Owner**: [Name]
**Tech Lead**: [Name]
**Design Lead**: [Name]

**Documentation**: [Link to additional docs]
**Repository**: [GitHub/GitLab URL]
**Figma Designs**: [Figma URL]

---

## Appendix A: Example Mock Data

```typescript
const mockPlayerData: Player = {
  id: "player-123",
  name: "LeBron James",
  team: "LA Lakers",
  number: "23",
  position: "SF/PF"
};

const mockGameContext: GameContext = {
  opponent: "Boston Celtics",
  date: "2025-11-05",
  time: "7:30 PM",
  location: "home",
  venue: "Crypto.com Arena"
};

const mockPropLines: PropLine[] = [
  {
    id: "prop-1",
    type: "points",
    line: 25.5,
    overUnder: "over",
    confidence: 78,
    trend: "up",
    recentAverage: 27.3,
    differential: 1.8
  },
  // ... more props
];

const mockRecentGames: GameStats[] = [
  {
    gameId: "game-1",
    date: "2025-11-03",
    opponent: "Phoenix Suns",
    minutes: 35,
    points: 27,
    assists: 8,
    rebounds: 9,
    threesMade: 1,
    fieldGoalsMade: 10,
    fieldGoalsAttempted: 20,
    freeThrowsMade: 5,
    freeThrowsAttempted: 6,
    turnovers: 3,
    steals: 1,
    blocks: 1,
    plusMinus: 8
  },
  // ... more games
];
```

---

## Appendix B: Design Assets Checklist

- [ ] Player avatar/placeholder graphics
- [ ] Team logos (all 30 NBA teams)
- [ ] Sportsbook logos (DraftKings, FanDuel, etc.)
- [ ] Icon set (arrows, checkmarks, X marks, etc.)
- [ ] Loading spinners/skeletons
- [ ] Empty state illustrations
- [ ] Error state graphics
- [ ] Favicon and app icons

---

## Document Version History

| Version | Date       | Author | Changes                          |
|---------|------------|--------|----------------------------------|
| 1.0     | 2025-11-05 | AI     | Initial document creation        |

---

## Appendix C: Component Implementation Examples

### Example 1: PropCard Component

```typescript
import React from 'react';

interface PropCardProps {
  label: string;
  value: string | number;
  trend: 'up' | 'down' | 'neutral';
  trendText: string;
  confidence: number;
  recommendation: string;
}

export const PropCard: React.FC<PropCardProps> = ({
  label,
  value,
  trend,
  trendText,
  confidence,
  recommendation
}) => {
  // Determine trend styling
  const trendColor = 
    trend === 'up' ? 'text-green-600' : 
    trend === 'down' ? 'text-red-600' : 
    'text-yellow-600';
  
  const trendArrow = 
    trend === 'up' ? '↑' : 
    trend === 'down' ? '↓' : 
    '→';

  return (
    <div className="bg-gradient-to-br from-white via-gray-50 to-gray-100 rounded-2xl p-6 border-l-4 border-blue-600 shadow-lg hover:shadow-2xl transition-all hover:-translate-y-2 duration-300">
      {/* Label */}
      <div className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
        {label}
      </div>
      
      {/* Value */}
      <div className="text-5xl font-extrabold text-blue-900 mb-2">
        {value}
      </div>
      
      {/* Trend */}
      <div className={`flex items-center gap-2 text-sm font-bold mb-4 ${trendColor}`}>
        <span className="text-xl">{trendArrow}</span>
        <span>{trendText}</span>
      </div>
      
      {/* Confidence Bar */}
      <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden mb-3 shadow-inner">
        <div 
          className="h-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500 rounded-full transition-all duration-500" 
          style={{ width: `${confidence}%` }}
        />
      </div>
      
      {/* Confidence Text */}
      <div className="text-xs text-gray-700 font-semibold">
        {confidence}% confidence {recommendation}
      </div>
    </div>
  );
};
```

### Example 2: Confidence Calculation Utility

```typescript
interface ConfidenceFactors {
  recentPerformance: number;
  historicalVsOpponent: number;
  homeAwayFactor: number;
  restDaysFactor: number;
  usageRateTrend: number;
  matchupRating: number;
}

export function calculateConfidence(
  recentGames: GameStats[],
  historicalVsOpponent: GameStats[],
  splitData: StatSplit[],
  propLine: number,
  propType: 'points' | 'assists' | 'rebounds',
  gameContext: GameContext
): number {
  const weights = {
    recentPerformance: 0.30,
    vsOpponent: 0.25,
    homeAway: 0.15,
    rest: 0.10,
    usage: 0.10,
    matchup: 0.10
  };

  // Recent Performance (Last 10 games)
  const recentScore = calculateRecentPerformance(
    recentGames.slice(0, 10),
    propLine,
    propType
  );

  // Historical vs Opponent
  const opponentScore = calculateOpponentHistory(
    historicalVsOpponent,
    propLine,
    propType
  );

  // Home/Away Factor
  const homeAwayScore = calculateHomeAwayFactor(
    splitData,
    propLine,
    propType,
    gameContext.location
  );

  // Rest Days Factor
  const restScore = calculateRestFactor(gameContext.restDays);

  // Usage Rate Trend
  const usageScore = calculateUsageTrend(recentGames);

  // Matchup Rating
  const matchupScore = calculateMatchupRating(
    gameContext.opponentDefenseRank,
    propType
  );

  // Weighted sum
  const confidence = (
    recentScore * weights.recentPerformance +
    opponentScore * weights.vsOpponent +
    homeAwayScore * weights.homeAway +
    restScore * weights.rest +
    usageScore * weights.usage +
    matchupScore * weights.matchup
  );

  return Math.round(confidence);
}

function calculateRecentPerformance(
  games: GameStats[],
  line: number,
  propType: 'points' | 'assists' | 'rebounds'
): number {
  if (games.length === 0) return 50;

  const values = games.map(g => {
    switch (propType) {
      case 'points': return g.points;
      case 'assists': return g.assists;
      case 'rebounds': return g.rebounds;
    }
  });

  const average = values.reduce((a, b) => a + b, 0) / values.length;
  const hitRate = values.filter(v => v > line).length / values.length;
  const differential = average - line;

  // Score based on hit rate and differential
  let score = hitRate * 100;
  
  // Adjust for differential magnitude
  if (differential > 2) score = Math.min(100, score + 10);
  if (differential < -2) score = Math.max(0, score - 10);

  return score;
}

function calculateOpponentHistory(
  games: GameStats[],
  line: number,
  propType: 'points' | 'assists' | 'rebounds'
): number {
  if (games.length === 0) return 50;

  const values = games.map(g => {
    switch (propType) {
      case 'points': return g.points;
      case 'assists': return g.assists;
      case 'rebounds': return g.rebounds;
    }
  });

  const average = values.reduce((a, b) => a + b, 0) / values.length;
  const hitRate = values.filter(v => v > line).length / values.length;

  return hitRate * 100;
}

function calculateHomeAwayFactor(
  splits: StatSplit[],
  line: number,
  propType: 'points' | 'assists' | 'rebounds',
  location: 'home' | 'away'
): number {
  const split = splits.find(s => 
    s.category.toLowerCase() === `${location} games`
  );

  if (!split) return 50;

  let value: number;
  switch (propType) {
    case 'points': value = split.points; break;
    case 'assists': value = split.assists; break;
    case 'rebounds': value = split.rebounds; break;
  }

  const differential = value - line;
  
  if (differential > 2) return 80;
  if (differential > 0) return 65;
  if (differential > -2) return 50;
  return 35;
}

function calculateRestFactor(restDays: number): number {
  // Optimal rest is 1-2 days
  if (restDays === 1 || restDays === 2) return 70;
  if (restDays === 0) return 40; // Back-to-back
  if (restDays >= 3) return 60; // Too much rest
  return 50;
}

function calculateUsageTrend(games: GameStats[]): number {
  if (games.length < 5) return 50;

  const recent5 = games.slice(0, 5);
  const previous5 = games.slice(5, 10);

  const recentMinutes = recent5.reduce((a, b) => a + b.minutes, 0) / 5;
  const previousMinutes = previous5.reduce((a, b) => a + b.minutes, 0) / 5;

  const minutesTrend = recentMinutes - previousMinutes;

  if (minutesTrend > 2) return 75; // Minutes increasing
  if (minutesTrend > 0) return 60;
  if (minutesTrend > -2) return 50;
  return 40; // Minutes decreasing
}

function calculateMatchupRating(
  defenseRank: number,
  propType: 'points' | 'assists' | 'rebounds'
): number {
  // Lower rank = better defense = harder matchup
  // Rank 1-10: Tough (35-45)
  // Rank 11-20: Average (50-60)
  // Rank 21-30: Favorable (65-80)

  if (defenseRank <= 10) return 40;
  if (defenseRank <= 20) return 55;
  return 70;
}
```

### Example 3: Parlay Odds Calculator

```typescript
export function calculateParlayOdds(legs: ParlayLeg[]): {
  combinedOdds: string;
  decimalOdds: number;
  probability: number;
  risk: number;
  toWin: number;
  totalPayout: number;
} {
  let totalDecimalOdds = 1;
  let combinedProbability = 1;

  // Convert each leg to decimal and multiply
  legs.forEach(leg => {
    const decimalOdds = americanToDecimal(leg.odds);
    totalDecimalOdds *= decimalOdds;
    combinedProbability *= (leg.confidence / 100);
  });

  const risk = 100; // Standard $100 bet
  const toWin = Math.round((totalDecimalOdds - 1) * risk);
  const totalPayout = risk + toWin;

  return {
    combinedOdds: decimalToAmerican(totalDecimalOdds),
    decimalOdds: totalDecimalOdds,
    probability: Math.round(combinedProbability * 100),
    risk,
    toWin,
    totalPayout
  };
}

function americanToDecimal(americanOdds: string): number {
  const odds = parseInt(americanOdds);
  
  if (odds > 0) {
    // Positive odds (underdog)
    return (odds / 100) + 1;
  } else {
    // Negative odds (favorite)
    return (100 / Math.abs(odds)) + 1;
  }
}

function decimalToAmerican(decimalOdds: number): string {
  if (decimalOdds >= 2.0) {
    // Convert to positive American odds
    return `+${Math.round((decimalOdds - 1) * 100)}`;
  } else {
    // Convert to negative American odds
    return `${Math.round(-100 / (decimalOdds - 1))}`;
  }
}
```

---

## Appendix D: Responsive Breakpoints

### Tailwind CSS Breakpoints

```typescript
const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px' // Extra large desktop
};
```

### Component Behavior by Breakpoint

| Component | Mobile (<768px) | Tablet (768-1023px) | Desktop (>1024px) |
|-----------|----------------|-------------------|------------------|
| PropCards | 1 column, stacked | 2 columns | 3 columns |
| Charts | 1 column, stacked | 1 column, stacked | 2 columns |
| Matchup Cards | 1 column, stacked | 2 columns | 4 columns |
| Splits Table | Horizontal scroll | Horizontal scroll | Full width |
| Odds Cards | 1 column, stacked | 1 column, stacked | 2 columns |
| Parlay Builder | Stacked layout | Stacked layout | Side-by-side |
| Header | Stacked, centered | Flex row | Flex row |

### Example Responsive Classes

```tsx
<div className="
  grid 
  grid-cols-1          /* Mobile: 1 column */
  md:grid-cols-2       /* Tablet: 2 columns */
  lg:grid-cols-3       /* Desktop: 3 columns */
  gap-6
">
  {/* PropCards */}
</div>
```

---

## Appendix E: Accessibility Guidelines

### WCAG 2.1 Level AA Requirements

#### Color Contrast
- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text** (18pt+ or 14pt+ bold): Minimum 3:1 contrast ratio
- **UI components**: Minimum 3:1 contrast ratio

#### Keyboard Navigation
```typescript
// All interactive elements must be keyboard accessible
<button 
  className="..."
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
  tabIndex={0}
>
  Place Bet
</button>
```

#### ARIA Labels
```tsx
// Charts
<ResponsiveContainer 
  width="100%" 
  height={280}
  role="img"
  aria-label="Line chart showing points scored over last 15 games"
>
  <LineChart data={data}>
    {/* ... */}
  </LineChart>
</ResponsiveContainer>

// PropCard
<div 
  className="..."
  role="article"
  aria-labelledby="prop-points-label"
>
  <div id="prop-points-label" className="...">
    Points Prop Line
  </div>
  {/* ... */}
</div>

// Confidence Bar
<div 
  role="progressbar" 
  aria-valuenow={confidence} 
  aria-valuemin={0} 
  aria-valuemax={100}
  aria-label={`${confidence}% confidence`}
>
  <div style={{ width: `${confidence}%` }} />
</div>
```

#### Focus Indicators
```css
/* Visible focus indicators for keyboard navigation */
.button:focus-visible {
  @apply outline-2 outline-offset-2 outline-blue-600;
}
```

#### Screen Reader Support
```tsx
// Hidden text for screen readers
<span className="sr-only">
  LeBron James points prop: Over 25.5, 78% confidence
</span>

// Skip to main content link
<a href="#main-content" className="sr-only focus:not-sr-only">
  Skip to main content
</a>
```

---

## Appendix F: Error States & Loading States

### Loading States

#### Skeleton Loaders
```tsx
export const PropCardSkeleton: React.FC = () => (
  <div className="bg-gray-100 rounded-2xl p-6 animate-pulse">
    <div className="h-3 bg-gray-300 rounded w-1/2 mb-2"></div>
    <div className="h-12 bg-gray-300 rounded w-1/3 mb-2"></div>
    <div className="h-4 bg-gray-300 rounded w-2/3 mb-4"></div>
    <div className="h-2 bg-gray-300 rounded mb-3"></div>
    <div className="h-3 bg-gray-300 rounded w-1/3"></div>
  </div>
);

export const ChartSkeleton: React.FC = () => (
  <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
    <div className="h-4 bg-gray-300 rounded w-1/3 mb-4 animate-pulse"></div>
    <div className="h-64 bg-gray-200 rounded animate-pulse"></div>
  </div>
);
```

#### Loading Spinner
```tsx
export const LoadingSpinner: React.FC = () => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);
```

### Error States

#### Error Message Component
```tsx
interface ErrorMessageProps {
  title?: string;
  message: string;
  retry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title = 'Something went wrong',
  message,
  retry
}) => (
  <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
    <div className="text-red-600 text-4xl mb-4">⚠️</div>
    <h3 className="text-lg font-bold text-red-900 mb-2">{title}</h3>
    <p className="text-sm text-red-700 mb-4">{message}</p>
    {retry && (
      <button
        onClick={retry}
        className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg transition-colors"
      >
        Try Again
      </button>
    )}
  </div>
);
```

#### Empty State
```tsx
export const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="text-center py-12">
    <div className="text-gray-400 text-6xl mb-4">📊</div>
    <p className="text-gray-600 text-lg">{message}</p>
  </div>
);
```

---

## Appendix G: Environment Variables

### Required Environment Variables

```bash
# .env.example

# API Configuration
VITE_API_BASE_URL=https://api.example.com
VITE_STATS_API_KEY=your_stats_api_key_here
VITE_ODDS_API_KEY=your_odds_api_key_here

# Feature Flags
VITE_ENABLE_PARLAY_BUILDER=true
VITE_ENABLE_LIVE_ODDS=true
VITE_ENABLE_ADVANCED_METRICS=true

# Analytics
VITE_GA_TRACKING_ID=G-XXXXXXXXXX
VITE_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# Environment
VITE_ENV=development
```

### Type-Safe Environment Variables

```typescript
// src/config/env.ts

interface EnvironmentConfig {
  apiBaseUrl: string;
  statsApiKey: string;
  oddsApiKey: string;
  enableParlayBuilder: boolean;
  enableLiveOdds: boolean;
  enableAdvancedMetrics: boolean;
  gaTrackingId: string;
  sentryDsn: string;
  environment: 'development' | 'staging' | 'production';
}

function getEnvVar(key: string, defaultValue?: string): string {
  const value = import.meta.env[key] || defaultValue;
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export const env: EnvironmentConfig = {
  apiBaseUrl: getEnvVar('VITE_API_BASE_URL'),
  statsApiKey: getEnvVar('VITE_STATS_API_KEY'),
  oddsApiKey: getEnvVar('VITE_ODDS_API_KEY'),
  enableParlayBuilder: getEnvVar('VITE_ENABLE_PARLAY_BUILDER', 'true') === 'true',
  enableLiveOdds: getEnvVar('VITE_ENABLE_LIVE_ODDS', 'true') === 'true',
  enableAdvancedMetrics: getEnvVar('VITE_ENABLE_ADVANCED_METRICS', 'true') === 'true',
  gaTrackingId: getEnvVar('VITE_GA_TRACKING_ID', ''),
  sentryDsn: getEnvVar('VITE_SENTRY_DSN', ''),
  environment: (getEnvVar('VITE_ENV', 'development') as EnvironmentConfig['environment']),
};
```

---

## Appendix H: Git Workflow & Branching Strategy

### Branch Naming Convention

```
feature/[ticket-id]-[short-description]
bugfix/[ticket-id]-[short-description]
hotfix/[ticket-id]-[short-description]
release/[version]
```

### Examples
```
feature/PLR-123-prop-card-component
bugfix/PLR-456-chart-tooltip-fix
hotfix/PLR-789-api-timeout
release/1.0.0
```

### Git Workflow

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/PLR-123-prop-card-component

# 2. Make changes and commit
git add .
git commit -m "feat(prop-card): add confidence bar animation"

# 3. Push to remote
git push origin feature/PLR-123-prop-card-component

# 4. Create Pull Request on GitHub/GitLab

# 5. After approval, merge to main
# (Usually done via PR interface)

# 6. Delete feature branch
git branch -d feature/PLR-123-prop-card-component
git push origin --delete feature/PLR-123-prop-card-component
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(prop-card): add hover animation effects

fix(chart): resolve tooltip positioning on mobile

docs(readme): update installation instructions

refactor(utils): simplify confidence calculation logic

test(prop-card): add unit tests for trend indicator
```

---

## Appendix I: Code Quality Standards

### ESLint Configuration

```json
// .eslintrc.json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:jsx-a11y/recommended"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    }
  },
  "rules": {
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-unused-vars": ["error", { 
      "argsIgnorePattern": "^_" 
    }],
    "no-console": ["warn", { 
      "allow": ["warn", "error"] 
    }]
  },
  "settings": {
    "react": {
      "version": "detect"
    }
  }
}
```

### Prettier Configuration

```json
// .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "avoid",
  "endOfLine": "lf"
}
```

### TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@utils/*": ["./src/utils/*"],
      "@types/*": ["./src/types/*"],
      "@hooks/*": ["./src/hooks/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## Appendix J: Performance Optimization Checklist

### Bundle Size Optimization
- [ ] Use code splitting with React.lazy()
- [ ] Implement dynamic imports for heavy components
- [ ] Tree-shake unused dependencies
- [ ] Use production build for deployment
- [ ] Analyze bundle with `vite-bundle-visualizer`
- [ ] Lazy load charts below the fold

### Runtime Performance
- [ ] Memoize expensive calculations with useMemo
- [ ] Prevent unnecessary re-renders with React.memo
- [ ] Use useCallback for event handlers in lists
- [ ] Implement virtual scrolling for large tables
- [ ] Debounce/throttle frequent updates
- [ ] Optimize images (WebP format, lazy loading)

### Network Optimization
- [ ] Implement API response caching
- [ ] Use React Query for data fetching
- [ ] Compress API responses (gzip)
- [ ] Implement request deduplication
- [ ] Use CDN for static assets
- [ ] Enable HTTP/2

### Rendering Optimization
```typescript
// Example: Memoized component
export const PropCard = React.memo<PropCardProps>(
  ({ label, value, trend, trendText, confidence, recommendation }) => {
    // Component implementation
  },
  (prevProps, nextProps) => {
    // Custom comparison function
    return (
      prevProps.value === nextProps.value &&
      prevProps.confidence === nextProps.confidence &&
      prevProps.trend === nextProps.trend
    );
  }
);

// Example: Memoized calculation
const confidence = useMemo(
  () => calculateConfidence(recentGames, historicalData, splitData, propLine),
  [recentGames, historicalData, splitData, propLine]
);

// Example: Callback optimization
const handleRemoveLeg = useCallback(
  (legId: string) => {
    setParlayLegs(legs => legs.filter(leg => leg.id !== legId));
  },
  []
);
```

---

## Appendix K: Security Best Practices

### API Key Management
```typescript
// NEVER expose API keys in client-side code
// Use environment variables and server-side proxy

// ❌ BAD - API key in client code
const response = await fetch(`https://api.example.com/stats?apiKey=${API_KEY}`);

// ✅ GOOD - Proxy through your backend
const response = await fetch('/api/stats');

// Backend proxy (e.g., Next.js API route)
export default async function handler(req, res) {
  const response = await fetch(`https://api.example.com/stats`, {
    headers: {
      'Authorization': `Bearer ${process.env.API_KEY}`
    }
  });
  const data = await response.json();
  res.status(200).json(data);
}
```

### Input Validation
```typescript
// Validate and sanitize all user inputs
import { z } from 'zod';

const ParlayLegSchema = z.object({
  player: z.string().min(1).max(100),
  propType: z.enum(['points', 'assists', 'rebounds', 'threes', 'pra']),
  line: z.number().positive(),
  selection: z.enum(['over', 'under']),
  odds: z.string().regex(/^[+-]\d+$/),
});

// Use in component
try {
  const validatedLeg = ParlayLegSchema.parse(userInput);
  // Safe to use validatedLeg
} catch (error) {
  // Handle validation error
}
```

### XSS Prevention
```typescript
// React escapes by default, but be careful with:

// ❌ BAD - dangerouslySetInnerHTML
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// ✅ GOOD - Let React handle it
<div>{userContent}</div>

// If you must use HTML, sanitize it
import DOMPurify from 'dompurify';
const cleanHTML = DOMPurify.sanitize(dirtyHTML);
```

### Content Security Policy
```html
<!-- Add to index.html -->
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;
  style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com;
  img-src 'self' data: https:;
  connect-src 'self' https://api.example.com;
  font-src 'self' data:;
">
```

---

## Appendix L: Monitoring & Analytics Setup

### Error Tracking (Sentry)

```typescript
// src/main.tsx
import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";

Sentry.init({
  dsn: env.sentryDsn,
  integrations: [new BrowserTracing()],
  tracesSampleRate: 1.0,
  environment: env.environment,
});

// Wrap your app
ReactDOM.createRoot(document.getElementById('root')!).render(
  <Sentry.ErrorBoundary fallback={<ErrorFallback />}>
    <App />
  </Sentry.ErrorBoundary>
);
```

### Google Analytics 4

```typescript
// src/utils/analytics.ts
import ReactGA from 'react-ga4';

export const initGA = () => {
  ReactGA.initialize(env.gaTrackingId);
};

export const logPageView = (path: string) => {
  ReactGA.send({ hitType: "pageview", page: path });
};

export const logEvent = (category: string, action: string, label?: string) => {
  ReactGA.event({
    category,
    action,
    label,
  });
};

// Usage in components
logEvent('Parlay', 'Add Leg', 'Points Over 25.5');
logEvent('PropCard', 'View', 'LeBron Points');
```

### Performance Monitoring

```typescript
// src/utils/performance.ts
export const measureComponentRender = (componentName: string) => {
  return {
    start: () => performance.mark(`${componentName}-start`),
    end: () => {
      performance.mark(`${componentName}-end`);
      performance.measure(
        componentName,
        `${componentName}-start`,
        `${componentName}-end`
      );
      const measure = performance.getEntriesByName(componentName)[0];
      console.log(`${componentName} render time: ${measure.duration}ms`);
    },
  };
};

// Usage
const PropCard: React.FC<PropCardProps> = (props) => {
  useEffect(() => {
    const measure = measureComponentRender('PropCard');
    measure.start();
    return () => measure.end();
  }, []);
  
  // Component code...
};
```

---

## Appendix M: Deployment Checklist

### Pre-Deployment Checklist

- [ ] All tests passing (unit, integration, e2e)
- [ ] No console errors or warnings
- [ ] Lighthouse score > 90 (Performance, Accessibility, Best Practices, SEO)
- [ ] All environment variables configured for production
- [ ] API endpoints pointing to production
- [ ] Error tracking configured (Sentry)
- [ ] Analytics configured (GA4)
- [ ] Bundle size analyzed and optimized
- [ ] Security headers configured
- [ ] HTTPS enabled
- [ ] CDN configured for assets
- [ ] Database migrations complete (if applicable)
- [ ] Backup strategy in place
- [ ] Monitoring and alerting configured

### Deployment Commands

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview

# Run production tests
npm run test:prod

# Analyze bundle
npm run analyze

# Deploy to Vercel
vercel --prod

# Deploy to Netlify
netlify deploy --prod

# Deploy to AWS
aws s3 sync dist/ s3://your-bucket-name --delete
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### Post-Deployment Verification

- [ ] Site accessible at production URL
- [ ] All pages loading correctly
- [ ] API calls working
- [ ] Charts rendering properly
- [ ] Mobile responsiveness verified
- [ ] Analytics tracking events
- [ ] Error tracking functional
- [ ] Performance metrics acceptable
- [ ] No broken links
- [ ] Forms submitting correctly

---

## Appendix N: Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Charts Not Rendering

**Symptoms:**
- Empty space where chart should be
- Console error: "Cannot read property 'x' of undefined"

**Solutions:**
1. Check data format matches Recharts expectations
2. Ensure ResponsiveContainer has proper height
3. Verify data array is not empty
4. Check for null/undefined values in data

```typescript
// Add data validation
const validData = chartData.filter(item => 
  item.value !== null && item.value !== undefined
);

if (validData.length === 0) {
  return <EmptyState message="No data available" />;
}
```

#### Issue: Tailwind Classes Not Applied

**Symptoms:**
- Styles not showing up
- Components look unstyled

**Solutions:**
1. Verify Tailwind is properly installed
2. Check `tailwind.config.js` content paths
3. Ensure PostCSS is configured
4. Clear build cache and rebuild

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // ...
}
```

#### Issue: Slow Performance

**Symptoms:**
- Lag when scrolling
- Slow chart renders
- High CPU usage

**Solutions:**
1. Use React.memo on expensive components
2. Implement virtualization for large lists
3. Debounce rapid updates
4. Use production build
5. Check for memory leaks

```typescript
// Virtualize large table
import { useVirtual } from 'react-virtual';

const { virtualItems, totalSize } = useVirtual({
  size: data.length,
  parentRef: containerRef,
  estimateSize: () => 50,
});
```

#### Issue: API Timeout Errors

**Symptoms:**
- Requests failing after 30 seconds
- Timeout errors in console

**Solutions:**
1. Increase timeout limit
2. Implement retry logic
3. Add loading states
4. Cache responses

```typescript
const fetchWithRetry = async (url: string, retries = 3) => {
  try {
    const response = await fetch(url, { 
      signal: AbortSignal.timeout(10000) 
    });
    return response.json();
  } catch (error) {
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return fetchWithRetry(url, retries - 1);
    }
    throw error;
  }
};
```

#### Issue: TypeScript Errors After Update

**Symptoms:**
- Type errors that weren't there before
- "Cannot find module" errors

**Solutions:**
1. Delete node_modules and reinstall
2. Update type definitions
3. Clear TypeScript cache
4. Check tsconfig.json

```bash
rm -rf node_modules package-lock.json
npm install
npm run type-check
```

---

## Appendix O: Team Roles & Responsibilities

### Development Team Structure

| Role | Responsibilities | Skills Required |
|------|-----------------|-----------------|
| **Product Owner** | Define requirements, prioritize features, accept deliverables | Domain knowledge, user research |
| **Tech Lead** | Architecture decisions, code review, technical guidance | Senior React/TS, system design |
| **Frontend Developer 1** | Component development, UI implementation | React, TypeScript, Tailwind CSS |
| **Frontend Developer 2** | Data visualization, charts, animations | Recharts, D3.js, CSS animations |
| **Backend Developer** | API development, data processing | Node.js/Python, API design |
| **QA Engineer** | Test planning, manual/automated testing | Jest, Cypress, testing strategies |
| **UI/UX Designer** | Interface design, user flows, prototypes | Figma, design systems |
| **DevOps Engineer** | CI/CD, deployment, monitoring | AWS/Vercel, GitHub Actions |

### Communication Plan

**Daily Standup** (15 min)
- What did you do yesterday?
- What will you do today?
- Any blockers?

**Sprint Planning** (2 hours, bi-weekly)
- Review backlog
- Estimate stories
- Commit to sprint goals

**Sprint Review** (1 hour, bi-weekly)
- Demo completed features
- Gather feedback
- Update roadmap

**Retrospective** (1 hour, bi-weekly)
- What went well?
- What could improve?
- Action items

---

## Appendix P: Final Checklist for Cursor/AI Integration

### Cursor-Specific Instructions

When providing this spec to Cursor, include these additional instructions:

```markdown
## Instructions for Cursor AI

### Build Order (Follow Strictly):

1. **Setup Phase**
   ```bash
   npm create vite@latest nba-player-profile -- --template react-ts
   cd nba-player-profile
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   npm install recharts
   ```

2. **Type Definitions First**
   - Create `src/types/index.ts`
   - Define ALL interfaces from Section 4
   - Do NOT proceed until types are complete

3. **Utility Functions**
   - Create `src/utils/calculations.ts`
   - Implement confidence calculations
   - Implement odds converters
   - Add unit tests

4. **Mock Data**
   - Create `src/data/mock.ts`
   - Use examples from Appendix A
   - Ensure data matches type definitions

5. **Components (Build in This Order)**
   - PropCard (simplest, most reusable)
   - PlayerProfileHeader
   - MatchupCard
   - SplitsTable
   - TrendChart
   - OddsCard
   - ParlayBuilder
   - BettingRecommendation

6. **Assembly**
   - Create main App.tsx
   - Import all components
   - Use mock data
   - Test in browser

### Critical Rules:

1. **Use ONLY Tailwind classes** - No custom CSS files
2. **Follow exact spacing** - Use `p-6`, `gap-6`, `mb-10` from spec
3. **Use exact colors** - Reference Appendix D color palette
4. **Type everything** - Every prop, every function
5. **Test as you go** - Build one component, test it, then move on

### Common Pitfalls to Avoid:

❌ Don't create custom CSS files
❌ Don't skip TypeScript types
❌ Don't build everything at once
❌ Don't ignore responsive breakpoints
❌ Don't forget accessibility attributes

✅ Do use Tailwind utilities
✅ Do follow type definitions exactly
✅ Do build incrementally
✅ Do test on mobile
✅ Do add ARIA labels

### Verification Steps:

After each component:
1. Does it render without errors?
2. Does TypeScript show no errors?
3. Does it match the design in Section 6?
4. Is it responsive at all breakpoints?
5. Does it have proper accessibility?

If any answer is NO, fix before proceeding.
```

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-05 | AI | Initial complete document |
| 1.1 | 2025-11-05 | AI | Added Appendices C-P for comprehensive coverage |

---

## Final Notes

This technical specification provides everything needed to build the NBA Player Profile Interface. It includes:

✅ Complete component hierarchy
✅ All type definitions
✅ Calculation algorithms
✅ UI/UX specifications
✅ Implementation phases
✅ Code examples
✅ Testing strategies
✅ Deployment guides
✅ Troubleshooting
✅ Cursor-specific instructions

**For Developers:**
Read this document top to bottom before writing any code. Reference specific sections as needed during implementation.

**For Cursor AI:**
Follow the build order in Appendix P exactly. Do not deviate from the type definitions. Test each component before moving to the next.

**For Product Owners:**
Use Section 2 (User Stories) and Section 7 (Feature Requirements) to verify deliverables match requirements.

---

**END OF DOCUMENT**

---

*This document is version-controlled. For updates or clarifications, contact the tech lead.*

*Last Updated: November 5, 2025*
*Document ID: NBA-PLR-TECHSPEC-001*
*Classification: Internal Use*