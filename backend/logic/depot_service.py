from backend.api.base_bank import BaseBankAPI
from backend.data.data_manager import DataManager
from backend.logic.yfinance_support import wkn_to_name, wkn_to_name_lookup

import yaml
import os
from datetime import datetime
import re

class DepotService:
    def __init__(self, bank_api: BaseBankAPI, data_manager: DataManager):
        self.api = bank_api
        self.data = data_manager

    def fetch_positions(self):
        return self.api.get_positions()

    def get_asset_allocation(self, positions):
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

    def compute_summary(self, positions: list) -> dict:
        total_value = sum(float(p["currentValue"]["value"]) for p in positions)
        total_cost = sum(float(p["purchaseValue"]["value"]) for p in positions)

        performance = ((total_value - total_cost) / total_cost) * 100 if total_cost else 0

        return {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "performance_percent": round(performance, 2)
        }

    def get_asset_pie_data(self, positions):
        import pandas as pd
        df = pd.json_normalize(positions)
        df["wkn"] = df["wkn"]
        df["wert"] = pd.to_numeric(df["currentValue.value"], errors="coerce")
        df = df.groupby("wkn").agg({"wert": "sum"}).reset_index()
        df["name"] = df["wkn"].apply(wkn_to_name_lookup)
        return df

    def extract_dividends_from_statements(self):
        DIVIDEND_YAML_PATH = "data/dividends.yaml"
        statements = self.api.get_statements()

        if os.path.exists(DIVIDEND_YAML_PATH):
            with open(DIVIDEND_YAML_PATH, "r") as f:
                existing = yaml.safe_load(f) or []
        else:
            existing = []

        existing_set = {(d["date"], d["amount"], d["company"]) for d in existing}
        new_dividends = []

        for txn in statements:
            info = txn.get("remittanceInfo", "")
            
            if not isinstance(info, str) or "ERTRAEGNISGUTSCHRIFT" not in info.upper():
                continue
            # --- Regex Parsing ---
            date = txn.get("bookingDate")
            amount = float(txn["amount"]["value"])

            # 03 = Firmenname (evtl. mit Rechtsform), In march we need to use the second 03 ;-)
            companies = re.findall(r"03(.*?)(?=03|04|05|06|$)", info)
            if len(companies) > 1:
                company_raw = companies[1]
            elif companies:
                company_raw = companies[0]
            else:
                company_raw = "Unbekannt"
            company = ' '.join(company_raw.split())  # Leerzeichen normalisieren
            
            # WKN (04...)
            m_wkn = re.search(r"04([A-Z0-9]{5,6})", info.upper())
            wkn = m_wkn.group(1).strip() if m_wkn else None


            # Anzahl Stücke (02...)
            m_shares = re.search(r"02DEPOTBESTAND:\s*([\d,.]+)", info)
            shares = float(m_shares.group(1).replace(",", ".")) if m_shares else None

            # Einzeldividende (04... currency + Betrag)
            m_div = re.search(r"USD\s*([\d,.]+)|EUR\s*([\d,.]+)", info)
            div_per_share = None
            currency = None
            if m_div:
                div_per_share = m_div.group(1) or m_div.group(2)
                div_per_share = float(div_per_share.replace(",", "."))

            entry = {
                "date": date,
                "amount": amount,
                "company": company,
                "wkn": wkn,
                "shares": shares,
                "div_per_share": div_per_share,
            }

            key = (date, amount, company)
            if key not in existing_set:
                new_dividends.append(entry)

        # Speichern
        if new_dividends:
            all_divs = existing + new_dividends
            with open(DIVIDEND_YAML_PATH, "w") as f:
                yaml.dump(all_divs, f, sort_keys=False, allow_unicode=True)
            print(f"💾 {len(new_dividends)} neue Dividenden gespeichert.")
        else:
            print("✅ Keine neuen Dividenden gefunden.")

        return new_dividends

