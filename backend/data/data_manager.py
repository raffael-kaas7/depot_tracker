class DataManager:
    def __init__(self, backend="yaml"):
        self.backend = backend
        if backend == "mongo":
            import pymongo
            self.client = pymongo.MongoClient("mongodb://localhost:27017/")
            self.db = self.client["depot_tracker"]
        else:
            import yaml
            self.yaml_path = "data.yaml"

    def save_dividends(self, dividends):
        pass

    def load_dividends(self):
        pass
