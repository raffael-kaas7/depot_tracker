"""
Depot Service for Investment Portfolio Business Logic.

This module provides high-level business logic operations for investment depot
management. It acts as a service layer between the raw data management and
the user interface, handling calculations, data transformations, and business
rules for portfolio analysis.

The service provides:
- Portfolio summary calculations (total value, performance, allocation)
- Asset classification and categorization
- Position data processing and enrichment
- Dividend analysis and tracking
- Performance metrics and KPIs
"""
from typing import Dict, List, Any, Optional
import yaml
import os
from datetime import datetime
import pandas as pd

from app.services.data_service import DataManager
from app.services.wkn_metadata_service import wkn_metadata_service


class DepotService:
    """
    Business logic service for depot portfolio management.
    
    This service class encapsulates all business logic operations for managing
    and analyzing investment portfolios. It works with a DataManager to access
    raw depot data and provides higher-level operations like performance
    calculations, asset allocation analysis, and portfolio summaries.
    
    The service handles:
    - Position data processing and enrichment
    - Portfolio-wide calculations and metrics
    - Asset classification and categorization
    - Dividend tracking and analysis
    - Performance monitoring and reporting
    """
    
    def __init__(self, data_manager: DataManager) -> None:
        """
        Initialize the depot service with a data manager.
        
        Sets up the service with access to the underlying data management layer
        and initializes the position data for immediate use.
        
        Args:
            data_manager: DataManager instance for accessing depot data
        """
        self.data: DataManager = data_manager
        self.positions: Optional[pd.DataFrame] = None
        
        # Initialize positions data on creation
        self._refresh_positions()

    def get_positions(self) -> pd.DataFrame:
        """
        Get processed position data for the depot.
        
        Returns the current positions with enriched data including performance
        calculations, allocation percentages, and other derived metrics.
        
        Returns:
            DataFrame containing processed position data with calculated fields
        """
        self._refresh_positions()
        return self.positions if self.positions is not None else pd.DataFrame()
    
    def compute_summary(self) -> Dict[str, float]:
        """
        Compute portfolio-wide summary statistics.
        
        Calculates key portfolio metrics including total market value, total
        invested capital, and overall performance percentage. These metrics
        provide a high-level overview of the portfolio's current status.
        
        Returns:
            Dictionary containing summary metrics:
            - total_value: Current market value of all positions
            - total_cost: Total amount invested (cost basis)
            - performance_percent: Overall portfolio performance as percentage
        """
        positions = self.get_positions()
        
        # Handle empty portfolio case
        if positions is None or positions.empty:
            return {
                "total_value": 0.0,
                "total_cost": 0.0,
                "performance_percent": 0.0
            }
        
        # Calculate portfolio totals
        total_value = positions["current_value"].sum() if "current_value" in positions.columns else 0.0
        total_cost = positions["purchase_value"].sum() if "purchase_value" in positions.columns else 0.0
        
        # Calculate overall performance percentage
        performance = ((total_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0.0

        return {
            "total_value": round(float(total_value), 2),
            "total_cost": round(float(total_cost), 2),
            "performance_percent": round(float(performance), 2)
        }

    def get_dividends(self) -> List[Dict[str, Any]]:
        """
        Get dividend data for the depot.
        
        Retrieves dividend information from the underlying data manager,
        providing access to historical dividend payments and related data.
        
        Returns:
            List of dividend records with payment details and dates
        """
        return self.data.get_dividends()

    def get_asset_allocation(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate asset allocation breakdown by asset class.
        
        Analyzes the portfolio composition by classifying each position into
        asset classes (ETF, stocks, precious metals, REITs) and calculating
        the total value allocated to each class.
        
        Args:
            positions: List of position dictionaries from the API
            
        Returns:
            Dictionary mapping asset classes to their total values
        """
        if not positions:
            return {}
        
        allocation: Dict[str, float] = {}
        
        # Process each position and accumulate by asset class
        for position in positions:
            asset_class = self._classify_asset(position)
            current_value = position.get("currentValue", {}).get("value", 0)
            allocation[asset_class] = allocation.get(asset_class, 0) + current_value
            
        return allocation

    def get_asset_pie_data(self, positions: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Prepare data for asset allocation pie charts.
        
        Processes position data and groups by WKN (German securities identifier)
        to create data suitable for pie chart visualization. Includes security
        names for better chart labeling.
        
        Args:
            positions: List of position dictionaries from the API
            
        Returns:
            DataFrame with columns: wkn, wert (value), name
        """
        if not positions:
            return pd.DataFrame()
            
        # Normalize nested JSON structure into flat DataFrame
        df = pd.json_normalize(positions)
        
        # Extract WKN and value, handling potential missing data
        df["wkn"] = df.get("wkn", "")
        df["wert"] = pd.to_numeric(df.get("currentValue.value", 0), errors="coerce")
        
        # Group by WKN and sum values for securities held in multiple positions
        df = df.groupby("wkn").agg({"wert": "sum"}).reset_index()
        
        # Add human-readable names for better chart labels
        df["name"] = df["wkn"].apply(wkn_metadata_service.get_name)
        
        return df

    def _refresh_positions(self) -> None:
        """
        Refresh and process position data from the data manager.
        
        This private method retrieves fresh position data from the underlying
        data manager and applies business logic transformations to enrich
        the data with calculated fields like performance and allocation percentages.
        """
        # Get raw positions from data manager
        raw_positions = self.data.get_positions()
        
        # Process and enrich the position data
        self.positions = self._process_positions(raw_positions) if raw_positions is not None else pd.DataFrame()

    def _process_positions(self, positions: pd.DataFrame) -> pd.DataFrame:
        """
        Process and enrich position data with calculated fields.
        
        Adds derived fields to the position data including performance percentages
        and allocation percentages within the portfolio. This enrichment makes
        the data ready for display in the user interface.
        
        Args:
            positions: Raw position DataFrame from the data manager
            
        Returns:
            Enhanced DataFrame with calculated performance and allocation fields
        """
        if positions is None or positions.empty:
            return pd.DataFrame()
            
        # Create a copy to avoid modifying the original data
        enriched_positions = positions.copy()
        
        # Calculate performance percentage for each position
        if "current_value" in enriched_positions.columns and "purchase_value" in enriched_positions.columns:
            # Calculate absolute gain/loss in euros for each position
            enriched_positions["absolute_gain_loss"] = round(
                enriched_positions["current_value"] - enriched_positions["purchase_value"], 2
            )
            
            # Avoid division by zero by using numpy where
            enriched_positions["performance_%"] = round(
                ((enriched_positions["current_value"] - enriched_positions["purchase_value"]) 
                 / enriched_positions["purchase_value"].replace(0, 1)) * 100, 2
            )
            
        # Calculate allocation percentage within the depot
        if "current_value" in enriched_positions.columns:
            total_current_value = enriched_positions["current_value"].sum()
            if total_current_value > 0:
                enriched_positions["percentage_in_depot"] = round(
                    (enriched_positions["current_value"] / total_current_value) * 100, 2
                )

        return enriched_positions
   
    def _classify_asset(self, position: Dict[str, Any]) -> str:
        """
        Classify a position into an asset class based on its name.
        
        Uses simple keyword matching to categorize securities into broad
        asset classes. This classification is used for allocation analysis
        and portfolio visualization.
        
        Args:
            position: Position dictionary containing instrument information
            
        Returns:
            Asset class name (ETF, Precious Metal, Real Estate, or Stock)
        """
        # Extract instrument name and convert to lowercase for matching
        instrument_name = position.get("instrument", {}).get("name", "").lower()
        
        # Classify based on keywords in the instrument name
        if "etf" in instrument_name:
            return "ETF"
        elif any(keyword in instrument_name for keyword in ["gold", "silber", "silver"]):
            return "Precious Metal"
        elif any(keyword in instrument_name for keyword in ["reit", "immobilie", "real estate"]):
            return "Real Estate"
        else:
            return "Stock"

