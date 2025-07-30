# recommendation_agent/recommendation_agent.py
import google.generativeai as genai
import pandas as pd
import json
from typing import Dict, Any, List
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import re

class RecommendationAgent:
    """
    A dedicated agent that receives structured data, analyzes it,
    generates AI-powered insights, and produces a comprehensive PDF report.
    """
    def __init__(self, gemini_api_key: str = None):
        if gemini_api_key is None:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Ensure the directory for reports and charts exists
        if not os.path.exists('reports'):
            os.makedirs('reports')

    def generate_report(self, sql_results_string: str) -> str:
        """
        Main public method. Orchestrates the full report generation process.

        Args:
            sql_results_string: A single string containing the aggregated results
                                from all SQL queries.

        Returns:
            The file path to the generated PDF report.
        """
        print("🤖 Recommendation Agent: Starting report generation process...")
        
        # 1. Parse the raw data string into a structured dictionary
        analysis = self._analyze_data(sql_results_string)
        
        # 2. Use Gemini to generate strategic insights from the analysis
        insights = self._generate_ai_insights(analysis)
        
        # 3. Create data visualizations
        charts = self._create_visualizations(analysis)
        
        # 4. Assemble the final PDF report
        pdf_path = self._generate_pdf_report(analysis, insights, charts)
        
        return pdf_path

    def _analyze_data(self, full_data_string: str) -> Dict[str, Any]:
        """Parses the aggregated data string into a structured dictionary."""
        print("  - Analyzing extracted data...")
        analysis = {
            "sales_metrics": {
                "total_sales": self._extract_number(full_data_string, "total sales"),
                "growth_rate": self._extract_number(full_data_string, "growth rate"),
                "top_region": self._extract_text(full_data_string, "top-selling region"),
                "best_category": self._extract_text(full_data_string, "best product category")
            },
            "social_metrics": {
                "total_engagement": self._extract_number(full_data_string, "engagement"),
                "total_followers": self._extract_number(full_data_string, "followers"),
                "leads_generated": self._extract_number(full_data_string, "leads generated"),
                "best_platform": self._extract_text(full_data_string, "best-performing platform")
            },
            "customer_metrics": {
                "satisfaction_score": self._extract_number(full_data_string, "satisfaction score"),
                "support_tickets": self._extract_number(full_data_string, "support tickets"),
                "retention_rate": self._extract_number(full_data_string, "retention rate")
            },
            "marketing_metrics": {
                "total_spend": self._extract_number(full_data_string, "total marketing spend"),
                "conversion_rate": self._extract_number(full_data_string, "overall conversion rate"),
                "cost_per_lead": self._extract_number(full_data_string, "cost per lead"),
                "roi": self._extract_number(full_data_string, "marketing roi")
            }
        }
        return analysis

    def _extract_number(self, text: str, keyword: str) -> float:
        """Extracts a numeric value. Returns 0.0 if not found."""
        try:
            pattern = rf"{keyword}\s*[:\-is\s]*([\d,]+\.?\d*)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        except (AttributeError, ValueError):
            pass
        return 0.0

    def _extract_text(self, text: str, keyword: str) -> str:
        """Extracts a text value. Returns 'N/A' if not found."""
        try:
            pattern = rf"{keyword}\s*[:\-is\s]*([A-Za-z\s&'-]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                return result.split('\n')[0].strip() if '\n' in result else result
        except AttributeError:
            pass
        return "N/A"

    def _generate_ai_insights(self, analysis: Dict[str, Any]) -> str:
        """Generates AI-powered strategic insights using Gemini."""
        print("  - Generating AI insights...")
        prompt = f"""
        Analyze this business data and provide strategic recommendations.
        - Sales: {analysis['sales_metrics']}
        - Social Media: {analysis['social_metrics']}
        - Customer: {analysis['customer_metrics']}
        - Marketing: {analysis['marketing_metrics']}

        Structure your response using Markdown for headings and bold text.
        ## Strategic Analysis
        Provide a brief overview of the company's current standing based on the data.

        ### Top Strengths
        1. Identify the first strength, citing specific metrics.
        2. Identify the second strength...

        ### Critical Weaknesses
        1. Identify the most critical weakness and its business impact.
        2. Identify the second weakness...

        ### Actionable Recommendations
        1. **Priority 1:** Provide a concrete, actionable recommendation. Estimate its potential impact or ROI.
        2. **Priority 2:** Another clear recommendation...
        
        ### 6-Month Forecast
        Provide brief optimistic and pessimistic scenarios based on whether the recommendations are implemented.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI insights generation failed: {e}"

    def _create_visualizations(self, analysis: Dict[str, Any]) -> List[str]:
        """Creates and saves key data visualizations."""
        print("  - Creating data visualizations...")
        chart_files = []
        plt.style.use('seaborn-v0_8-whitegrid')
        
        try:
            plt.figure(figsize=(10, 6))
            metrics = ['Sales (k)', 'Growth (%)', 'Satisfaction (/5)', 'ROI (%)']
            values = [
                analysis['sales_metrics']['total_sales'] / 1000,
                analysis['sales_metrics']['growth_rate'],
                analysis['customer_metrics']['satisfaction_score'],
                analysis['marketing_metrics']['roi']
            ]
            colors_list = ['#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4']
            bars = plt.bar(metrics, values, color=colors_list)
            plt.title('Overall Business Key Performance Indicators', fontsize=16, pad=20)
            plt.ylabel('Value')
            for bar in bars:
                yval = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.1, f'{yval:.1f}', va='bottom', ha='center', fontsize=10)
            
            filepath = 'reports/kpi_overview.png'
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            chart_files.append(filepath)
            plt.close()
        except Exception as e:
            print(f"    - Warning: Failed to create KPI chart: {e}")
            
        return chart_files

    def _generate_pdf_report(self, analysis: Dict[str, Any], insights: str, charts: List[str]) -> str:
        """Assembles the final comprehensive PDF report."""
        print("  - Assembling PDF report...")
        filename = f"reports/strategic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=50, bottomMargin=50, leftMargin=50, rightMargin=50)
        styles = getSampleStyleSheet()
        story = []

        # --- Define Styles ---
        title_style = ParagraphStyle('CustomTitle', parent=styles['h1'], fontSize=22, spaceAfter=20, textColor=colors.HexColor("#1e3a8a"))
        h2_style = ParagraphStyle('CustomH2', parent=styles['h2'], fontSize=14, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1e3a8a"), borderPadding=4)
        body_style = ParagraphStyle('Body', parent=styles['Normal'], leading=14, spaceAfter=6)

        # --- Process Insights Text for ReportLab ---
        processed_insights = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', insights)
        processed_insights = re.sub(r'##\s*(.*)', r'<para style="CustomH2">\1</para>', processed_insights)
        processed_insights = re.sub(r'###\s*(.*)', r'<b>\1</b>', processed_insights)
        processed_insights = processed_insights.replace('\n', '<br/>')

        # --- Build PDF Story ---
        story.append(Paragraph("Strategic Business Analysis Report", title_style))
        story.append(Paragraph(f"<i>Generated on: {datetime.now().strftime('%B %d, %Y')}</i>", body_style))
        story.append(Spacer(1, 24))

        story.append(Paragraph("Executive Summary", h2_style))
        summary = f"""
        <b>Total Sales:</b> ${analysis['sales_metrics']['total_sales']:,.2f}<br/>
        <b>Sales Growth Rate:</b> {analysis['sales_metrics']['growth_rate']:.1f}%<br/>
        <b>Customer Satisfaction:</b> {analysis['customer_metrics']['satisfaction_score']:.1f} / 5.0<br/>
        <b>Marketing ROI:</b> {analysis['marketing_metrics']['roi']:.1f}%<br/>
        <b>Top Performing Region:</b> {analysis['sales_metrics']['top_region']}
        """
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 24))

        if charts and os.path.exists(charts[0]):
            story.append(Paragraph("Key Performance Indicators Overview", h2_style))
            story.append(Image(charts[0], width=480, height=288))
            story.append(Spacer(1, 24))

        story.append(Paragraph(processed_insights, body_style))
        
        doc.build(story)
        return filename