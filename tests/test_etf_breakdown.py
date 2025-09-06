#!/usr/bin/env python3
"""
Test script to demonstrate the ETF breakdown allocation feature.

This script shows how the new dynamic allocation columns work for ETFs
with region and sector breakdowns.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.services.data_service import DataManager
from app.services.depot_service import DepotService
from app.services.wkn_metadata_service import wkn_metadata_service


def test_etf_breakdown():
    """Test the ETF breakdown functionality."""
    print("🧪 Testing ETF Breakdown Allocation Feature")
    print("=" * 50)
    
    # Test metadata service
    print("\n📊 Testing WKN Metadata Service:")
    
    # Test ETF with breakdown
    etf_wkn = "A1103E"  # MSCI World Value ETF
    metadata = wkn_metadata_service.get_metadata(etf_wkn)
    
    if metadata:
        print(f"ETF: {metadata.name} ({etf_wkn})")
        print(f"Asset Class: {metadata.asset_class}")
        print(f"Is ETF: {metadata.is_etf()}")
        print(f"Has Region Breakdown: {metadata.has_region_breakdown()}")
        print(f"Has Sector Breakdown: {metadata.has_sector_breakdown()}")
        
        if metadata.region_breakdown:
            print("Region Breakdown:")
            for region, percentage in metadata.region_breakdown.items():
                print(f"  {region}: {percentage:.1%}")
        
        if metadata.sector_breakdown:
            print("Sector Breakdown:")
            for sector, percentage in metadata.sector_breakdown.items():
                print(f"  {sector}: {percentage:.1%}")
    
    # Test all regions and sectors
    print(f"\n🌍 All Regions Found: {sorted(wkn_metadata_service.get_all_regions())}")
    print(f"🏭 All Sectors Found: {sorted(wkn_metadata_service.get_all_sectors())}")
    
    # Test data processing
    print("\n📈 Testing Data Processing:")
    try:
        # Load data from first depot
        data_manager = DataManager("Acc_ETF_and_Growth")
        positions = data_manager.get_positions()
        
        if not positions.empty:
            print(f"Loaded {len(positions)} positions")
            
            # Show allocation columns
            allocation_columns = [col for col in positions.columns if '_value' in col and ('region_' in col or 'sector_' in col)]
            print(f"Dynamic allocation columns created: {len(allocation_columns)}")
            
            # Show sample allocation data
            if allocation_columns:
                print("\nSample allocation data:")
                for col in allocation_columns[:5]:  # Show first 5 columns
                    total = positions[col].sum()
                    if total > 0:
                        print(f"  {col}: €{total:,.2f}")
            
            # Show total portfolio value
            total_value = positions['current_value'].sum()
            print(f"\nTotal Portfolio Value: €{total_value:,.2f}")
            
        else:
            print("No positions found in the depot")
            
    except Exception as e:
        print(f"Error loading data: {e}")
    
    print("\n✅ ETF Breakdown Test Complete!")


if __name__ == "__main__":
    test_etf_breakdown()
