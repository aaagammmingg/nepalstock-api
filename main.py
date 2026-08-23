import datetime as dt
import json
import os
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import pywasm
import pytz
import requests


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://www.nepalstock.com.np"
NEPSE_API = f"{BASE_URL}/api/nots"
API_URL = "https://nepalstock-api-qycd.onrender.com"

PORT = int(os.getenv("PORT", "5000"))

TZ_NP = pytz.timezone("Asia/Kathmandu")

BASE_DIR = Path(__file__).resolve().parent
WASM_FILE = BASE_DIR / "css.wasm"

REQUEST_TIMEOUT = (10, 30)
STOCK_CACHE_TTL = 60


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/128.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE_URL + "/",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
)


# ============================================================
# HELPERS
# ============================================================

def now_np():
    return dt.datetime.now(TZ_NP)


def json_or_raw(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return {"raw": text}


def first_present(mapping, *keys):
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_symbol(stock):
    return first_present(stock, "symbol", "securitySymbol", "ticker", "code", "scripCode", "stockSymbol")


def extract_security_name(stock):
    return first_present(stock, "securityName", "companyName", "securityNameNepali", "name", "stockName")


def extract_security_id(stock):
    return first_present(stock, "securityId", "id", "security_id")


def normalize_stock(stock):
    """
    Normalize a stock record. If it's from the /security endpoint,
    only symbol, securityName, and securityId are available.
    """
    if not isinstance(stock, dict):
        return stock

    # Try to get price fields if they exist (from /today-price)
    return {
        "symbol": extract_symbol(stock),
        "securityName": extract_security_name(stock),
        "securityId": extract_security_id(stock),
        "ltp": first_present(stock, "lastTradedPrice", "ltp", "lastTradedPrice"),
        "open": first_present(stock, "openPrice", "open"),
        "high": first_present(stock, "highPrice", "high"),
        "low": first_present(stock, "lowPrice", "low"),
        "previousClose": first_present(stock, "previousClose", "previousClosingPrice"),
        "change": first_present(stock, "change", "difference"),
        "percentageChange": first_present(stock, "percentageChange", "percentChange"),
        "volume": first_present(stock, "totalTradeQuantity", "volume", "totalTradedQuantity"),
        "turnover": first_present(stock, "totalTradeValue", "turnover"),
        "trades": first_present(stock, "totalTrades", "numberOfTrades"),
        "timestamp": now_np().isoformat(),
    }


def stock_matches_query(stock, query):
    """
    Case-insensitive partial match on symbol, securityName, and securityId.
    """
    query_lower = query.lower()
    symbol = str(extract_symbol(stock) or "").lower()
    name = str(extract_security_name(stock) or "").lower()
    sid = str(extract_security_id(stock) or "").lower()
    return query_lower in symbol or query_lower in name or query_lower in sid


# ============================================================
# TOKEN PARSER
# ============================================================

class TokenParser:
    def __init__(self, wasm_file=WASM_FILE):
        wasm_file = Path(wasm_file)
        if not wasm_file.is_file():
            raise FileNotFoundError(f"WASM file not found: {wasm_file}")
        self.runtime = pywasm.core.Runtime()
        self.wasm_module = self.runtime.instance_from_file(str(wasm_file))

    def invoke(self, function_name, args):
        result = self.runtime.invocate(self.wasm_module, function_name, args)
        if not result:
            raise RuntimeError(f"WASM function returned no value: {function_name}")
        return int(result[0])

    @staticmethod
    def remove_indexes(token, indexes, token_name):
        if not isinstance(token, str):
            raise TypeError(f"{token_name} must be a string")
        if len(indexes) != 5:
            raise ValueError(f"{token_name}: expected 5 indexes")
        if any(i < 0 or i >= len(token) for i in indexes):
            raise ValueError(
                f"{token_name}: WASM produced an invalid token index. "
                f"token length={len(token)}, indexes={indexes}"
            )
        if len(set(indexes)) != len(indexes):
            raise ValueError(f"{token_name}: duplicate token indexes: {indexes}")
        chars = list(token)
        for index in sorted(indexes, reverse=True):
            del chars[index]
        return "".join(chars)

    def parse_token_response(self, token):
        required = [
            "salt1", "salt2", "salt3", "salt4", "salt5",
            "accessToken", "refreshToken"
        ]
        missing = [key for key in required if key not in token]
        if missing:
            raise ValueError("Authentication response is missing: " + ", ".join(missing))

        s1 = int(token["salt1"])
        s2 = int(token["salt2"])
        s3 = int(token["salt3"])
        s4 = int(token["salt4"])
        s5 = int(token["salt5"])

        access_token = token["accessToken"]
        refresh_token = token["refreshToken"]

        access_indexes = [
            self.invoke("cdx", [s1, s2, s3, s4, s5]),
            self.invoke("rdx", [s1, s2, s4, s3, s5]),
            self.invoke("bdx", [s1, s2, s4, s3, s5]),
            self.invoke("ndx", [s1, s2, s4, s3, s5]),
            self.invoke("mdx", [s1, s2, s4, s3, s5]),
        ]
        parsed_access_token = self.remove_indexes(access_token, access_indexes, "accessToken")

        refresh_indexes = [
            self.invoke("cdx", [s2, s1, s3, s5, s4]),
            self.invoke("rdx", [s2, s1, s3, s4, s5]),
            self.invoke("bdx", [s2, s1, s4, s3, s5]),
            self.invoke("ndx", [s2, s1, s4, s3, s5]),
            self.invoke("mdx", [s2, s1, s4, s3, s5]),
        ]
        parsed_refresh_token = self.remove_indexes(refresh_token, refresh_indexes, "refreshToken")

        return parsed_access_token, parsed_refresh_token


# ============================================================
# NEPSE CLIENT
# ============================================================

class Nepse:
    def __init__(self):
        self.token_parser = TokenParser()
        self.access_token = None
        self.refresh_token = None
        self.salts = []
        self.payload_date = None
        self.payload_id = None
        self.lock = threading.RLock()

        # Cache for the full security list
        self._security_cache = None
        self._security_cache_time = None
        self._cache_lock = threading.RLock()

    # ---------- Authentication ----------
    def authenticate(self):
        print("Authenticating with NEPSE...")
        response = session.get(f"{BASE_URL}/api/authenticate/prove", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        token_response = response.json()

        salts = []
        for i in range(1, 6):
            key = f"salt{i}"
            if key not in token_response:
                raise RuntimeError(f"NEPSE authentication response missing {key}")
            value = int(token_response[key])
            token_response[key] = value
            salts.append(value)

        access_token, refresh_token = self.token_parser.parse_token_response(token_response)
        if not access_token:
            raise RuntimeError("NEPSE returned an empty access token")

        with self.lock:
            self.salts = salts
            self.access_token = access_token
            self.refresh_token = refresh_token
        print("NEPSE authentication successful.")

    def get_token(self):
        with self.lock:
            if not self.access_token:
                self.authenticate()
            return self.access_token, self.refresh_token

    def reset_token(self):
        with self.lock:
            self.access_token = None
            self.refresh_token = None
            self.salts = []

    def get_headers(self):
        access_token, _ = self.get_token()
        return {
            **session.headers,
            "Authorization": f"Salter {access_token}",
        }

    @staticmethod
    def build_url(path):
        path = "/" + path.lstrip("/")
        return f"{NEPSE_API}{path}"

    def get(self, path):
        url = self.build_url(path)
        response = session.get(url, headers=self.get_headers(), timeout=REQUEST_TIMEOUT)
        if response.status_code != 401:
            return response.text, response.status_code
        print("Token expired. Re-authenticating...")
        self.reset_token()
        response = session.get(url, headers=self.get_headers(), timeout=REQUEST_TIMEOUT)
        return response.text, response.status_code

    # ---------- Payload helpers ----------
    def get_dummy_id(self):
        current_date = now_np().date()
        with self.lock:
            if self.payload_date == current_date and self.payload_id is not None:
                return self.payload_id

        response, status = self.get("/nepse-data/market-open")
        if status != 200:
            raise RuntimeError(f"Could not get market-open. HTTP {status}: {response[:500]}")
        data = json.loads(response)
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected market-open response")
        if "id" not in data:
            raise RuntimeError("market-open response does not contain id")
        dummy_id = int(data["id"])
        if dummy_id < 0:
            raise RuntimeError(f"Invalid NEPSE payload id: {dummy_id}")

        with self.lock:
            self.payload_id = dummy_id
            self.payload_date = current_date
        return dummy_id

    @staticmethod
    def get_dummy_data():
        return [
            147, 117, 239, 143, 157, 312, 161, 612, 512, 804, 411, 527,
            170, 511, 421, 667, 764, 621, 301, 106, 133, 793, 411, 511,
            312, 423, 344, 346, 653, 758, 342, 222, 236, 811, 711, 611,
            122, 447, 128, 199, 183, 135, 489, 703, 800, 745, 152, 863,
            134, 211, 142, 564, 375, 793, 212, 153, 138, 153, 648, 611,
            151, 649, 318, 143, 117, 756, 119, 141, 717, 113, 112, 146,
            162, 660, 693, 261, 362, 354, 251, 641, 157, 178, 631, 192,
            734, 445, 192, 883, 187, 122, 591, 731, 852, 384, 565, 596,
            451, 772, 624, 691,
        ]

    def _payload_base(self):
        dummy_id = self.get_dummy_id()
        data = self.get_dummy_data()
        if dummy_id >= len(data):
            raise RuntimeError(f"NEPSE payload id {dummy_id} is outside payload table (size={len(data)})")
        now = now_np()
        return data[dummy_id] + dummy_id + 2 * now.day

    def get_floor_payload_id(self):
        e = self._payload_base()
        now = now_np()
        with self.lock:
            if len(self.salts) != 5:
                raise RuntimeError("NEPSE salts are not initialized")
            salts = self.salts.copy()
        salt_index = 1 if e % 10 < 4 else 3
        return e + salts[salt_index] * now.day - salts[salt_index - 1]

    def get_post_payload_id(self):
        return self._payload_base()

    def get_index_payload_id(self):
        e = self._payload_base()
        now = now_np()
        with self.lock:
            if len(self.salts) != 5:
                raise RuntimeError("NEPSE salts are not initialized")
            salts = self.salts.copy()
        salt_index = 3 if e % 10 < 5 else 1
        return e + salts[salt_index] * now.day - salts[salt_index - 1]

    # ---------- POST ----------
    def post(self, path, body=None):
        url = self.build_url(path)
        if body is None:
            if "/nepse-data/floorsheet" in path or "/nepse-data/today-price" in path:
                payload_id = self.get_floor_payload_id()
            elif "/graph/index/" in path:
                payload_id = self.get_index_payload_id()
            else:
                payload_id = self.get_post_payload_id()
            body = {"id": payload_id}

        headers = {**self.get_headers(), "Content-Type": "application/json"}
        response = session.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        if response.status_code != 401:
            return response.text, response.status_code

        print("Token expired. Re-authenticating...")
        self.reset_token()
        headers = {**self.get_headers(), "Content-Type": "application/json"}
        response = session.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        return response.text, response.status_code

    # ---------- Fetch all securities (using /security endpoint) ----------
    def fetch_all_securities(self, force_refresh=False):
        """
        Fetch the full list of securities from /security (GET).
        This endpoint returns all securities without pagination.
        """
        with self._cache_lock:
            if not force_refresh and self._security_cache is not None:
                if time.time() - self._security_cache_time < STOCK_CACHE_TTL:
                    print("Using cached security list")
                    return self._security_cache

        print("Fetching full security list from /security...")
        body, status = self.get("/security")
        if status != 200:
            raise RuntimeError(f"Could not fetch security list. HTTP {status}: {body[:500]}")

        data = json_or_raw(body)
        if not isinstance(data, list):
            # Sometimes the response might be wrapped in a 'content' or 'data' field
            if isinstance(data, dict):
                data = data.get("content") or data.get("data") or data.get("items")
                if not isinstance(data, list):
                    data = []
            else:
                data = []

        print(f"Fetched {len(data)} securities.")

        # Cache
        with self._cache_lock:
            self._security_cache = data
            self._security_cache_time = time.time()

        return data

    # ---------- Public method to get all stocks (for search) ----------
    def get_all_stocks(self, force_refresh=False):
        """
        Returns the full list of securities.
        This is used for the search endpoint.
        """
        return self.fetch_all_securities(force_refresh)

    # ---------- Existing methods for other endpoints ----------
    def get_stock_page(self, page=0, size=20):
        """
        Fetch one page from today-price (for /api/stocks).
        Note: pagination may not work; we keep it for compatibility.
        """
        payload_id = self.get_floor_payload_id()
        body, status = self.post(
            "/nepse-data/today-price",
            {"id": payload_id, "page": page, "size": size}
        )
        if status != 200:
            raise RuntimeError(f"Could not fetch stock page {page}. HTTP {status}: {body[:500]}")
        data = json_or_raw(body)
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected today-price response on page {page}")
        return data


# ============================================================
# SINGLE CLIENT
# ============================================================

nepse = Nepse()


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def response(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.cors()
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        print("GET", self.path)

        try:
            # ---------- Home ----------
            if path == "/":
                self.response({
                    "name": "Open NEPSE API",
                    "status": "running",
                    "timezone": "Asia/Kathmandu",
                    "endpoints": [
                        "/api/stocks",
                        "/api/stocks/SYMBOL",
                        "/api/search?q=NGPL",
                        "/api/search?q=bank",
                        "/api/market",
                        "/api/index",
                        "/api/status",
                        "/api/gainers",
                        "/api/losers",
                        "/api/today-price",
                        "/api/floorsheet",
                    ],
                })
                return

            # ---------- SEARCH ----------
            if path == "/api/search":
                query = parse_qs(parsed.query)
                q = query.get("q", [""])[0].strip()
                if not q:
                    self.response({"success": False, "error": "q is required"}, 400)
                    return

                try:
                    page = int(query.get("page", ["0"])[0])
                    size = int(query.get("size", ["20"])[0])
                except ValueError:
                    self.response({"success": False, "error": "page and size must be integers"}, 400)
                    return

                if page < 0:
                    self.response({"success": False, "error": "page must be >= 0"}, 400)
                    return
                if size < 1 or size > 100:
                    self.response({"success": False, "error": "size must be between 1 and 100"}, 400)
                    return

                # Get the full security list
                all_stocks = nepse.get_all_stocks()
                matches = [s for s in all_stocks if stock_matches_query(s, q)]
                total = len(matches)
                start = page * size
                end = start + size
                paginated = matches[start:end]
                total_pages = (total + size - 1) // size if total > 0 else 0

                self.response({
                    "success": True,
                    "query": q,
                    "page": page,
                    "size": size,
                    "total": total,
                    "totalPages": total_pages,
                    "hasNext": page + 1 < total_pages,
                    "hasPrevious": page > 0,
                    "count": len(paginated),
                    "data": [normalize_stock(s) for s in paginated],
                })
                return

            # ---------- /api/stocks ----------
            if path == "/api/stocks":
                query = parse_qs(parsed.query)
                try:
                    page = int(query.get("page", ["0"])[0])
                    size = int(query.get("size", ["20"])[0])
                except ValueError:
                    self.response({"success": False, "error": "page and size must be integers"}, 400)
                    return
                if page < 0 or size < 1 or size > 100:
                    self.response({"success": False, "error": "invalid page or size"}, 400)
                    return

                symbol = query.get("symbol", [""])[0].strip()
                security_name = query.get("securityName", [""])[0].strip()

                # If no filter, use the today-price endpoint (paginated, but may not work)
                if not symbol and not security_name:
                    try:
                        data = nepse.get_stock_page(page=page, size=size)
                        if isinstance(data, dict):
                            content = data.get("content") or data.get("data") or []
                            if isinstance(content, list):
                                data["content"] = [normalize_stock(s) for s in content]
                        self.response({"success": True, "page": page, "size": size, "data": data})
                    except Exception as e:
                        self.response({"success": False, "error": str(e)}, 500)
                    return

                # If filter is present, search the full security list
                all_stocks = nepse.get_all_stocks()
                matches = []
                for s in all_stocks:
                    sym = str(extract_symbol(s) or "").lower()
                    name = str(extract_security_name(s) or "").lower()
                    if symbol and symbol.lower() not in sym:
                        continue
                    if security_name and security_name.lower() not in name:
                        continue
                    matches.append(s)

                total = len(matches)
                start = page * size
                end = start + size
                paginated = matches[start:end]
                total_pages = (total + size - 1) // size if total > 0 else 0

                self.response({
                    "success": True,
                    "page": page,
                    "size": size,
                    "total": total,
                    "totalPages": total_pages,
                    "hasNext": page + 1 < total_pages,
                    "hasPrevious": page > 0,
                    "count": len(paginated),
                    "data": [normalize_stock(s) for s in paginated],
                })
                return

            # ---------- Single stock ----------
            if path.startswith("/api/stocks/"):
                symbol = unquote(path[len("/api/stocks/"):]).strip().upper()
                if not symbol or "/" in symbol:
                    self.response({"success": False, "error": "Invalid stock symbol"}, 400)
                    return
                body, status = nepse.get(f"/security/{symbol}")
                self.response({"success": status == 200, "symbol": symbol, "data": json_or_raw(body)}, status)
                return

            # ---------- Other endpoints ----------
            if path == "/api/market":
                body, status = nepse.get("/market-summary")
                self.response({"success": status == 200, "data": json_or_raw(body)}, status)
                return

            if path == "/api/index":
                body, status = nepse.get("/nepse-index")
                self.response({"success": status == 200, "data": json_or_raw(body)}, status)
                return

            if path == "/api/status":
                body, status = nepse.get("/nepse-data/market-open")
                self.response({"success": status == 200, "data": json_or_raw(body)}, status)
                return

            if path == "/api/gainers":
                body, status = nepse.get("/top-ten/top-gainer?all=true")
                self.response({"success": status == 200, "data": json_or_raw(body)}, status)
                return

            if path == "/api/losers":
                body, status = nepse.get("/top-ten/top-loser?all=true")
                self.response({"success": status == 200, "data": json_or_raw(body)}, status)
                return

            if path.startswith("/nepse/"):
                nepse_path = path[len("/nepse/") - 1:]
                body, status = nepse.get(nepse_path)
                self.response(json_or_raw(body), status)
                return

            self.response({"success": False, "error": "Endpoint not found"}, 404)

        except requests.RequestException as e:
            print("GET REQUEST ERROR:", repr(e))
            self.response({"success": False, "error": "NEPSE request failed", "details": str(e)}, 502)
        except Exception as e:
            print("GET ERROR:", repr(e))
            self.response({"success": False, "error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        print("POST", self.path)

        try:
            content_length_header = self.headers.get("Content-Length")
            try:
                content_length = int(content_length_header or 0)
            except ValueError:
                self.response({"success": False, "error": "Invalid Content-Length"}, 400)
                return
            if content_length < 0:
                self.response({"success": False, "error": "Invalid request body"}, 400)
                return

            body = None
            if content_length:
                raw = self.rfile.read(content_length).decode("utf-8")
                if raw.strip():
                    try:
                        body = json.loads(raw)
                    except json.JSONDecodeError as e:
                        self.response({"success": False, "error": "Invalid JSON", "details": str(e)}, 400)
                        return

            if path == "/api/today-price":
                response, status = nepse.post("/nepse-data/today-price", body)
                data = json_or_raw(response)
                if isinstance(data, dict):
                    content = data.get("content") or data.get("data") or []
                    if isinstance(content, list):
                        data["content"] = [normalize_stock(s) for s in content]
                self.response({"success": status == 200, "data": data}, status)
                return

            if path == "/api/floorsheet":
                response, status = nepse.post("/nepse-data/floorsheet", body)
                self.response({"success": status == 200, "data": json_or_raw(response)}, status)
                return

            self.response({"success": False, "error": "POST endpoint not found"}, 404)

        except requests.RequestException as e:
            print("POST REQUEST ERROR:", repr(e))
            self.response({"success": False, "error": "NEPSE request failed", "details": str(e)}, 502)
        except Exception as e:
            print("POST ERROR:", repr(e))
            self.response({"success": False, "error": str(e)}, 500)


# ============================================================
# SERVER
# ============================================================

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    server = ReusableThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("\n==========================================")
    print("             OPEN NEPSE API")
    print("==========================================\n")
    print(f"Server: {API_URL}\n")
    print(f"Stocks: {API_URL}/api/stocks")
    print(f"Search: {API_URL}/api/search?q=NGPL")
    print(f"Market: {API_URL}/api/market")
    print(f"Index:  {API_URL}/api/index")
    print(f"Status: {API_URL}/api/status")
    print(f"Today:  {API_URL}/api/today-price\n")
    print("Press CTRL+C to stop.")
    print("==========================================\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
