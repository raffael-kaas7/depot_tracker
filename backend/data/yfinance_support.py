
import yfinance as yf
import json
import os
import math
import pandas as pd

WKN_NAME_CACHE_PATH = "data/wkn_name_cache.json" if os.getenv("USE_GENERATED_MOCK_DATA") == "false" else "data/wkn_name_dummy_cache.json"
WKN_TICKER_CACHE_PATH = "data/wkn_ticker_cache.json" if os.getenv("USE_GENERATED_MOCK_DATA") == "false" else "data/wkn_ticker_dummy_cache.json"

def wkn_to_name(wkn: str) -> str:
    try:
        ticker = yf.Ticker(wkn)
        info = ticker.info
        return info.get("shortName") or info.get("longName") or "Unbekannt"
    except Exception:
        return "Unbekannt"


def wkn_to_ticker_lookup(wkn: str) -> str:
    wkn = str(wkn)  # always string

    # load cache
    if os.path.exists(WKN_TICKER_CACHE_PATH):
        with open(WKN_TICKER_CACHE_PATH, "r") as f:
            raw = json.load(f)
            cache = {str(k): v for k, v in raw.items()}  # all keys as str
    else:
        cache = {}

    if wkn in cache:
        return cache[wkn]

    # Workaround: User inputs it manually if needed
    print(f"🔍 WKN '{wkn}' not found, please add manually.")
    # cache[wkn] = "Unknown"

    with open(WKN_TICKER_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)

    return cache[wkn]

def wkn_to_name_lookup(wkn: str) -> str:
    wkn = str(wkn)  # always string

    # load cache
    if os.path.exists(WKN_NAME_CACHE_PATH):
        with open(WKN_NAME_CACHE_PATH, "r") as f:
            raw = json.load(f)
            cache = {str(k): v for k, v in raw.items()}  # ← alle Keys als str
    else:
        cache = {}

    if wkn in cache:
        return cache[wkn]

    # Workaround: User gibt es manuell ein bei Bedarf
    print(f"🔍 WKN '{wkn}' not found, please add manually.")
    #cache[wkn] = "Unknown"

    with open(WKN_NAME_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)

    return cache[wkn]


def update_prices_from_yf(df: pd.DataFrame):
    """
    Aktualisiert df["current_price"] mit aktuellen Kursen aus yfinance, in EUR.
    Die Zuordnung erfolgt über WKN -> Yahoo-Ticker (wkn_to_ticker_lookup).

    Args:
        df: DataFrame mit mindestens [wkn, current_price] Spalten.

    Returns:
        DataFrame mit aktualisiertem "current_price" in EUR.
    """
    # Cache für FX-Raten (Multiplikator: from_currency -> EUR)
    fx_cache = {"EUR": 1.0}

    def _log(msg):
        print(msg)

    def _safe_last_price(t: yf.Ticker):
        """
        Robust den letzten Preis holen:
        - fast_info['last_price']
        - info['regularMarketPrice']
        - history(period='1d')['Close'][-1]
        """
        try:
            fi = getattr(t, "fast_info", None) or {}
            p = fi.get("last_price")
            if p is not None and not (isinstance(p, float) and math.isnan(p)):
                return float(p)
        except Exception:
            pass

        try:
            inf = t.info or {}
            p = inf.get("regularMarketPrice")
            if p is not None and not (isinstance(p, float) and math.isnan(p)):
                return float(p)
        except Exception:
            pass

        try:
            h = t.history(period="1d", auto_adjust=False)
            if not h.empty:
                return float(h["Close"].dropna().iloc[-1])
        except Exception:
            pass

        return None

    def _ticker_currency(t: yf.Ticker):
        """Währung des Listings bestimmen."""
        # fast_info ist schneller/robuster als info
        try:
            fi = getattr(t, "fast_info", None) or {}
            cur = fi.get("currency")
            if cur:
                return cur
        except Exception:
            pass
        try:
            inf = t.info or {}
            cur = inf.get("currency")
            if cur:
                return cur
        except Exception:
            pass
        return "EUR"  # Fallback

    def fx_to_eur_multiplier(from_currency: str):
        """
        Liefert den Multiplikator, um einen Betrag in 'from_currency' nach EUR zu konvertieren:
        EUR_amount = amount * multiplier
        Implementiert per Yahoo-FX-Paare, mit Fallbacks und Cache.

        Logik:
        - Wenn from_currency == EUR -> 1.0
        - Versuche 'EUR{CUR}=X' -> 1 EUR = X {CUR} => EUR = CUR / X => multiplier = 1 / X? NEIN!
          Achtung: amount ist in CUR, wir wollen EUR: EUR = CUR / (EURCUR)
          Das heißt MULTIPLIKATOR = 1 / (EURCUR).
          Um ohne Division bei Nutzung als Multiplikator zu bleiben,
          speichern wir direkt multiplier = 1 / quote.
        - Falls nicht verfügbar, versuche '{CUR}EUR=X' -> 1 {CUR} = X EUR => EUR = CUR * X => multiplier = X
        """
        from_currency = (from_currency or "EUR").upper()
        if from_currency in fx_cache:
            return fx_cache[from_currency]

        if from_currency == "EUR":
            fx_cache[from_currency] = 1.0
            return 1.0

        # 1) Versuche EURCUR=X  (z.B. EURUSD=X: 1 EUR = 1.10 USD)
        pair1 = f"EUR{from_currency}=X"
        # 2) Versuche CUREUR=X  (z.B. USDEUR=X: 1 USD = 0.91 EUR)
        pair2 = f"{from_currency}EUR=X"

        quote = None
        # Versuch 1: EURCUR=X  -> multiplier = 1 / quote
        try:
            q = yf.Ticker(pair1)
            price = getattr(q, "fast_info", {}).get("last_price")
            if price is None or (isinstance(price, float) and math.isnan(price)):
                hist = q.history(period="1d")
                price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
            if price and price > 0:
                quote = float(price)
                multiplier = 1.0 / quote
                fx_cache[from_currency] = multiplier
                return multiplier
        except Exception:
            pass

        # Versuch 2: CUREUR=X  -> multiplier = quote
        try:
            q = yf.Ticker(pair2)
            price = getattr(q, "fast_info", {}).get("last_price")
            if price is None or (isinstance(price, float) and math.isnan(price)):
                hist = q.history(period="1d")
                price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
            if price and price > 0:
                quote = float(price)
                multiplier = quote
                fx_cache[from_currency] = multiplier
                return multiplier
        except Exception:
            pass

        _log(f"⚠️ Keine FX-Quote für {from_currency} gefunden – Kurs wird nicht konvertiert.")
        fx_cache[from_currency] = 1.0  # konservativer Fallback (keine Umrechnung)
        return 1.0

    df_out = df.copy()
    updated_map = {}

    # Einmalige Liste der WKNs durchgehen
    for wkn in df_out["wkn"].astype(str):
        ticker = wkn_to_ticker_lookup(wkn)
        if not ticker:
            _log(f"⚠️ Keine Ticker-Zuordnung für WKN {wkn}.")
            continue

        try:
            t = yf.Ticker(ticker)
            price_native = _safe_last_price(t)
            if price_native is None:
                _log(f"❌ Kein Preis für Ticker {ticker} (WKN {wkn}) erhalten.")
                continue

            cur = _ticker_currency(t)
            mult = fx_to_eur_multiplier(cur)
            price_eur = float(price_native) * float(mult)

            # Sicherheitscheck: kein NaN/inf
            if price_eur is None or math.isnan(price_eur) or math.isinf(price_eur):
                _log(f"❌ Ungültiger EUR-Preis für {ticker} (WKN {wkn}).")
                continue

            updated_map[wkn] = price_eur

        except Exception as e:
            _log(f"❌ Fehler bei {ticker} (WKN {wkn}): {e}")

    # Preise in df schreiben, nur wenn vorhanden; sonst alten Wert belassen
    if updated_map:
        df_out["current_price"] = (
            df_out["wkn"].astype(str).map(updated_map).combine_first(df_out["current_price"])
        )

    return df_out



