# Swagger/OpenAPI Documentation Guide

## Overview

The NBA Stat Spot API now includes comprehensive Swagger/OpenAPI documentation that makes it easy for developers to understand and integrate with the API.

## Accessing the Documentation

### Interactive Swagger UI

Once the API server is running, you can access the interactive Swagger documentation at:

**Local Development:**
```
http://localhost:8000/docs
```

**Production:**
```
https://nba-stat-spot-ai.fly.dev/docs
```

The Swagger UI provides:
- Interactive API explorer
- Try-it-out functionality to test endpoints directly
- Request/response examples
- Schema definitions
- Authentication information (if applicable)

### OpenAPI JSON Schema

You can also access the raw OpenAPI JSON schema at:

**Local Development:**
```
http://localhost:8000/openapi.json
```

**Production:**
```
https://nba-stat-spot-ai.fly.dev/openapi.json
```

This JSON can be imported into:
- Postman
- Insomnia
- API clients
- Code generators
- Documentation tools

### Alternative Documentation (ReDoc)

FastAPI also provides an alternative documentation interface using ReDoc:

**Local Development:**
```
http://localhost:8000/redoc
```

**Production:**
```
https://nba-stat-spot-ai.fly.dev/redoc
```

ReDoc provides a clean, readable documentation format that some developers prefer.

## Documentation Features

### Comprehensive API Information

The documentation includes:

1. **API Overview**
   - Description of the API and its capabilities
   - Key features and use cases
   - Rate limiting information
   - Data sources

2. **Endpoint Documentation**
   - Summary and detailed descriptions
   - Request parameters with types and examples
   - Response models with field descriptions
   - Error responses
   - Rate limits per endpoint

3. **Data Models**
   - Pydantic models for all request/response types
   - Field descriptions and examples
   - Validation rules
   - Type information

4. **Tagged Endpoints**
   - Endpoints organized by category:
     - `props_v1`: Player prop bet analysis
     - `players_v1`: Player information and statistics
     - `teams_v1`: Team information and rosters
     - `games_v1`: Game schedules and information
     - `games_enhanced_v1`: Enhanced game data
     - `espn_v1`: ESPN integration endpoints
     - `over_under_v1`: Over/under game analysis
     - `bets_v1`: Bet tracking and management
     - `parlays_v1`: Parlay bet builder
     - `admin_v1`: Administrative endpoints

## Using the Documentation

### For API Consumers

1. **Explore Endpoints**: Browse all available endpoints organized by category
2. **View Examples**: See example requests and responses for each endpoint
3. **Test Endpoints**: Use the "Try it out" feature to make actual API calls
4. **Understand Models**: Review request/response schemas to understand data structures
5. **Check Rate Limits**: See rate limiting information for each endpoint

### For Developers Building on the API

1. **Import OpenAPI Schema**: Download the `openapi.json` file to generate client libraries
2. **Code Generation**: Use tools like:
   - [OpenAPI Generator](https://openapi-generator.tech/)
   - [Swagger Codegen](https://swagger.io/tools/swagger-codegen/)
   - Language-specific generators (e.g., `openapi-typescript-codegen` for TypeScript)

3. **API Testing**: Import the schema into Postman or Insomnia for API testing

4. **Documentation Integration**: Embed the Swagger UI in your own documentation

## Example: Generating a TypeScript Client

```bash
# Install openapi-typescript-codegen
npm install -g openapi-typescript-codegen

# Generate TypeScript client
openapi-typescript-codegen \
  --input http://localhost:8000/openapi.json \
  --output ./generated-client \
  --client axios
```

## Example: Importing into Postman

1. Open Postman
2. Click "Import"
3. Select "Link" tab
4. Enter: `http://localhost:8000/openapi.json`
5. Click "Continue" and "Import"

All endpoints will be imported with example requests ready to use.

## Key Endpoints to Start With

### 1. Get Daily Props
```
GET /api/v1/props/daily
```
Get top prop suggestions for today's games.

### 2. Search Players
```
GET /api/v1/players/search?q=LeBron
```
Search for players by name.

### 3. Get Player Prop Suggestions
```
POST /api/v1/props/player
```
Get AI-powered prop analysis for a specific player.

### 4. Track a Bet
```
POST /api/v1/bets
```
Record a bet in the system.

## Tips for Using the Documentation

1. **Start with Examples**: Each endpoint includes example requests - use these as starting points
2. **Check Required Fields**: Required parameters are marked with asterisks (*)
3. **Review Response Models**: Understand what data you'll receive before making requests
4. **Test in Swagger UI**: Use the "Try it out" feature to test endpoints without writing code
5. **Check Rate Limits**: Be aware of rate limits to avoid hitting them

## Updating the Documentation

The documentation is automatically generated from:
- FastAPI route decorators (`@router.get`, `@router.post`, etc.)
- Pydantic models for request/response validation
- Docstrings and descriptions in the code

To update documentation:
1. Modify endpoint descriptions in router files
2. Update Pydantic model field descriptions
3. Add examples to request/response models
4. The documentation will automatically update when the server restarts

## Support

For questions or issues with the API documentation:
- Check the main API documentation in `/docs/api-contracts.md`
- Review the endpoint descriptions in Swagger UI
- Check the project README for setup instructions

