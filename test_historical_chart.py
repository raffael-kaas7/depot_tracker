#!/usr/bin/env python3
"""
Quick test script to verify the historical chart functionality.
"""

import sys
sys.path.append('src')

from app.services.data_service import DataManager
from app.ui.components.charts import create_historical_depot_chart

def test_snapshot_loading():
    """Test loading snapshot data from both depots."""
    print("🧪 Testing snapshot data loading...")
    
    # Test depot 1
    data_cd_1 = DataManager("Acc_ETF_and_Growth")
    snapshots_1 = data_cd_1.get_snapshot_data()
    print(f"✅ Depot 1 (Acc_ETF_and_Growth): Loaded {len(snapshots_1)} snapshots")
    if snapshots_1:
        print(f"   First snapshot: {snapshots_1[0]}")
        print(f"   Last snapshot: {snapshots_1[-1]}")
    
    # Test depot 2
    data_cd_2 = DataManager("Dividends")
    snapshots_2 = data_cd_2.get_snapshot_data()
    print(f"✅ Depot 2 (Dividends): Loaded {len(snapshots_2)} snapshots")
    if snapshots_2:
        print(f"   First snapshot: {snapshots_2[0]}")
        print(f"   Last snapshot: {snapshots_2[-1]}")
    
    # Test chart creation
    print("\n📊 Testing chart creation...")
    snapshots_data = {
        "Acc_ETF_and_Growth": snapshots_1,
        "Dividends": snapshots_2
    }
    
    fig = create_historical_depot_chart(snapshots_data)
    print(f"✅ Chart created successfully with {len(fig.data)} traces")
    
    return snapshots_1, snapshots_2

if __name__ == "__main__":
    snapshots_1, snapshots_2 = test_snapshot_loading()
    print(f"\n🎉 Test completed successfully!")
    print(f"   - Depot 1: {len(snapshots_1)} snapshots")
    print(f"   - Depot 2: {len(snapshots_2)} snapshots")
