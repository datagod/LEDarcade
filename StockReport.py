"""
Fetch and format stock reports for LEDarcade terminal scrolling.
"""

import os
import traceback
from configparser import ConfigParser

KeyConfigFileName = "KeyConfig.ini"
DEFAULT_SYMBOLS = ["TSLA", "MSFT", "AAPL"]
STOCK_TYPE_SPEED = 0.064
STOCK_SCROLL_REPEAT = 2
STOCK_POST_SCROLL_WAIT = 30
STOCK_HEADER_RGB = (200, 200, 0)


def CheckConfigFiles():
    if os.path.exists(KeyConfigFileName):
        return

    try:
        with open(KeyConfigFileName, "a+") as config_file:
            config_file.write("[KEYS]\n")
            config_file.write("STOCK_SYMBOLS = TSLA,MSFT,AAPL\n")
            config_file.write("\n")
        print(f"[StockReport] Created default {KeyConfigFileName}")
    except Exception as error:
        print(f"[StockReport] Could not create {KeyConfigFileName}: {error}")


def ParseStockSymbols(symbols):
    if symbols is None:
        return None
    if isinstance(symbols, str):
        raw_symbols = symbols.split(",")
    elif isinstance(symbols, (list, tuple)):
        raw_symbols = symbols
    else:
        return None

    parsed = []
    for symbol in raw_symbols:
        cleaned = str(symbol).strip().upper()
        if cleaned:
            parsed.append(cleaned)
    return parsed or None


def LoadStockSymbols(symbols_override=None):
    parsed = ParseStockSymbols(symbols_override)
    if parsed:
        return parsed

    CheckConfigFiles()
    if not os.path.exists(KeyConfigFileName):
        return DEFAULT_SYMBOLS.copy()

    try:
        key_file = ConfigParser()
        key_file.read(KeyConfigFileName)
        raw = key_file.get("KEYS", "STOCK_SYMBOLS", fallback=",".join(DEFAULT_SYMBOLS))
        symbols = [symbol.strip().upper() for symbol in raw.split(",") if symbol.strip()]
        return symbols or DEFAULT_SYMBOLS.copy()
    except Exception as error:
        print(f"[StockReport] Config read error: {error}")
        return DEFAULT_SYMBOLS.copy()


def _FormatChangePercent(change_percent):
    if change_percent is None:
        return None
    try:
        value = float(change_percent)
    except (TypeError, ValueError):
        return None
    if abs(value) <= 1:
        value *= 100
    return value


def _FormatSymbolLine(symbol, info):
    price = info.get("regularMarketPrice")
    if price is None:
        return f"{symbol} unavailable."

    try:
        price_value = float(price)
    except (TypeError, ValueError):
        return f"{symbol} unavailable."

    change = info.get("regularMarketChange")
    change_percent = _FormatChangePercent(info.get("regularMarketChangePercent"))

    parts = [f"{symbol} ${price_value:.2f}"]
    if change is not None:
        try:
            change_value = float(change)
            sign = "+" if change_value >= 0 else ""
            parts.append(f"{sign}{change_value:.2f} today")
        except (TypeError, ValueError):
            pass
    if change_percent is not None:
        parts.append(f"({change_percent:+.2f}%)")

    return " ".join(parts)


def FetchSymbolInfo(symbol):
    try:
        import yfinance as yf
    except ImportError as error:
        print(f"[StockReport] yfinance not installed: {error}")
        return None

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        if not info:
            return None
        return info
    except Exception as error:
        print(f"[StockReport] Fetch failed for {symbol}: {error}")
        return None


def FetchStockReport(symbols=None):
    """Fetch stock data and return a scrollable header/body report."""
    symbol_list = LoadStockSymbols(symbols)
    lines = []
    errors = []

    for symbol in symbol_list:
        info = FetchSymbolInfo(symbol)
        if info:
            lines.append(_FormatSymbolLine(symbol, info))
        else:
            errors.append(symbol)

    if not lines and errors:
        return {
            "header": "",
            "body": f"Stock data unavailable for {', '.join(errors)}.",
        }

    body_parts = lines
    if errors:
        body_parts.append(f"Unavailable: {', '.join(errors)}.")

    return {
        "header": "Stock report.",
        "body": " ".join(body_parts),
    }