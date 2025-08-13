import google.generativeai as genai
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os
import re
import hashlib
import requests
import pandas as pd
import io  # Added io import for StringIO
import os
import requests
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import google.generativeai as genai
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

class RecommendationAgent:
    def __init__(self, gemini_api_key: str = None):
        if gemini_api_key is None:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        os.makedirs('reports', exist_ok=True)
        self.insights_cache = {}
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.cache = {}
        self._cached_analysis = None
        self._cached_five_forces = None
        
        self.data_urls = {
            'product_performance': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/product_performance-EfI5rRMJcUIca0pVlaSrfDPCOU1zqp.csv',
            'financial_kpis': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/financial_kpis-M7T83co0K78tQU7WwkKn41tOHxOhZW.csv',
            'competitive_analysis': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/competitive_analysis-gM8Zv16lIR5hRALDBAYT0H2j9C1bST.csv',
            'customer_segments': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/customer_segments-2pXkDtN7FYkkzZoyGUyFR38qGb4dKB.csv',
            'commercial_performance': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/commercial_performance-IDMtD5DY6YOdzFvTI7CQ3NN40FYx8J.csv',
            'marketing_spend_performance': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/marketing_spend_performance-qu3JJ2yint7wkpyEu7vvVKuTJbeC42.csv',
            'sales_funnel_metrics': 'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/sales_funnel_metrics-ZqFaWXvtu5BQC5yVwcjfNb2StQVblC.csv'
        }

    def generate_report(self, sql_results, feedback: Optional[str] = None, iteration: int = 1) -> Tuple[str, str]:
        print("Starting report generation...")
        
        # Process data and cache it for consistency
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
        
        analysis = self._process_enhanced_data(analysis)
        five_forces_analysis = self._analyze_five_forces_enhanced(analysis)
        
        # Cache the processed data for subsequent iterations
        self._cached_analysis = analysis.copy()  # Store a copy
        self._cached_five_forces = five_forces_analysis.copy()  # Store a copy
        
        cache_key = self._generate_cache_key(analysis)
        if cache_key in self.insights_cache and iteration == 1:  # Only use cache on first iteration
            insights = self.insights_cache[cache_key]
        else:
            insights = self._generate_ai_insights(analysis, five_forces_analysis, feedback, iteration)
            self.insights_cache[cache_key] = insights
        
        pdf_path = self._generate_pdf_report(analysis, insights, five_forces_analysis)
        print(f"Report generated: {pdf_path}")
        
        return pdf_path, insights
    def _fetch_csv_data(self, data_type: str) -> Optional[pd.DataFrame]:
        """Fetch CSV data from URLs"""
        try:
            if data_type in self.data_urls:
                response = requests.get(self.data_urls[data_type])
                if response.status_code == 200:
                    return pd.read_csv(self.data_urls[data_type])
        except Exception as e:
            print(f"Error fetching {data_type} data: {e}")
        return None

    def _process_enhanced_data(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced data processing with CSV data fetching and company/industry extraction"""
        try:
            csv_data = self._fetch_all_csv_data()
            
            if not csv_data or all(df.empty for df in csv_data.values()):
                print("CSV data fetching failed, using fallback metrics")
                return self._get_fallback_metrics(analysis)
            
            enhanced_metrics = self._calculate_enhanced_metrics(csv_data)
            analysis.update(enhanced_metrics)
            
            company_info = self._extract_company_info(csv_data)
            analysis.update(company_info)
            
            return analysis
        except Exception as e:
            print(f"Enhanced data processing failed: {e}")
            return self._get_fallback_metrics(analysis)

    def _get_fallback_metrics(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Provide consistent fallback metrics when CSV data is unavailable"""
        fallback_data = {
            'company_name': 'TechCorp Solutions',
            'industry': 'Technology Services',
            'market_share': 28.5,
            'market_growth_rate': 23.2,
            'profit_margin': 70.1,
            'customer_satisfaction': 4.2,
            'churn_rate': 20.1,
            'revenue': 28850000,
            'competitive_pressure': 7.1,
            'total_sales': 28850000,
            'growth_rate': 9.5,
            'marketing_roi': 5.6,
            'satisfaction_score': 4.2
        }
        
        analysis.update(fallback_data)
        return analysis

    def _fetch_all_csv_data(self) -> Dict[str, pd.DataFrame]:
        """Fetch all CSV data from URLs"""
        csv_data = {}
        success_count = 0
        
        for name, url in self.data_urls.items():
            try:
                response = requests.get(url, timeout=15)  # Increased timeout
                response.raise_for_status()
                df = pd.read_csv(io.StringIO(response.text))
                csv_data[name] = df
                success_count += 1
                print(f"✓ Fetched {name}: {len(df)} rows")
            except Exception as e:
                print(f"✗ Failed to fetch {name}: {e}")
                csv_data[name] = pd.DataFrame()
        
        print(f"CSV fetch success rate: {success_count}/{len(self.data_urls)}")
        return csv_data

    def _extract_company_info(self, csv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:  # Accept csv_data parameter
        """Extract company name and industry from CSV data"""
        company_info = {
            'company_name': 'TechCorp Solutions',  # Default fallback
            'industry': 'Technology Services'      # Default fallback
        }
        
        try:
            if 'commercial_performance' in csv_data and not csv_data['commercial_performance'].empty:
                df = csv_data['commercial_performance']
                if 'product_category' in df.columns:
                    categories = df['product_category'].unique()
                    if 'CRM Solutions' in categories:
                        company_info['company_name'] = 'CRM Solutions Inc'
                        company_info['industry'] = 'Software & Technology'
                    elif 'ERP Systems' in categories:
                        company_info['company_name'] = 'Enterprise Systems Corp'
                        company_info['industry'] = 'Enterprise Software'
            
            if 'customer_segments' in csv_data and not csv_data['customer_segments'].empty:
                df = csv_data['customer_segments']
                if 'industry_focus' in df.columns:
                    industries = df['industry_focus'].unique()
                    if len(industries) > 0 and industries[0] != 'Mixed':
                        company_info['industry'] = industries[0]
                        
        except Exception as e:
            print(f"Company info extraction failed: {e}")
            
        return company_info

    def _calculate_enhanced_metrics(self, csv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate enhanced metrics from CSV data"""
        metrics = {}
        
        try:
            if 'competitive_analysis' in csv_data and not csv_data['competitive_analysis'].empty:
                df = csv_data['competitive_analysis']
                if 'market_share_percent' in df.columns:
                    # Assume first row is our company
                    our_market_share = self._safe_float(df.iloc[0]['market_share_percent'])
                    metrics['market_share'] = our_market_share
                    
                    # Calculate market growth rate
                    if 'market_growth_rate_percent' in df.columns:
                        market_growth = df['market_growth_rate_percent'].apply(self._safe_float).mean()
                        metrics['market_growth_rate'] = market_growth

            if 'commercial_performance' in csv_data and not csv_data['commercial_performance'].empty:
                df = csv_data['commercial_performance']
                if 'gross_margin_percent' in df.columns:
                    profit_margin = df['gross_margin_percent'].apply(self._safe_float).mean()
                    metrics['profit_margin'] = profit_margin
                    
                # Customer satisfaction from commercial data
                if 'customer_satisfaction_score' in df.columns:
                    satisfaction = df['customer_satisfaction_score'].apply(self._safe_float).mean()
                    metrics['customer_satisfaction_commercial'] = satisfaction

            if 'customer_segments' in csv_data and not csv_data['customer_segments'].empty:
                df = csv_data['customer_segments']
                if 'churn_rate_percent' in df.columns:
                    churn_rate = df['churn_rate_percent'].apply(self._safe_float).mean()
                    metrics['churn_rate'] = churn_rate
                    
                # Customer satisfaction from segments
                if 'satisfaction_score' in df.columns:
                    satisfaction = df['satisfaction_score'].apply(self._safe_float).mean()
                    metrics['satisfaction_score'] = satisfaction

            if 'commercial_performance' in csv_data and not csv_data['commercial_performance'].empty:
                df = csv_data['commercial_performance']
                if 'brand_awareness_percent' in df.columns:
                    brand_awareness = df['brand_awareness_percent'].apply(self._safe_float).mean()
                    metrics['brand_awareness'] = brand_awareness
                    
                if 'innovation_score' in df.columns:
                    innovation = df['innovation_score'].apply(self._safe_float).mean()
                    metrics['innovation_index'] = innovation

            if 'product_performance' in csv_data and not csv_data['product_performance'].empty:
                df = csv_data['product_performance']
                if 'customer_rating' in df.columns:
                    product_rating = df['customer_rating'].apply(self._safe_float).mean()
                    metrics['product_rating'] = product_rating

        except Exception as e:
            print(f"Enhanced metrics calculation failed: {e}")
            
        return metrics

    def _safe_float(self, value) -> float:
        """Safely convert value to float, handling strings with % signs"""
        try:
            if value is None or value == '':
                return 0.0
            if isinstance(value, str):
                # Remove % sign and convert
                value = value.replace('%', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _analyze_csv_data(self) -> Dict[str, Any]:
        """Analyze CSV data to calculate real business metrics"""
        metrics = {}
        
        try:
            csv_data = self._fetch_all_csv_data()
            company_info = self._extract_company_info(csv_data)
            metrics.update(company_info)
            
            # Analyze competitive data
            if 'competitive_analysis' in csv_data and not csv_data['competitive_analysis'].empty:
                competitive_df = csv_data['competitive_analysis']
                market_shares = []
                growth_rates = []
                
                for _, row in competitive_df.iterrows():
                    # Handle market share
                    market_share_str = str(row.get('market_share_percent', '0'))
                    market_share = float(market_share_str.replace('%', '')) if market_share_str != 'nan' else 0
                    market_shares.append(market_share)
                    
                    # Handle growth rate
                    growth_rate_str = str(row.get('market_growth_rate_percent', '0'))
                    growth_rate = float(growth_rate_str.replace('%', '')) if growth_rate_str != 'nan' else 0
                    growth_rates.append(growth_rate)
                
                # Use the first row as "our company" data
                our_market_share = market_shares[0] if market_shares else 0
                avg_growth_rate = sum(growth_rates) / len(growth_rates) if growth_rates else 0
                
                metrics.update({
                    'market_share': our_market_share,
                    'market_growth_rate': avg_growth_rate,
                    'competitive_pressure': self._safe_float(competitive_df.iloc[0].get('competitive_pressure_score', 0)) if len(competitive_df) > 0 else 0
                })

            # Analyze commercial performance
            if 'commercial_performance' in csv_data and not csv_data['commercial_performance'].empty:
                commercial_df = csv_data['commercial_performance']
                gross_margins = []
                satisfaction_scores = []
                
                for _, row in commercial_df.iterrows():
                    gross_margin = self._safe_float(row.get('gross_margin_percent', 0))
                    gross_margins.append(gross_margin)
                    
                    satisfaction = self._safe_float(row.get('customer_satisfaction_score', 0))
                    satisfaction_scores.append(satisfaction)
                
                metrics.update({
                    'gross_margin': sum(gross_margins) / len(gross_margins) if gross_margins else 0,
                    'customer_satisfaction_commercial': sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
                    'brand_awareness': self._safe_float(commercial_df.iloc[0].get('brand_awareness_percent', 0)) if len(commercial_df) > 0 else 0
                })

            # Analyze customer segments
            if 'customer_segments' in csv_data and not csv_data['customer_segments'].empty:
                customer_df = csv_data['customer_segments']
                churn_rates = []
                satisfaction_scores = []
                renewal_rates = []
                
                for _, row in customer_df.iterrows():
                    churn_str = str(row.get('churn_rate_percent', '0'))
                    churn_rate = float(churn_str.replace('%', '')) if churn_str != 'nan' else 0
                    churn_rates.append(churn_rate)
                    
                    satisfaction_str = str(row.get('satisfaction_score', '0'))
                    satisfaction = float(satisfaction_str) if satisfaction_str != 'nan' else 0
                    satisfaction_scores.append(satisfaction)
                    
                    renewal_str = str(row.get('renewal_rate_percent', '0'))
                    renewal_rate = float(renewal_str.replace('%', '')) if renewal_str != 'nan' else 0
                    renewal_rates.append(renewal_rate)
                
                metrics.update({
                    'churn_rate': sum(churn_rates) / len(churn_rates) if churn_rates else 0,
                    'satisfaction_score': sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
                    'renewal_rate': sum(renewal_rates) / len(renewal_rates) if renewal_rates else 0,
                    'avg_ltv': self._safe_float(customer_df['lifetime_value'].mean()) if 'lifetime_value' in customer_df.columns else 0
                })

            # Analyze product performance
            if 'product_performance' in csv_data and not csv_data['product_performance'].empty:
                product_df = csv_data['product_performance']  # Use fetched data instead of calling method
                profit_margins = []
                ratings = []
                
                for _, row in product_df.iterrows():
                    profit_margin = self._safe_float(row.get('profit_margin_percent', 0))
                    profit_margins.append(profit_margin)
                    
                    rating = self._safe_float(row.get('customer_rating', 0))
                    ratings.append(rating)
                
                metrics.update({
                    'profit_margin': sum(profit_margins) / len(profit_margins) if profit_margins else 0,
                    'product_rating': sum(ratings) / len(ratings) if ratings else 0,
                    'innovation_index': self._safe_float(product_df['innovation_index'].mean()) if 'innovation_index' in product_df.columns else 0
                })

            # Analyze financial KPIs
            if 'financial_kpis' in csv_data and not csv_data['financial_kpis'].empty:
                financial_df = csv_data['financial_kpis']  # Use fetched data instead of calling method
                # Extract specific KPIs
                for _, row in financial_df.iterrows():
                    metric_name = str(row['metric']).lower().replace(' ', '_').replace('score', '').replace('rate', '');
                    current_value = self._safe_float(row['current_value'])
                    metrics[f'kpi_{metric_name}'] = current_value

        except Exception as e:
            print(f"Error analyzing CSV data: {e}")
        
        return metrics

    def _extract_company_info(self, csv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Extract company name and industry from CSV data"""
        company_info = {
            'company_name': 'TechCorp Solutions',  # Default fallback
            'industry': 'Technology Services'      # Default fallback
        }
        
        try:
            # Try to extract from product performance data
            if 'product_performance' in csv_data and not csv_data['product_performance'].empty:
                product_df = csv_data['product_performance']
                if product_df is not None and len(product_df) > 0:
                    # Infer industry from product lines
                    product_lines = product_df['product_line'].tolist() if 'product_line' in product_df.columns else []
                    if product_lines:
                        if any('compliance' in str(p).lower() for p in product_lines):
                            company_info['industry'] = 'Compliance & Risk Management'
                        elif any('crm' in str(p).lower() for p in product_lines):
                            company_info['industry'] = 'Customer Relationship Management'
                        elif any('analytics' in str(p).lower() for p in product_lines):
                            company_info['industry'] = 'Business Analytics'
                        else:
                            company_info['industry'] = 'Enterprise Software'
            
            # Try to extract from customer segments
            if 'customer_segments' in csv_data and not csv_data['customer_segments'].empty:
                customer_df = csv_data['customer_segments']
                if customer_df is not None and len(customer_df) > 0:
                    segments = customer_df['segment'].tolist() if 'segment' in customer_df.columns else []
                    if segments:
                        # Infer company focus from customer segments
                        if 'telecommunications' in str(segments).lower():
                            company_info['company_name'] = 'TelecomTech Solutions'
                        elif 'healthcare' in str(segments).lower():
                            company_info['company_name'] = 'HealthTech Systems'
                        elif 'financial' in str(segments).lower():
                            company_info['company_name'] = 'FinTech Solutions'
                        else:
                            company_info['company_name'] = 'Enterprise Solutions Inc'
                        
        except Exception as e:
            print(f"Error extracting company info: {e}")
        
        return company_info

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

    def _analyze_five_forces_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Enhanced Porter's Five Forces analysis using real data"""
        
        forces = {
            "competitive_rivalry": self._assess_competitive_rivalry_enhanced(analysis),
            "threat_of_new_entrants": self._assess_threat_of_new_entrants_enhanced(analysis),
            "bargaining_power_suppliers": self._assess_supplier_power_enhanced(analysis),
            "bargaining_power_buyers": self._assess_buyer_power_enhanced(analysis),
            "threat_of_substitutes": self._assess_threat_of_substitutes_enhanced(analysis)
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

    def _assess_competitive_rivalry_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced competitive rivalry assessment"""
        market_share = analysis.get("market_share", 0)
        growth_rate = analysis.get("market_growth_rate", 0)
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
                f"Market share: {market_share:.1f}%",
                f"Industry growth: {growth_rate:.1f}%",
                f"Profit margins: {profit_margin:.1f}%"
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

    def _assess_threat_of_new_entrants_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        growth_rate = analysis.get("market_growth_rate", 0)
        profit_margin = analysis.get("profit_margin", analysis.get("gross_margin", 0))
        brand_awareness = analysis.get("brand_awareness", 0)
        
        intensity_score = 0
        if growth_rate > 15: intensity_score += 1
        if profit_margin > 25: intensity_score += 1
        if brand_awareness < 60: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Market attractiveness (growth): {growth_rate:.1f}%",
                f"Profitability signal: {profit_margin:.1f}%"
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

    def _assess_supplier_power_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        profit_margin = analysis.get("profit_margin", analysis.get("gross_margin", 0))
        
        intensity_score = 0
        if profit_margin < 15: intensity_score += 1
        if profit_margin < 10: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Margin pressure indicator: {profit_margin:.1f}%"
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

    def _assess_buyer_power_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced buyer power assessment"""
        customer_satisfaction = analysis.get("satisfaction_score", analysis.get("customer_satisfaction_commercial", 0))
        churn_rate = analysis.get("churn_rate", 0)
        
        intensity_score = 0
        if customer_satisfaction < 3.5: intensity_score += 1
        if churn_rate > 15: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 2 else "MEDIUM" if intensity_score == 1 else "LOW"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Customer satisfaction: {customer_satisfaction:.1f}/5",
                f"Churn rate: {churn_rate:.1f}%"
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

    def _assess_threat_of_substitutes_enhanced(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced threat of substitutes assessment"""
        product_rating = analysis.get("product_rating", 0)
        innovation_index = analysis.get("innovation_index", 0)
        
        intensity_score = 0
        if product_rating < 3.5: intensity_score += 1
        if innovation_index < 6: intensity_score += 1
        
        intensity = "HIGH" if intensity_score >= 1 else "MEDIUM"
        
        return {
            "intensity": intensity,
            "score": intensity_score,
            "factors": [
                f"Product competitiveness: {product_rating:.1f}/5"
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

    def _generate_ai_insights(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]], feedback: Optional[str] = None, iteration: int = 1) -> str:
        company_name = analysis.get('company_name', 'Our Company')
        industry = analysis.get('industry', 'Technology Services')
        
        context = f"""
        COMPANY: {company_name}
        INDUSTRY: {industry}
        
        PERFORMANCE METRICS:
        - Market Share: {analysis.get('market_share', 0):.1f}%
        - Revenue Growth: {analysis.get('market_growth_rate', 0):.1f}%
        - Profit Margin: {analysis.get('profit_margin', analysis.get('gross_margin', 0)):.1f}%
        - Customer Satisfaction: {analysis.get('satisfaction_score', analysis.get('customer_satisfaction_commercial', 0)):.1f}/5
        - Churn Rate: {analysis.get('churn_rate', 0):.1f}%
        - Brand Awareness: {analysis.get('brand_awareness', 0):.1f}%
        - Innovation Index: {analysis.get('innovation_index', 0):.1f}/10
        """

        context_metrics = []
        
        if analysis.get("market_share", 0) > 0:
            context_metrics.append(f"Market Share: {analysis['market_share']:.1f}%")
        if analysis.get("profit_margin", 0) > 0:
            context_metrics.append(f"Profit Margin: {analysis['profit_margin']:.1f}%")
        if analysis.get("satisfaction_score", 0) > 0:
            context_metrics.append(f"Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5")
        if analysis.get("churn_rate", 0) > 0:
            context_metrics.append(f"Churn Rate: {analysis['churn_rate']:.1f}%")
        if analysis.get("market_growth_rate", 0) > 0:
            context_metrics.append(f"Market Growth: {analysis['market_growth_rate']:.1f}%")
        
        context = "; ".join(context_metrics)
        
        forces_context = []
        for force_name, force_data in five_forces.items():
            forces_context.append(f"{force_name.replace('_', ' ').title()}: {force_data['intensity']}")
        
        forces_summary = "; ".join(forces_context)
        
        feedback_context = f"\n\nPREVIOUS FEEDBACK TO ADDRESS: {feedback}" if feedback else ""
        iteration_context = f" (Iteration {iteration})" if iteration > 1 else ""
        
        prompt = f"""
        Generate a professional business analysis report{iteration_context} based on the following data. 
        
        BUSINESS METRICS: {context}
        COMPETITIVE FORCES: {forces_summary}{feedback_context}
        
        Structure your analysis as follows:
        
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
        
        IMPORTANT: Provide ONLY the business analysis content. Do not include any conversational phrases like "I will generate", "Okay", "Based on your request", or similar AI response text. Start directly with the analysis content using the structure above.
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                cleaned_response = self._clean_ai_response(response.text)
                return cleaned_response
            else:
                return self._generate_fallback_analysis(analysis, five_forces)
        except Exception as e:
            print(f"AI insight generation failed: {e}")
            return self._generate_fallback_analysis(analysis, five_forces)

    def _clean_ai_response(self, response: str) -> str:
        """Clean AI response to remove conversational elements"""
        conversational_phrases = [
            "I will generate", "Okay, I will", "Based on your request",
            "Here is a comprehensive", "Let me provide", "As requested",
            "Following your instructions", "I'll create", "Based on the data provided"
        ]
        
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append('')
                continue
                
            # Skip lines that start with conversational phrases
            line_lower = line.lower()
            is_conversational = any(phrase.lower() in line_lower[:50] for phrase in conversational_phrases)
            
            if not is_conversational:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

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
            name='CompanyTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#1a202c'),
            spaceAfter=12,
            alignment=1,  # Center alignment
            fontName='Helvetica-Bold',
            borderWidth=2,
            borderColor=colors.HexColor('#3182ce'),
            borderPadding=12
        ))
        
        styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#718096'),
            spaceAfter=25,
            alignment=1,  # Center alignment
            fontName='Helvetica-Oblique'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=15,
            spaceBefore=25,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#f7fafc'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=10,
            leftIndent=5
        ))
        
        styles.add(ParagraphStyle(
            name='SubSectionHeader',
            parent=styles['Heading3'],
            fontSize=13,
            textColor=colors.HexColor('#2b6cb0'),
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold',
            leftIndent=10
        ))
        
        styles.add(ParagraphStyle(
            name='MetricItem',
            parent=styles['Normal'],
            leftIndent=25,
            fontSize=11,
            leading=18,
            spaceAfter=6,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='ForceAnalysis',
            parent=styles['Normal'],
            leftIndent=20,
            fontSize=10,
            leading=16,
            spaceAfter=4,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='CleanBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=18,
            spaceAfter=10,
            textColor=colors.HexColor('#2d3748'),
            alignment=0,  # Left alignment
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='HighlightBox',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            spaceBefore=8,
            textColor=colors.HexColor('#1a365d'),
            backColor=colors.HexColor('#ebf8ff'),
            borderWidth=1,
            borderColor=colors.HexColor('#3182ce'),
            borderPadding=8,
            leftIndent=10,
            rightIndent=10
        ))
        
        return styles

    def _clean_ai_artifacts(self, text: str) -> str:
        """Remove AI conversational artifacts and clean up text"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            if any(starter in line.lower() for starter in [
                'okay, i will', 'i will generate', 'based on your request',
                'let me provide', 'here is', 'i can see', 'looking at',
                'based on the data provided', 'according to', 'i notice',
                'given the data', 'analyzing the', 'from the information',
                'the analysis shows', 'it appears that', 'we can see that'
            ]):
                continue
                
            # Skip empty lines and very short lines
            if len(line) < 3:
                continue
                
            line = line.replace('**', '').replace('*', '•')
            line = line.replace('###', '').replace('##', '')
            line = re.sub(r'\[.*?\]', '', line)  # Remove all bracketed placeholders
            
            # Remove redundant spacing
            line = re.sub(r'\s+', ' ', line).strip()
            
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def _generate_pdf_report(self, analysis: Dict[str, Any], insights: str, five_forces: Dict[str, Dict[str, Any]]) -> str:
        filename = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(
                filename, 
                pagesize=letter, 
                topMargin=60, 
                bottomMargin=60,
                leftMargin=70,
                rightMargin=70
            )
            styles = self._create_custom_styles()
            story = []

            story.append(Paragraph("STRATEGIC BUSINESS ANALYSIS", styles['CompanyTitle']))
            story.append(Paragraph(f"Executive Report • {datetime.now().strftime('%B %d, %Y')}", styles['ReportSubtitle']))
            story.append(Spacer(1, 35))

            story.append(Paragraph("EXECUTIVE SUMMARY", styles['SectionHeader']))
            
            summary_metrics = []
            if analysis.get("total_sales", 0) > 0:
                summary_metrics.append(f"Revenue: ${analysis['total_sales']:,.0f}")
            if analysis.get("growth_rate", 0) != 0:
                summary_metrics.append(f"Growth: {analysis['growth_rate']:.1f}%")
            if analysis.get("marketing_roi", 0) > 0:
                summary_metrics.append(f"Marketing ROI: {analysis['marketing_roi']:.1f}x")
            if analysis.get("satisfaction_score", 0) > 0:
                summary_metrics.append(f"Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5.0")
            
            if summary_metrics:
                story.append(Paragraph(" • ".join(summary_metrics), styles['HighlightBox']))
            
            story.append(Spacer(1, 20))

            story.append(Paragraph("COMPETITIVE LANDSCAPE ANALYSIS", styles['SectionHeader']))
            
            for force_name, force_data in five_forces.items():
                force_title = force_name.replace('_', ' ').title()
                
                # Color-code intensity levels
                intensity_color = colors.HexColor('#e53e3e') if force_data['intensity'] == 'HIGH' else \
                                colors.HexColor('#d69e2e') if force_data['intensity'] == 'MEDIUM' else \
                                colors.HexColor('#38a169')
                
                story.append(Paragraph(f"<b>{force_title}:</b> <font color='{intensity_color}'>{force_data['intensity']}</font>", styles['SubSectionHeader']))
                
                for factor in force_data['factors']:
                    if factor.strip():
                        story.append(Paragraph(f"• {factor}", styles['ForceAnalysis']))
                
                story.append(Paragraph(f"<b>Strategic Response:</b> {force_data['recommendation']}", styles['ForceAnalysis']))
                story.append(Spacer(1, 12))

            story.append(Spacer(1, 20))

            story.append(Paragraph("STRATEGIC INSIGHTS & RECOMMENDATIONS", styles['SectionHeader']))
            
            cleaned_insights = self._clean_ai_artifacts(insights)
            insight_lines = cleaned_insights.split('\n')
            
            for line in insight_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect and style section headers
                if any(header in line.upper() for header in [
                    'STRATEGIC POSITION', 'FIVE FORCES', 'RECOMMENDATIONS', 
                    'FINANCIAL PROJECTIONS', 'IMPLEMENTATION', 'ROADMAP'
                ]):
                    story.append(Spacer(1, 15))
                    story.append(Paragraph(line.upper(), styles['SubSectionHeader']))
                elif line.startswith('•') or line.startswith('-'):
                    story.append(Paragraph(line, styles['ForceAnalysis']))
                elif ':' in line and len(line) < 100:  # Likely a key-value pair
                    story.append(Paragraph(f"<b>{line}</b>", styles['MetricItem']))
                else:
                    story.append(Paragraph(line, styles['CleanBody']))

            doc.build(story)
            return filename
        
        except Exception as e:
            print(f"PDF generation failed: {e}")
            fallback_path = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write("STRATEGIC BUSINESS ANALYSIS\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}\n\n")
                
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 20 + "\n")
                for key, value in analysis.items():
                    if value and value != "N/A" and value != 0:
                        f.write(f"• {key.replace('_', ' ').title()}: {value}\n")
                
                f.write(f"\nCOMPETITIVE ANALYSIS\n")
                f.write("-" * 20 + "\n")
                for force_name, force_data in five_forces.items():
                    f.write(f"• {force_name.replace('_', ' ').title()}: {force_data['intensity']}\n")
                    f.write(f"  Recommendation: {force_data['recommendation']}\n\n")
                
                f.write(f"STRATEGIC INSIGHTS\n")
                f.write("-" * 20 + "\n")
                f.write(self._clean_ai_artifacts(insights))
                
            return fallback_path

    def improve_report_with_feedback(self, sql_results: str, judge_feedback: str, iteration: int) -> Tuple[str, str]:
        """Improve the report based on judge feedback - FIXED VERSION"""
        print(f"🔄 Recommendation Agent: Improving report based on feedback (iteration {iteration})")
        
        # USE THE SAME DATA PROCESSING PIPELINE AS INITIAL GENERATION
        # This ensures consistency in data and structure
        
        if self._cached_analysis is not None and self._cached_five_forces is not None:
            # Use cached data to ensure consistency
            analysis = self._cached_analysis.copy()
            five_forces_analysis = self._cached_five_forces.copy()
            print("✅ Using cached analysis data for consistency")
        else:
            # Fallback: reprocess the data using the same pipeline as generate_report
            print("⚠️  No cached data, reprocessing...")
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
            
            # IMPORTANT: Use the same enhanced processing as initial generation
            analysis = self._process_enhanced_data(analysis)
            five_forces_analysis = self._analyze_five_forces_enhanced(analysis)  # Use ENHANCED version
            
            # Cache for future iterations
            self._cached_analysis = analysis.copy()
            self._cached_five_forces = five_forces_analysis.copy()
        
        # Generate improved insights based on feedback BUT with same underlying data
        improved_insights = self._generate_improved_insights_with_feedback(
            analysis, five_forces_analysis, judge_feedback, iteration
        )
        
        # Generate improved PDF report with SAME data structure
        pdf_path = self._generate_improved_pdf_report(
            analysis, improved_insights, five_forces_analysis, judge_feedback, iteration
        )
        
        print(f"🔄 Improved report generated: {pdf_path}")
        return pdf_path, improved_insights

    def _generate_improved_insights_with_feedback(self, analysis: Dict[str, Any], five_forces: Dict[str, Dict[str, Any]], 
                                                 judge_feedback: str, iteration: int) -> str:
        """Generate improved insights incorporating judge feedback"""
        
        # Extract key improvement areas from judge feedback
        improvement_areas = self._extract_improvement_areas(judge_feedback)
        
        # ENSURE CONSISTENT COMPANY INFO USAGE
        company_name = analysis.get('company_name', 'TechCorp Solutions')
        industry = analysis.get('industry', 'Technology Services')
        
        # Build consistent context using the SAME metrics as initial generation
        context_metrics = []
        if analysis.get("market_share", 0) > 0:
            context_metrics.append(f"Market Share: {analysis['market_share']:.1f}%")
        if analysis.get("market_growth_rate", 0) > 0:
            context_metrics.append(f"Market Growth: {analysis['market_growth_rate']:.1f}%")
        if analysis.get("profit_margin", analysis.get("gross_margin", 0)) > 0:
            profit_margin = analysis.get("profit_margin", analysis.get("gross_margin", 0))
            context_metrics.append(f"Profit Margin: {profit_margin:.1f}%")
        if analysis.get("satisfaction_score", analysis.get("customer_satisfaction_commercial", 0)) > 0:
            satisfaction = analysis.get("satisfaction_score", analysis.get("customer_satisfaction_commercial", 0))
            context_metrics.append(f"Customer Satisfaction: {satisfaction:.1f}/5")
        if analysis.get("churn_rate", 0) > 0:
            context_metrics.append(f"Churn Rate: {analysis['churn_rate']:.1f}%")
        
        context = "; ".join(context_metrics) if context_metrics else "Limited metrics available"
        
        # Build forces context consistently
        forces_context = []
        for force_name, force_data in five_forces.items():
            forces_context.append(f"{force_name.replace('_', ' ').title()}: {force_data['intensity']}")
        forces_summary = "; ".join(forces_context)
        
        prompt = f"""
        ENHANCED STRATEGIC BUSINESS ANALYSIS - ITERATION {iteration}
        
        COMPANY: {company_name}
        INDUSTRY: {industry}
        
        PERFORMANCE METRICS: {context}
        COMPETITIVE FORCES: {forces_summary}
        
        PREVIOUS ANALYSIS FEEDBACK TO ADDRESS:
        {judge_feedback}
        
        IMPROVEMENT FOCUS AREAS:
        {chr(10).join(f"• {area}" for area in improvement_areas)}
        
        GENERATE AN ENHANCED VERSION of the strategic analysis that addresses the feedback while maintaining the same data foundation and structure. Focus on:
        
        1. STRATEGIC POSITION
        • Provide more specific, data-driven insights using the exact metrics above
        • Enhance competitive advantage analysis with concrete examples
        • Detail performance drivers with quantified impact
        
        2. FIVE FORCES IMPACT
        • Deepen analysis of each force using {company_name}'s specific situation
        • Provide industry-specific strategic vulnerabilities
        • Connect market dynamics to profitability impact
        
        3. STRATEGIC RECOMMENDATIONS
        • Make recommendations more specific and actionable
        • Include implementation timelines and resource requirements
        • Prioritize based on current capabilities and market position
        
        4. FINANCIAL PROJECTIONS
        • Provide more detailed scenarios with specific assumptions
        • Include risk factors with mitigation strategies
        • Reference historical performance trends
        
        CRITICAL: Use the SAME underlying data and company information. Only improve the analysis depth, specificity, and actionability - do NOT change the fundamental metrics or company details.
        """
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                cleaned_response = self._clean_ai_response(response.text)
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
        filename = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        try:
            doc = SimpleDocTemplate(
                filename, 
                pagesize=letter, 
                topMargin=60, 
                bottomMargin=60,
                leftMargin=70,
                rightMargin=70
            )
            styles = self._create_custom_styles()
            story = []

            story.append(Paragraph("STRATEGIC BUSINESS ANALYSIS", styles['CompanyTitle']))
            story.append(Paragraph(f"Executive Report • {datetime.now().strftime('%B %d, %Y')}", styles['ReportSubtitle']))
            story.append(Spacer(1, 35))

            story.append(Paragraph("EXECUTIVE SUMMARY", styles['SectionHeader']))
            
            summary_metrics = []
            if analysis.get("total_sales", 0) > 0:
                summary_metrics.append(f"Revenue: ${analysis['total_sales']:,.0f}")
            if analysis.get("growth_rate", 0) != 0:
                summary_metrics.append(f"Growth: {analysis['growth_rate']:.1f}%")
            if analysis.get("marketing_roi", 0) > 0:
                summary_metrics.append(f"Marketing ROI: {analysis['marketing_roi']:.1f}x")
            if analysis.get("satisfaction_score", 0) > 0:
                summary_metrics.append(f"Customer Satisfaction: {analysis['satisfaction_score']:.1f}/5.0")
            
            if summary_metrics:
                story.append(Paragraph(" • ".join(summary_metrics), styles['HighlightBox']))
            
            story.append(Spacer(1, 20))

            story.append(Paragraph("COMPETITIVE LANDSCAPE ANALYSIS", styles['SectionHeader']))
            
            for force_name, force_data in five_forces.items():
                force_title = force_name.replace('_', ' ').title()
                
                # Color-code intensity levels
                intensity_color = colors.HexColor('#e53e3e') if force_data['intensity'] == 'HIGH' else \
                                colors.HexColor('#d69e2e') if force_data['intensity'] == 'MEDIUM' else \
                                colors.HexColor('#38a169')
                
                story.append(Paragraph(f"<b>{force_title}:</b> <font color='{intensity_color}'>{force_data['intensity']}</font>", styles['SubSectionHeader']))
                
                for factor in force_data['factors']:
                    if factor.strip():
                        story.append(Paragraph(f"• {factor}", styles['ForceAnalysis']))
                
                story.append(Paragraph(f"<b>Strategic Response:</b> {force_data['recommendation']}", styles['ForceAnalysis']))
                story.append(Spacer(1, 12))

            story.append(Spacer(1, 20))

            story.append(Paragraph("STRATEGIC INSIGHTS & RECOMMENDATIONS", styles['SectionHeader']))
            
            cleaned_insights = self._clean_ai_artifacts(insights)
            insight_lines = cleaned_insights.split('\n')
            
            for line in insight_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect and style section headers
                if any(header in line.upper() for header in [
                    'STRATEGIC POSITION', 'FIVE FORCES', 'RECOMMENDATIONS', 
                    'FINANCIAL PROJECTIONS', 'IMPLEMENTATION', 'ROADMAP'
                ]):
                    story.append(Spacer(1, 15))
                    story.append(Paragraph(line.upper(), styles['SubSectionHeader']))
                elif line.startswith('•') or line.startswith('-'):
                    story.append(Paragraph(line, styles['ForceAnalysis']))
                elif ':' in line and len(line) < 100:  # Likely a key-value pair
                    story.append(Paragraph(f"<b>{line}</b>", styles['MetricItem']))
                else:
                    story.append(Paragraph(line, styles['CleanBody']))

            doc.build(story)
            return filename
            
        except Exception as e:
            print(f"Improved PDF generation failed: {e}")
            fallback_path = f"reports/strategic_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write("STRATEGIC BUSINESS ANALYSIS\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}\n\n")
                
                f.write("EXECUTIVE SUMMARY\n")
                f.write("-" * 20 + "\n")
                for key, value in analysis.items():
                    if value and value != "N/A" and value != 0:
                        f.write(f"• {key.replace('_', ' ').title()}: {value}\n")
                
                f.write(f"\nCOMPETITIVE ANALYSIS\n")
                f.write("-" * 20 + "\n")
                for force_name, force_data in five_forces.items():
                    f.write(f"• {force_name.replace('_', ' ').title()}: {force_data['intensity']}\n")
                    f.write(f"  Recommendation: {force_data['recommendation']}\n\n")
                
                f.write(f"STRATEGIC INSIGHTS\n")
                f.write("-" * 20 + "\n")
                f.write(self._clean_ai_artifacts(insights))
                
            return fallback_path

    def _create_enhanced_pdf_styles(self):
        """Create enhanced PDF styles with professional formatting"""
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor('#2c3e50')
        ))
        
        # Enhanced styles
        styles.add(ParagraphStyle(
            name='CompanyHeader',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=30,
            alignment=1  # Center alignment
        ))
        
        styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=20,
            spaceBefore=30,
            alignment=0,  # Left alignment
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SubSectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=12,
            spaceBefore=20,
            alignment=0,  # Left alignment
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='NormalText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#718096'),
            spaceAfter=10,
            alignment=0,  # Left alignment
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='ItalicText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#718096'),
            spaceAfter=10,
            alignment=0,
            fontName='Helvetica-Oblique'
        ))
        
        styles.add(ParagraphStyle(
            name='BulletedText',
            parent=styles['Normal'],
            leftIndent=20,
            bulletIndent=10,
            fontSize=11,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=8,
            bulletType='bullet',
            bulletColor=colors.HexColor('#3182ce')
        ))
        
        styles.add(ParagraphStyle(
            name='CodeSnippet',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=10,
            textColor=colors.HexColor('#2d3748'),
            backColor=colors.HexColor('#edf2f7'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=8,
            leftIndent=10
        ))
        
        return styles

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
