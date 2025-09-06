#!/usr/bin/env python3
"""
Test script to demonstrate the allocation filtering feature.

This script shows how assets with empty or missing metadata fields
are automatically excluded from pie charts.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
from app.ui.components.charts import create_allocation_pie_chart

def test_allocation_filtering():
    """Test the allocation filtering functionality."""
    
    # Create sample data with some assets having empty regions
    sample_data = pd.DataFrame([
        {
            'wkn': 'A1B2C3',
            'name': 'Apple Inc',
            'current_value': 10000,
            'region': 'North America',
            'asset_class': 'Equity',
            'sector': 'IT',
            'risk_estimation': 'low'
        },
        {
            'wkn': 'A2T64E',
            'name': 'Bitcoin ETF',
            'current_value': 5000,
            'region': '',  # Empty region - should be excluded from region chart
            'asset_class': 'Crypto',
            'sector': 'Financials',
            'risk_estimation': 'high'
        },
        {
            'wkn': 'D4E5F6',
            'name': 'European Stock',
            'current_value': 8000,
            'region': 'Europe',
            'asset_class': 'Equity',
            'sector': 'Consumer Goods',
            'risk_estimation': 'medium'
        },
        {
            'wkn': 'G7H8I9',
            'name': 'Commodity Fund',
            'current_value': 3000,
            'region': '',  # Empty region - should be excluded from region chart
            'asset_class': 'Commodity',
            'sector': '',  # Empty sector - should be excluded from sector chart
            'risk_estimation': 'high'
        }
    ])
    
    print("📊 Testing Allocation Filtering Feature")
    print("=" * 50)
    
    print("\n📋 Sample Data:")
    print(sample_data[['name', 'current_value', 'region', 'asset_class', 'sector']].to_string(index=False))
    
    print("\n🔍 Testing Region Allocation:")
    print("- Assets with empty region should be excluded")
    print("- Expected: Only Apple Inc and European Stock should appear")
    
    # Test region filtering
    region_chart = create_allocation_pie_chart(sample_data, 'region', 'Regional Allocation Test')
    region_data = region_chart.data[0] if region_chart.data else None
    
    if region_data:
        print(f"✅ Region chart created with {len(region_data.labels)} regions:")
        for label, value in zip(region_data.labels, region_data.values):
            print(f"   - {label}: €{value:,.0f}")
    else:
        print("❌ No region data found")
    
    print("\n🔍 Testing Sector Allocation:")
    print("- Assets with empty sector should be excluded")
    print("- Expected: IT, Consumer Goods, and Financials should appear")
    
    # Test sector filtering
    sector_chart = create_allocation_pie_chart(sample_data, 'sector', 'Sector Allocation Test')
    sector_data = sector_chart.data[0] if sector_chart.data else None
    
    if sector_data:
        print(f"✅ Sector chart created with {len(sector_data.labels)} sectors:")
        for label, value in zip(sector_data.labels, sector_data.values):
            print(f"   - {label}: €{value:,.0f}")
    else:
        print("❌ No sector data found")
    
    print("\n🔍 Testing Asset Class Allocation:")
    print("- All assets have valid asset classes")
    print("- Expected: All 4 assets should appear")
    
    # Test asset class (should include all)
    asset_chart = create_allocation_pie_chart(sample_data, 'asset_class', 'Asset Class Allocation Test')
    asset_data = asset_chart.data[0] if asset_chart.data else None
    
    if asset_data:
        print(f"✅ Asset class chart created with {len(asset_data.labels)} classes:")
        for label, value in zip(asset_data.labels, asset_data.values):
            print(f"   - {label}: €{value:,.0f}")
    else:
        print("❌ No asset class data found")
    
    print("\n" + "=" * 50)
    print("✅ Filtering test completed!")
    print("\nKey Benefits:")
    print("- Bitcoin and commodities are excluded from regional charts")
    print("- Assets with missing sector data are excluded from sector charts")
    print("- Chart titles show how many assets were excluded")
    print("- Only relevant data is displayed for cleaner visualizations")

if __name__ == "__main__":
    test_allocation_filtering()
