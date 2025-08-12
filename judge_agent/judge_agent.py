import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import httpx
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

@dataclass
class ComparisonResult:
    anomalies: List[str]
    similarities: List[str] = None
    confidence_score: float = 0.0
    detailed_analysis: str = ""
    authenticity_score: Optional[float] = None
    data_integration_score: Optional[float] = None
    personalization_evidence: Optional[List[str]] = None
    generic_indicators: Optional[List[str]] = None
    key_inconsistencies: Optional[List[str]] = None
    overall_assessment: Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None
    quality_score: Optional[float] = None
    external_market_data: Optional[Dict[str, Any]] = None

class LLMJudge:
    """Enhanced judge with external market intelligence and Mistral API"""
    
    def __init__(self, mistral_key: str = None):
        self.mistral_key = mistral_key or os.getenv("MISTRAL_API_KEY")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.fmp_key = os.getenv("FMP_API_KEY")
        
        # Porter's Five Forces framework for strategic analysis
        self.porter_framework = {
            "competitive_rivalry": ["market_concentration", "industry_growth", "switching_costs"],
            "supplier_power": ["supplier_concentration", "switching_costs", "substitute_inputs"],
            "buyer_power": ["buyer_concentration", "price_sensitivity", "switching_costs"],
            "threat_of_substitutes": ["substitute_performance", "switching_costs", "buyer_propensity"],
            "threat_of_new_entrants": ["barriers_to_entry", "capital_requirements", "economies_of_scale"]
        }
    
    async def get_external_market_intelligence(self, company_symbol: str = None, industry: str = None) -> Dict[str, Any]:
        """Fetch external market intelligence using MCP-style data integration"""
        
        if not company_symbol and not industry:
            return {"error": "No company symbol or industry provided for market analysis"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                market_data = {}
                
                # Alpha Vantage - Market sentiment and news analysis
                if self.alpha_vantage_key and company_symbol:
                    sentiment_data = await self._get_market_sentiment(client, company_symbol)
                    market_data["sentiment_analysis"] = sentiment_data
                
                # Financial Modeling Prep - Competitive analysis
                if self.fmp_key and company_symbol:
                    competitive_data = await self._get_competitive_intelligence(client, company_symbol)
                    market_data["competitive_intelligence"] = competitive_data
                
                # Apply Porter's Five Forces framework
                if market_data:
                    porter_analysis = self._apply_porter_framework(market_data)
                    market_data["porter_five_forces"] = porter_analysis
                
                return market_data
                
        except Exception as e:
            return {"error": f"Failed to fetch market intelligence: {str(e)}"}
    
    async def _get_market_sentiment(self, client: httpx.AsyncClient, symbol: str) -> Dict[str, Any]:
        """Get market sentiment from Alpha Vantage"""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": symbol,
                "apikey": self.alpha_vantage_key,
                "limit": 20
            }
            
            response = await client.get(url, params=params)
            data = response.json()
            
            if "feed" in data:
                sentiment_scores = []
                competitive_mentions = 0
                
                for article in data["feed"][:10]:
                    if "ticker_sentiment" in article:
                        for ticker_data in article["ticker_sentiment"]:
                            if ticker_data["ticker"] == symbol:
                                sentiment_scores.append(float(ticker_data["ticker_sentiment_score"]))
                    
                    # Check for competitive keywords
                    title_lower = article.get("title", "").lower()
                    if any(word in title_lower for word in ["competition", "rival", "market share"]):
                        competitive_mentions += 1
                
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
                
                return {
                    "average_sentiment": avg_sentiment,
                    "competitive_mentions": competitive_mentions,
                    "sentiment_trend": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
                    "market_attention": len(data["feed"])
                }
            
            return {"error": "No sentiment data available"}
            
        except Exception as e:
            return {"error": f"Sentiment analysis failed: {str(e)}"}
    
    async def _get_competitive_intelligence(self, client: httpx.AsyncClient, symbol: str) -> Dict[str, Any]:
        """Get competitive intelligence from FMP"""
        try:
            # Get company profile
            profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}"
            params = {"apikey": self.fmp_key}
            
            response = await client.get(profile_url, params=params)
            profile_data = response.json()
            
            if profile_data and len(profile_data) > 0:
                company_info = profile_data[0]
                
                return {
                    "industry": company_info.get("industry", "Unknown"),
                    "sector": company_info.get("sector", "Unknown"),
                    "market_cap": company_info.get("mktCap", 0),
                    "competitive_position": self._assess_competitive_position(company_info),
                    "financial_strength": {
                        "beta": company_info.get("beta", 1.0),
                        "pe_ratio": company_info.get("pe", 0),
                        "profit_margin": company_info.get("profitMargin", 0)
                    }
                }
            
            return {"error": "No competitive data available"}
            
        except Exception as e:
            return {"error": f"Competitive analysis failed: {str(e)}"}
    
    def _assess_competitive_position(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess competitive position based on company metrics"""
        market_cap = float(company_data.get("mktCap", 0))
        
        if market_cap > 100_000_000_000:  # >100B
            position = "Market Leader"
            strength = "High"
        elif market_cap > 10_000_000_000:  # >10B
            position = "Major Player"
            strength = "Medium-High"
        elif market_cap > 1_000_000_000:  # >1B
            position = "Established Competitor"
            strength = "Medium"
        else:
            position = "Niche Player"
            strength = "Low-Medium"
        
        return {
            "position": position,
            "strength": strength,
            "market_cap_category": self._categorize_market_cap(market_cap)
        }
    
    def _categorize_market_cap(self, market_cap: float) -> str:
        """Categorize company by market cap"""
        if market_cap > 200_000_000_000:
            return "Mega Cap"
        elif market_cap > 10_000_000_000:
            return "Large Cap"
        elif market_cap > 2_000_000_000:
            return "Mid Cap"
        elif market_cap > 300_000_000:
            return "Small Cap"
        else:
            return "Micro Cap"
    
    def _apply_porter_framework(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Porter's Five Forces framework to market data"""
        sentiment = market_data.get("sentiment_analysis", {})
        competitive = market_data.get("competitive_intelligence", {})
        
        # Assess each force based on available data
        forces_analysis = {}
        
        # Competitive Rivalry
        competitive_mentions = sentiment.get("competitive_mentions", 0)
        if competitive_mentions > 5:
            forces_analysis["competitive_rivalry"] = {"intensity": "High", "score": 4}
        elif competitive_mentions > 2:
            forces_analysis["competitive_rivalry"] = {"intensity": "Medium", "score": 3}
        else:
            forces_analysis["competitive_rivalry"] = {"intensity": "Low", "score": 2}
        
        # Supplier Power (inferred from profit margins)
        profit_margin = competitive.get("financial_strength", {}).get("profit_margin", 0)
        if profit_margin > 0.2:
            forces_analysis["supplier_power"] = {"power": "Low", "score": 2}
        elif profit_margin > 0.1:
            forces_analysis["supplier_power"] = {"power": "Medium", "score": 3}
        else:
            forces_analysis["supplier_power"] = {"power": "High", "score": 4}
        
        # Calculate overall industry attractiveness
        total_score = sum(force.get("score", 3) for force in forces_analysis.values())
        avg_score = total_score / len(forces_analysis) if forces_analysis else 3
        
        forces_analysis["overall_attractiveness"] = {
            "score": avg_score,
            "attractiveness": "High" if avg_score <= 2.5 else "Medium" if avg_score <= 3.5 else "Low"
        }
        
        return forces_analysis
    
    def analyze_report_with_feedback(self, report_data: str, comparison_data: str, 
                                   iteration: int = 1, improvement_history: List[dict] = None) -> ComparisonResult:
        """Enhanced analysis with external market intelligence using Mistral API"""
        
        if not self.mistral_key:
            return ComparisonResult(
                anomalies=["Mistral API key not provided"],
                similarities=[],
                confidence_score=0.0,
                detailed_analysis="Cannot perform analysis without Mistral API key"
            )
        
        if not REQUESTS_AVAILABLE:
            return ComparisonResult(
                anomalies=["Requests library not installed. Run: pip install requests"],
                similarities=[],
                confidence_score=0.0,
                detailed_analysis="Requests library is required for Mistral API calls"
            )
        
        try:
            external_data = {}
            try:
                # Try to extract company symbol from report for market analysis
                company_symbol = self._extract_company_symbol(report_data)
                if company_symbol:
                    external_data = asyncio.run(self.get_external_market_intelligence(company_symbol))
            except Exception as e:
                external_data = {"error": f"External data fetch failed: {str(e)}"}
            
            iteration_context = ""
            if improvement_history:
                iteration_context = f"Previous iterations: {len(improvement_history)} completed"
            
            external_context = ""
            if external_data and "error" not in external_data:
                external_context = f"""
                EXTERNAL MARKET INTELLIGENCE:
                {json.dumps(external_data, indent=2)[:1000]}...
                
                Use this real-time market data to validate the report's strategic analysis.
                """
            
            prompt = f"""
            You are an expert business analyst with access to real-time market intelligence.
            Provide feedback to improve this strategic report. This is iteration {iteration}. {iteration_context}
            
            REPORT TO ANALYZE:
            {report_data[:2500]}...
            
            SOURCE DATA:
            {comparison_data[:2000]}...
            
            {external_context}
            
            Apply Porter's Five Forces framework and validate against external market data.
            Provide feedback in this JSON format:
            {{
                "quality_score": 0.75,
                "authenticity_score": 0.80,
                "data_integration_score": 0.70,
                "improvement_suggestions": [
                    "Specific actionable suggestion based on market intelligence",
                    "Strategic recommendation using Porter's framework"
                ],
                "personalization_evidence": ["Evidence of good market-specific customization"],
                "generic_indicators": ["Signs of generic content not validated by market data"],
                "key_inconsistencies": ["Data inconsistencies vs external market intelligence"],
                "anomalies": ["Issues requiring attention based on market analysis"],
                "similarities": ["Positive aspects validated by external data"],
                "overall_assessment": "Strategic assessment with market validation",
                "confidence_score": 0.85,
                "detailed_analysis": "Detailed feedback incorporating market intelligence"
            }}
            
            Focus on strategic insights validated by external market intelligence.
            """
            
            headers = {
                "Authorization": f"Bearer {self.mistral_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "mistral-large-latest",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 2500
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                return ComparisonResult(
                    anomalies=[f"Mistral API error: {response.status_code} - {response.text}"],
                    similarities=[],
                    confidence_score=0.0,
                    detailed_analysis="Failed to get response from Mistral API"
                )
            
            response_data = response.json()
            response_content = response_data["choices"][0]["message"]["content"]
            
            try:
                parsed_response = json.loads(response_content)
                
                result = ComparisonResult(
                    anomalies=parsed_response.get("anomalies", []),
                    similarities=parsed_response.get("similarities", []),
                    confidence_score=parsed_response.get("confidence_score", 0.7),
                    detailed_analysis=parsed_response.get("detailed_analysis", response_content),
                    authenticity_score=parsed_response.get("authenticity_score"),
                    data_integration_score=parsed_response.get("data_integration_score"),
                    personalization_evidence=parsed_response.get("personalization_evidence", []),
                    generic_indicators=parsed_response.get("generic_indicators", []),
                    key_inconsistencies=parsed_response.get("key_inconsistencies", []),
                    overall_assessment=parsed_response.get("overall_assessment", "Analysis completed"),
                    improvement_suggestions=parsed_response.get("improvement_suggestions", []),
                    quality_score=parsed_response.get("quality_score", 0.5),
                    external_market_data=external_data if "error" not in external_data else None
                )
                
                return result
                
            except json.JSONDecodeError:
                return ComparisonResult(
                    anomalies=["Failed to parse JSON response"],
                    similarities=[],
                    confidence_score=0.5,
                    detailed_analysis=response_content,
                    quality_score=0.5,
                    external_market_data=external_data if "error" not in external_data else None
                )
                
        except Exception as e:
            return ComparisonResult(
                anomalies=[f"Analysis error: {str(e)}"],
                similarities=[],
                confidence_score=0.0,
                detailed_analysis=f"Failed to analyze report: {str(e)}"
            )
    
    def _extract_company_symbol(self, report_data: str) -> Optional[str]:
        """Extract company symbol from report for market analysis"""
        # Simple extraction - look for common stock symbols patterns
        import re
        
        # Look for patterns like "AAPL", "MSFT", etc.
        symbol_pattern = r'\b[A-Z]{2,5}\b'
        matches = re.findall(symbol_pattern, report_data[:500])  # Check first 500 chars
        
        # Filter out common words that might match the pattern
        common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "HAD", "BUT", "WHAT", "WERE", "THEY", "WE", "BEEN", "HAVE", "THEIR", "SAID", "EACH", "WHICH", "SHE", "DO", "HOW", "WILL", "UP", "OTHER", "ABOUT", "OUT", "MANY", "THEN", "THEM", "THESE", "SO", "SOME", "HER", "WOULD", "MAKE", "LIKE", "INTO", "HIM", "HAS", "TWO", "MORE", "GO", "NO", "WAY", "COULD", "MY", "THAN", "FIRST", "BEEN", "CALL", "WHO", "OIL", "ITS", "NOW", "FIND", "LONG", "DOWN", "DAY", "DID", "GET", "COME", "MADE", "MAY", "PART"}
        
        valid_symbols = [match for match in matches if match not in common_words and len(match) <= 5]
        
        return valid_symbols[0] if valid_symbols else None
