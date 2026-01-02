"""AI-powered portfolio analysis using Claude."""

from typing import Optional
from anthropic import Anthropic

from portfolio.config import settings
from portfolio.utils.logging import logger


class PortfolioAnalyzer:
    """Generate AI-powered portfolio insights."""

    def __init__(self):
        """Initialize the analyzer."""
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    def analyze_portfolio(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict,
        recommended_trades: Optional[list[dict]] = None
    ) -> str:
        """
        Generate AI analysis of portfolio.

        Args:
            portfolio_data: Portfolio summary (NAV, cash, etc.)
            positions: List of current positions
            metrics: Risk metrics (sharpe, beta, volatility)
            recommended_trades: Optional list of recommended trades

        Returns:
            AI-generated analysis and recommendations
        """
        if not self.client:
            logger.warning("No Anthropic API key configured - skipping AI analysis")
            return self._fallback_analysis(portfolio_data, positions, metrics)

        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(
                portfolio_data, positions, metrics, recommended_trades
            )

            # Call Claude
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",  # Claude 3.5 Sonnet
                max_tokens=1500,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            analysis = response.content[0].text
            logger.info("AI portfolio analysis generated successfully")
            return analysis

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._fallback_analysis(portfolio_data, positions, metrics)

    def _build_analysis_prompt(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict,
        recommended_trades: Optional[list[dict]]
    ) -> str:
        """Build the analysis prompt for Claude."""
        prompt = f"""You are a portfolio analyst reviewing a multi-strategy equity portfolio.

PORTFOLIO SUMMARY:
- Total NAV: ${portfolio_data.get('nav_total', 0):,.2f}
- Cash: ${portfolio_data.get('nav_cash', 0):,.2f}
- Invested: ${portfolio_data.get('nav_total', 0) - portfolio_data.get('nav_cash', 0):,.2f}

RISK METRICS:
- Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}
- Beta: {metrics.get('beta', 'N/A')}
- Volatility: {metrics.get('volatility', 'N/A')}%

STRATEGY SLEEVES:
- Momentum: {portfolio_data.get('sleeve_breakdown', {}).get('momentum', {}).get('count', 0)} positions, ${portfolio_data.get('sleeve_breakdown', {}).get('momentum', {}).get('value', 0):,.2f}
- Futuristic: {portfolio_data.get('sleeve_breakdown', {}).get('futuristic', {}).get('count', 0)} positions, ${portfolio_data.get('sleeve_breakdown', {}).get('futuristic', {}).get('value', 0):,.2f}
- Real-world: {portfolio_data.get('sleeve_breakdown', {}).get('realworld', {}).get('count', 0)} positions, ${portfolio_data.get('sleeve_breakdown', {}).get('realworld', {}).get('value', 0):,.2f}
- Risk/Hedge: {portfolio_data.get('sleeve_breakdown', {}).get('risk', {}).get('count', 0)} positions, ${portfolio_data.get('sleeve_breakdown', {}).get('risk', {}).get('value', 0):,.2f}

CURRENT POSITIONS:
"""
        for pos in positions[:10]:  # Top 10 positions
            prompt += f"- {pos['ticker']}: {pos['shares']:.0f} shares @ ${pos['market_price']:.2f} = ${pos['market_value']:,.2f} ({pos['sleeve']})\n"

        if recommended_trades:
            prompt += f"\nRECOMMENDED TRADES ({len(recommended_trades)} total):\n"
            for trade in recommended_trades[:5]:  # Top 5 trades
                prompt += f"- {trade['action']} {trade['ticker']}: {trade['shares']} shares\n"

        prompt += """
Provide a concise portfolio analysis (4-6 sentences) covering:
1. Overall portfolio health and balance
2. Notable concentration or diversification issues
3. Risk profile assessment
4. One actionable recommendation for improvement

Keep it professional but accessible. Focus on insights that matter."""

        return prompt

    def _fallback_analysis(
        self,
        portfolio_data: dict,
        positions: list[dict],
        metrics: dict
    ) -> str:
        """Fallback analysis when AI is unavailable."""
        nav_total = portfolio_data.get('nav_total', 0)
        nav_cash = portfolio_data.get('nav_cash', 0)
        invested_pct = ((nav_total - nav_cash) / nav_total * 100) if nav_total > 0 else 0

        analysis = f"""Portfolio is {invested_pct:.1f}% invested across {len(positions)} positions. """

        if metrics.get('sharpe_ratio'):
            sharpe = metrics['sharpe_ratio']
            if sharpe > 2:
                analysis += "Strong risk-adjusted returns. "
            elif sharpe > 1:
                analysis += "Solid risk-adjusted returns. "
            else:
                analysis += "Consider reviewing position sizing for better risk/reward. "

        sleeve_counts = {
            'momentum': portfolio_data.get('sleeve_breakdown', {}).get('momentum', {}).get('count', 0),
            'futuristic': portfolio_data.get('sleeve_breakdown', {}).get('futuristic', {}).get('count', 0),
            'realworld': portfolio_data.get('sleeve_breakdown', {}).get('realworld', {}).get('count', 0),
            'risk': portfolio_data.get('sleeve_breakdown', {}).get('risk', {}).get('count', 0),
        }

        dominant_sleeve = max(sleeve_counts.items(), key=lambda x: x[1])
        if dominant_sleeve[1] > len(positions) * 0.6:
            analysis += f"Portfolio is heavily weighted toward {dominant_sleeve[0]} strategy. "

        analysis += "Continue monitoring for rebalancing opportunities."

        return analysis

    def get_ticker_description(self, ticker: str) -> str:
        """
        Get a brief description of what a ticker/company does.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Brief company description
        """
        if not self.client:
            return ""

        try:
            prompt = f"""Provide a one-sentence description of {ticker} that explains what the company does.
Focus on their main business and why an investor might own it.
Keep it under 20 words and make it informative.
Just return the description, no preamble."""

            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # Use Haiku for speed
                max_tokens=100,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            description = response.content[0].text.strip()
            logger.info(f"Generated description for {ticker}")
            return description

        except Exception as e:
            logger.error(f"Failed to generate description for {ticker}: {e}")
            return ""


# Global analyzer instance
portfolio_analyzer = PortfolioAnalyzer()
