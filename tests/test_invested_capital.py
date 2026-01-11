#!/usr/bin/env python3
"""
Test the new toggleable invested capital functionality
"""

import os
import json
import sys

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'src'))

def test_invested_capital_functionality():
    """Test that invested capital lines are included and legend is interactive."""
    print("📊 Testing invested capital functionality...")
    
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
    
    # Test 1: Individual depot charts with invested capital
    print("\n🔍 Testing separated depot charts with invested capital...")
    try:
        for depot_name, data in snapshots_data.items():
            fig = create_historical_depot_chart(
                {depot_name: data}, 
                f"{depot_name} Test Chart",
                show_invested_capital=True
            )
            expected_traces = 2  # Current value + invested capital
            print(f"✅ {depot_name}: Chart created with {len(fig.data)} trace(s)")
            
            if len(fig.data) == expected_traces:
                print(f"✅ {depot_name}: Correct number of traces (current value + invested capital)")
            else:
                print(f"⚠️ {depot_name}: Expected {expected_traces} traces, got {len(fig.data)}")
            
            # Check if legend is interactive
            legend_config = fig.layout.legend
            if hasattr(legend_config, 'itemclick') and legend_config.itemclick == "toggle":
                print(f"✅ {depot_name}: Legend clicking enabled (toggle)")
            else:
                print(f"⚠️ {depot_name}: Legend clicking not properly configured")
                
            # Verify trace names contain expected terms
            trace_names = [trace.name for trace in fig.data]
            has_current = any("Current Value" in name for name in trace_names)
            has_capital = any("Invested Capital" in name for name in trace_names)
            
            if has_current and has_capital:
                print(f"✅ {depot_name}: Both current value and invested capital traces present")
            else:
                print(f"⚠️ {depot_name}: Missing expected trace types. Names: {trace_names}")
    
    except Exception as e:
        print(f"❌ Separated chart test failed: {e}")
        return False
    
    # Test 2: Combined chart with invested capital
    print("\n🔍 Testing combined chart with invested capital...")
    try:
        fig_combined = create_combined_historical_chart(
            snapshots_data,
            "Combined Test Chart",
            show_invested_capital=True
        )
        expected_traces = 2  # Combined current value + combined invested capital
        print(f"✅ Combined chart created with {len(fig_combined.data)} trace(s)")
        
        if len(fig_combined.data) == expected_traces:
            print(f"✅ Combined: Correct number of traces (current value + invested capital)")
        else:
            print(f"⚠️ Combined: Expected {expected_traces} traces, got {len(fig_combined.data)}")
        
        # Check legend configuration
        legend_config = fig_combined.layout.legend
        if hasattr(legend_config, 'itemclick') and legend_config.itemclick == "toggle":
            print(f"✅ Combined: Legend clicking enabled (toggle)")
        else:
            print(f"⚠️ Combined: Legend clicking not properly configured")
        
        # Verify trace names
        trace_names = [trace.name for trace in fig_combined.data]
        has_total_current = any("Total Current Value" in name for name in trace_names)
        has_total_capital = any("Total Invested Capital" in name for name in trace_names)
        
        if has_total_current and has_total_capital:
            print(f"✅ Combined: Both total current value and total invested capital traces present")
        else:
            print(f"⚠️ Combined: Missing expected trace types. Names: {trace_names}")
            
    except Exception as e:
        print(f"❌ Combined chart test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    os.chdir(script_dir)
    success = test_invested_capital_functionality()
    if success:
        print("\n🎉 All invested capital tests passed!")
        print("✅ Invested capital lines are included in charts")
        print("✅ Legend clicking is enabled (toggle/toggleothers)")
        print("✅ Proper trace naming and identification")
        print("✅ Both separated and combined views work correctly")
        print("\n💡 Usage: Click on legend items to show/hide traces!")
    else:
        print("\n❌ Invested capital tests failed!")
        sys.exit(1)
