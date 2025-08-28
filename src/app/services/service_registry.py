"""
Service Registry for Depot Tracker.

This module implements a singleton service registry pattern to provide centralized
access to service instances across the application. The registry solves the problem
of sharing service instances between different parts of the application (like UI
callbacks and background schedulers) without creating circular import dependencies.

The registry uses the singleton pattern to ensure only one instance exists throughout
the application lifecycle, preventing duplicate service creation and maintaining
consistent state across all components.
"""
from typing import Optional

from app.services.data_service import DataManager
from app.services.depot_service import DepotService


class ServiceRegistry:
    """
    Singleton service registry for managing shared service instances.
    
    This class provides a centralized location to store and access service instances
    that need to be shared between different parts of the application. It uses the
    singleton pattern to ensure only one registry exists throughout the application.
    
    The registry is particularly useful for:
    - Sharing data managers between UI callbacks and background schedulers
    - Avoiding circular import dependencies
    - Maintaining consistent service state across the application
    - Providing a clean interface for service dependency injection
    """
    
    _instance: Optional['ServiceRegistry'] = None
    
    def __new__(cls) -> 'ServiceRegistry':
        """
        Create or return the singleton instance.
        
        This method implements the singleton pattern by ensuring only one instance
        of the ServiceRegistry exists. If an instance already exists, it returns
        that instance; otherwise, it creates a new one.
        
        Returns:
            The singleton ServiceRegistry instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """
        Initialize the service registry.
        
        This method sets up the internal storage for service instances. It uses
        a flag to prevent re-initialization when the singleton instance is
        accessed multiple times throughout the application.
        """
        if self._initialized:
            return
            
        # Initialize storage for service instances
        self._data_cd_1: Optional[DataManager] = None
        self._data_cd_2: Optional[DataManager] = None
        self._service_cd_1: Optional[DepotService] = None
        self._service_cd_2: Optional[DepotService] = None
        self._initialized = True
    
    def register_services(
        self, 
        data_cd_1: DataManager, 
        data_cd_2: DataManager, 
        service_cd_1: DepotService, 
        service_cd_2: DepotService
    ) -> None:
        """
        Register service instances with the registry.
        
        This method stores the provided service instances in the registry, making
        them available to other parts of the application. It should be called
        once during application initialization after all services are created.
        
        Args:
            data_cd_1: Data manager for the first depot
            data_cd_2: Data manager for the second depot
            service_cd_1: Business logic service for the first depot
            service_cd_2: Business logic service for the second depot
        """
        self._data_cd_1 = data_cd_1
        self._data_cd_2 = data_cd_2
        self._service_cd_1 = service_cd_1
        self._service_cd_2 = service_cd_2
    
    @property
    def data_cd_1(self) -> Optional[DataManager]:
        """
        Get the data manager for the first depot.
        
        Returns:
            The DataManager instance for depot 1, or None if not registered yet
        """
        return self._data_cd_1
    
    @property
    def data_cd_2(self) -> Optional[DataManager]:
        """
        Get the data manager for the second depot.
        
        Returns:
            The DataManager instance for depot 2, or None if not registered yet
        """
        return self._data_cd_2
    
    @property
    def service_cd_1(self) -> Optional[DepotService]:
        """
        Get the depot service for the first depot.
        
        Returns:
            The DepotService instance for depot 1, or None if not registered yet
        """
        return self._service_cd_1
    
    @property
    def service_cd_2(self) -> Optional[DepotService]:
        """
        Get the depot service for the second depot.
        
        Returns:
            The DepotService instance for depot 2, or None if not registered yet
        """
        return self._service_cd_2


# Global registry instance - this is the single point of access for all services
# Other modules import this instance to access registered services
registry = ServiceRegistry()
