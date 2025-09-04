"""
Dividend Service for Depot Tracker.

This service provides centralized dividend calculations and statistics
across multiple depots, handling data aggregation and analysis.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import yaml
import os


class DividendService:
    """
    Service for dividend calculations and statistics across multiple depots.
    
    This service aggregates dividend data from multiple sources and provides
    comprehensive statistics including yearly totals, year-over-year changes,
    and rolling averages.
    """
    
    def __init__(self, depot_services: List):
        """
        Initialize dividend service with depot services.
        
        Args:
            depot_services: List of depot service instances
        """
        self.depot_services = depot_services
        self.dividends_file = "data/dividends.yaml"
    
    def get_all_dividends(self) -> List[Dict[str, Any]]:
        """
        Get all dividends from all depot services and the persistent storage.
        
        Returns:
            List of all dividend records
        """
        # Refresh dividends from all depot services
        for service in self.depot_services:
            try:
                service.get_dividends()
            except Exception as e:
                print(f"Error refreshing dividends from depot service: {e}")
        
        # Load from persistent storage
        try:
            with open(self.dividends_file, "r", encoding="utf-8") as f:
                dividends = yaml.safe_load(f) or []
        except Exception as e:
            print(f"Error loading dividends from file: {e}")
            dividends = []
        
        return dividends
    
    def get_dividend_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive dividend statistics.
        
        Returns:
            Dictionary containing all dividend statistics and calculations
        """
        dividends = self.get_all_dividends()
        
        if not dividends:
            return {
                "total": 0,
                "per_year": {},
                "year_changes": [],
                "avg_12_months": 0,
                "last_12_months_data": []
            }
        
        df = pd.DataFrame(dividends)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["year"] = df["date"].dt.year
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        
        # Total all time
        total = df["amount"].sum()
        
        # Per year totals
        per_year = df.groupby("year")["amount"].sum().sort_index()
        
        # Year-over-year changes
        year_changes = []
        per_year_list = list(per_year.items())
        
        for i, (year, amount) in enumerate(per_year_list):
            if i > 0:
                prev_year, prev_amount = per_year_list[i-1]
                if prev_amount > 0:
                    percentage_change = ((amount - prev_amount) / prev_amount) * 100
                    year_changes.append((year, amount, percentage_change))
                else:
                    year_changes.append((year, amount, None))
            else:
                year_changes.append((year, amount, None))
        
        # Last 12 months average
        current_date = datetime.now()
        twelve_months_ago = current_date - timedelta(days=365)
        
        last_12_months = df[df["date"] >= twelve_months_ago]
        avg_per_month = last_12_months["amount"].sum() / 12 if not last_12_months.empty else 0
        
        # Monthly data for last 12 months (for chart)
        last_12_months_chart_data = []
        if not last_12_months.empty:
            last_12_months_copy = last_12_months.copy()
            last_12_months_copy["year_month"] = last_12_months_copy["date"].dt.to_period('M')
            last_12_months_copy["month_name"] = last_12_months_copy["date"].dt.strftime("%b %Y")
            monthly_sums = last_12_months_copy.groupby(["year_month", "month_name"])["amount"].sum().reset_index()
            monthly_sums = monthly_sums.sort_values("year_month")
            
            last_12_months_chart_data = [
                {"month_name": row["month_name"], "amount": row["amount"]}
                for _, row in monthly_sums.iterrows()
            ]
        
        return {
            "total": float(total),
            "per_year": {int(k): float(v) for k, v in per_year.items()},
            "year_changes": [(int(year), float(amount), float(change) if change is not None else None) 
                           for year, amount, change in year_changes],
            "avg_12_months": float(avg_per_month),
            "last_12_months_data": last_12_months_chart_data
        }
    
    def get_monthly_chart_data(self) -> Dict[str, Any]:
        """
        Get data specifically formatted for the monthly dividend chart.
        
        Returns:
            Dictionary containing chart data and configuration
        """
        dividends = self.get_all_dividends()
        
        if not dividends:
            return {
                "monthly_data": [],
                "all_years": [],
                "month_order": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", 
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            }
        
        df = pd.DataFrame(dividends)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["month_name"] = df["date"].dt.strftime("%b")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        all_years = sorted(df["year"].unique())
        month_order = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Create complete month grid
        all_months = pd.DataFrame(
            [(y, i, m) for y in all_years for i, m in enumerate(month_order, start=1)],
            columns=["year", "month", "month_name"]
        )
        
        # Aggregate monthly data
        monthly = df.groupby(["year", "month", "month_name"])["amount"].sum().reset_index()
        monthly = pd.merge(all_months, monthly, on=["year", "month", "month_name"], how="left")
        monthly["amount"] = monthly["amount"].fillna(0)
        monthly["year"] = monthly["year"].astype(str)
        
        return {
            "monthly_data": monthly.to_dict("records"),
            "all_years": [str(y) for y in all_years],
            "month_order": month_order
        }
