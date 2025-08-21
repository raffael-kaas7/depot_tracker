from backend.data.data_manager import DataManager
from backend.data.yfinance_support import wkn_to_name, wkn_to_name_lookup

import yaml
import os
from datetime import datetime
import pandas as pd

class DepotService:
    def __init__(self, data_manager: DataManager):
        self.data = data_manager

    def get_positions(self):
        return self.data.get_positions()

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

    def compute_summary(self) -> dict:
        positions = self.get_positions()
        total_value = sum(float(p["currentValue"]["value"]) for p in positions)
        total_cost = sum(float(p["purchaseValue"]["value"]) for p in positions)

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

