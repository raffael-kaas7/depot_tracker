import os
import json
from typing import Union

class MockHelper:
    def __init__(self, depot_name):
        self.depot_name = depot_name
        self.mock_folder = os.path.join("mock", self.depot_name)
        os.makedirs(self.mock_folder, exist_ok=True)

    def normalize_positions(self, positions: list, init_value=50000):
        """ normalize purchase Value to init_value"""
        purchase_value_total = sum(float(p["purchaseValue"]["value"]) for p in positions)
        if purchase_value_total == 0:
            raise ValueError("Purchase Value is 0 – can not be normalized")
        factor = init_value / purchase_value_total

        for p in positions:
            count = float(p["quantity"]["value"])
            purchase_value = float(p["purchaseValue"]["value"])
            current_value = float(p["currentValue"]["value"])

            p["quantity"]["value"] = round(count * factor, 4)
            p["purchaseValue"]["value"] = round(purchase_value * factor, 2)
            p["currentValue"]["value"] = round(current_value * factor, 2)

            p["purchasePrice"]["value"] = round(p["purchaseValue"]["value"] / p["quantity"]["value"], 4)
            p["currentPrice"]["price"]["value"] = round(p["currentValue"]["value"] / p["quantity"]["value"], 4)

        return positions

    def _write_mock(self, filename: str, data: Union[dict, list]):
        path = os.path.join(self.mock_folder, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Mock-Datei gespeichert: {path}")

    def _read_mock(self, filename: str) -> Union[dict, list]:
        path = os.path.join(self.mock_folder, filename)
        with open(path, "r") as f:
            print(f"📂 Mock-Datei geladen: {path}")
            return json.load(f)

    def save_mock_positions(self, positions: list, normalize=True, target_value=50000):
        data = self.normalize_positions(positions, target_value) if normalize else positions
        self._write_mock("positions.json", data)

    def save_mock_statements(self, statements: list):
        self._write_mock("statements.json", statements)

    def save_mock_depot_id(self, depot_id: str):
        self._write_mock("depot_id.json", {"depot_id": depot_id})

    def load_mock_positions(self):
        return self._read_mock("positions.json")

    def load_mock_statements(self):
        return self._read_mock("statements.json")

    def load_mock_depot_id(self):
        return self._read_mock("depot_id.json")["depot_id"]
