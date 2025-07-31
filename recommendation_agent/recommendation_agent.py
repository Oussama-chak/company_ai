# recommendation_agent/recommendation_agent.py
import google.generativeai as genai
import json
from typing import Dict, Any, List
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import re

class RecommendationAgent:
    def __init__(self, gemini_api_key: str = None):
        if gemini_api_key is None:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create reports directory
        os.makedirs('reports', exist_ok=True)

    def generate_report(self, sql_results_string: str) -> str:
        print("🤖 Starting report generation...")
        
        # Parse data
        analysis = self._analyze_data(sql_results_string)
        print(f"  - Parsed data: {analysis}")
        
        # Generate insights
        insights = self._generate_ai_insights(analysis)
        print(f"  - Generated insights: {len(insights)} characters")
        
        # Create chart
        chart_path = self._create_chart(analysis)
        
        # Generate PDF
        pdf_path = self._generate_pdf_report(analysis, insights, chart_path)
        print(f"✅ Report generated: {pdf_path}")
        
        return pdf_path

    def _analyze_data(self, data_string: str) -> Dict[str, Any]:
        analysis = {
            "total_sales": self._extract_number(data_string, "total sales"),
            "growth_rate": self._extract_number(data_string, "growth rate"),
            "top_region": self._extract_text(data_string, "top-selling region"),
            "satisfaction_score": self._extract_number(data_string, "satisfaction score"),
            "marketing_roi": self._extract_number(data_string, "marketing roi"),
            "engagement": self._extract_number(data_string, "engagement"),
            "conversion_rate": self._extract_number(data_string, "conversion rate")
        }
        return analysis

    def _extract_number(self, text: str, keyword: str) -> float:
        try:
            pattern = rf"{keyword}\s*[:\-is\s]*([\d,]+\.?\d*)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        except:
            pass
        return 0.0

    def _extract_text(self, text: str, keyword: str) -> str:
        try:
            pattern = rf"{keyword}\s*[:\-is\s]*([A-Za-z\s&'-]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().split('\n')[0].strip()
        except:
            pass
        return "N/A"

    def _generate_ai_insights(self, analysis: Dict[str, Any]) -> str:
        prompt = f"""
        Based on this business data, provide 3 key insights and 3 recommendations:
        Sales: ${analysis['total_sales']:,.0f}, Growth: {analysis['growth_rate']:.1f}%
        Top Region: {analysis['top_region']}
        Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5
        Marketing ROI: {analysis['marketing_roi']:.1f}%
        
        Keep it concise and actionable.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Insights: Sales performance shows {analysis['growth_rate']:.1f}% growth. Focus on {analysis['top_region']} region optimization."

    def _create_chart(self, analysis: Dict[str, Any]) -> str:
        try:
            plt.figure(figsize=(8, 5))
            metrics = ['Sales (k)', 'Growth %', 'Satisfaction', 'ROI %']
            values = [
                analysis['total_sales'] / 1000,
                analysis['growth_rate'],
                analysis['satisfaction_score'],
                analysis['marketing_roi']
            ]
            
            plt.bar(metrics, values, color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
            plt.title('Key Performance Metrics')
            plt.tight_layout()
            
            chart_path = 'reports/metrics_chart.png'
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            return chart_path
        except Exception as e:
            print(f"Chart creation failed: {e}")
            return None

    def _generate_pdf_report(self, analysis: Dict[str, Any], insights: str, chart_path: str) -> str:
        filename = f"reports/business_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Title
            story.append(Paragraph("Business Analysis Report", styles['Title']))
            story.append(Spacer(1, 20))

            # Date
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 20))

            # Key Metrics
            story.append(Paragraph("Key Metrics", styles['Heading2']))
            metrics_text = f"""
            Total Sales: ${analysis['total_sales']:,.0f}<br/>
            Growth Rate: {analysis['growth_rate']:.1f}%<br/>
            Top Region: {analysis['top_region']}<br/>
            Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5<br/>
            Marketing ROI: {analysis['marketing_roi']:.1f}%
            """
            story.append(Paragraph(metrics_text, styles['Normal']))
            story.append(Spacer(1, 20))

            # Chart
            if chart_path and os.path.exists(chart_path):
                story.append(Paragraph("Performance Overview", styles['Heading2']))
                story.append(Image(chart_path, width=400, height=250))
                story.append(Spacer(1, 20))

            # Insights
            story.append(Paragraph("Strategic Insights", styles['Heading2']))
            story.append(Paragraph(insights, styles['Normal']))

            doc.build(story)
            print(f"✅ PDF saved successfully: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ PDF generation failed: {e}")
            # Create a simple text report as fallback
            fallback_path = f"reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w') as f:
                f.write(f"Business Report - {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write("="*50 + "\n\n")
                f.write(f"Total Sales: ${analysis['total_sales']:,.0f}\n")
                f.write(f"Growth Rate: {analysis['growth_rate']:.1f}%\n")
                f.write(f"Top Region: {analysis['top_region']}\n")
                f.write(f"Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5\n")
                f.write(f"Marketing ROI: {analysis['marketing_roi']:.1f}%\n\n")
                f.write("Insights:\n")
                f.write(insights)
            return fallback_path