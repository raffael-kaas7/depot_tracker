#!/usr/bin/env python3
"""
Test script for dividend service functionality.
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.services.dividend_service import DividendService
from app.services.depot_service import DepotService  
from app.services.data_service import DataManager

def test_dividend_features():
    """Test the new dividend features."""
    print("🧪 Testing Dividend Service Features")
    print("=" * 50)
    
    # Initialize services
    try:
        data1 = DataManager('Acc_ETF_and_Growth')
        data2 = DataManager('Dividends')
        service1 = DepotService(data1)
        service2 = DepotService(data2)

        dividend_service = DividendService([service1, service2])
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return

    # Test dividend statistics
    print("\n📊 Testing Dividend Statistics:")
    try:
        stats = dividend_service.get_dividend_statistics()
        
        print(f"✅ Total dividends: €{stats['total']:.2f}")
        print(f"✅ 12-month average: €{stats['avg_12_months']:.2f}")
        print(f"✅ Years with data: {list(stats['per_year'].keys())}")
        
        print(f"\n📈 Year-over-Year Changes:")
        for year, amount, change in stats['year_changes']:
            change_str = f"({change:+.1f}%)" if change is not None else "(first year)"
            print(f"  {year}: €{amount:.0f} {change_str}")
            
        print(f"\n📅 Last 12 months data points: {len(stats['last_12_months_data'])}")
        
    except Exception as e:
        print(f"❌ Error getting dividend statistics: {e}")

    # Test chart data
    print("\n📊 Testing Chart Data:")
    try:
        chart_data = dividend_service.get_monthly_chart_data()
        
        print(f"✅ Monthly data points: {len(chart_data['monthly_data'])}")
        print(f"✅ Years in chart: {chart_data['all_years']}")
        print(f"✅ Month order: {len(chart_data['month_order'])} months")
        
    except Exception as e:
        print(f"❌ Error getting chart data: {e}")

    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    test_dividend_features()
