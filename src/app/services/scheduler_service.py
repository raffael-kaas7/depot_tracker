"""
Background Scheduler Service for Depot Tracker.

This module implements a background task scheduler using APScheduler that handles
automated data updates and snapshot creation for the depot tracking application.
The scheduler runs background jobs that:

1. Update current prices from Yahoo Finance for both depots
2. Create daily snapshots of depot values for historical tracking

The scheduler uses the registry pattern to access shared service instances and
implements proper lifecycle management to ensure clean shutdown when the 
application stops.
"""
import atexit
import datetime as dt
import json
import os
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

from config.settings import get_settings, Config


class SchedulerService:
    """
    Background task scheduler for automated depot data updates.
    
    This service manages background tasks that keep the depot data fresh by
    periodically updating prices from external APIs and creating daily snapshots
    for historical tracking. It uses APScheduler to run tasks at regular intervals
    without blocking the main application thread.
    
    The scheduler handles:
    - Price updates from Yahoo Finance API
    - Daily snapshot creation for portfolio tracking
    - Graceful shutdown when the application stops
    - Error handling for failed background tasks
    """
    
    def __init__(self) -> None:
        """
        Initialize the scheduler service.
        
        Sets up the APScheduler instance, loads configuration settings, and
        prepares the timezone for proper timestamp handling. The scheduler
        is created but not started until explicitly requested.
        """
        # Create background scheduler that runs in separate thread
        self.scheduler: BackgroundScheduler = BackgroundScheduler()
        self.scheduler_started: bool = False
        
        # Load application settings for depot names and configuration
        self.settings: Config = get_settings()
        
        # Set timezone for proper timestamp handling in German market hours
        self.BERLIN_TZ: ZoneInfo = ZoneInfo("Europe/Berlin")
        
    def save_daily_snapshot(self) -> None:
        """
        Create daily snapshots of depot values for historical tracking.
        
        This method saves exactly one snapshot per calendar day for each depot
        to separate JSON files. Each snapshot contains the date, current market
        value, and total invested capital. If a snapshot for today already exists,
        it updates the values instead of creating a duplicate entry.
        
        The snapshots are stored in:
        - data/{DEPOT_1_NAME}/snapshot.json
        - data/{DEPOT_2_NAME}/snapshot.json
        
        File format: List of objects with date, current_value, and invested_capital
        """
        # Import here to avoid circular imports during module initialization
        from app.services.service_registry import registry
        
        # Get depot services from the registry
        service_cd_1 = registry.service_cd_1
        service_cd_2 = registry.service_cd_2
        
        # Skip snapshot creation if services are not yet initialized
        if not service_cd_1 or not service_cd_2:
            print("⚠️ Services not yet registered, skipping snapshot")
            return
        
        # Get current date in German timezone for consistent daily snapshots
        today: str = dt.datetime.now(self.BERLIN_TZ).date().isoformat()

        # Calculate current portfolio values for both depots
        total_pos1: Dict[str, float] = service_cd_1.compute_summary()
        total_pos2: Dict[str, float] = service_cd_2.compute_summary()

        # Prepare snapshot data structure for both depots
        depot_snapshots: Dict[str, Dict[str, Any]] = {
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

        # Process each depot's snapshot file
        for depot_name, snapshot_info in depot_snapshots.items():
            self._save_depot_snapshot(depot_name, snapshot_info, today)
    
    def _save_depot_snapshot(self, depot_name: str, snapshot_info: Dict[str, Any], today: str) -> None:
        """
        Save or update a single depot's snapshot file.
        
        This private method handles the file I/O operations for saving daily snapshots.
        It ensures the directory exists, creates the file if needed, and either updates
        existing entries or appends new ones.
        
        Args:
            depot_name: The name of the depot being processed
            snapshot_info: Dictionary containing file path and snapshot data
            today: Today's date in ISO format for duplicate checking
        """
        snapshot_file: str = snapshot_info["path"]
        snap: Dict[str, Any] = snapshot_info["data"]

        # Ensure the directory structure exists for the snapshot file
        os.makedirs(os.path.dirname(snapshot_file), exist_ok=True)

        # Initialize empty snapshot file if it doesn't exist
        if not os.path.exists(snapshot_file):
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump([], f)  # Initialize with empty list
            print(f"📂 Created new Snapshot file: {snapshot_file}")

        # Read existing snapshots and update or append today's data
        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshots = json.load(f)

            # Check if today's snapshot already exists
            existing_snapshot: Optional[Dict[str, Any]] = next(
                (s for s in snapshots if s["date"] == today), None
            )
            
            if existing_snapshot:
                # Update existing snapshot with current values
                existing_snapshot["current_value"] = snap["current_value"]
                existing_snapshot["invested_capital"] = snap["invested_capital"]
            else:
                # Add new snapshot for today
                snapshots.append(snap)

            # Write updated snapshots back to file with pretty formatting
            with open(snapshot_file, "w", encoding="utf-8") as f:
                json.dump(snapshots, f, indent=4, ensure_ascii=False)

        except (json.JSONDecodeError, IOError) as e:
            print(f"❌ Error saving snapshot for {depot_name}: {e}")
    
    def start_scheduler(self) -> None:
        """
        Start the background scheduler with all scheduled jobs.
        
        This method configures and starts the APScheduler with jobs for price updates
        and snapshot creation. It ensures the scheduler only starts once and registers
        a shutdown handler for clean application termination.
        
        The current schedule runs jobs every 0.1 minutes (6 seconds) for testing,
        but this should be adjusted for production use to avoid API rate limits.
        """
        # Prevent multiple scheduler instances
        if self.scheduler_started:
            return
            
        # Import here to avoid circular imports during module initialization
        from app.services.service_registry import registry
        
        # Get data managers from the registry for price updates
        data_cd_1 = registry.data_cd_1
        data_cd_2 = registry.data_cd_2
        
        # Skip scheduler start if services are not yet initialized
        if not data_cd_1 or not data_cd_2:
            print("⚠️ Services not yet registered, skipping scheduler start")
            return
        
        # Schedule price updates for both depots
        # These jobs fetch current prices from Yahoo Finance and update the data
        self.scheduler.add_job(
            func=data_cd_1.update_prices, 
            trigger="interval", 
            minutes=0.5,  # TODO: Increase interval for production (e.g., 15 minutes)
            id="prices1", 
            max_instances=1,  # Prevent overlapping executions
            coalesce=True  # Skip missed executions if system is busy
        )
        
        self.scheduler.add_job(
            func=data_cd_2.update_prices, 
            trigger="interval", 
            minutes=0.5,  # TODO: Increase interval for production
            id="prices2", 
            max_instances=1, 
            coalesce=True
        )
        
        # Schedule daily snapshot creation
        # This job creates historical records of portfolio values
        self.scheduler.add_job(
            func=self.save_daily_snapshot, 
            trigger="interval", 
            minutes=0.1,  # TODO: Change to daily schedule for production
            id="snapshot", 
            max_instances=1, 
            coalesce=True
        )
        
        # Start the scheduler and register shutdown handler
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown(wait=False))
        self.scheduler_started = True
        print("✅ Scheduler started successfully")
        
    def shutdown(self) -> None:
        """
        Gracefully shutdown the scheduler.
        
        This method stops all running jobs and shuts down the scheduler thread.
        It's called automatically when the application exits via the atexit handler,
        but can also be called manually for controlled shutdown.
        """
        if self.scheduler_started:
            self.scheduler.shutdown(wait=False)
            self.scheduler_started = False
            print("⏹️ Scheduler stopped")


# Global scheduler service instance
# This singleton instance is used throughout the application for background task management
scheduler_service = SchedulerService()
