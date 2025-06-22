from abc import ABC, abstractmethod
from backend.api.mock_helper import MockHelper

import os

class BaseBankAPI(ABC):
    def __init__(self, name: str):
        self.name = name
        self.use_mock = os.getenv("USE_MOCK", "false").lower() == "true"
        self.mock = MockHelper(depot_name=name)

        if self.use_mock:
            print(f"⚠️  MOCK-MODUS aktiv für {self.name}")

    @abstractmethod
    def authenticate(self):
        """ bank api specific authentication procedure """
        pass

    @abstractmethod
    def get_positions(self):
        """ return all current depot positions """
        pass

    @abstractmethod
    def get_statements(self):
        """ return bank statements (e.g. 3 years) """
        pass

    def get_name(self) -> str:
        """ e.g. 'comdirect' """
        return self.name

    def _sanitize_numbers(self, obj):
        if isinstance(obj, dict):
            return {k: self._sanitize_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_numbers(i) for i in obj]
        elif isinstance(obj, str):
            try:
                return float(obj) if "." in obj else int(obj)
            except ValueError:
                return obj
        return obj
        
    def save_mock_positions(self, normalize=True, target_value=50000):
        self.mock.save_mock_positions(self.get_positions(), normalize, target_value)

    def save_mock_statements(self):
        pass
        #self.mock.save_mock_statements("statements.json", statements)

    def save_mock_depot_id(self):
        self.mock.save_mock_depot_id(depot_id=self.depot_id)
