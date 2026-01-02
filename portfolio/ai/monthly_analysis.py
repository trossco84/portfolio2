"""Monthly deep-dive portfolio analysis with news and market context."""

from typing import Optional
from anthropic import Anthropic

from portfolio.config import settings
from portfolio.utils.logging import logger


class MonthlyAnalyzer:
    """Generate comprehensive monthly portfolio analysis."""

    def __init__(self):
        """Initialize the analyzer."""
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    def analyze_with_news(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict,
        news_data: dict[str, list[dict]],
        sentiment_data: dict[str, dict],
        recommended_trades: Optional[list[dict]] = None
    ) -> str:
        """
        Generate comprehensive monthly analysis with news context.

        Args:
            portfolio_data: Portfolio summary (NAV, cash, etc.)
            positions: List of current positions
            metrics: Risk metrics
            news_data: News articles by ticker
            sentiment_data: Analyst sentiment by ticker
            recommended_trades: Optional list of recommended trades

        Returns:
            Detailed monthly analysis report
        """
        if not self.client:
            logger.warning("No Anthropic API key - using fallback analysis")
            return self._fallback_monthly_analysis(portfolio_data, positions, metrics)

        try:
            prompt = self._build_monthly_prompt(
                portfolio_data, positions, metrics, news_data, sentiment_data, recommended_trades
            )

            response = self.client.messages.create(
                model="claude-3-7-sonnet-20250219",  # Latest Sonnet
                max_tokens=3000,  # Longer for monthly deep-dive
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis = response.content[0].text
            logger.info("Monthly AI analysis generated successfully")
            return analysis

        except Exception as e:
            logger.error(f"Monthly AI analysis failed: {e}")
            return self._fallback_monthly_analysis(portfolio_data, positions, metrics)

    def _build_monthly_prompt(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict,
        news_data: dict,
        sentiment_data: dict,
        recommended_trades: Optional[list[dict]]
    ) -> str:
        """Build comprehensive monthly analysis prompt."""
        prompt = f"""You are a portfolio analyst conducting a monthly deep-dive review of a multi-strategy equity portfolio.

PORTFOLIO SUMMARY:
- Total NAV: ${portfolio_data.get('nav_total', 0):,.2f}
- Cash: ${portfolio_data.get('nav_cash', 0):,.2f}
- Invested: ${portfolio_data.get('nav_total', 0) - portfolio_data.get('nav_cash', 0):,.2f}

RISK METRICS:
- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}
- Beta (vs SPY): {metrics.get('beta_spy', 'N/A')}
- Annual Volatility: {metrics.get('volatility_annual', 'N/A')}
- Max Drawdown: {metrics.get('max_drawdown', 'N/A')}

STRATEGY SLEEVES:
"""
        for sleeve in ['momentum', 'futuristic', 'realworld', 'risk']:
            sleeve_data = portfolio_data.get('sleeve_breakdown', {}).get(sleeve, {})
            prompt += f"- {sleeve.title()}: {sleeve_data.get('count', 0)} positions, ${sleeve_data.get('value', 0):,.2f}\n"

        prompt += "\nCURRENT POSITIONS WITH NEWS & SENTIMENT:\n\n"

        for pos in positions:
            ticker = pos['ticker']
            prompt += f"**{ticker}** ({pos['sleeve']}): {pos['shares']:.0f} shares @ ${pos['market_price']:.2f} = ${pos['market_value']:,.2f}\n"

            # Add sentiment data
            if ticker in sentiment_data and sentiment_data[ticker]:
                sent = sentiment_data[ticker]
                if sent.get('analyst_recommendation'):
                    prompt += f"  - Analyst Rating: {sent['analyst_recommendation']}\n"
                if sent.get('analyst_upside_pct'):
                    prompt += f"  - Target Upside: {sent['analyst_upside_pct']}%\n"

            # Add recent news headlines
            if ticker in news_data and news_data[ticker]:
                prompt += f"  Recent News:\n"
                for article in news_data[ticker][:3]:  # Top 3 articles
                    prompt += f"    • {article['title']} ({article['date']})\n"

            prompt += "\n"

        if recommended_trades:
            prompt += f"\nRECOMMENDED REBALANCING ({len(recommended_trades)} trades):\n"
            for trade in recommended_trades[:10]:
                prompt += f"- {trade['action']} {trade['ticker']}: {trade['shares']} shares - {trade['reason']}\n"

        prompt += """
MONTHLY ANALYSIS REQUIREMENTS:

Provide a comprehensive monthly portfolio review (10-15 sentences) covering:

1. **Portfolio Health & Performance**: Overall assessment considering risk metrics and returns
2. **Sleeve Balance**: Evaluate strategy diversification and any concerning concentrations
3. **Position-Level Insights**: Highlight 2-3 positions with notable news/sentiment (positive or negative)
4. **Market Context**: How current news/sentiment affects the portfolio's risk profile
5. **Strategic Recommendations**:
   - Should any positions be reduced/eliminated based on news?
   - Are there concentration risks that need addressing?
   - What's the optimal rebalancing strategy this month?
6. **Risk Assessment**: Given current market conditions and news, what are the key risks?

Be specific, actionable, and data-driven. Reference actual news when relevant. Focus on decisions the investor should make."""

        return prompt

    def _fallback_monthly_analysis(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict
    ) -> str:
        """Fallback analysis when AI unavailable."""
        nav_total = portfolio_data.get('nav_total', 0)
        nav_cash = portfolio_data.get('nav_cash', 0)
        invested_pct = ((nav_total - nav_cash) / nav_total * 100) if nav_total > 0 else 0

        analysis = f"""MONTHLY PORTFOLIO REVIEW

Portfolio is {invested_pct:.1f}% invested across {len(positions)} positions worth ${nav_total:,.2f}.

RISK METRICS:
- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}
- Beta: {metrics.get('beta_spy', 'N/A')}
- Volatility: {metrics.get('volatility_annual', 'N/A')}

"""

        # Analyze sleeve distribution
        sleeve_counts = {}
        sleeve_values = {}
        for pos in positions:
            sleeve = pos.get('sleeve', 'unknown')
            sleeve_counts[sleeve] = sleeve_counts.get(sleeve, 0) + 1
            sleeve_values[sleeve] = sleeve_values.get(sleeve, 0) + pos.get('market_value', 0)

        analysis += "SLEEVE DISTRIBUTION:\n"
        for sleeve, count in sorted(sleeve_counts.items()):
            value = sleeve_values.get(sleeve, 0)
            pct = (float(value) / float(nav_total) * 100) if nav_total > 0 else 0
            analysis += f"- {sleeve}: {count} positions (${value:,.2f}, {pct:.1f}%)\n"

        # Concentration analysis
        top_positions = sorted(positions, key=lambda x: x.get('market_value', 0), reverse=True)[:5]
        top_5_value = sum(p.get('market_value', 0) for p in top_positions)
        top_5_pct = (float(top_5_value) / float(nav_total) * 100) if nav_total > 0 else 0

        analysis += f"\nTOP 5 POSITIONS: ${top_5_value:,.2f} ({top_5_pct:.1f}% of portfolio)\n"
        for pos in top_positions:
            analysis += f"  {pos['ticker']}: ${pos.get('market_value', 0):,.2f}\n"

        analysis += "\nRECOMMENDATIONS:\n"
        if top_5_pct > 60:
            analysis += "- High concentration risk. Consider diversifying top positions.\n"

        dominant_sleeve = max(sleeve_counts.items(), key=lambda x: x[1])
        if dominant_sleeve[1] > len(positions) * 0.6:
            analysis += f"- Portfolio heavily weighted toward {dominant_sleeve[0]}. Consider rebalancing.\n"

        if invested_pct > 95:
            analysis += "- Very low cash reserves. Consider building dry powder for opportunities.\n"
        elif invested_pct < 80:
            analysis += "- Significant cash on sidelines. Consider deploying into positions.\n"

        analysis += "\nNote: AI analysis unavailable. Add ANTHROPIC_API_KEY for detailed insights with news context."

        return analysis


# Global monthly analyzer instance
monthly_analyzer = MonthlyAnalyzer()
