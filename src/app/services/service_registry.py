"""
Service Registry for Depot Tracker
Provides centralized access to service instances
"""

class ServiceRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._data_cd_1 = None
        self._data_cd_2 = None
        self._service_cd_1 = None
        self._service_cd_2 = None
        self._initialized = True
    
    def register_services(self, data_cd_1, data_cd_2, service_cd_1, service_cd_2):
        """Register the service instances"""
        self._data_cd_1 = data_cd_1
        self._data_cd_2 = data_cd_2
        self._service_cd_1 = service_cd_1
        self._service_cd_2 = service_cd_2
    
    @property
    def data_cd_1(self):
        return self._data_cd_1
    
    @property
    def data_cd_2(self):
        return self._data_cd_2
    
    @property
    def service_cd_1(self):
        return self._service_cd_1
    
    @property
    def service_cd_2(self):
        return self._service_cd_2


# Global registry instance
registry = ServiceRegistry()
