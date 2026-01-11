"""
WKN Metadata Service for Depot Tracker.

This service module provides comprehensive metadata lookup functionality for 
German WKN (Wertpapierkennnummer) identifiers. It centralizes all metadata
operations and provides a clean interface for accessing security information
including names, tickers, regions, sectors, asset classes, and risk assessments.

The service handles loading and caching of the metadata lookup table and
provides methods to retrieve complete or partial metadata for analysis.
"""
import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class WKNMetadata:
    """
    Data class representing complete metadata for a WKN security.
    
    This class encapsulates all metadata fields for a security, providing
    a structured way to access and work with the comprehensive information
    available for each WKN identifier. For ETFs, it also includes regional
    and sectoral breakdown data for accurate allocation analysis.
    """
    wkn: str
    name: str
    ticker: str
    region: str
    asset_class: str
    sector: str
    risk_estimation: str
    region_breakdown: Optional[Dict[str, float]] = None
    sector_breakdown: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format."""
        result = {
            'wkn': self.wkn,
            'name': self.name,
            'ticker': self.ticker,
            'region': self.region,
            'asset_class': self.asset_class,
            'sector': self.sector,
            'risk_estimation': self.risk_estimation
        }
        if self.region_breakdown:
            result['region_breakdown'] = self.region_breakdown
        if self.sector_breakdown:
            result['sector_breakdown'] = self.sector_breakdown
        return result

    def is_etf(self) -> bool:
        """Check if this security is an ETF."""
        return self.asset_class.upper() == "ETF"

    def has_region_breakdown(self) -> bool:
        """Check if this security has regional breakdown data."""
        return self.region_breakdown is not None and len(self.region_breakdown) > 0

    def has_sector_breakdown(self) -> bool:
        """Check if this security has sectoral breakdown data."""
        return self.sector_breakdown is not None and len(self.sector_breakdown) > 0


class WKNMetadataService:
    """
    Service class for WKN metadata lookup operations.
    
    This service provides centralized access to WKN metadata including
    company names, ticker symbols, geographic regions, asset classifications,
    sector information, and risk assessments. It handles loading and caching
    of the metadata lookup table.
    """
    
    def __init__(self, metadata_file_path: str = "data/wkn_metadata_lookup.json"):
        """
        Initialize the metadata service with the specified lookup file.
        
        Args:
            metadata_file_path: Path to the WKN metadata lookup JSON file
        """
        self.metadata_file_path = metadata_file_path
        self._metadata_cache: Optional[Dict[str, Dict[str, str]]] = None

    def _load_metadata_cache(self) -> Dict[str, Dict[str, str]]:
        """
        Load the WKN metadata from file and cache it.
        
        Returns:
            Dictionary mapping WKN to complete metadata information
        """
        if self._metadata_cache is None:
            if os.path.exists(self.metadata_file_path):
                with open(self.metadata_file_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    # Ensure all keys are strings for consistent lookup
                    self._metadata_cache = {str(k): v for k, v in raw.items()}
            else:
                self._metadata_cache = {}
                
        return self._metadata_cache

    def get_metadata(self, wkn: str) -> Optional[WKNMetadata]:
        """
        Get complete metadata for a WKN identifier.
        
        This is the primary method for accessing WKN metadata. It returns
        a structured metadata object containing all available information
        about the security.
        
        Args:
            wkn: The WKN (German securities identifier) to look up
            
        Returns:
            WKNMetadata object with complete information, or None if not found
        """
        wkn = str(wkn)  # Ensure WKN is always a string
        cache = self._load_metadata_cache()
        
        if wkn in cache:
            data = cache[wkn]
            return WKNMetadata(
                wkn=wkn,
                name=data.get("name", "Unknown"),
                ticker=data.get("ticker", "Unknown"),
                region=data.get("region", "Unknown"),
                asset_class=data.get("asset_class", "Unknown"),
                sector=data.get("sector", "Unknown"),
                risk_estimation=data.get("risk_estimation", "medium"),
                region_breakdown=data.get("region_breakdown", None),
                sector_breakdown=data.get("sector_breakdown", None)
            )
        else:
            print(f"🔍 WKN '{wkn}' not found in metadata lookup, please add manually to {self.metadata_file_path}.")
            return None

    def get_name(self, wkn: str) -> str:
        """
        Get company name for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Company name or "Unknown" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.name if metadata else "Unknown"

    def get_ticker(self, wkn: str) -> str:
        """
        Get Yahoo Finance ticker for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Yahoo Finance ticker symbol or "Unknown" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.ticker if metadata else "Unknown"

    def get_region(self, wkn: str) -> str:
        """
        Get regional classification for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Regional classification or "Unknown" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.region if metadata else "Unknown"

    def get_asset_class(self, wkn: str) -> str:
        """
        Get asset class for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Asset class or "Unknown" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.asset_class if metadata else "Unknown"

    def get_risk_estimation(self, wkn: str) -> str:
        """
        Get risk estimation for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Risk estimation ("low", "medium", "high") or "medium" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.risk_estimation if metadata else "medium"

    def get_risk_level(self, wkn: str) -> str:
        """
        Get risk estimation for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Risk estimation ("low", "medium", "high") or "medium" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.risk_estimation if metadata else "medium"

    def get_sector(self, wkn: str) -> str:
        """
        Get sector classification for a WKN (convenience method).
        
        Args:
            wkn: The WKN identifier to look up
            
        Returns:
            Sector classification or "Unknown" if not found
        """
        metadata = self.get_metadata(wkn)
        return metadata.sector if metadata else "Unknown"

    def get_all_metadata_dict(self) -> Dict[str, WKNMetadata]:
        """
        Get all metadata as a dictionary of WKNMetadata objects.
        
        Returns:
            Dictionary mapping WKN to WKNMetadata objects
        """
        cache = self._load_metadata_cache()
        result = {}
        
        for wkn, data in cache.items():
            result[wkn] = WKNMetadata(
                wkn=wkn,
                name=data.get("name", "Unknown"),
                ticker=data.get("ticker", "Unknown"),
                region=data.get("region", "Unknown"),
                asset_class=data.get("asset_class", "Unknown"),
                sector=data.get("sector", "Unknown"),
                risk_estimation=data.get("risk_estimation", "medium"),
                region_breakdown=data.get("region_breakdown", None),
                sector_breakdown=data.get("sector_breakdown", None)
            )
            
        return result

    def get_all_regions(self) -> set:
        """
        Get all unique regions from both single-value regions and breakdown data.
        
        Returns:
            Set of all region names found in the metadata
        """
        cache = self._load_metadata_cache()
        regions = set()
        
        for data in cache.values():
            # Add single-value region if not empty
            region = data.get("region", "")
            if region and region.strip():
                regions.add(region)
            
            # Add breakdown regions
            region_breakdown = data.get("region_breakdown", {})
            if region_breakdown:
                regions.update(region_breakdown.keys())
        
        return regions

    def get_all_sectors(self) -> set:
        """
        Get all unique sectors from both single-value sectors and breakdown data.
        
        Returns:
            Set of all sector names found in the metadata
        """
        cache = self._load_metadata_cache()
        sectors = set()
        
        for data in cache.values():
            # Add single-value sector if not empty
            sector = data.get("sector", "")
            if sector and sector.strip():
                sectors.add(sector)
            
            # Add breakdown sectors
            sector_breakdown = data.get("sector_breakdown", {})
            if sector_breakdown:
                sectors.update(sector_breakdown.keys())
        
        return sectors

    def refresh_cache(self) -> None:
        """
        Clear the internal cache to force reload from file.
        
        This method should be called if the metadata file has been updated
        externally and the cache needs to be refreshed.
        """
        self._metadata_cache = None


# Create singleton instance for application-wide use
wkn_metadata_service = WKNMetadataService()
