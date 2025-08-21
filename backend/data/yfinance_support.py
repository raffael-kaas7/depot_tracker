
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


def update_prices_from_yf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aktualisiert df['current_price'] in EUR und fügt df['momentum_3m'] hinzu.
    - Preis: letzter Kurs -> in EUR umgerechnet (Heimatwährung -> EUR)
    - Momentum: 3-Monats-Rendite auf Adj Close, OHNE FX-Umrechnung (unitless)

    Erwartet:
        df mit Spalten ['wkn', 'current_price']
        und eine Funktion: wkn_to_ticker_lookup(wkn: str) -> str (Yahoo-Ticker)
    """
    # FX-Cache: Multiplikator von Quellwährung nach EUR
    fx_cache = {"EUR": 1.0}

    def _log(msg):
        print(msg)

    def _safe_last_price(t: yf.Ticker):
        """Robust den letzten Preis holen (native Währung)."""
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
        return "EUR"

    def fx_to_eur_multiplier(from_currency: str):
        """
        EUR_amount = amount_native * multiplier.
        Versucht erst EURCUR=X (multiplier = 1/quote), dann CUREUR=X (multiplier = quote).
        """
        from_currency = (from_currency or "EUR").upper()
        if from_currency in fx_cache:
            return fx_cache[from_currency]
        if from_currency == "EUR":
            fx_cache[from_currency] = 1.0
            return 1.0

        pair1 = f"EUR{from_currency}=X"   # 1 EUR = X CUR -> EUR = CUR / X -> mult = 1/X
        pair2 = f"{from_currency}EUR=X"   # 1 CUR = X EUR -> EUR = CUR * X -> mult = X

        # Versuch 1
        try:
            q = yf.Ticker(pair1)
            price = getattr(q, "fast_info", {}).get("last_price")
            if price is None:
                hist = q.history(period="1d")
                price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
            if price and price > 0:
                mult = 1.0 / float(price)
                fx_cache[from_currency] = mult
                return mult
        except Exception:
            pass

        # Versuch 2
        try:
            q = yf.Ticker(pair2)
            price = getattr(q, "fast_info", {}).get("last_price")
            if price is None:
                hist = q.history(period="1d")
                price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
            if price and price > 0:
                mult = float(price)
                fx_cache[from_currency] = mult
                return mult
        except Exception:
            pass

        _log(f"⚠️ Keine FX-Quote für {from_currency}; behalte native Werte (mult=1).")
        fx_cache[from_currency] = 1.0
        return 1.0

    def _momentum_3m_native(ticker: str):
        """
        3M-Momentum auf Adj Close (auto_adjust=True), OHNE FX.
        Def.: (P_t / P_{t-3M}) - 1; wenn an t-3M kein Handel, nimm letzten <= t-3M.
        Fallback: ~63 Handelstage zurück.
        """
        try:
            hist = yf.Ticker(ticker).history(period="9mo", interval="1d", auto_adjust=True)
            if hist.empty or "Close" not in hist:
                return None
            s = hist["Close"].dropna()
            if s.empty:
                return None

            last_date = s.index[-1]
            target_date = last_date - pd.DateOffset(months=3)

            s_before = s.loc[:target_date]
            if not s_before.empty:
                base = s_before.iloc[-1]
            else:
                if len(s) <= 63:
                    return None
                base = s.iloc[-63]

            last = s.iloc[-1]
            if pd.isna(base) or base == 0 or pd.isna(last):
                return None

            return float(last / base - 1.0)
        except Exception:
            return None

    df_out = df.copy()
    price_eur_map = {}
    mom3m_map = {}

    for wkn in df_out["wkn"].astype(str):
        ticker = wkn_to_ticker_lookup(wkn)
        if not ticker:
            _log(f"⚠️ Keine Ticker-Zuordnung für WKN {wkn}.")
            continue

        try:
            t = yf.Ticker(ticker)

            # 1) current_price in EUR
            price_native = _safe_last_price(t)
            if price_native is not None:
                cur = _ticker_currency(t)
                mult = fx_to_eur_multiplier(cur)
                price_eur = float(price_native) * float(mult)
                if price_eur is not None and not (math.isnan(price_eur) or math.isinf(price_eur)):
                    price_eur_map[wkn] = price_eur
                else:
                    _log(f"❌ Ungültiger EUR-Preis für {ticker} (WKN {wkn}).")
            else:
                _log(f"❌ Kein aktueller Preis für {ticker} (WKN {wkn}).")

            # 2) momentum_3m (OHNE FX)
            m3 = _momentum_3m_native(ticker)
            if m3 is not None:
                mom3m_map[wkn] = m3
            else:
                _log(f"ℹ️ Kein 3M-Momentum berechenbar für {ticker} (WKN {wkn}).")

        except Exception as e:
            _log(f"❌ Fehler bei {ticker} (WKN {wkn}): {e}")

    # Preise aktualisieren
    if price_eur_map:
        df_out["current_price"] = (
            df_out["wkn"].astype(str).map(price_eur_map).combine_first(df_out["current_price"])
        )

    # Momentum-Spalte hinzufügen
    df_out["momentum_3m"] = df_out["wkn"].astype(str).map(mom3m_map)

    return df_out



