import google.generativeai as genai
import json
from typing import Dict, Any, List
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
import os
import re

class RecommendationAgent:
    def __init__(self, gemini_api_key: str = None):
        if gemini_api_key is None:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create reports directory
        os.makedirs('reports', exist_ok=True)
        
        # Cache for reducing API calls
        self.insights_cache = {}

    def generate_report(self, sql_results) -> str:
        print("🤖 Starting report generation...")
        
        # Handle structured data from improved SQL agent
        if isinstance(sql_results, str):
            try:
                # Try to parse JSON string from SQL agent
                parsed_results = json.loads(sql_results)
                if isinstance(parsed_results, dict) and parsed_results.get("type") == "structured_data":
                    analysis = self._process_structured_data(parsed_results)
                    print(f"  - Processed structured JSON data: {len(analysis)} metrics")
                else:
                    analysis = self._analyze_data_fallback(sql_results)
                    print(f"  - Processed string data: {len(analysis)} metrics")
            except json.JSONDecodeError:
                analysis = self._analyze_data_fallback(sql_results)
                print(f"  - Processed fallback string data: {len(analysis)} metrics")
        elif isinstance(sql_results, dict) and sql_results.get("type") == "structured_data":
            analysis = self._process_structured_data(sql_results)
            print(f"  - Processed structured dict data: {len(analysis)} metrics")
        else:
            analysis = self._analyze_data_fallback(str(sql_results))
            print(f"  - Processed fallback data: {len(analysis)} metrics")
        
        # Validate we have meaningful data
        if not self._has_meaningful_data(analysis):
            print("  - ⚠️ Warning: Limited meaningful data extracted")
        
        # Generate insights with caching
        cache_key = self._generate_cache_key(analysis)
        if cache_key in self.insights_cache:
            print("  - Using cached insights")
            insights = self.insights_cache[cache_key]
        else:
            insights = self._generate_ai_insights(analysis)
            self.insights_cache[cache_key] = insights
            print(f"  - Generated new insights: {len(insights)} characters")
        
        # Create chart with available data
        chart_path = self._create_chart(analysis)
        
        # Generate PDF
        pdf_path = self._generate_pdf_report(analysis, insights, chart_path)
        print(f"✅ Report generated: {pdf_path}")
        
        return pdf_path

    def _process_structured_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process structured data from improved SQL agent"""
        analysis = {}
        
        for result in structured_data.get("results", []):
            if result["status"] == "success" and "data" in result:
                data = result["data"]
                template = result["template"]
                
                # Map template data to analysis metrics with proper error handling
                try:
                    if template == "sales_performance":
                        analysis.update({
                            "total_sales": self._safe_float(data.get("total_sales", 0)),
                            "growth_rate": self._safe_float(data.get("avg_growth_rate", 0)),
                            "top_category": str(data.get("top_category", "N/A"))
                        })
                    
                    elif template == "marketing_efficiency":
                        analysis.update({
                            "marketing_roi": self._safe_float(data.get("avg_roi", 0)),
                            "total_spend": self._safe_float(data.get("total_spend", 0)),
                            "conversion_rate": self._safe_float(data.get("avg_conversion", 0)),
                            "best_channel": str(data.get("best_channel", "N/A")),
                            "total_leads": self._safe_float(data.get("total_leads", 0))
                        })
                    
                    elif template == "customer_insights":
                        analysis.update({
                            "satisfaction_score": self._safe_float(data.get("avg_satisfaction", 0)),
                            "churn_rate": self._safe_float(data.get("avg_churn", 0)),
                            "top_segment": str(data.get("top_segment", "N/A")),
                            "avg_ltv": self._safe_float(data.get("avg_ltv", 0))
                        })
                    
                    elif template == "product_performance":
                        analysis.update({
                            "top_product": str(data.get("top_product", "N/A")),
                            "product_revenue": self._safe_float(data.get("total_revenue", 0)),
                            "product_rating": self._safe_float(data.get("avg_rating", 0)),
                            "profit_margin": self._safe_float(data.get("avg_margin", 0))
                        })
                    
                    elif template == "financial_overview":
                        analysis.update({
                            "total_revenue": self._safe_float(data.get("total_revenue", 0)),
                            "revenue_growth": self._safe_float(data.get("growth_rate", 0)),
                            "performance_rating": str(data.get("rating", "N/A"))
                        })
                        
                except Exception as e:
                    print(f"    - Warning: Error processing {template}: {e}")
                    continue
        
        # Log what we extracted
        non_zero_metrics = {k: v for k, v in analysis.items() if v != 0 and v != "N/A"}
        print(f"    - Extracted metrics: {list(non_zero_metrics.keys())}")
        
        return analysis

    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _has_meaningful_data(self, analysis: Dict[str, Any]) -> bool:
        """Check if we have meaningful data for analysis"""
        meaningful_keys = ["total_sales", "marketing_roi", "satisfaction_score", "product_revenue"]
        return any(analysis.get(key, 0) > 0 for key in meaningful_keys)

    def _analyze_data_fallback(self, data_string: str) -> Dict[str, Any]:
        """Fallback parsing method for string data"""
        print(f"  - Using fallback parsing for: {data_string[:200]}...")
        
        analysis = {
            "total_sales": self._extract_number_pattern(data_string, ["total_sales", "revenue"]),
            "growth_rate": self._extract_number_pattern(data_string, ["growth_rate", "avg_growth_rate"]),
            "top_category": self._extract_text_pattern(data_string, ["top_category", "product_category"]),
            "satisfaction_score": self._extract_number_pattern(data_string, ["satisfaction", "avg_satisfaction"]),
            "marketing_roi": self._extract_number_pattern(data_string, ["roi", "return_on_ad_spend"]),
            "total_leads": self._extract_number_pattern(data_string, ["leads", "total_leads"]),
            "conversion_rate": self._extract_number_pattern(data_string, ["conversion", "conversion_rate"])
        }
        
        return analysis

    def _extract_number_pattern(self, text: str, keywords: List[str]) -> float:
        """Extract numbers using multiple keyword patterns"""
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
        """Extract text using multiple keyword patterns"""
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

    def _generate_cache_key(self, analysis: Dict[str, Any]) -> str:
        """Generate cache key based on analysis data"""
        try:
            # Convert all values to strings to ensure they're hashable
            key_data = {
                "sales": str(analysis.get("total_sales", 0)),
                "growth": str(analysis.get("growth_rate", 0)),
                "roi": str(analysis.get("marketing_roi", 0)),
                "satisfaction": str(analysis.get("satisfaction_score", 0)),
                "leads": str(analysis.get("total_leads", 0))
            }
            # Create a simple string-based key instead of using hash
            key_string = "_".join([f"{k}:{v}" for k, v in sorted(key_data.items())])
            return key_string
        except Exception as e:
            print(f"  - Cache key generation failed: {e}")
            # Fallback to timestamp-based key
            return f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _generate_ai_insights(self, analysis: Dict[str, Any]) -> str:
        """Generate surgical precision AI insights using your proven template"""
        # Build precise context with exact figures
        context_metrics = []
        
        if analysis.get("total_sales", 0) > 0:
            context_metrics.append(f"Chiffre d'affaires: {analysis['total_sales']:,.0f}€")
        if analysis.get("growth_rate", 0) != 0:
            context_metrics.append(f"Croissance: {analysis['growth_rate']:.2f}%")
        if analysis.get("marketing_roi", 0) > 0:
            context_metrics.append(f"ROI Marketing: {analysis['marketing_roi']:.2f}x")
        if analysis.get("satisfaction_score", 0) > 0:
            context_metrics.append(f"Satisfaction: {analysis['satisfaction_score']:.2f}/5")
        if analysis.get("churn_rate", 0) > 0:
            context_metrics.append(f"Taux attrition: {analysis['churn_rate']:.2f}%")
        if analysis.get("total_leads", 0) > 0:
            context_metrics.append(f"Leads générés: {analysis['total_leads']:,.0f}")
        if analysis.get("conversion_rate", 0) > 0:
            context_metrics.append(f"Taux conversion: {analysis['conversion_rate']:.2f}%")
        
        # Build additional context
        additional_context = []
        if analysis.get("top_category", "N/A") != "N/A":
            additional_context.append(f"Catégorie leader: {analysis['top_category']}")
        if analysis.get("best_channel", "N/A") != "N/A":
            additional_context.append(f"Canal performant: {analysis['best_channel']}")
        
        context = "; ".join(context_metrics + additional_context)
        
        if not context_metrics:
            return self._generate_surgical_fallback(analysis)
        
        prompt = f"""
        ANALYSEZ CES DONNÉES COMMERCIALES avec précision chirurgicale :
        
        CONTEXTE : {context}
        
        DELIVERABLES REQUIS :
        
        1. 🔥 3 FORCES CLÉS
        • Chiffres exacts à l'appui
        • Tendances quantifiées sur 3-6 mois
        • Impact métier précis
        
        2. ⚠️ 3 FAIBLESSES CRITIQUES
        • Écarts vs benchmarks sectoriels
        • Pertes de revenus chiffrées
        • Causes racines identifiées
        
        3. 🎯 5 ACTIONS PRIORITAIRES
        Chaque action DOIT inclure :
        • Objectif : métrique précise + deadline
        • Méthode : étapes concrètes (2-3 max)
        • ROI estimé : gain financier attendu
        
        4. 📈 FORECAST 6 MOIS
        • 3 scénarios chiffrés (pessimiste/réaliste/optimiste)
        • Risques quantifiés + probabilités
        
        5. ⚡ VUE D'ENSEMBLE RAPIDE (MAX 4 LIGNES)
        • Où en sommes-nous ?
        • Ce dont nous avons besoin
        • Ce qu'il faut améliorer

        CONSIGNES STRICTES :
        • Citez les chiffres exacts des données.
        • Zéro généralité, 100% spécifique aux données fournies.
        • Recommandations immédiatement actionnables.
        • Format : bullet points courts et percutants avec émojis.
        • Chaque section doit commencer par son émoji et titre.
        • Utilisez EXACTEMENT ce format :
          
          🔥 3 FORCES CLÉS
          • Point 1
          • Point 2
          • Point 3
          
          ⚠️ 3 FAIBLESSES CRITIQUES
          • Point 1
          • Point 2
          • Point 3
          
          etc...
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text
            else:
                return self._generate_surgical_fallback(analysis)
        except Exception as e:
            print(f"  - AI insight generation failed: {e}")
            return self._generate_surgical_fallback(analysis)

    def _generate_surgical_fallback(self, analysis: Dict[str, Any]) -> str:
        """Generate surgical precision fallback analysis"""
        
        # Calculate key metrics
        sales = analysis.get("total_sales", 0)
        growth = analysis.get("growth_rate", 0)
        roi = analysis.get("marketing_roi", 0)
        satisfaction = analysis.get("satisfaction_score", 0)
        churn = analysis.get("churn_rate", 0)
        leads = analysis.get("total_leads", 0)
        conversion = analysis.get("conversion_rate", 0)
        
        report = f"""🔥 3 FORCES CLÉS

• PERFORMANCE COMMERCIALE: {sales:,.0f}€ de CA {"avec croissance de +"+str(growth)+"%" if growth > 0 else ""}
  Impact: Génère {sales/12:,.0f}€/mois de revenus récurrents
  Tendance 6M: {"Accélération attendue" if growth > 10 else "Croissance modérée" if growth > 0 else "Stabilisation requise"}

• EFFICACITÉ MARKETING: ROI de {roi:.1f}x {"(Performance excellente)" if roi > 4 else "(Performance correcte)" if roi > 2 else "(Optimisation requise)"}
  Impact: Chaque 1€ investi génère {roi:.1f}€ de retour
  Tendance 6M: {"Maintien performance" if roi > 3 else "Amélioration nécessaire"}

• SATISFACTION CLIENT: {satisfaction:.1f}/5 {"(Excellent)" if satisfaction > 4.5 else "(Bon)" if satisfaction > 4 else "(À améliorer)"}
  Impact: Taux de rétention estimé à {100-churn:.0f}%
  Tendance 6M: {"Fidélisation renforcée" if satisfaction > 4 else "Actions correctives requises"}

⚠️ 3 FAIBLESSES CRITIQUES

• TAUX ATTRITION: {churn:.1f}% vs benchmark 12-15%
  Perte: {(sales * churn/100):,.0f}€ de CA annuel perdu
  Cause: {"Score satisfaction insuffisant" if satisfaction < 4 else "Optimisation parcours client"}

• CONVERSION: {conversion:.1f}% {"vs benchmark 3-5%" if conversion > 0 else "Non mesurée"}
  Perte: {(leads * (5-conversion)/100 * 1000):,.0f}€ potentiel non capté {"si benchmark atteint" if conversion > 0 else ""}
  Cause: {"Parcours d'achat non optimisé" if conversion < 3 else "Ciblage à affiner"}

• CROISSANCE: {growth:.1f}% {"vs objectif 15-20%" if growth < 15 else "Rythme insuffisant"}
  Perte: {sales * (15-growth)/100:,.0f}€ d'écart vs potentiel
  Cause: {"Acquisition client limitée" if leads < 1000 else "Optimisation tarifaire"}

🎯 5 ACTIONS PRIORITAIRES

1. OPTIMISATION CONVERSION
   • Objectif: +2% taux conversion d'ici 60 jours
   • Méthode: A/B test pages de vente + simplification checkout
   • ROI: +{(leads * 2/100 * 1000):,.0f}€/mois

2. RÉDUCTION ATTRITION
   • Objectif: Churn <15% d'ici 90 jours
   • Méthode: Programme rétention + enquêtes satisfaction
   • ROI: +{(sales * min(churn-15, 0)/100):,.0f}€ préservés/an

3. AMPLIFICATION LEADS
   • Objectif: +30% leads générés d'ici 45 jours
   • Méthode: Budget +20% sur canaux ROI>3x + contenu viral
   • ROI: +{(leads * 0.3 * conversion/100 * 1000):,.0f}€/mois

4. OPTIMISATION PRIX
   • Objectif: +5% marge d'ici 30 jours
   • Méthode: Test prix segments haute valeur + bundling
   • ROI: +{(sales * 0.05):,.0f}€/an

5. AUTOMATISATION SUPPORT
   • Objectif: -25% tickets support d'ici 60 jours
   • Méthode: Chatbot FAQ + self-service client
   • ROI: -50k€ coûts opérationnels/an

📈 FORECAST 6 MOIS

🔴 PESSIMISTE (-10%): {sales * 0.9:,.0f}€
• Probabilité: 20%
• Risques: Concurrence aggressive, baisse conversion

🟡 RÉALISTE (+8%): {sales * 1.08:,.0f}€
• Probabilité: 60%
• Hypothèse: Actions 1-3 mises en œuvre

🟢 OPTIMISTE (+25%): {sales * 1.25:,.0f}€
• Probabilité: 20%
• Catalyseurs: Toutes actions + expansion marché

⚡ RISQUES QUANTIFIÉS
• Perte concurrent majeur: -15% CA (prob: 30%)
• Réduction budget marketing: -10% leads (prob: 25%)
• Problème tech majeur: -5% satisfaction (prob: 15%)
        """
        
        return report

    def _create_chart(self, analysis: Dict[str, Any]) -> str:
        """Create visualization with available data"""
        try:
            # Collect meaningful metrics for visualization
            chart_data = {}
            
            if analysis.get("total_sales", 0) > 0:
                chart_data["Sales ($M)"] = analysis["total_sales"] / 1000000
            
            if analysis.get("growth_rate", 0) != 0:
                chart_data["Growth (%)"] = analysis["growth_rate"]
            
            if analysis.get("marketing_roi", 0) > 0:
                chart_data["Marketing ROI"] = analysis["marketing_roi"]
            
            if analysis.get("satisfaction_score", 0) > 0:
                chart_data["Satisfaction"] = analysis["satisfaction_score"]
            
            if analysis.get("total_leads", 0) > 0:
                chart_data["Leads (k)"] = analysis["total_leads"] / 1000
            
            if len(chart_data) < 2:
                print("  - Insufficient data for chart creation")
                return None
            
            # Create chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            metrics = list(chart_data.keys())
            values = list(chart_data.values())
            colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#4CAF50'][:len(metrics)]
            
            bars = ax.bar(metrics, values, color=colors, alpha=0.8, edgecolor='white', linewidth=1)
            
            # Customize chart
            ax.set_title('Key Business Performance Metrics', fontsize=16, fontweight='bold', pad=20)
            ax.set_ylabel('Value', fontsize=12)
            ax.grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.01,
                       f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            chart_path = 'reports/business_metrics_chart.png'
            plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"  - Chart created with {len(metrics)} metrics")
            return chart_path
            
        except Exception as e:
            print(f"  - Chart creation failed: {e}")
            return None

    def _create_custom_styles(self):
        """Create custom paragraph styles for better formatting"""
        styles = getSampleStyleSheet()
        
        # Custom style for bullet points
        styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=6,
            fontSize=10,
            leading=14
        ))
        
        # Custom style for section headers
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Custom style for subsection headers
        styles.add(ParagraphStyle(
            name='SubSectionHeader',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.darkred,
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        return styles

    def _parse_gemini_output_to_pdf_elements(self, insights: str, styles):
        """Parse Gemini output and convert to PDF elements preserving exact formatting"""
        elements = []
        lines = insights.split('\n')
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if not line:  # Empty line
                elements.append(Spacer(1, 6))
                continue
            
            # Check if it's a main section header (with emoji)
            if any(emoji in line for emoji in ['🔥', '⚠️', '🎯', '📈', '⚡']):
                if 'FORCES CLÉS' in line:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'forces'
                elif 'FAIBLESSES CRITIQUES' in line:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'faiblesses'
                elif 'ACTIONS PRIORITAIRES' in line:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'actions'
                elif 'FORECAST' in line or 'PRÉVISIONS' in line:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'forecast'
                elif 'RISQUES' in line or 'VUE D\'ENSEMBLE' in line:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'overview'
                else:
                    elements.append(Paragraph(line, styles['SectionHeader']))
                    current_section = 'other'
                continue
            
            # Check if it's a bullet point
            if line.startswith('•'):
                # Clean the bullet point and format it properly
                bullet_text = line[1:].strip()  # Remove the bullet
                elements.append(Paragraph(f"• {bullet_text}", styles['BulletPoint']))
                continue
            
            # Check if it's a numbered action
            if re.match(r'^\d+\.', line):
                elements.append(Paragraph(line, styles['SubSectionHeader']))
                continue
            
            # Check if it's a sub-bullet or indented content
            if line.startswith('  ') and ('•' in line or ':' in line):
                # This is indented content, format as smaller bullet
                clean_line = line.strip()
                if clean_line.startswith('•'):
                    clean_line = clean_line[1:].strip()
                elements.append(Paragraph(f"    ◦ {clean_line}", styles['Normal']))
                continue
            
            # Check for scenario lines (🔴, 🟡, 🟢)
            if any(emoji in line for emoji in ['🔴', '🟡', '🟢']):
                elements.append(Paragraph(line, styles['SubSectionHeader']))
                continue
            
            # Default: treat as normal paragraph
            if line:
                elements.append(Paragraph(line, styles['Normal']))
        
        return elements

    def _generate_pdf_report(self, analysis: Dict[str, Any], insights: str, chart_path: str) -> str:
        """Generate surgical precision PDF report with exact Gemini formatting"""
        filename = f"reports/analyse_strategique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(filename, pagesize=letter, topMargin=40, bottomMargin=40)
            styles = self._create_custom_styles()
            story = []

            # Title Section
            story.append(Paragraph("📊 ANALYSE STRATÉGIQUE COMMERCIALE", styles['Title']))
            story.append(Paragraph("Rapport de Précision Chirurgicale", styles['Heading2']))
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 30))

            # Executive Dashboard
            story.append(Paragraph("🎯 DASHBOARD EXÉCUTIF", styles['SectionHeader']))
            
            # Key metrics with precise calculations
            dashboard_metrics = []
            if analysis.get("total_sales", 0) > 0:
                sales = analysis["total_sales"]
                dashboard_metrics.append(f"💰 CA Total: {sales:,.0f}€")
                dashboard_metrics.append(f"📅 CA Mensuel: {sales/12:,.0f}€")
                
            if analysis.get("growth_rate", 0) != 0:
                growth = analysis["growth_rate"]
                dashboard_metrics.append(f"📈 Croissance: {growth:+.2f}%")
                if sales > 0:
                    dashboard_metrics.append(f"💎 Gain Croissance: {sales * growth/100:,.0f}€")
                
            if analysis.get("marketing_roi", 0) > 0:
                roi = analysis["marketing_roi"]
                dashboard_metrics.append(f"🎯 ROI Marketing: {roi:.2f}x")
                
            if analysis.get("satisfaction_score", 0) > 0:
                satisfaction = analysis["satisfaction_score"]
                dashboard_metrics.append(f"😊 Satisfaction: {satisfaction:.2f}/5")
                
            if analysis.get("churn_rate", 0) > 0:
                churn = analysis["churn_rate"]
                dashboard_metrics.append(f"⚠️ Attrition: {churn:.2f}%")
                if sales > 0:
                    dashboard_metrics.append(f"💸 Perte Attrition: {sales * churn/100:,.0f}€/an")

            # Add dashboard metrics as bullet points
            for metric in dashboard_metrics:
                story.append(Paragraph(f"• {metric}", styles['BulletPoint']))
            story.append(Spacer(1, 20))

            # Chart
            if chart_path and os.path.exists(chart_path):
                story.append(Paragraph("📊 VUE D'ENSEMBLE PERFORMANCE", styles['SectionHeader']))
                story.append(Image(chart_path, width=500, height=300))
                story.append(Spacer(1, 20))

            # AI Analysis - Use the new parsing method
            story.append(Paragraph("🤖 ANALYSE STRATÉGIQUE IA", styles['SectionHeader']))
            
            # Parse Gemini output and add elements preserving exact formatting
            gemini_elements = self._parse_gemini_output_to_pdf_elements(insights, styles)
            story.extend(gemini_elements)
            story.append(Spacer(1, 20))

            # Precision calculations
            story.append(Paragraph("🔢 CALCULS DE PRÉCISION", styles['SectionHeader']))
            precision_calcs = []
            
            if analysis.get("total_sales", 0) > 0 and analysis.get("growth_rate", 0) != 0:
                sales = analysis["total_sales"]
                growth = analysis["growth_rate"]
                precision_calcs.append(f"Projection 6M (croissance actuelle): {sales * (1 + growth/100)**0.5:,.0f}€")
                precision_calcs.append(f"Potentiel si croissance +5%: {sales * (1 + (growth+5)/100)**0.5:,.0f}€")
                precision_calcs.append(f"Écart de performance: {sales * 5/100:,.0f}€")
            
            if analysis.get("marketing_roi", 0) > 0 and analysis.get("total_leads", 0) > 0:
                roi = analysis["marketing_roi"]
                leads = analysis["total_leads"]
                precision_calcs.append(f"Optimisation ROI +1x = +{leads * 1000:,.0f}€ CA potentiel")
                
            if analysis.get("churn_rate", 0) > 0 and analysis.get("total_sales", 0) > 0:
                churn = analysis["churn_rate"]
                sales = analysis["total_sales"]
                target_churn = 12  # Industry benchmark
                precision_calcs.append(f"Réduction churn à {target_churn}% = +{sales * (churn-target_churn)/100:,.0f}€ préservés")

            if precision_calcs:
                for calc in precision_calcs:
                    story.append(Paragraph(f"• {calc}", styles['BulletPoint']))

            # Build the PDF
            doc.build(story)
            print(f"  - ✅ Rapport stratégique sauvegardé: {filename}")
            return filename
            
        except Exception as e:
            print(f"  - ❌ Échec génération PDF: {e}")
            # Fallback to text report with surgical analysis
            fallback_path = f"reports/analyse_strategique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(f"📊 ANALYSE STRATÉGIQUE COMMERCIALE\n")
                f.write(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n")
                f.write("="*60 + "\n\n")
                
                f.write("🎯 MÉTRIQUES CLÉS:\n")
                for key, value in analysis.items():
                    if value and value != "N/A" and value != 0:
                        f.write(f"  • {key}: {value}\n")
                
                f.write(f"\n🤖 ANALYSE IA:\n{insights}\n")
                
            return fallback_path

    def _format_surgical_insights_for_pdf(self, insights: str) -> str:
        """DEPRECATED - This method is no longer needed with the new parsing approach"""
        # This method is kept for backward compatibility but is not used
        return insights