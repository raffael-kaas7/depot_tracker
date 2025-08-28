from app.services.data_service import DataManager
from utils.yfinance_support import wkn_to_name, wkn_to_name_lookup

import yaml
import os
from datetime import datetime
import pandas as pd

class DepotService:
    def __init__(self, data_manager: DataManager):
        self.data = data_manager
        self.get_positions()

    def get_positions(self):
        self.data.get_positions()
        self.positions = self._process_positions(self.data.get_positions())
        return self.positions
    
    def compute_summary(self):
        """Compute total value and cost for the depot"""
        positions = self.get_positions()
        if positions is None or positions.empty:
            return {"total_value": 0, "total_cost": 0}
        
        total_value = positions["current_value"].sum() if "current_value" in positions else 0
        total_cost = positions["purchase_value"].sum() if "purchase_value" in positions else 0
        
        return {
            "total_value": float(total_value),
            "total_cost": float(total_cost)
        }

    def get_dividends(self):
        return self.data.get_dividends()

    def get_asset_allocation(self, positions):
        if not positions:
            return
        
        allocation = {}
        for p in positions:
            klass = self._classify_asset(p)
            allocation[klass] = allocation.get(klass, 0) + p["currentValue"]["value"]
        return allocation

    def _classify_asset(self, position):
        name = position["instrument"]["name"].lower()
        if "etf" in name:
            return "ETF"
        elif "gold" in name or "silber" in name:
            return "Edelmetall"
        elif "reit" in name or "immobilie" in name:
            return "Immobilie"
        else:
            return "Aktie"

    def parse_dividends(self, statements):
        pass

    def _process_positions(self, positions):
        # add new columns
        positions["performance_%"] = round(((positions["current_value"] - positions["purchase_value"]) / positions["purchase_value"]) * 100, 2)
        total_current_value = positions["current_value"].sum()
        positions["percentage_in_depot"] = round((positions["current_value"] / total_current_value) * 100, 2)

        return positions
   
    def compute_summary(self) -> dict:
        self.data.get_positions()
        total_value = self.positions["current_value"].sum()
        total_cost = self.positions["purchase_value"].sum()

        performance = ((total_value - total_cost) / total_cost) * 100 if total_cost else 0

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "performance_percent": round(performance, 2)
        }

    def get_asset_pie_data(self, positions):
        
        if not positions:
            return pd.DataFrame()
        df = pd.json_normalize(positions)
        df["wkn"] = df["wkn"]
        df["wert"] = pd.to_numeric(df["currentValue.value"], errors="coerce")
        df = df.groupby("wkn").agg({"wert": "sum"}).reset_index()
        df["name"] = df["wkn"].apply(wkn_to_name_lookup)
        return df

