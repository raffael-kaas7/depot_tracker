#!/usr/bin/env python3
"""
Simple test for snapshot data loading without starting the full app.
"""

import os
import json
import sys

def test_snapshot_loading_simple():
    """Simple test to load and verify snapshot data."""
    print("🧪 Testing snapshot data loading (simple test)...")
    
    # Test data paths
    depot_1_path = "data/Acc_ETF_and_Growth/snapshot.json"
    depot_2_path = "data/Dividends/snapshot.json"
    
    results = {}
    
    # Load depot 1 snapshots
    if os.path.exists(depot_1_path):
        with open(depot_1_path, 'r') as f:
            snapshots_1 = json.load(f)
        results['Acc_ETF_and_Growth'] = snapshots_1
        print(f"✅ Depot 1 (Acc_ETF_and_Growth): Loaded {len(snapshots_1)} snapshots")
        if snapshots_1:
            print(f"   Date range: {snapshots_1[0]['date']} to {snapshots_1[-1]['date']}")
    else:
        print(f"❌ Depot 1 snapshot file not found: {depot_1_path}")
        results['Acc_ETF_and_Growth'] = []
    
    # Load depot 2 snapshots
    if os.path.exists(depot_2_path):
        with open(depot_2_path, 'r') as f:
            snapshots_2 = json.load(f)
        results['Dividends'] = snapshots_2
        print(f"✅ Depot 2 (Dividends): Loaded {len(snapshots_2)} snapshots")
        if snapshots_2:
            print(f"   Date range: {snapshots_2[0]['date']} to {snapshots_2[-1]['date']}")
    else:
        print(f"❌ Depot 2 snapshot file not found: {depot_2_path}")
        results['Dividends'] = []
    
    # Test data structure
    for depot_name, snapshots in results.items():
        if snapshots:
            sample = snapshots[0]
            required_keys = ['date', 'current_value', 'invested_capital']
            missing_keys = [key for key in required_keys if key not in sample]
            if missing_keys:
                print(f"❌ {depot_name}: Missing keys in snapshot data: {missing_keys}")
            else:
                print(f"✅ {depot_name}: All required keys present")
    
    print(f"\n🎉 Test completed!")
    total_snapshots = sum(len(snapshots) for snapshots in results.values())
    print(f"   Total snapshots across all depots: {total_snapshots}")
    
    return results

if __name__ == "__main__":
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    results = test_snapshot_loading_simple()
