#!/usr/bin/env python3
"""
Test chart creation functionality
"""

import os
import json
import sys

# Add src to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, 'src'))

def test_chart_creation():
    """Test the chart creation without full app dependencies."""
    print("📊 Testing chart creation...")
    
    try:
        from app.ui.components.charts import create_historical_depot_chart
        print("✅ Successfully imported chart creation function")
    except ImportError as e:
        print(f"❌ Failed to import chart function: {e}")
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
    
    # Test chart creation
    try:
        fig = create_historical_depot_chart(snapshots_data, "Test Historical Chart")
        print(f"✅ Chart created successfully")
        print(f"   Number of traces: {len(fig.data)}")
        print(f"   Chart title: {fig.layout.title.text}")
        
        # Verify traces
        expected_traces = len(snapshots_data) * 2  # 2 traces per depot (current value + invested capital)
        if len(fig.data) == expected_traces:
            print(f"✅ Expected number of traces ({expected_traces}) created")
        else:
            print(f"⚠️ Unexpected number of traces: got {len(fig.data)}, expected {expected_traces}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create chart: {e}")
        return False

if __name__ == "__main__":
    os.chdir(script_dir)
    success = test_chart_creation()
    if success:
        print("\n🎉 Chart creation test passed!")
    else:
        print("\n❌ Chart creation test failed!")
        sys.exit(1)
