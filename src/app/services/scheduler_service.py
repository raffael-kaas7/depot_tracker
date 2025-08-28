"""
Background Scheduler Service for Depot Tracker
"""
import atexit
import datetime as dt
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from config.settings import get_settings


class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler_started = False
        self.settings = get_settings()
        self.BERLIN_TZ = ZoneInfo("Europe/Berlin")
        
    def save_daily_snapshot(self):
        """
        Writes exactly ONE snapshot per calendar day for each depot into separate files:
        - data/DEPOT_1_NAME/snapshot.json
        - data/DEPOT_2_NAME/snapshot.json
        Format: - date: YYYY-MM-DD; current_value: float; invested_capital: float
        """
        # Import here to avoid circular imports
        from app.services.service_registry import registry
        
        service_cd_1 = registry.service_cd_1
        service_cd_2 = registry.service_cd_2
        
        if not service_cd_1 or not service_cd_2:
            print("⚠️ Services not yet registered, skipping snapshot")
            return
        
        today = dt.datetime.now(self.BERLIN_TZ).date().isoformat()

        # Compute summaries for both depots
        total_pos1 = service_cd_1.compute_summary()
        total_pos2 = service_cd_2.compute_summary()

        # Prepare snapshots for each depot
        depot_snapshots = {
            f"{self.settings.DEPOT_1_NAME}": {
                "path": os.path.join("data", f"{self.settings.DEPOT_1_NAME}", "snapshot.json"),
                "data": {
                    "date": today,
                    "current_value": round(total_pos1["total_value"], 2),
                    "invested_capital": round(total_pos1["total_cost"], 2),
                },
            },
            f"{self.settings.DEPOT_2_NAME}": {
                "path": os.path.join("data", f"{self.settings.DEPOT_2_NAME}", "snapshot.json"),
                "data": {
                    "date": today,
                    "current_value": round(total_pos2["total_value"], 2),
                    "invested_capital": round(total_pos2["total_cost"], 2),
                },
            },
        }

        for depot_name, snapshot_info in depot_snapshots.items():
            snapshot_file = snapshot_info["path"]
            snap = snapshot_info["data"]

            # Ensure the directory exists
            os.makedirs(os.path.dirname(snapshot_file), exist_ok=True)

            # Check if the file exists
            if not os.path.exists(snapshot_file):
                # Create an empty file with default content (empty list)
                with open(snapshot_file, "w") as f:
                    json.dump([], f)  # Default to an empty list
                print(f"📂 Created new Snapshot file: {snapshot_file}")

            # Write or update the snapshot
            try:
                with open(snapshot_file, "r") as f:
                    snapshots = json.load(f)

                # Check if today's snapshot already exists
                existing_snapshot = next((s for s in snapshots if s["date"] == today), None)
                if existing_snapshot:
                    # Update existing snapshot
                    existing_snapshot["current_value"] = snap["current_value"]
                    existing_snapshot["invested_capital"] = snap["invested_capital"]
                else:
                    # Append new snapshot
                    snapshots.append(snap)

                # Write updated snapshots back to file
                with open(snapshot_file, "w") as f:
                    json.dump(snapshots, f, indent=4)

            except Exception as e:
                print(f"❌ Error saving snapshot for {depot_name}: {e}")
    
    def start_scheduler(self):
        """Start the background scheduler with all jobs"""
        if self.scheduler_started:
            return
            
        # Import here to avoid circular imports  
        from app.services.service_registry import registry
        
        data_cd_1 = registry.data_cd_1
        data_cd_2 = registry.data_cd_2
        
        if not data_cd_1 or not data_cd_2:
            print("⚠️ Services not yet registered, skipping scheduler start")
            return
        
        # Add jobs with 0.1 minute intervals (6 seconds for testing)
        self.scheduler.add_job(
            func=data_cd_1.update_prices, 
            trigger="interval", 
            minutes=0.1, 
            id="prices1", 
            max_instances=1, 
            coalesce=True
        )
        self.scheduler.add_job(
            func=data_cd_2.update_prices, 
            trigger="interval", 
            minutes=0.1, 
            id="prices2", 
            max_instances=1, 
            coalesce=True
        )
        self.scheduler.add_job(
            func=self.save_daily_snapshot, 
            trigger="interval", 
            minutes=0.1, 
            id="snapshot", 
            max_instances=1, 
            coalesce=True
        )
        
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler_started = True
        print("✅ Scheduler gestartet")
        
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler_started:
            self.scheduler.shutdown(wait=False)
            self.scheduler_started = False
            print("⏹️ Scheduler gestoppt")


# Global scheduler instance
scheduler_service = SchedulerService()
