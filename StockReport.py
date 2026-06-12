"""
Fetch and format stock reports for LEDarcade terminal scrolling.
"""

import os
import re
import traceback
from configparser import ConfigParser

KeyConfigFileName = "KeyConfig.ini"
DEFAULT_SYMBOLS = ["TSLA", "MSFT", "AAPL"]
STOCK_TYPE_SPEED = 0.064
STOCK_SCROLL_REPEAT = 2
STOCK_POST_SCROLL_WAIT = 0
STOCK_HEADER_RGB = (200, 200, 0)
STOCK_SYMBOL_RGB = (200, 0, 200)
STOCK_BLANK_LINES_BEFORE_FIRST = 1
STOCK_BLANK_LINES_BETWEEN = 2


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
        raw_symbols = re.split(r"[,\s]+", symbols.strip())
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


def _FormatPrice(value):
    if value is None:
        return None
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return None


def _FormatLargeCount(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    abs_number = abs(number)
    if abs_number >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.2f}T"
    if abs_number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    if abs_number >= 1_000:
        return f"{number / 1_000:.2f}K"
    return f"{int(number)}"


def _FormatMarketCap(value):
    formatted = _FormatLargeCount(value)
    if formatted is None:
        return None
    return f"${formatted}"


def _JoinParts(parts):
    return "  ".join(part for part in parts if part)


def _FormatSymbolEntry(symbol, info):
    price = info.get("regularMarketPrice")
    if price is None:
        return {"symbol": symbol, "detail_lines": ["Data unavailable."]}

    try:
        price_value = float(price)
    except (TypeError, ValueError):
        return {"symbol": symbol, "detail_lines": ["Data unavailable."]}

    name = info.get("shortName") or info.get("longName") or symbol
    change = info.get("regularMarketChange")
    change_percent = _FormatChangePercent(info.get("regularMarketChangePercent"))

    price_parts = [f"Price ${price_value:.2f}"]
    if change is not None:
        try:
            change_value = float(change)
            sign = "+" if change_value >= 0 else ""
            price_parts.append(f"{sign}{change_value:.2f} today")
        except (TypeError, ValueError):
            pass
    if change_percent is not None:
        price_parts.append(f"({change_percent:+.2f}%)")

    lines = [
        name,
        _JoinParts(price_parts),
        _JoinParts([
            f"Open {_FormatPrice(info.get('regularMarketOpen'))}" if _FormatPrice(info.get('regularMarketOpen')) else None,
            f"High {_FormatPrice(info.get('regularMarketDayHigh'))}" if _FormatPrice(info.get('regularMarketDayHigh')) else None,
            f"Low {_FormatPrice(info.get('regularMarketDayLow'))}" if _FormatPrice(info.get('regularMarketDayLow')) else None,
        ]),
        _JoinParts([
            f"Prev close {_FormatPrice(info.get('regularMarketPreviousClose'))}" if _FormatPrice(info.get('regularMarketPreviousClose')) else None,
            f"Volume {_FormatLargeCount(info.get('regularMarketVolume'))}" if _FormatLargeCount(info.get('regularMarketVolume')) else None,
            f"Avg vol {_FormatLargeCount(info.get('averageVolume'))}" if _FormatLargeCount(info.get('averageVolume')) else None,
        ]),
        _JoinParts([
            f"52 week low {_FormatPrice(info.get('fiftyTwoWeekLow'))}" if _FormatPrice(info.get('fiftyTwoWeekLow')) else None,
            f"high {_FormatPrice(info.get('fiftyTwoWeekHigh'))}" if _FormatPrice(info.get('fiftyTwoWeekHigh')) else None,
        ]),
        _JoinParts([
            f"Market cap {_FormatMarketCap(info.get('marketCap'))}" if _FormatMarketCap(info.get('marketCap')) else None,
            f"PE {float(info.get('trailingPE')):.2f}" if info.get("trailingPE") is not None else None,
            f"Fwd PE {float(info.get('forwardPE')):.2f}" if info.get("forwardPE") is not None else None,
        ]),
        _JoinParts([
            f"Bid {_FormatPrice(info.get('bid'))}" if _FormatPrice(info.get('bid')) else None,
            f"Ask {_FormatPrice(info.get('ask'))}" if _FormatPrice(info.get('ask')) else None,
            f"Yield {float(info.get('dividendYield')) * 100:.2f}%" if info.get("dividendYield") is not None else None,
        ]),
        _JoinParts([
            info.get("fullExchangeName") or info.get("exchange"),
            info.get("currency"),
        ]),
    ]

    detail_lines = [line for line in lines if line]
    return {"symbol": symbol, "detail_lines": detail_lines}


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
    stock_lines = []
    errors = []

    for symbol in symbol_list:
        info = FetchSymbolInfo(symbol)
        if info:
            stock_lines.append(_FormatSymbolEntry(symbol, info))
        else:
            errors.append(symbol)

    if not stock_lines and errors:
        return {
            "header": "",
            "body": f"Stock data unavailable for {', '.join(errors)}.",
            "stock_lines": [],
        }

    body_parts = []
    for entry in stock_lines:
        body_parts.append(entry["symbol"])
        body_parts.extend(entry.get("detail_lines", []))
    if errors:
        body_parts.append(f"Unavailable: {', '.join(errors)}.")

    return {
        "header": "Stock report.",
        "body": " ".join(body_parts),
        "stock_lines": stock_lines,
        "errors": errors,
    }