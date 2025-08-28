import os
from typing import Union
import yaml
import re
import json
from utils.yfinance_support import update_prices_from_yf
from app.services.wkn_metadata_service import wkn_metadata_service
import pandas as pd


class DataManager:
    def __init__(self, depot_name: str):
        self.name = depot_name
        
        self.data_folder = os.path.join("data", self.name)

        # load data from last Comdirect API synchronization
        self.statements = self._load_statements()
        self.depot_id = self._load_depot_id()
        self.positions = self._load_positions()
        
        # parse dividends from account statements and add total_dividends to positions DataFrame
        self.dividends = self._extract_dividends_from_statements()
        self._merge_dividends_into_positions()
    
    def get_positions(self):
        return self.positions

    def get_dividends(self):
        return self.dividends

    # update current prices from yfinance data and not via Comdirect API
    def update_prices(self):
        self.positions = update_prices_from_yf(self.positions)
        self.positions["current_value"] = self.positions["count"] * self.positions["current_price"]
        
        self.positions["current_price"] = round(self.positions["current_price"], 2)
        self.positions["current_value"] = round(self.positions["current_value"], 0)

    # update full data based on retrieved data from Comdirect API
    def update_data(self): 
        self.statements = self._load_statements()
        self.depot_id = self._load_depot_id()

        self.positions = self._load_positions()
        self.dividends = self._extract_dividends_from_statements()
        self._merge_dividends_into_positions()

    # ---------------------------
    # private methods
    # ---------------------------
    
    # Merge total_dividends into positions DataFrame to show total dividends received by an asset in the portfolio table
    def _merge_dividends_into_positions(self):
        # Only merge if positions DataFrame is not empty
        if self.positions.empty:
            return

        # Extract dividends
        dividends = self._extract_dividends_from_statements()  # check for new dividends in account statements
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
        """
        Load and process position data from JSON file into a pandas DataFrame.
        
        This method reads the positions.json file, normalizes the nested JSON structure,
        and enriches the data with company names and Yahoo Finance ticker symbols
        using the consolidated WKN cache. The resulting DataFrame includes both
        the original financial data and the lookup information for complete
        security details.
        
        Returns:
            pandas.DataFrame: Processed position data with columns including:
                - Standard position data (wkn, count, prices, values)
                - name: Company name from WKN lookup  
                - ticker: Yahoo Finance ticker symbol from WKN lookup
                - All original JSON fields as normalized columns
        """
        data = self._read_data("positions.json")
        if not data:
            return pd.DataFrame()
        df = pd.json_normalize(data)
        df["wkn"] = df["wkn"]
        df["count"] = pd.to_numeric(df["quantity.value"], errors="coerce").round(2)
        df["purchase_price"] = pd.to_numeric(df["purchasePrice.value"], errors="coerce").round(2)
        df["purchase_value"] = pd.to_numeric(df["purchaseValue.value"], errors="coerce").round(0)
        df["current_price"] = pd.to_numeric(df["currentPrice.price.value"], errors="coerce").round(2)
        df["current_value"] = pd.to_numeric(df["currentValue.value"], errors="coerce").round(0)
        
        # Add complete metadata from WKN metadata service for allocation analysis
        # These columns provide comprehensive security information for charts and analysis
        df["name"] = df["wkn"].apply(wkn_metadata_service.get_name)
        df["ticker"] = df["wkn"].apply(wkn_metadata_service.get_ticker)
        df["region"] = df["wkn"].apply(wkn_metadata_service.get_region)
        df["asset_class"] = df["wkn"].apply(wkn_metadata_service.get_asset_class)
        df["sector"] = df["wkn"].apply(wkn_metadata_service.get_sector)
        df["risk_estimation"] = df["wkn"].apply(wkn_metadata_service.get_risk_estimation)

        # Create dynamic allocation columns for advanced ETF breakdown analysis
        df = self._add_allocation_columns(df)

        # store as a pandas datafield
        return df

    def _add_allocation_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add dynamic allocation columns for region and sector breakdown analysis.
        
        For ETFs with breakdown data, distributes the position value across multiple
        region/sector columns based on the breakdown percentages. For non-ETFs,
        allocates 100% to the single region/sector.
        
        Args:
            df: DataFrame with position data
            
        Returns:
            Enhanced DataFrame with dynamic allocation columns
        """
        if df.empty:
            return df

        # Get all unique regions and sectors for dynamic column creation
        all_regions = wkn_metadata_service.get_all_regions()
        all_sectors = wkn_metadata_service.get_all_sectors()

        # Initialize allocation columns with zeros
        for region in all_regions:
            col_name = f"region_{region.lower().replace(' ', '_').replace('-', '_')}_value"
            df[col_name] = 0.0

        for sector in all_sectors:
            col_name = f"sector_{sector.lower().replace(' ', '_').replace('-', '_')}_value"
            df[col_name] = 0.0

        # Process each position to distribute values across allocation columns
        for idx, row in df.iterrows():
            wkn = row['wkn']
            current_value = row['current_value']
            
            if pd.isna(current_value) or current_value <= 0:
                continue
                
            metadata = wkn_metadata_service.get_metadata(wkn)
            if not metadata:
                continue

            # Handle region allocation
            if metadata.is_etf() and metadata.has_region_breakdown():
                # ETF with region breakdown - distribute across regions
                for region, percentage in metadata.region_breakdown.items():
                    col_name = f"region_{region.lower().replace(' ', '_').replace('-', '_')}_value"
                    if col_name in df.columns:
                        df.loc[idx, col_name] = current_value * percentage
            elif metadata.region and metadata.region.strip():
                # Single region allocation
                col_name = f"region_{metadata.region.lower().replace(' ', '_').replace('-', '_')}_value"
                if col_name in df.columns:
                    df.loc[idx, col_name] = current_value

            # Handle sector allocation
            if metadata.is_etf() and metadata.has_sector_breakdown():
                # ETF with sector breakdown - distribute across sectors
                for sector, percentage in metadata.sector_breakdown.items():
                    col_name = f"sector_{sector.lower().replace(' ', '_').replace('-', '_')}_value"
                    if col_name in df.columns:
                        df.loc[idx, col_name] = current_value * percentage
            elif metadata.sector and metadata.sector.strip():
                # Single sector allocation
                col_name = f"sector_{metadata.sector.lower().replace(' ', '_').replace('-', '_')}_value"
                if col_name in df.columns:
                    df.loc[idx, col_name] = current_value

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

            # WKN (04...)
            m_wkn = re.search(r"04([A-Z0-9]{5,6})", info.upper())
            wkn = m_wkn.group(1).strip() if m_wkn else None
            
            # Use wkn to get company name
            company = wkn_metadata_service.get_name(wkn) if wkn else "Unknown"

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