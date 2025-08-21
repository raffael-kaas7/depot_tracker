
import yfinance as yf
import json
import os

WKN_CACHE_PATH = "data/wkn_name_cache.json" if os.getenv("USE_GENERATED_MOCK_DATA") == "false" else "data/wkn_name_dummy_cache.json"


def wkn_to_name(wkn: str) -> str:
    try:
        ticker = yf.Ticker(wkn)
        info = ticker.info
        return info.get("shortName") or info.get("longName") or "Unbekannt"
    except Exception:
        return "Unbekannt"


def wkn_to_name_lookup(wkn: str) -> str:
    wkn = str(wkn)  # always string

    # load cache
    if os.path.exists(WKN_CACHE_PATH):
        with open(WKN_CACHE_PATH, "r") as f:
            raw = json.load(f)
            cache = {str(k): v for k, v in raw.items()}  # ← alle Keys als str
    else:
        cache = {}

    if wkn in cache:
        return cache[wkn]

    # Workaround: User gibt es manuell ein bei Bedarf
    print(f"🔍 WKN '{wkn}' not found, please add manually.")
    #cache[wkn] = "Unknown"

    with open(WKN_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)

    return cache[wkn]
