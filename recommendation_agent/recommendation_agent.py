import google.generativeai as genai
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
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

    def generate_report(self, sql_results) -> Tuple[str, str]: # <--- MODIFIED RETURN TYPE
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
        
        five_forces_analysis = self._analyze_five_forces(analysis)
        
        cache_key = self._generate_cache_key(analysis)
        if cache_key in self.insights_cache:
            insights = self.insights_cache[cache_key]
        else:
            insights = self._generate_ai_insights(analysis, five_forces_analysis)
            self.insights_cache[cache_key] = insights
        
        pdf_path = self._generate_pdf_report(analysis, insights, five_forces_analysis)
        print(f"Report generated: {pdf_path}")
        
        return pdf_path, insights # <--- RETURN INSIGHTS TEXT HERE

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

    def _clean_llm_response(self, raw_response: str) -> str:
        """Clean LLM response to remove conversational elements and return only content"""
        # Remove common conversational starters
        conversational_phrases = [
            "Okay, I will generate",
            "I will generate",
            "Here is a comprehensive",
            "I'll provide",
            "Let me provide",
            "Based on the provided",
            "Given the data and feedback",
            "I will focus on",
            "As requested",
            "In response to",
            "Following your request"
        ]
        
        lines = raw_response.split('\n')
        cleaned_lines = []
        skip_first_sentences = True
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines at the beginning
            if not line and skip_first_sentences:
                continue
                
            # Check if this line contains conversational phrases
            line_lower = line.lower()
            is_conversational = any(phrase.lower() in line_lower for phrase in conversational_phrases)
            
            # If we encounter actual content (headers, bullet points, or substantial text), start including
            if (line.startswith('•') or 
                line.startswith('#') or 
                line.isupper() or 
                any(keyword in line.upper() for keyword in ['STRATEGIC', 'ANALYSIS', 'RECOMMENDATIONS', 'PROJECTIONS', 'FORCES', 'POSITION']) or
                (len(line) > 20 and not is_conversational)):
                skip_first_sentences = False
            
            # Include the line if we're past the conversational intro
            if not skip_first_sentences and not is_conversational:
                cleaned_lines.append(line)
        
        # Join the cleaned lines
        cleaned_response = '\n'.join(cleaned_lines)
        
        # Additional cleanup: remove any remaining conversational elements
        sentences_to_remove = [
            "analysis addressing the feedback provided",
            "focusing on quantifiable projections",
            "measurable outcomes",
            "detailed timelines",
            "specific data points",
            "given the data and feedback provided"
        ]
        
        for sentence in sentences_to_remove:
            cleaned_response = cleaned_response.replace(sentence, "")
        
        # Clean up any double spaces or empty lines
        cleaned_response = re.sub(r'\n\s*\n', '\n\n', cleaned_response)
        cleaned_response = re.sub(r' +', ' ', cleaned_response)
        
        return cleaned_response.strip()

    def _generate_ai_insights(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]]) -> str:
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
        
        forces_context = []
        for force_name, force_data in five_forces.items():
            forces_context.append(f"{force_name.replace('_', ' ').title()}: {force_data['intensity']}")
        
        forces_summary = "; ".join(forces_context)
        
        prompt = f"""
        Generate a strategic business analysis report with the following data:
        
        FINANCIAL DATA: {context}
        COMPETITIVE FORCES: {forces_summary}
        
        Structure the analysis with these sections. Start directly with the content, no introductory statements:
        
        STRATEGIC POSITION
        • Current market position assessment
        • Competitive advantage analysis  
        • Key performance drivers
        
        FIVE FORCES IMPACT
        • Most critical competitive threats
        • Strategic vulnerabilities
        • Market dynamics affecting profitability
        
        STRATEGIC RECOMMENDATIONS  
        • Priority actions based on force analysis
        • Defensive strategies for high-intensity forces
        • Offensive opportunities in low-intensity areas
        
        FINANCIAL PROJECTIONS
        • 6-month revenue forecast scenarios
        • Risk factors and mitigation strategies
        
        Requirements:
        - Start immediately with section headers and content
        - Use bullet points for clarity
        - Be data-driven and specific
        - No conversational language or meta-commentary
        - Focus on actionable insights
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                # Clean the response to remove conversational elements
                cleaned_response = self._clean_llm_response(response.text)
                return cleaned_response
            else:
                return self._generate_fallback_analysis(analysis, five_forces)
        except Exception as e:
            print(f"AI insight generation failed: {e}")
            return self._generate_fallback_analysis(analysis, five_forces)

    def _generate_fallback_analysis(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]]) -> str:
        sales = analysis.get("total_sales", 0)
        growth = analysis.get("growth_rate", 0)
        
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

            story.append(Paragraph("STRATEGIC BUSINESS ANALYSIS", styles['Title']))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y at %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 30))

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

            story.append(Paragraph("PORTER'S FIVE FORCES ANALYSIS", styles['SectionHeader']))
            
            for force_name, force_data in five_forces.items():
                force_title = force_name.replace('_', ' ').title()
                story.append(Paragraph(f"{force_title}: {force_data['intensity']}", styles['BulletPoint']))
                
                for factor in force_data['factors']:
                    story.append(Paragraph(f"  - {factor}", styles['Normal']))
                
                story.append(Paragraph(f"  Recommendation: {force_data['recommendation']}", styles['Normal']))
                story.append(Spacer(1, 8))

            story.append(Spacer(1, 20))

            story.append(Paragraph("STRATEGIC ANALYSIS", styles['SectionHeader']))
            
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

    def improve_report_with_feedback(self, sql_results: str, judge_feedback: str, iteration: int) -> Tuple[str, str]:
        """Improve the report based on judge feedback"""
        print(f"🔄 Recommendation Agent: Improving report based on feedback (iteration {iteration})")
        
        # Parse the current data
        if isinstance(sql_results, str):
            try:
                parsed_results = json.loads(sql_results)
                if isinstance(parsed_results, dict) and parsed_results.get("type") == "structured_data":
                    analysis = self._process_structured_data(parsed_results)
                else:
                    analysis = self._analyze_data_fallback(sql_results)
            except json.JSONDecodeError:
                analysis = self._analyze_data_fallback(sql_results)
        else:
            analysis = self._analyze_data_fallback(str(sql_results))
        
        five_forces_analysis = self._analyze_five_forces(analysis)
        
        # Generate improved insights based on feedback
        improved_insights = self._generate_improved_insights_with_feedback(
            analysis, five_forces_analysis, judge_feedback, iteration
        )
        
        # Generate improved PDF report
        pdf_path = self._generate_improved_pdf_report(
            analysis, improved_insights, five_forces_analysis, judge_feedback, iteration
        )
        
        print(f"📄 Improved report generated: {pdf_path}")
        return pdf_path, improved_insights

    def _generate_improved_insights_with_feedback(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]], 
                                                 judge_feedback: str, iteration: int) -> str:
        """Generate improved insights incorporating judge feedback"""
        
        # Extract key improvement areas from judge feedback
        improvement_areas = self._extract_improvement_areas(judge_feedback)
        
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
        
        forces_context = []
        for force_name, force_data in five_forces.items():
            forces_context.append(f"{force_name.replace('_', ' ').title()}: {force_data['intensity']}")
        forces_summary = "; ".join(forces_context)
        
        prompt = f"""
        Create an enhanced strategic business analysis report incorporating the feedback provided. Start directly with content, no meta-commentary.
        
        DATA: {context}
        COMPETITIVE FORCES: {forces_summary}
        FEEDBACK AREAS: {'; '.join(improvement_areas)}
        
        Generate analysis with these sections. Start immediately with section headers:
        
        STRATEGIC POSITION
        • Concrete market position with specific data points
        • Quantified competitive advantages
        • Measurable performance drivers
        
        FIVE FORCES IMPACT
        • Enterprise-specific threat analysis
        • Quantified strategic vulnerabilities  
        • Market dynamics with financial impact
        
        STRATEGIC RECOMMENDATIONS
        • Specific actions with timelines and resources
        • Measurable outcomes and success metrics
        • Priority ranking with implementation costs
        
        FINANCIAL PROJECTIONS
        • Multi-scenario revenue forecasts with assumptions
        • Quantified risk factors and impact assessment
        • Detailed mitigation strategies with costs
        
        IMPLEMENTATION ROADMAP
        • 30-60-90 day action plan with milestones
        • Resource allocation and budget requirements
        • KPIs and success metrics for tracking
        
        Requirements:
        - Start directly with section content
        - Use specific numbers and metrics from the data
        - Provide quantified projections and timelines
        - Make all recommendations actionable and measurable
        - No conversational language or introductory statements
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                # Clean the response to remove any conversational elements
                cleaned_response = self._clean_llm_response(response.text)
                return cleaned_response
            else:
                return self._generate_fallback_improved_analysis(analysis, five_forces, judge_feedback)
        except Exception as e:
            print(f"AI improved insight generation failed: {e}")
            return self._generate_fallback_improved_analysis(analysis, five_forces, judge_feedback)

    def _extract_improvement_areas(self, judge_feedback: str) -> List[str]:
        """Extract key improvement areas from judge feedback"""
        improvement_areas = []
        
        # Look for common improvement indicators
        feedback_lower = judge_feedback.lower()
        
        if "generic" in feedback_lower or "template" in feedback_lower:
            improvement_areas.append("Increase specificity and personalization to enterprise data")
        
        if "data integration" in feedback_lower or "data points" in feedback_lower:
            improvement_areas.append("Better integration of specific enterprise metrics and KPIs")
        
        if "actionable" in feedback_lower or "implementation" in feedback_lower:
            improvement_areas.append("Provide more specific, implementable recommendations")
        
        if "quantified" in feedback_lower or "measurable" in feedback_lower:
            improvement_areas.append("Include quantified projections and measurable outcomes")
        
        if "competitive" in feedback_lower or "industry" in feedback_lower:
            improvement_areas.append("Add industry-specific and competitive intelligence")
        
        if "timeline" in feedback_lower or "roadmap" in feedback_lower:
            improvement_areas.append("Include detailed implementation timeline and roadmap")
        
        # Default improvements if none detected
        if not improvement_areas:
            improvement_areas = [
                "Enhance data-driven insights",
                "Improve recommendation specificity",
                "Add measurable outcomes"
            ]
        
        return improvement_areas

    def _generate_improved_pdf_report(self, analysis: Dict[str, Any], insights: str, 
                                    five_forces: Dict[str, Dict[str, Any]], judge_feedback: str, iteration: int) -> str:
        """Generate improved PDF report incorporating judge feedback"""
        filename = f"reports/strategic_analysis_v{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=40, bottomMargin=40)
            styles = self._create_custom_styles()
            story = []

            # Enhanced title with iteration info
            story.append(Paragraph(f"STRATEGIC BUSINESS ANALYSIS - VERSION {iteration}", styles['Title']))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%d/%m/%Y at %H:%M')} | Iteration: {iteration}", styles['Normal']))
            story.append(Spacer(1, 20))

            # Add improvement summary if not first iteration
            if iteration > 1:
                story.append(Paragraph("IMPROVEMENTS IN THIS VERSION", styles['SectionHeader']))
                improvement_areas = self._extract_improvement_areas(judge_feedback)
                for area in improvement_areas:
                    story.append(Paragraph(f"• {area}", styles['BulletPoint']))
                story.append(Spacer(1, 20))

            # ... existing code for metrics and five forces ...
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

            story.append(Paragraph("PORTER'S FIVE FORCES ANALYSIS", styles['SectionHeader']))
            
            for force_name, force_data in five_forces.items():
                force_title = force_name.replace('_', ' ').title()
                story.append(Paragraph(f"{force_title}: {force_data['intensity']}", styles['BulletPoint']))
                
                for factor in force_data['factors']:
                    story.append(Paragraph(f"  - {factor}", styles['Normal']))
                
                story.append(Paragraph(f"  Recommendation: {force_data['recommendation']}", styles['Normal']))
                story.append(Spacer(1, 8))

            story.append(Spacer(1, 20))

            story.append(Paragraph("ENHANCED STRATEGIC ANALYSIS", styles['SectionHeader']))
            
            insight_lines = insights.split('\n')
            for line in insight_lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                elif line.startswith('•'):
                    story.append(Paragraph(line, styles['BulletPoint']))
                elif any(header in line.upper() for header in ['STRATEGIC', 'FIVE FORCES', 'RECOMMENDATIONS', 'PROJECTIONS', 'IMPLEMENTATION']):
                    story.append(Paragraph(line, styles['SectionHeader']))
                else:
                    story.append(Paragraph(line, styles['Normal']))

            doc.build(story)
            return filename
            
        except Exception as e:
            print(f"Improved PDF generation failed: {e}")
            # Fallback to text file
            fallback_path = f"reports/strategic_analysis_v{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(f"STRATEGIC BUSINESS ANALYSIS - VERSION {iteration}\n")
                f.write(f"Generated: {datetime.now().strftime('%d/%m/%Y at %H:%M')}\n")
                f.write("="*60 + "\n\n")
                f.write(f"ENHANCED INSIGHTS:\n{insights}\n")
                
            return fallback_path

    def _generate_fallback_improved_analysis(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]], judge_feedback: str) -> str:
        """Generate fallback improved analysis when AI fails"""
        sales = analysis.get("total_sales", 0)
        growth = analysis.get("growth_rate", 0)
        
        high_threat_forces = [name.replace('_', ' ').title() for name, data in five_forces.items() if data['intensity'] == 'HIGH']
        
        report = f"""ENHANCED STRATEGIC POSITION

• Financial Performance: {sales:,.0f} revenue with {growth:.1f}% growth trajectory
• Market Position: {"Expanding market presence" if growth > 5 else "Stabilizing operations" if growth > 0 else "Defensive positioning required"}
• Competitive Landscape: {len(high_threat_forces)} high-intensity competitive forces requiring immediate attention

TARGETED FIVE FORCES RESPONSE

• Critical Threats Identified: {', '.join(high_threat_forces) if high_threat_forces else 'Market position is defensible'}
• Strategic Priority: {"Multi-front competitive response" if len(high_threat_forces) >= 2 else "Focused competitive strategy"}
• Resource Allocation: {"Defensive investments required" if high_threat_forces else "Growth investments recommended"}

SPECIFIC STRATEGIC RECOMMENDATIONS

• Immediate Actions (30 days): {"Competitive threat assessment and response planning" if high_threat_forces else "Market expansion opportunity analysis"}
• Medium-term Strategy (90 days): {"Market differentiation and barrier building" if "Competitive Rivalry" in high_threat_forces else "Operational optimization and scaling"}
• Long-term Positioning (6 months): {"Sustainable competitive advantage development" if high_threat_forces else "Market leadership consolidation"}

QUANTIFIED FINANCIAL PROJECTIONS

• Conservative Scenario (6M): {sales * 1.03:,.0f} (+3% growth, defensive positioning)
• Base Case Scenario (6M): {sales * 1.08:,.0f} (+8% growth, balanced strategy)
• Optimistic Scenario (6M): {sales * 1.18:,.0f} (+18% growth, aggressive expansion)
• Primary Risk Factor: {high_threat_forces[0] if high_threat_forces else "Market volatility and economic conditions"}

IMPLEMENTATION ROADMAP

• Week 1-2: Data validation and competitive intelligence gathering
• Week 3-4: Strategic initiative prioritization and resource allocation
• Month 2: Implementation of priority recommendations
• Month 3: Performance monitoring and strategy adjustment
• Months 4-6: Scaling successful initiatives and continuous optimization
        """
        
        return report