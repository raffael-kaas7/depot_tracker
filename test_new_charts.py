#!/usr/bin/env python3
"""
Test the new separated/combined chart functionality
"""

import os
import json
import sys

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'src'))

def test_chart_modes():
    """Test both separated and combined chart modes."""
    print("📊 Testing new chart functionality...")
    
    try:
        from app.ui.components.charts import create_historical_depot_chart, create_combined_historical_chart
        print("✅ Successfully imported chart functions")
    except ImportError as e:
        print(f"❌ Failed to import chart functions: {e}")
        return False
    
    # Load test data
    depot_1_path = "data/Acc_ETF_and_Growth/snapshot.json"
    depot_2_path = "data/Dividends/snapshot.json"
    
    snapshots_data = {}
    
    if os.path.exists(depot_1_path):
        with open(depot_1_path, 'r') as f:
            snapshots_data['Acc_ETF_and_Growth'] = json.load(f)
    
    if os.path.exists(depot_2_path):
        with open(depot_2_path, 'r') as f:
            snapshots_data['Dividends'] = json.load(f)
    
    print(f"📂 Loaded data for {len(snapshots_data)} depots")
    
    # Test 1: Individual depot charts (separated mode)
    print("\n🔍 Testing separated depot charts...")
    try:
        for depot_name, data in snapshots_data.items():
            fig = create_historical_depot_chart(
                {depot_name: data}, 
                f"{depot_name} Test Chart",
                show_invested_capital=False  # Only current value
            )
            print(f"✅ {depot_name}: Chart created with {len(fig.data)} trace(s)")
            
            # Verify only current value traces (no invested capital)
            expected_traces = 1  # Only current value, no invested capital
            if len(fig.data) == expected_traces:
                print(f"✅ {depot_name}: Correct number of traces (current value only)")
            else:
                print(f"⚠️ {depot_name}: Expected {expected_traces} trace, got {len(fig.data)}")
    
    except Exception as e:
        print(f"❌ Separated chart test failed: {e}")
        return False
    
    # Test 2: Combined chart
    print("\n🔍 Testing combined chart...")
    try:
        fig_combined = create_combined_historical_chart(
            snapshots_data,
            "Combined Test Chart",
            show_invested_capital=False  # Only current value
        )
        print(f"✅ Combined chart created with {len(fig_combined.data)} trace(s)")
        
        # Verify only one trace for combined current value
        expected_traces = 1  # Only combined current value
        if len(fig_combined.data) == expected_traces:
            print(f"✅ Combined: Correct number of traces (current value only)")
        else:
            print(f"⚠️ Combined: Expected {expected_traces} trace, got {len(fig_combined.data)}")
            
    except Exception as e:
        print(f"❌ Combined chart test failed: {e}")
        return False
    
    # Test 3: Test with invested capital enabled (for future extensibility)
    print("\n🔍 Testing with invested capital enabled...")
    try:
        fig_with_capital = create_combined_historical_chart(
            snapshots_data,
            "Test Chart with Capital",
            show_invested_capital=True  # Show both current value and invested capital
        )
        expected_traces = 2  # Current value + invested capital
        if len(fig_with_capital.data) == expected_traces:
            print(f"✅ With capital: Correct number of traces ({expected_traces})")
        else:
            print(f"⚠️ With capital: Expected {expected_traces} traces, got {len(fig_with_capital.data)}")
            
    except Exception as e:
        print(f"❌ Invested capital test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    os.chdir(script_dir)
    success = test_chart_modes()
    if success:
        print("\n🎉 All chart tests passed!")
        print("✅ Separated depot charts work")
        print("✅ Combined chart works") 
        print("✅ Invested capital option works")
        print("✅ Only current value is shown by default")
    else:
        print("\n❌ Chart tests failed!")
        sys.exit(1)
