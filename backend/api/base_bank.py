import os
import json
from typing import Union
from abc import ABC, abstractmethod
import yaml

class BaseBankAPI(ABC):
    def __init__(self, depot_name: str):
        self.name = depot_name
        self.account_id = None
        self.use_generated_mock_data = os.getenv("USE_GENERATED_MOCK_DATA", "false").lower() == "true"
        
        if self.use_generated_mock_data:
            print(f"⚠️  Using GENERATED DATA for {self.name}")
            self.data_folder = os.path.join("mock", "generated_mock_data/", self.name)  
        else:
            print(f"⚠️  Using REAL DATA for {self.name} (... last synchronized depot data)")
            self.data_folder = os.path.join("data", self.name)

    def get_name(self) -> str:
        """ e.g. 'comdirect' """
        return self.name

    # ---------------------------
    # abstract methods
    # ---------------------------
    @abstractmethod
    def authenticate(self):
        """ bank api specific authentication procedure """
        pass


    # ---------------------------
    # private methods
    # ---------------------------

    @abstractmethod
    def _get_positions(self):
        """ return all current depot positions """
        pass

    @abstractmethod
    def _get_statements(self):
        """ return bank statements (e.g. 3 years) """
        pass
    
    # helper to handle types in json data
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

    def _write_data(self, filename: str, data: Union[dict, list]):
        path = os.path.join(self.data_folder, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 New data stored: {path}")

    def _save_positions(self, normalize=True, init_value=50000):
        if not self.use_generated_mock_data:
            self._write_data("positions.json", self._get_positions())

    def _save_statements(self):
        if not self.use_generated_mock_data:
            self._write_data("statements.json", self._get_statements())

    def _save_depot_id(self):
        if not self.use_generated_mock_data:
            self._write_data("depot_id.json", {"depot_id": self.depot_id})

