import os
from typing import Union
import yaml
import re
import json
from backend.data.yfinance_support import wkn_to_name, wkn_to_name_lookup, update_prices_from_yf
import pandas as pd


class DataManager:
    def __init__(self, depot_name: str):
        self.name = depot_name
        self.use_generated_mock_data = os.getenv("USE_GENERATED_MOCK_DATA", "false").lower() == "true"
        
        if self.use_generated_mock_data:
            self.data_folder = os.path.join("mock", "generated_mock_data/", self.name)  
        else:
            self.data_folder = os.path.join("data", self.name)

        self.statements = self._load_statements()
        self.depot_id = self._load_depot_id()

        self.positions = self._load_positions()
        self.dividends = self._extract_dividends_from_statements()
        self._merge_dividends_into_positions()
    
    def get_positions(self):
        return self.positions
    
    def update_prices(self):
        self.positions = update_prices_from_yf(self.positions)
        self.positions["current_value"] = self.positions["count"] * self.positions["current_price"]
        
        self.positions["current_price"] = round(self.positions["current_price"], 2)
        self.positions["current_value"] = round(self.positions["current_value"], 0)
        
    def get_dividends(self):
        return self.dividends

    def update_data(self): 
        self.statements = self._load_statements()
        self.depot_id = self._load_depot_id()

        self.positions = self._load_positions()
        self.dividends = self._extract_dividends_from_statements()
        self._merge_dividends_into_positions()

    def _merge_dividends_into_positions(self):
        # Extract dividends
        dividends = self._extract_dividends_from_statements()
        # Convert dividends to a DataFrame
        dividends_df = pd.DataFrame(dividends)
        # Ensure the wkn column is of type string in both DataFrames
        self.positions["wkn"] = self.positions["wkn"].astype(str)
        if not dividends_df.empty:
            dividends_df["wkn"] = dividends_df["wkn"].astype(str)
            # Group by WKN and calculate the total dividends for each position
            total_dividends = dividends_df.groupby("wkn")["amount"].sum().reset_index()
            total_dividends.rename(columns={"amount": "total_dividends"}, inplace=True)
        else:
            total_dividends = pd.DataFrame(columns=["wkn", "total_dividends"])

        total_dividends["total_dividends"] = pd.to_numeric(total_dividends["total_dividends"], errors="coerce").round(0)
        
        # Merge the total dividends into the positions DataFrame
        self.positions = self.positions.merge(total_dividends, on="wkn", how="left")

        # Fill NaN values with 0 for positions with no dividends
        #self.positions["total_dividends"] = self.positions["total_dividends"].fillna(0)

    def _read_data(self, filename: str) -> Union[dict, list]:
        path = os.path.join(self.data_folder, filename)
        
        # Check if the file exists
        if not os.path.exists(path):
            
            # Ensure the directory exists
            if not os.path.exists(self.data_folder):
                os.makedirs(self.data_folder)
            
            # Create an empty file with default content (empty list or dict)
            with open(path, "w") as f:
                json.dump([], f)  # Default to an empty list
            print(f"📂 Created persistent local data: {path}")
        
        # Read the file
        with open(path, "r") as f:
            print(f"📂 Read local data: {path}")
            return json.load(f)
    
    def _load_positions(self):
        df = pd.json_normalize(self._read_data("positions.json"))

        df["wkn"] = df["wkn"]
        df["count"] = pd.to_numeric(df["quantity.value"], errors="coerce").round(2)
        df["purchase_price"] = pd.to_numeric(df["purchasePrice.value"], errors="coerce").round(2)
        df["purchase_value"] = pd.to_numeric(df["purchaseValue.value"], errors="coerce").round(0)
        df["current_price"] = pd.to_numeric(df["currentPrice.price.value"], errors="coerce").round(2)
        df["current_value"] = pd.to_numeric(df["currentValue.value"], errors="coerce").round(0)
        
        # get name from wkn via yfinance
        df["name"] = df["wkn"].apply(wkn_to_name_lookup)

        # store as a pandas datafield
        return df
        

    def _load_statements(self):
        return self._read_data("statements.json")

    def _load_depot_id(self):
        data = self._read_data("depot_id.json")
        # Return the depot_id if it exists, otherwise return 0
        try:
            return data.get("depot_id", 0)
        except (json.JSONDecodeError, AttributeError):
            return 0

    def _extract_dividends_from_statements(self):
        DIVIDEND_YAML_PATH = "data/dividends.yaml"

        if os.path.exists(DIVIDEND_YAML_PATH):
            with open(DIVIDEND_YAML_PATH, "r") as f:
                existing = yaml.safe_load(f) or []
        else:
            existing = []

        existing_set = {(d["date"], d["amount"], d["company"]) for d in existing}
        new_dividends = []

        for txn in self.statements:
            info = txn.get("remittanceInfo", "")
            
            if not isinstance(info, str) or "ERTRAEGNISGUTSCHRIFT" not in info.upper():
                continue
            # --- Regex Parsing ---
            date = txn.get("bookingDate")
            amount = float(txn["amount"]["value"])

            # # 03 = Firmenname (evtl. mit Rechtsform), In march we need to use the second 03 ;-)
            # companies = re.findall(r"03(.*?)(?=03|04|05|06|$)", info)
            # if len(companies) > 1:
            #     company_raw = companies[1]
            # elif companies:
            #     company_raw = companies[0]
            # else:
            #     company_raw = "Unbekannt"
            # company = ' '.join(company_raw.split())  # Leerzeichen normalisieren
            
            # WKN (04...)
            m_wkn = re.search(r"04([A-Z0-9]{5,6})", info.upper())
            wkn = m_wkn.group(1).strip() if m_wkn else None
            
            # Use wkn to get company name
            company = wkn_to_name_lookup(wkn) if wkn else "Unbekannt"

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
        
        # save
        all_divs = existing + new_dividends
        if new_dividends:
            with open(DIVIDEND_YAML_PATH, "w") as f:
                yaml.dump(all_divs, f, sort_keys=False, allow_unicode=True)
            print(f"💾 {len(new_dividends)} stored new dividends to persistent local data.")
        else:
            print("✅ No new dividends retrieved via Rest API.")

        return all_divs