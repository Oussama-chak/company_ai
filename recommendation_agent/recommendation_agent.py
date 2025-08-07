import os
import sys


from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import google.generativeai as genai
import json
from typing import Dict, Any, List
from datetime import datetime

import os
import re

class RecommendationAgent:
    def __init__(self, gemini_api_key: str = None):
        if gemini_api_key is None:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        os.makedirs('reports', exist_ok=True)
        self.insights_cache = {}

    def generate_report(self, sql_results) -> str:
        print("Starting report generation...")
        
        if isinstance(sql_results, str):
            try:
                parsed_results = json.loads(sql_results)
                if isinstance(parsed_results, dict) and parsed_results.get("type") == "structured_data":
                    analysis = self._process_structured_data(parsed_results)
                else:
                    analysis = self._analyze_data_fallback(sql_results)
            except json.JSONDecodeError:
                analysis = self._analyze_data_fallback(sql_results)
        elif isinstance(sql_results, dict) and sql_results.get("type") == "structured_data":
            analysis = self._process_structured_data(sql_results)
        else:
            analysis = self._analyze_data_fallback(str(sql_results))
        
        # Generate 5 Forces analysis
        five_forces_analysis = self._analyze_five_forces(analysis)
        
        # Generate insights with caching
        cache_key = self._generate_cache_key(analysis)
        if cache_key in self.insights_cache:
            insights = self.insights_cache[cache_key]
        else:
            insights = self._generate_ai_insights(analysis, five_forces_analysis)
            self.insights_cache[cache_key] = insights
        
        pdf_path = self._generate_pdf_report(analysis, insights, five_forces_analysis)
        print(f"Report generated: {pdf_path}")
        
        return pdf_path

    def _process_structured_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        analysis = {}
        
        for result in structured_data.get("results", []):
            if result["status"] == "success" and "data" in result:
                data = result["data"]
                template = result["template"]
                
                try:
                    if template == "sales_performance":
                        analysis.update({
                            "total_sales": self._safe_float(data.get("total_sales", 0)),
                            "growth_rate": self._safe_float(data.get("avg_growth_rate", 0)),
                            "top_category": str(data.get("top_category", "N/A")),
                            "market_share": self._safe_float(data.get("market_share", 0))
                        })
                    
                    elif template == "marketing_efficiency":
                        analysis.update({
                            "marketing_roi": self._safe_float(data.get("avg_roi", 0)),
                            "total_spend": self._safe_float(data.get("total_spend", 0)),
                            "conversion_rate": self._safe_float(data.get("avg_conversion", 0)),
                            "best_channel": str(data.get("best_channel", "N/A")),
                            "total_leads": self._safe_float(data.get("total_leads", 0)),
                            "customer_acquisition_cost": self._safe_float(data.get("cac", 0))
                        })
                    
                    elif template == "customer_insights":
                        analysis.update({
                            "satisfaction_score": self._safe_float(data.get("avg_satisfaction", 0)),
                            "churn_rate": self._safe_float(data.get("avg_churn", 0)),
                            "top_segment": str(data.get("top_segment", "N/A")),
                            "avg_ltv": self._safe_float(data.get("avg_ltv", 0)),
                            "switching_cost": self._safe_float(data.get("switching_cost", 0))
                        })
                    
                    elif template == "product_performance":
                        analysis.update({
                            "top_product": str(data.get("top_product", "N/A")),
                            "product_revenue": self._safe_float(data.get("total_revenue", 0)),
                            "product_rating": self._safe_float(data.get("avg_rating", 0)),
                            "profit_margin": self._safe_float(data.get("avg_margin", 0)),
                            "product_differentiation": self._safe_float(data.get("differentiation_score", 0))
                        })
                    
                    elif template == "financial_overview":
                        analysis.update({
                            "total_revenue": self._safe_float(data.get("total_revenue", 0)),
                            "revenue_growth": self._safe_float(data.get("growth_rate", 0)),
                            "performance_rating": str(data.get("rating", "N/A"))
                        })
                        
                except Exception as e:
                    print(f"Error processing {template}: {e}")
                    continue
        
        return analysis

    def _safe_float(self, value) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _analyze_data_fallback(self, data_string: str) -> Dict[str, Any]:
        analysis = {
            "total_sales": self._extract_number_pattern(data_string, ["total_sales", "revenue"]),
            "growth_rate": self._extract_number_pattern(data_string, ["growth_rate", "avg_growth_rate"]),
            "top_category": self._extract_text_pattern(data_string, ["top_category", "product_category"]),
            "satisfaction_score": self._extract_number_pattern(data_string, ["satisfaction", "avg_satisfaction"]),
            "marketing_roi": self._extract_number_pattern(data_string, ["roi", "return_on_ad_spend"]),
            "total_leads": self._extract_number_pattern(data_string, ["leads", "total_leads"]),
            "conversion_rate": self._extract_number_pattern(data_string, ["conversion", "conversion_rate"]),
            "market_share": self._extract_number_pattern(data_string, ["market_share", "share"]),
            "churn_rate": self._extract_number_pattern(data_string, ["churn", "attrition"]),
            "profit_margin": self._extract_number_pattern(data_string, ["margin", "profit_margin"])
        }
        
        return analysis

    def _extract_number_pattern(self, text: str, keywords: List[str]) -> float:
        for keyword in keywords:
            patterns = [
                rf"{keyword}[:\s]*(\d+\.?\d*)",
                rf"'{keyword}':\s*(\d+\.?\d*)",
                rf'"{keyword}":\s*(\d+\.?\d*)',
                rf"{keyword}=(\d+\.?\d*)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        continue
        return 0.0

    def _extract_text_pattern(self, text: str, keywords: List[str]) -> str:
        for keyword in keywords:
            patterns = [
                rf"{keyword}[:\s]*([A-Za-z\s&'\-]+)",
                rf"'{keyword}':\s*'([^']+)'",
                rf'"{keyword}":\s*"([^"]+)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip().split('\n')[0].strip()
                    if result and len(result) > 1:
                        return result
        return "N/A"

    def _analyze_five_forces(self, analysis: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Analyze Porter's Five Forces based on business data"""
        
        # Calculate force intensities based on available data
        forces = {
            "competitive_rivalry": self._assess_competitive_rivalry(analysis),
            "threat_of_new_entrants": self._assess_threat_of_new_entrants(analysis),
            "bargaining_power_suppliers": self._assess_supplier_power(analysis),
            "bargaining_power_buyers": self._assess_buyer_power(analysis),
            "threat_of_substitutes": self._assess_threat_of_substitutes(analysis)
        }
        
        return forces

    def _assess_competitive_rivalry(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        market_share = analysis.get("market_share", 0)
        growth_rate = analysis.get("growth_rate", 0)
        profit_margin = analysis.get("profit_margin", 0)
        
        # High competition if low market share, declining growth, or low margins
        intensity_score = 0
        if market_share < 20: intensity_score += 1
        if growth_rate < 5: intensity_score += 1
        if profit_margin < 15: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Market share: {market_share}%",
                f"Industry growth: {growth_rate}%",
                f"Profit margins: {profit_margin}%"
            ],
            "recommendation": "Focus on differentiation and cost optimization" if intensity == "HIGH" else "Maintain competitive advantage"
        }

    def _assess_threat_of_new_entrants(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        growth_rate = analysis.get("growth_rate", 0)
        profit_margin = analysis.get("profit_margin", 0)
        
        # High threat if high growth and high margins (attractive market)
        intensity_score = 0
        if growth_rate > 15: intensity_score += 1
        if profit_margin > 20: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Market attractiveness (growth): {growth_rate}%",
                f"Profitability signal: {profit_margin}%"
            ],
            "recommendation": "Build barriers to entry through innovation" if intensity == "HIGH" else "Monitor market developments"
        }

    def _assess_supplier_power(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        profit_margin = analysis.get("profit_margin", 0)
        
        # Assume medium power by default, low margins might indicate high supplier power
        intensity_score = 1 if profit_margin < 10 else 0
        intensity = "HIGH" if intensity_score >= 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Margin pressure indicator: {profit_margin}%"
            ],
            "recommendation": "diversify supplier base and negotiate better terms" if intensity == "HIGH" else "Maintain supplier relationships"
        }

    def _assess_buyer_power(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        customer_satisfaction = analysis.get("satisfaction_score", 0)
        churn_rate = analysis.get("churn_rate", 0)
        
        # High buyer power if low satisfaction or high churn
        intensity_score = 0
        if customer_satisfaction < 3.5: intensity_score += 1
        if churn_rate > 15: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Customer satisfaction: {customer_satisfaction}/5",
                f"Churn rate: {churn_rate}%"
            ],
            "recommendation": "Improve customer value proposition" if intensity == "HIGH" else "Maintain customer relationships"
        }

    def _assess_threat_of_substitutes(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        product_rating = analysis.get("product_rating", 0)
        
        # Assume medium threat, low product rating indicates vulnerability to substitutes
        intensity_score = 1 if product_rating < 3.5 else 0
        intensity = "HIGH" if intensity_score >= 1 else "MEDIUM"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Product competitiveness: {product_rating}/5"
            ],
            "recommendation": "Enhance product uniqueness and customer lock-in" if intensity == "HIGH" else "Monitor substitute developments"
        }

    def _generate_cache_key(self, analysis: Dict[str, Any]) -> str:
        try:
            key_data = {
                "sales": str(analysis.get("total_sales", 0)),
                "growth": str(analysis.get("growth_rate", 0)),
                "roi": str(analysis.get("marketing_roi", 0)),
                "satisfaction": str(analysis.get("satisfaction_score", 0))
            }
            key_string = "_".join([f"{k}:{v}" for k, v in sorted(key_data.items())])
            return key_string
        except Exception as e:
            return f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _generate_ai_insights(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]]) -> str:
        # Build context
        context_metrics = []
        
        if analysis.get("total_sales", 0) > 0:
            context_metrics.append(f"Revenue: {analysis['total_sales']:,.0f}")
        if analysis.get("growth_rate", 0) != 0:
            context_metrics.append(f"Growth: {analysis['growth_rate']:.2f}%")
        if analysis.get("marketing_roi", 0) > 0:
            context_metrics.append(f"Marketing ROI: {analysis['marketing_roi']:.2f}x")
        if analysis.get("satisfaction_score", 0) > 0:
            context_metrics.append(f"Satisfaction: {analysis['satisfaction_score']:.2f}/5")
        
        context = "; ".join(context_metrics)
        
        # Build 5 Forces context
        forces_context = []
        for force_name, force_data in five_forces.items():
            forces_context.append(f"{force_name.replace('_', ' ').title()}: {force_data['intensity']}")
        
        forces_summary = "; ".join(forces_context)
        
        prompt = f"""
        BUSINESS ANALYSIS WITH PORTER'S 5 FORCES:
        
        FINANCIAL DATA: {context}
        COMPETITIVE FORCES: {forces_summary}
        
        REQUIRED ANALYSIS:
        
        1. STRATEGIC POSITION
        • Current market position assessment
        • Competitive advantage analysis
        • Key performance drivers
        
        2. FIVE FORCES IMPACT
        • Most critical competitive threats
        • Strategic vulnerabilities
        • Market dynamics affecting profitability
        
        3. STRATEGIC RECOMMENDATIONS  
        • Priority actions based on force analysis
        • Defensive strategies for high-intensity forces
        • Offensive opportunities in low-intensity areas
        
        4. FINANCIAL PROJECTIONS
        • 6-month revenue forecast scenarios
        • Risk factors and mitigation strategies
        
        Keep response focused, data-driven, and actionable. Use bullet points.Don't give like response text only generate report driven text focus on anayzing data really carefully and give realistic prediciton on th ecommercial strategy 
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text
            else:
                return self._generate_fallback_analysis(analysis, five_forces)
        except Exception as e:
            print(f"AI insight generation failed: {e}")
            return self._generate_fallback_analysis(analysis, five_forces)

    def _generate_fallback_analysis(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]]) -> str:
        sales = analysis.get("total_sales", 0)
        growth = analysis.get("growth_rate", 0)
        
        # Identify highest threat forces
        high_threat_forces = [name.replace('_', ' ').title() for name, data in five_forces.items() if data['intensity'] == 'HIGH']
        
        report = f"""STRATEGIC POSITION

• Financial Performance: {sales:,.0f} revenue with {growth:.1f}% growth
• Market Position: {"Growing" if growth > 0 else "Declining"} trajectory
• Competitive Pressure: {len(high_threat_forces)} high-intensity forces identified

FIVE FORCES IMPACT

• Critical Threats: {', '.join(high_threat_forces) if high_threat_forces else 'No critical threats identified'}
• Strategic Focus: {"Defensive positioning required" if len(high_threat_forces) >= 2 else "Balanced growth strategy"}

STRATEGIC RECOMMENDATIONS

• Priority 1: {"Address competitive threats" if high_threat_forces else "Capitalize on market position"}
• Priority 2: {"Build differentiation barriers" if "Competitive Rivalry" in high_threat_forces else "Expand market presence"}
• Priority 3: {"Strengthen customer relationships" if "Bargaining Power Buyers" in high_threat_forces else "Optimize operations"}

FINANCIAL PROJECTIONS

• 6M Conservative: {sales * 1.02:,.0f} (+2% growth)
• 6M Optimistic: {sales * 1.15:,.0f} (+15% growth)
• Key Risk: {high_threat_forces[0] if high_threat_forces else "Market volatility"}
        """
        
        return report

    def _create_custom_styles(self):
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=6,
            fontSize=10,
            leading=14
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        return styles

    def _generate_pdf_report(self, analysis: Dict[str, Any], insights: str, five_forces: Dict[str, Dict[str, Any]]) -> str:
        filename = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=40, bottomMargin=40)
            styles = self._create_custom_styles()
            story = []

            # Title
            story.append(Paragraph("STRATEGIC BUSINESS ANALYSIS", styles['Title']))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y at %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 30))

            # Key Metrics Dashboard
            story.append(Paragraph("KEY PERFORMANCE METRICS", styles['SectionHeader']))
            
            if analysis.get("total_sales", 0) > 0:
                story.append(Paragraph(f"• Total Revenue: {analysis['total_sales']:,.0f}", styles['BulletPoint']))
            if analysis.get("growth_rate", 0) != 0:
                story.append(Paragraph(f"• Growth Rate: {analysis['growth_rate']:.2f}%", styles['BulletPoint']))
            if analysis.get("marketing_roi", 0) > 0:
                story.append(Paragraph(f"• Marketing ROI: {analysis['marketing_roi']:.2f}x", styles['BulletPoint']))
            if analysis.get("satisfaction_score", 0) > 0:
                story.append(Paragraph(f"• Customer Satisfaction: {analysis['satisfaction_score']:.2f}/5", styles['BulletPoint']))
            
            story.append(Spacer(1, 20))

            # Porter's Five Forces Analysis
            story.append(Paragraph("PORTER'S FIVE FORCES ANALYSIS", styles['SectionHeader']))
            
            for force_name, force_data in five_forces.items():
                force_title = force_name.replace('_', ' ').title()
                story.append(Paragraph(f"{force_title}: {force_data['intensity']}", styles['BulletPoint']))
                
                for factor in force_data['factors']:
                    story.append(Paragraph(f"  - {factor}", styles['Normal']))
                
                story.append(Paragraph(f"  Recommendation: {force_data['recommendation']}", styles['Normal']))
                story.append(Spacer(1, 8))

            story.append(Spacer(1, 20))

            # AI Insights
            story.append(Paragraph("STRATEGIC ANALYSIS", styles['SectionHeader']))
            
            # Parse insights into paragraphs
            insight_lines = insights.split('\n')
            for line in insight_lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                elif line.startswith('•'):
                    story.append(Paragraph(line, styles['BulletPoint']))
                elif any(header in line.upper() for header in ['STRATEGIC', 'FIVE FORCES', 'RECOMMENDATIONS', 'PROJECTIONS']):
                    story.append(Paragraph(line, styles['SectionHeader']))
                else:
                    story.append(Paragraph(line, styles['Normal']))

            doc.build(story)
            return filename
            
        except Exception as e:
            print(f"PDF generation failed: {e}")
            # Text fallback
            fallback_path = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(f"STRATEGIC BUSINESS ANALYSIS\n")
                f.write(f"Generated: {datetime.now().strftime('%d/%m/%Y at %H:%M')}\n")
                f.write("="*60 + "\n\n")
                
                f.write("KEY METRICS:\n")
                for key, value in analysis.items():
                    if value and value != "N/A" and value != 0:
                        f.write(f"  • {key}: {value}\n")
                
                f.write(f"\nFIVE FORCES ANALYSIS:\n")
                for force_name, force_data in five_forces.items():
                    f.write(f"  • {force_name.replace('_', ' ').title()}: {force_data['intensity']}\n")
                    f.write(f"    Recommendation: {force_data['recommendation']}\n")
                
                f.write(f"\nSTRATEGIC INSIGHTS:\n{insights}\n")
                
            return fallback_path