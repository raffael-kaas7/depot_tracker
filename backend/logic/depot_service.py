from backend.api.base_bank import BaseBankAPI
from backend.data.data_manager import DataManager

class DepotService:
    def __init__(self, bank_api: BaseBankAPI, data_manager: DataManager):
        self.api = bank_api
        self.data = data_manager

    def fetch_positions(self):
        return self.api.get_positions()

    def get_asset_allocation(self, positions):
        allocation = {}
        for p in positions:
            klass = self._classify_asset(p)
            allocation[klass] = allocation.get(klass, 0) + p["currentValue"]["value"]
        return allocation

    def _classify_asset(self, position):
        name = position["instrument"]["name"].lower()
        if "etf" in name:
            return "ETF"
        elif "gold" in name or "silber" in name:
            return "Edelmetall"
        elif "reit" in name or "immobilie" in name:
            return "Immobilie"
        else:
            return "Aktie"

    def parse_dividends(self, statements):
        pass
