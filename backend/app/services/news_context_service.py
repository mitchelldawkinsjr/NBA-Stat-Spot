"""
News Context Service - Extracts relevant news and transaction context
"""
from __future__ import annotations
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import structlog
import xml.etree.ElementTree as ET
import httpx
from .espn_api_service import get_espn_service
from .espn_mapping_service import get_espn_mapping_service
from .team_player_service import TeamPlayerService
from .cache_service import get_cache_service

logger = structlog.get_logger()


class NewsContextService:
    """Service to extract news and transaction context"""
    
    def __init__(self):
        self.espn_service = get_espn_service()
        self.mapping_service = get_espn_mapping_service()
        self.cache = get_cache_service()
        self.yahoo_rss_url = "https://sports.yahoo.com/nba/rss/"
    
    def get_player_news_context(self, player_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get recent news context for a player.
        
        Args:
            player_id: Player ID
            days: Number of days to look back
            
        Returns:
            Dictionary with news context:
            - has_recent_news: bool
            - news_sentiment: float (-1 to 1)
            - news_count: int
            - latest_news_date: Optional[date]
        """
        try:
            cache_key = f"player_news:{player_id}:{days}:15m"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Get player info
            from .nba_api_service import NBADataService
            all_players = NBADataService.fetch_all_players_including_rookies()
            player = next((p for p in all_players if p.get("id") == player_id), None)
            if not player:
                return self._get_default_news_context()
            
            player_name = player.get("full_name", "")
            
            # Fetch news from multiple sources
            articles = []
            
            # Fetch from ESPN
            news_data = self.espn_service.get_news()
            if news_data:
                espn_articles = news_data.get("articles", [])
                articles.extend(espn_articles)
            
            # Fetch from Yahoo Sports RSS
            yahoo_articles = self._fetch_yahoo_rss_news()
            articles.extend(yahoo_articles)
            
            if not articles:
                return self._get_default_news_context()
            
            # Filter articles by player name and date
            cutoff_date = datetime.now() - timedelta(days=days)
            relevant_articles = []
            
            for article in articles:
                # Check date
                published = article.get("published", "")
                if published:
                    try:
                        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        if pub_date < cutoff_date:
                            continue
                    except Exception:
                        pass
                
                # Check if article mentions player
                headline = article.get("headline", "").lower()
                description = article.get("description", "").lower()
                player_name_lower = player_name.lower()
                
                # Simple keyword matching
                if player_name_lower in headline or player_name_lower in description:
                    relevant_articles.append(article)
            
            # Calculate sentiment (simplified - positive/negative keywords)
            sentiment = self._calculate_sentiment(relevant_articles)
            
            # Get latest news date
            latest_date = None
            if relevant_articles:
                dates = []
                for article in relevant_articles:
                    published = article.get("published", "")
                    if published:
                        try:
                            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                            dates.append(pub_date.date())
                        except Exception:
                            pass
                if dates:
                    latest_date = max(dates)
            
            result = {
                "has_recent_news": len(relevant_articles) > 0,
                "news_sentiment": sentiment,
                "news_count": len(relevant_articles),
                "latest_news_date": latest_date
            }
            
            self.cache.set(cache_key, result, ttl=900)  # 15 minutes
            return result
            
        except Exception as e:
            logger.warning("Error fetching player news context", player_id=player_id, error=str(e))
            return self._get_default_news_context()
    
    def get_team_news_context(self, team_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Get recent news context for a team.
        
        Args:
            team_id: Team ID
            days: Number of days to look back
            
        Returns:
            Dictionary with news context
        """
        try:
            cache_key = f"team_news:{team_id}:{days}:15m"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Get ESPN team slug
            espn_slug = self.mapping_service.get_espn_team_slug(team_id)
            if not espn_slug:
                return self._get_default_news_context()
            
            # Get team name
            from .nba_api_service import NBADataService
            teams = NBADataService.fetch_all_teams()
            team = next((t for t in teams if t.get("id") == team_id), None)
            if not team:
                return self._get_default_news_context()
            
            team_name = team.get("full_name", "")
            team_city = team.get("city", "")
            
            # Fetch news from multiple sources
            articles = []
            
            # Fetch from ESPN
            news_data = self.espn_service.get_news()
            if news_data:
                espn_articles = news_data.get("articles", [])
                articles.extend(espn_articles)
            
            # Fetch from Yahoo Sports RSS
            yahoo_articles = self._fetch_yahoo_rss_news()
            articles.extend(yahoo_articles)
            
            if not articles:
                return self._get_default_news_context()
            
            # Filter articles by team name and date
            cutoff_date = datetime.now() - timedelta(days=days)
            relevant_articles = []
            
            for article in articles:
                # Check date
                published = article.get("published", "")
                if published:
                    try:
                        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        if pub_date < cutoff_date:
                            continue
                    except Exception:
                        pass
                
                # Check if article mentions team
                headline = article.get("headline", "").lower()
                description = article.get("description", "").lower()
                team_name_lower = team_name.lower()
                team_city_lower = team_city.lower()
                
                if team_name_lower in headline or team_name_lower in description or \
                   team_city_lower in headline or team_city_lower in description:
                    relevant_articles.append(article)
            
            # Calculate sentiment
            sentiment = self._calculate_sentiment(relevant_articles)
            
            # Check for transactions
            has_transaction = self._check_recent_transactions(team_id, days)
            
            result = {
                "has_recent_news": len(relevant_articles) > 0,
                "news_sentiment": sentiment,
                "news_count": len(relevant_articles),
                "has_recent_transaction": has_transaction,
                "team_momentum_score": self._calculate_momentum_score(relevant_articles)
            }
            
            self.cache.set(cache_key, result, ttl=900)  # 15 minutes
            return result
            
        except Exception as e:
            logger.warning("Error fetching team news context", team_id=team_id, error=str(e))
            return self._get_default_news_context()
    
    def _calculate_sentiment(self, articles: List[Dict[str, Any]]) -> float:
        """
        Calculate sentiment score from articles (-1 to 1).
        Simplified keyword-based approach.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Sentiment score (-1.0 to 1.0)
        """
        if not articles:
            return 0.0
        
        positive_keywords = [
            "win", "wins", "winning", "victory", "success", "great", "excellent",
            "outstanding", "amazing", "strong", "improved", "better", "hot streak",
            "dominating", "leading", "top", "best", "record", "breakthrough"
        ]
        
        negative_keywords = [
            "loss", "loses", "losing", "defeat", "struggle", "poor", "bad",
            "worst", "weak", "declined", "worse", "cold streak", "slump",
            "injury", "injured", "suspended", "trouble", "problem", "concern"
        ]
        
        positive_count = 0
        negative_count = 0
        
        for article in articles:
            text = (article.get("headline", "") + " " + article.get("description", "")).lower()
            
            for keyword in positive_keywords:
                if keyword in text:
                    positive_count += 1
            
            for keyword in negative_keywords:
                if keyword in text:
                    negative_count += 1
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        # Normalize to -1 to 1
        sentiment = (positive_count - negative_count) / max(total, 1)
        return max(-1.0, min(1.0, sentiment))
    
    def _check_recent_transactions(self, team_id: int, days: int) -> bool:
        """
        Check if team has recent transactions.
        
        Args:
            team_id: Team ID
            days: Number of days to look back
            
        Returns:
            True if recent transaction found
        """
        try:
            transactions = self.espn_service.get_transactions()
            if not transactions:
                return False
            
            # Get team name
            from .nba_api_service import NBADataService
            teams = NBADataService.fetch_all_teams()
            team = next((t for t in teams if t.get("id") == team_id), None)
            if not team:
                return False
            
            team_name = team.get("full_name", "")
            team_city = team.get("city", "")
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for transaction in transactions:
                # Check date
                date_str = transaction.get("date", "")
                if date_str:
                    try:
                        trans_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if trans_date < cutoff_date:
                            continue
                    except Exception:
                        pass
                
                # Check if transaction involves team
                text = (transaction.get("headline", "") + " " + transaction.get("description", "")).lower()
                if team_name.lower() in text or team_city.lower() in text:
                    return True
            
            return False
        except Exception as e:
            logger.warning("Error checking transactions", team_id=team_id, error=str(e))
            return False
    
    def _calculate_momentum_score(self, articles: List[Dict[str, Any]]) -> float:
        """
        Calculate team momentum score from news (0 to 1).
        Based on winning streaks, positive news, etc.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Momentum score (0.0 to 1.0)
        """
        if not articles:
            return 0.5  # Neutral
        
        momentum_keywords = [
            "streak", "winning streak", "hot", "momentum", "rolling",
            "dominating", "unbeaten", "undefeated", "surge"
        ]
        
        negative_keywords = [
            "losing streak", "cold", "struggling", "slump", "decline"
        ]
        
        momentum_count = 0
        negative_count = 0
        
        for article in articles:
            text = (article.get("headline", "") + " " + article.get("description", "")).lower()
            
            for keyword in momentum_keywords:
                if keyword in text:
                    momentum_count += 1
            
            for keyword in negative_keywords:
                if keyword in text:
                    negative_count += 1
        
        if momentum_count > negative_count:
            return min(1.0, 0.5 + (momentum_count * 0.1))
        elif negative_count > momentum_count:
            return max(0.0, 0.5 - (negative_count * 0.1))
        else:
            return 0.5
    
    def _fetch_yahoo_rss_news(self) -> List[Dict[str, Any]]:
        """
        Fetch and parse Yahoo Sports NBA RSS feed.
        
        Returns:
            List of article dictionaries in the same format as ESPN articles
        """
        try:
            cache_key = "yahoo_rss_news:15m"
            cached_articles = self.cache.get(cache_key)
            if cached_articles is not None:
                return cached_articles
            
            # Fetch RSS feed
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.yahoo_rss_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()
                xml_content = response.text
            
            # Parse RSS XML
            root = ET.fromstring(xml_content)
            
            # RSS namespaces
            ns = {
                'content': 'http://purl.org/rss/1.0/modules/content/',
                'dc': 'http://purl.org/dc/elements/1.1/'
            }
            
            articles = []
            
            # Find all item elements
            for item in root.findall('.//item'):
                try:
                    title_elem = item.find('title')
                    link_elem = item.find('link')
                    description_elem = item.find('description')
                    pub_date_elem = item.find('pubDate')
                    content_elem = item.find('content:encoded', ns)
                    
                    if not title_elem or not link_elem:
                        continue
                    
                    # Extract title (handle CDATA)
                    title = (title_elem.text or '').strip()
                    if title.startswith('<![CDATA[') and title.endswith(']]>'):
                        title = title[9:-3].strip()
                    
                    # Extract link
                    link = (link_elem.text or '').strip()
                    
                    # Extract description (handle CDATA)
                    description = ''
                    if description_elem is not None:
                        description = description_elem.text or ''
                        if description.startswith('<![CDATA[') and description.endswith(']]>'):
                            description = description[9:-3].strip()
                    
                    # Try to get full content from content:encoded if available
                    if content_elem is not None and content_elem.text:
                        content_text = content_elem.text
                        if content_text.startswith('<![CDATA[') and content_text.endswith(']]>'):
                            content_text = content_text[9:-3].strip()
                        # Use content if description is empty or short
                        if not description or len(description) < 50:
                            description = content_text
                    
                    # Clean up HTML tags from description
                    import re
                    description = re.sub(r'<[^>]+>', '', description).strip()
                    # Remove extra whitespace
                    description = ' '.join(description.split())
                    
                    # Parse publication date
                    published = None
                    if pub_date_elem is not None and pub_date_elem.text:
                        try:
                            # Parse RFC 822 date format (e.g., "Wed, 12 Nov 2025 00:55:19 +0000")
                            from email.utils import parsedate_to_datetime
                            published = parsedate_to_datetime(pub_date_elem.text).isoformat()
                        except Exception:
                            # Fallback to current time if parsing fails
                            published = datetime.now().isoformat()
                    else:
                        published = datetime.now().isoformat()
                    
                    article = {
                        "headline": title,
                        "description": description[:500] if description else "",  # Limit description length
                        "link": link,
                        "published": published,
                        "source": "Yahoo Sports"
                    }
                    
                    articles.append(article)
                except Exception as e:
                    logger.debug("Error parsing RSS item", error=str(e))
                    continue
            
            # Cache for 15 minutes
            self.cache.set(cache_key, articles, ttl=900)
            logger.info("Fetched Yahoo RSS news", article_count=len(articles))
            return articles
            
        except Exception as e:
            logger.warning("Error fetching Yahoo RSS news", error=str(e))
            return []
    
    def _get_default_news_context(self) -> Dict[str, Any]:
        """Return default news context"""
        return {
            "has_recent_news": False,
            "news_sentiment": 0.0,
            "news_count": 0,
            "latest_news_date": None,
            "has_recent_transaction": False,
            "team_momentum_score": 0.5
        }


# Global service instance
_news_service: Optional[NewsContextService] = None


def get_news_context_service() -> NewsContextService:
    """Get or create the global news context service instance"""
    global _news_service
    if _news_service is None:
        _news_service = NewsContextService()
    return _news_service

