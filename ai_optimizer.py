#!/usr/bin/env python3
import openai
import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AIStrategyOptimizer:
    """Use OpenAI to analyze performance and optimize strategies"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.optimization_history = []
        
    def analyze_performance(self, strategy_performance: Dict, recent_trades: List[Dict]) -> Dict:
        """Use AI to analyze strategy performance and suggest improvements"""
        
        prompt = self._create_analysis_prompt(strategy_performance, recent_trades)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional quantitative trading analyst. Analyze trading strategy performance and provide specific, actionable recommendations for improvement."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            return self._parse_analysis(analysis)
            
        except Exception as e:
            logger.error(f"❌ OpenAI analysis failed: {e}")
            return {"error": str(e)}
    
    def _create_analysis_prompt(self, performance: Dict, trades: List[Dict]) -> str:
        """Create prompt for AI analysis"""
        
        return f"""
        TRADING STRATEGY PERFORMANCE ANALYSIS REQUEST
        
        PERFORMANCE SUMMARY:
        {json.dumps(performance, indent=2)}
        
        RECENT TRADES (last 20):
        {json.dumps(trades[-20:], indent=2)}
        
        Please analyze this trading performance and provide:
        
        1. STRATEGY STRENGTHS: What is working well?
        2. WEAKNESSES: What needs improvement?
        3. RISK MANAGEMENT: Any risk management issues?
        4. SPECIFIC OPTIMIZATIONS: Concrete parameter adjustments
        5. MARKET CONDITIONS: How strategies perform in different conditions
        
        Format response as JSON with these keys:
        - strengths
        - weaknesses  
        - risk_issues
        - optimizations (specific parameter changes)
        - market_insights
        - confidence_score
        - recommended_actions
        """
    
    def _parse_analysis(self, analysis: str) -> Dict:
        """Parse AI analysis response"""
        try:
            # Try to extract JSON from response
            if "```json" in analysis:
                json_str = analysis.split("```json")[1].split("```")[0]
            elif "```" in analysis:
                json_str = analysis.split("```")[1].split("```")[0]
            else:
                json_str = analysis
                
            return json.loads(json_str)
        except:
            # Fallback: return as text
            return {"analysis": analysis}
    
    def optimize_parameters(self, strategy: str, historical_data: Dict) -> Dict:
        """Use AI to optimize strategy parameters"""
        
        prompt = f"""
        Optimize parameters for trading strategy: {strategy}
        
        HISTORICAL PERFORMANCE:
        {json.dumps(historical_data, indent=2)}
        
        Suggest optimized parameters for:
        - Stop loss percentages
        - Take profit targets
        - Position sizing
        - Entry/exit conditions
        - Confidence thresholds
        
        Return as JSON with specific numerical values and reasoning.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ Parameter optimization failed: {e}")
            return {}
