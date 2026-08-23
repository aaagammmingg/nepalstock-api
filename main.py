# import datetime
# import json
# import os
# import threading
# from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# from urllib.parse import urlparse

# import requests
# import pywasm
# import pytz


# # ============================================================
# # CONFIG
# # ============================================================

# BASE_URL = "https://www.nepalstock.com.np"
# NEPSE_API = f"{BASE_URL}/api/nots"

# PORT = int(os.getenv("PORT", "5000"))

# TZ_NP = pytz.timezone("Asia/Kathmandu")


# # ============================================================
# # HTTP SESSION
# # ============================================================

# session = requests.Session()

# session.headers.update({
#     "User-Agent": (
#         "Mozilla/5.0 (X11; Linux x86_64) "
#         "AppleWebKit/537.36 "
#         "(KHTML, like Gecko) "
#         "Chrome/128.0 Safari/537.36"
#     ),
#     "Accept": "application/json, text/plain, */*",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Referer": BASE_URL + "/",
#     "Pragma": "no-cache",
#     "Cache-Control": "no-cache",
# })


# # ============================================================
# # TOKEN PARSER
# # ============================================================

# class TokenParser:

#     def __init__(self):

#         self.runtime = pywasm.core.Runtime()

#         self.wasm_module = (
#             self.runtime.instance_from_file("css.wasm")
#         )

#     def parse_token_response(self, token):

#         s1 = int(token["salt1"])
#         s2 = int(token["salt2"])
#         s3 = int(token["salt3"])
#         s4 = int(token["salt4"])
#         s5 = int(token["salt5"])

#         access_token = token["accessToken"]
#         refresh_token = token["refreshToken"]

#         # ----------------------------------------------------
#         # ACCESS TOKEN
#         # ----------------------------------------------------

#         n = self.runtime.invocate(
#             self.wasm_module,
#             "cdx",
#             [s1, s2, s3, s4, s5]
#         )[0]

#         l = self.runtime.invocate(
#             self.wasm_module,
#             "rdx",
#             [s1, s2, s4, s3, s5]
#         )[0]

#         o = self.runtime.invocate(
#             self.wasm_module,
#             "bdx",
#             [s1, s2, s4, s3, s5]
#         )[0]

#         p = self.runtime.invocate(
#             self.wasm_module,
#             "ndx",
#             [s1, s2, s4, s3, s5]
#         )[0]

#         q = self.runtime.invocate(
#             self.wasm_module,
#             "mdx",
#             [s1, s2, s4, s3, s5]
#         )[0]

#         parsed_access_token = (
#             access_token[:n]
#             + access_token[n + 1:l]
#             + access_token[l + 1:o]
#             + access_token[o + 1:p]
#             + access_token[p + 1:q]
#             + access_token[q + 1:]
#         )

#         # ----------------------------------------------------
#         # REFRESH TOKEN
#         # ----------------------------------------------------

#         a = self.runtime.invocate(
#             self.wasm_module,
#             "cdx",
#             [s2, s1, s3, s5, s4]
#         )[0]

#         b = self.runtime.invocate(
#             self.wasm_module,
#             "rdx",
#             [s2, s1, s3, s4, s5]
#         )[0]

#         c = self.runtime.invocate(
#             self.wasm_module,
#             "bdx",
#             [s2, s1, s4, s3, s5]
#         )[0]

#         d = self.runtime.invocate(
#             self.wasm_module,
#             "ndx",
#             [s2, s1, s4, s3, s5]
#         )[0]

#         e = self.runtime.invocate(
#             self.wasm_module,
#             "mdx",
#             [s2, s1, s4, s3, s5]
#         )[0]

#         parsed_refresh_token = (
#             refresh_token[:a]
#             + refresh_token[a + 1:b]
#             + refresh_token[b + 1:c]
#             + refresh_token[c + 1:d]
#             + refresh_token[d + 1:e]
#             + refresh_token[e + 1:]
#         )

#         return (
#             parsed_access_token,
#             parsed_refresh_token
#         )


# # ============================================================
# # NEPSE CLIENT
# # ============================================================

# class Nepse:

#     def __init__(self):

#         self.token_parser = TokenParser()

#         self.access_token = None
#         self.refresh_token = None

#         self.salts = []

#         self.payload_day = None
#         self.payload_id = None

#         self.lock = threading.Lock()

#     # ========================================================
#     # AUTHENTICATION
#     # ========================================================

#     def authenticate(self):

#         print("Authenticating with NEPSE...")

#         response = session.get(
#             f"{BASE_URL}/api/authenticate/prove",
#             timeout=20
#         )

#         response.raise_for_status()

#         token_response = response.json()

#         self.salts = []

#         for i in range(1, 6):

#             value = int(
#                 token_response[f"salt{i}"]
#             )

#             token_response[f"salt{i}"] = value

#             self.salts.append(value)

#         (
#             self.access_token,
#             self.refresh_token
#         ) = self.token_parser.parse_token_response(
#             token_response
#         )

#         print("NEPSE authentication successful.")

#     def get_token(self):

#         with self.lock:

#             if not self.access_token:
#                 self.authenticate()

#             return (
#                 self.access_token,
#                 self.refresh_token
#             )

#     def reset_token(self):

#         with self.lock:

#             self.access_token = None
#             self.refresh_token = None

#     # ========================================================
#     # HEADERS
#     # ========================================================

#     def get_headers(self):

#         access_token, _ = self.get_token()

#         return {
#             **session.headers,
#             "Authorization": f"Salter {access_token}",
#         }

#     # ========================================================
#     # URL
#     # ========================================================

#     def build_url(self, path):

#         path = path.lstrip("/")

#         return f"{NEPSE_API}/{path}"

#     # ========================================================
#     # GET REQUEST
#     # ========================================================

#     def get(self, path):

#         url = self.build_url(path)

#         response = session.get(
#             url,
#             headers=self.get_headers(),
#             timeout=20
#         )

#         # Try once again if token expired.
#         if response.status_code == 401:

#             print("Token expired. Re-authenticating...")

#             self.reset_token()

#             response = session.get(
#                 url,
#                 headers=self.get_headers(),
#                 timeout=20
#             )

#         return (
#             response.text,
#             response.status_code
#         )

#     # ========================================================
#     # DUMMY ID
#     #
#     # IMPORTANT:
#     # This is NOT stock-price dummy data.
#     # It is used by NEPSE's protected POST payload mechanism.
#     # ========================================================

#     def get_dummy_id(self):

#         now = datetime.datetime.now(TZ_NP)

#         if self.payload_day == now.day:
#             return self.payload_id

#         response, status = self.get(
#             "/nepse-data/market-open"
#         )

#         if status != 200:

#             raise RuntimeError(
#                 f"Could not get market-open. "
#                 f"HTTP {status}"
#             )

#         data = json.loads(response)

#         self.payload_id = int(data["id"])

#         self.payload_day = now.day

#         return self.payload_id

#     # ========================================================
#     # NEPSE PAYLOAD DATA
#     #
#     # Required by the current protected POST mechanism.
#     # This is NOT market data.
#     # ========================================================

#     def get_dummy_data(self):

#         return [
#             147, 117, 239, 143, 157, 312, 161, 612,
#             512, 804, 411, 527, 170, 511, 421, 667,
#             764, 621, 301, 106, 133, 793, 411, 511,
#             312, 423, 344, 346, 653, 758, 342, 222,
#             236, 811, 711, 611, 122, 447, 128, 199,
#             183, 135, 489, 703, 800, 745, 152, 863,
#             134, 211, 142, 564, 375, 793, 212, 153,
#             138, 153, 648, 611, 151, 649, 318, 143,
#             117, 756, 119, 141, 717, 113, 112, 146,
#             162, 660, 693, 261, 362, 354, 251, 641,
#             157, 178, 631, 192, 734, 445, 192, 883,
#             187, 122, 591, 731, 852, 384, 565, 596,
#             451, 772, 624, 691
#         ]

#     # ========================================================
#     # NORMAL POST PAYLOAD
#     # ========================================================

#     def get_post_payload_id(self):

#         dummy_id = self.get_dummy_id()

#         now = datetime.datetime.now(TZ_NP)

#         data = self.get_dummy_data()

#         return (
#             data[dummy_id]
#             + dummy_id
#             + 2 * now.day
#         )

#     # ========================================================
#     # FLOORSHEET / TODAY PRICE PAYLOAD
#     # ========================================================

#     def get_floor_payload_id(self):

#         dummy_id = self.get_dummy_id()

#         now = datetime.datetime.now(TZ_NP)

#         data = self.get_dummy_data()

#         e = (
#             data[dummy_id]
#             + dummy_id
#             + 2 * now.day
#         )

#         salt_index = (
#             1 if e % 10 < 4
#             else 3
#         )

#         return (
#             e
#             + self.salts[salt_index] * now.day
#             - self.salts[salt_index - 1]
#         )

#     # ========================================================
#     # INDEX GRAPH PAYLOAD
#     # ========================================================

#     def get_index_payload_id(self):

#         dummy_id = self.get_dummy_id()

#         now = datetime.datetime.now(TZ_NP)

#         data = self.get_dummy_data()

#         e = (
#             data[dummy_id]
#             + dummy_id
#             + 2 * now.day
#         )

#         salt_index = (
#             3 if e % 10 < 5
#             else 1
#         )

#         return (
#             e
#             + self.salts[salt_index] * now.day
#             - self.salts[salt_index - 1]
#         )

#     # ========================================================
#     # POST
#     # ========================================================

#     def post(self, path, body=None):

#         url = self.build_url(path)

#         if body is None:

#             if (
#                 "/nepse-data/floorsheet" in path
#                 or "/nepse-data/today-price" in path
#             ):

#                 payload_id = (
#                     self.get_floor_payload_id()
#                 )

#             elif "/graph/index/" in path:

#                 payload_id = (
#                     self.get_index_payload_id()
#                 )

#             else:

#                 payload_id = (
#                     self.get_post_payload_id()
#                 )

#             body = {
#                 "id": payload_id
#             }

#         headers = {
#             **self.get_headers(),
#             "Content-Type": "application/json",
#         }

#         response = session.post(
#             url,
#             headers=headers,
#             json=body,
#             timeout=30
#         )

#         if response.status_code == 401:

#             self.reset_token()

#             headers = {
#                 **self.get_headers(),
#                 "Content-Type": "application/json",
#             }

#             response = session.post(
#                 url,
#                 headers=headers,
#                 json=body,
#                 timeout=30
#             )

#         return (
#             response.text,
#             response.status_code
#         )


# # ============================================================
# # SINGLE CLIENT INSTANCE
# # ============================================================

# nepse = Nepse()


# # ============================================================
# # JSON HELPER
# # ============================================================

# def parse_json(text):

#     try:
#         return json.loads(text)

#     except Exception:

#         return {
#             "raw": text
#         }


# # ============================================================
# # NORMALIZE STOCK
# # ============================================================

# def normalize_stock(stock):

#     if not isinstance(stock, dict):
#         return stock

#     return {
#         "symbol": stock.get("symbol"),

#         "securityName": (
#             stock.get("securityName")
#             or stock.get("companyName")
#             or stock.get("securityNameNepali")
#         ),

#         "ltp": (
#             stock.get("lastTradedPrice")
#             or stock.get("ltp")
#         ),

#         "open": (
#             stock.get("openPrice")
#             or stock.get("open")
#         ),

#         "high": (
#             stock.get("highPrice")
#             or stock.get("high")
#         ),

#         "low": (
#             stock.get("lowPrice")
#             or stock.get("low")
#         ),

#         "previousClose": (
#             stock.get("previousClose")
#             or stock.get("previousClosingPrice")
#         ),

#         "change": (
#             stock.get("change")
#             or stock.get("difference")
#         ),

#         "percentageChange": (
#             stock.get("percentageChange")
#             or stock.get("percentChange")
#         ),

#         "volume": (
#             stock.get("totalTradeQuantity")
#             or stock.get("volume")
#         ),

#         "turnover": (
#             stock.get("totalTradeValue")
#             or stock.get("turnover")
#         ),

#         "trades": (
#             stock.get("totalTrades")
#             or stock.get("numberOfTrades")
#         ),

#         "timestamp": (
#             datetime.datetime.now(TZ_NP)
#             .isoformat()
#         )
#     }


# # ============================================================
# # HTTP HANDLER
# # ============================================================

# class Handler(BaseHTTPRequestHandler):

#     # --------------------------------------------------------
#     # CORS
#     # --------------------------------------------------------

#     def cors(self):

#         self.send_header(
#             "Access-Control-Allow-Origin",
#             "*"
#         )

#         self.send_header(
#             "Access-Control-Allow-Methods",
#             "GET, POST, OPTIONS"
#         )

#         self.send_header(
#             "Access-Control-Allow-Headers",
#             "Content-Type, Authorization"
#         )

#     # --------------------------------------------------------
#     # RESPONSE
#     # --------------------------------------------------------

#     def response(self, data, status=200):

#         self.send_response(status)

#         self.send_header(
#             "Content-Type",
#             "application/json; charset=utf-8"
#         )

#         self.cors()

#         self.end_headers()

#         self.wfile.write(
#             json.dumps(
#                 data,
#                 ensure_ascii=False
#             ).encode("utf-8")
#         )

#     # --------------------------------------------------------
#     # OPTIONS
#     # --------------------------------------------------------

#     def do_OPTIONS(self):

#         self.response({}, 200)

#     # --------------------------------------------------------
#     # GET
#     # --------------------------------------------------------

#     def do_GET(self):

#         parsed = urlparse(self.path)

#         path = parsed.path

#         print("GET", self.path)

#         try:

#             # ==================================================
#             # API HOME
#             # ==================================================

#             if path == "/":

#                 self.response({
#                     "name": "Open NEPSE API",
#                     "status": "running",
#                     "timezone": "Asia/Kathmandu",
#                     "endpoints": [
#                         "/api/stocks",
#                         "/api/stocks/SYMBOL",
#                         "/api/market",
#                         "/api/index",
#                         "/api/status",
#                         "/api/gainers",
#                         "/api/losers"
#                     ]
#                 })

#                 return

#             # ==================================================
#             # STOCKS
#             # ==================================================

#             if path == "/api/stocks":

#                 # Today's price is a protected POST endpoint.
#                 body, status = nepse.post(
#                     "/nepse-data/today-price"
#                 )

#                 data = parse_json(body)

#                 if isinstance(data, list):

#                     data = [
#                         normalize_stock(stock)
#                         for stock in data
#                     ]

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "count": (
#                             len(data)
#                             if isinstance(data, list)
#                             else 0
#                         ),
#                         "data": data
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # SINGLE STOCK
#             # ==================================================

#             if path.startswith("/api/stocks/"):

#                 symbol = path.split("/")[-1].upper()

#                 body, status = nepse.get(
#                     f"/security/{symbol}"
#                 )

#                 data = parse_json(body)

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "symbol": symbol,
#                         "data": data
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # MARKET SUMMARY
#             # ==================================================

#             if path == "/api/market":

#                 body, status = nepse.get(
#                     "/market-summary"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": parse_json(body)
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # NEPSE INDEX
#             # ==================================================

#             if path == "/api/index":

#                 body, status = nepse.get(
#                     "/nepse-index"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": parse_json(body)
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # MARKET STATUS
#             # ==================================================

#             if path == "/api/status":

#                 body, status = nepse.get(
#                     "/nepse-data/market-open"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": parse_json(body)
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # GAINERS
#             # ==================================================

#             if path == "/api/gainers":

#                 body, status = nepse.get(
#                     "/top-ten/top-gainer?all=true"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": parse_json(body)
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # LOSERS
#             # ==================================================

#             if path == "/api/losers":

#                 body, status = nepse.get(
#                     "/top-ten/top-loser?all=true"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": parse_json(body)
#                     },
#                     status
#                 )

#                 return

#             # ==================================================
#             # ORIGINAL NEPSE PROXY
#             # ==================================================

#             if path.startswith("/nepse/"):

#                 nepse_path = path.replace(
#                     "/nepse/",
#                     "/",
#                     1
#                 )

#                 body, status = nepse.get(
#                     nepse_path
#                 )

#                 self.response(
#                     parse_json(body),
#                     status
#                 )

#                 return

#             # ==================================================
#             # NOT FOUND
#             # ==================================================

#             self.response({
#                 "success": False,
#                 "error": "Endpoint not found"
#             }, 404)

#         except Exception as error:

#             print(
#                 "GET ERROR:",
#                 repr(error)
#             )

#             self.response({
#                 "success": False,
#                 "error": str(error)
#             }, 500)

#     # --------------------------------------------------------
#     # POST
#     # --------------------------------------------------------

#     def do_POST(self):

#         parsed = urlparse(self.path)

#         path = parsed.path

#         print("POST", self.path)

#         try:

#             content_length = int(
#                 self.headers.get(
#                     "Content-Length",
#                     0
#                 )
#             )

#             body = None

#             if content_length > 0:

#                 raw = self.rfile.read(
#                     content_length
#                 ).decode("utf-8")
                
#                 if raw.strip():

#                     body = json.loads(raw)

#             # ------------------------------------------------
#             # Today price
#             # ------------------------------------------------

#             if path == "/api/today-price":

#                 response, status = nepse.post(
#                     "/nepse-data/today-price",
#                     body
#                 )

#                 data = parse_json(response)

#                 if isinstance(data, list):

#                     data = [
#                         normalize_stock(stock)
#                         for stock in data
#                     ]

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": data
#                     },
#                     status
#                 )

#                 return

#             # ------------------------------------------------
#             # Floor sheet
#             # ------------------------------------------------

#             if path == "/api/floorsheet":

#                 response, status = nepse.post(
#                     "/nepse-data/floorsheet",
#                     body
#                 )

#                 self.response(
#                     parse_json(response),
#                     status
#                 )

#                 return

#             self.response({
#                 "success": False,
#                 "error": "POST endpoint not found"
#             }, 404)

#         except Exception as error:

#             print(
#                 "POST ERROR:",
#                 repr(error)
#             )

#             self.response({
#                 "success": False,
#                 "error": str(error)
#             }, 500)


# # ============================================================
# # SERVER
# # ============================================================

# def main():

#     server = ThreadingHTTPServer(
#         ("0.0.0.0", PORT),
#         Handler
#     )

#     print()
#     print("==========================================")
#     print("        OPEN NEPSE API")
#     print("==========================================")
#     print()
#     print(
#         f"Server: {API_URL}"
#     )
#     print()
#     print(
#         f"Stocks: http://localhost:{PORT}/api/stocks"
#     )
#     print(
#         f"Market: http://localhost:{PORT}/api/market"
#     )
#     print(
#         f"Index:  http://localhost:{PORT}/api/index"
#     )
#     print(
#         f"Status: http://localhost:{PORT}/api/status"
#     )
#     print()
#     print("Press CTRL+C to stop.")
#     print("==========================================")
#     print()

#     server.serve_forever()


# if __name__ == "__main__":
#     main()



# import datetime as dt
# import json
# import os
# import threading
# from pathlib import Path
# from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
# from urllib.parse import parse_qs, unquote, urlparse

# import pywasm
# import pytz
# import requests


# # ============================================================
# # CONFIG
# # ============================================================

# BASE_URL = "https://www.nepalstock.com.np"
# NEPSE_API = f"{BASE_URL}/api/nots"
# API_URL = "https://nepalstock-api-qycd.onrender.com"

# PORT = int(os.getenv("PORT", "5000"))

# TZ_NP = pytz.timezone("Asia/Kathmandu")

# BASE_DIR = Path(__file__).resolve().parent
# WASM_FILE = BASE_DIR / "css.wasm"

# REQUEST_TIMEOUT = (10, 30)


# # ============================================================
# # HTTP SESSION
# # ============================================================

# session = requests.Session()

# session.headers.update(
#     {
#         "User-Agent": (
#             "Mozilla/5.0 (X11; Linux x86_64) "
#             "AppleWebKit/537.36 "
#             "(KHTML, like Gecko) "
#             "Chrome/128.0 Safari/537.36"
#         ),
#         "Accept": "application/json, text/plain, */*",
#         "Accept-Language": "en-US,en;q=0.9",
#         "Referer": BASE_URL + "/",
#         "Pragma": "no-cache",
#         "Cache-Control": "no-cache",
#     }
# )


# # ============================================================
# # HELPERS
# # ============================================================

# def now_np():
#     return dt.datetime.now(TZ_NP)


# def json_or_raw(text):
#     try:
#         return json.loads(text)
#     except (TypeError, ValueError):
#         return {"raw": text}


# def first_present(mapping, *keys):
#     """
#     Return the first value whose key exists and whose value is
#     not None.

#     Unlike `a or b`, this preserves valid values such as 0.
#     """
#     for key in keys:
#         if key in mapping and mapping[key] is not None:
#             return mapping[key]

#     return None

# def matches_stock(stock, symbol=None, security_name=None):
#     symbol = (symbol or "").strip().lower()
#     security_name = (security_name or "").strip().lower()

#     if symbol:
#         stock_symbol = str(
#             stock.get("symbol", "")
#         ).lower()

#         if symbol not in stock_symbol:
#             return False

#     if security_name:
#         name = str(
#             stock.get("securityName", "")
#         ).lower()

#         if security_name not in name:
#             return False

#     return True


# def normalize_stock(stock):
#     if not isinstance(stock, dict):
#         return stock

#     return {
#         "symbol": first_present(
#             stock,
#             "symbol",
#         ),

#         "securityName": first_present(
#             stock,
#             "securityName",
#             "companyName",
#             "securityNameNepali",
#         ),

#         "ltp": first_present(
#             stock,
#             "lastTradedPrice",
#             "ltp",
#         ),

#         "open": first_present(
#             stock,
#             "openPrice",
#             "open",
#         ),

#         "high": first_present(
#             stock,
#             "highPrice",
#             "high",
#         ),

#         "low": first_present(
#             stock,
#             "lowPrice",
#             "low",
#         ),

#         "previousClose": first_present(
#             stock,
#             "previousClose",
#             "previousClosingPrice",
#         ),

#         "change": first_present(
#             stock,
#             "change",
#             "difference",
#         ),

#         "percentageChange": first_present(
#             stock,
#             "percentageChange",
#             "percentChange",
#         ),

#         "volume": first_present(
#             stock,
#             "totalTradeQuantity",
#             "volume",
#         ),

#         "turnover": first_present(
#             stock,
#             "totalTradeValue",
#             "turnover",
#         ),

#         "trades": first_present(
#             stock,
#             "totalTrades",
#             "numberOfTrades",
#         ),

#         "timestamp": now_np().isoformat(),
#     }


# # ============================================================
# # TOKEN PARSER
# # ============================================================

# class TokenParser:

#     def __init__(self, wasm_file=WASM_FILE):
#         wasm_file = Path(wasm_file)

#         if not wasm_file.is_file():
#             raise FileNotFoundError(
#                 f"WASM file not found: {wasm_file}"
#             )

#         self.runtime = pywasm.core.Runtime()

#         self.wasm_module = (
#             self.runtime.instance_from_file(
#                 str(wasm_file)
#             )
#         )

#     def invoke(self, function_name, args):
#         result = self.runtime.invocate(
#             self.wasm_module,
#             function_name,
#             args,
#         )

#         if not result:
#             raise RuntimeError(
#                 f"WASM function returned no value: "
#                 f"{function_name}"
#             )

#         return int(result[0])

#     @staticmethod
#     def remove_indexes(token, indexes, token_name):
#         """
#         Remove characters at the supplied indexes.

#         The indexes are validated before modifying the token.
#         """
#         if not isinstance(token, str):
#             raise TypeError(
#                 f"{token_name} must be a string"
#             )

#         if len(indexes) != 5:
#             raise ValueError(
#                 f"{token_name}: expected 5 indexes"
#             )

#         if any(i < 0 or i >= len(token) for i in indexes):
#             raise ValueError(
#                 f"{token_name}: WASM produced an invalid "
#                 f"token index. token length={len(token)}, "
#                 f"indexes={indexes}"
#             )

#         if len(set(indexes)) != len(indexes):
#             raise ValueError(
#                 f"{token_name}: duplicate token indexes: "
#                 f"{indexes}"
#             )

#         # Removing characters from right to left avoids
#         # changing the positions of earlier indexes.
#         chars = list(token)

#         for index in sorted(indexes, reverse=True):
#             del chars[index]

#         return "".join(chars)

#     def parse_token_response(self, token):

#         required = [
#             "salt1",
#             "salt2",
#             "salt3",
#             "salt4",
#             "salt5",
#             "accessToken",
#             "refreshToken",
#         ]

#         missing = [
#             key for key in required
#             if key not in token
#         ]

#         if missing:
#             raise ValueError(
#                 "Authentication response is missing: "
#                 + ", ".join(missing)
#             )

#         s1 = int(token["salt1"])
#         s2 = int(token["salt2"])
#         s3 = int(token["salt3"])
#         s4 = int(token["salt4"])
#         s5 = int(token["salt5"])

#         access_token = token["accessToken"]
#         refresh_token = token["refreshToken"]

#         # ----------------------------------------------------
#         # ACCESS TOKEN
#         # ----------------------------------------------------

#         access_indexes = [
#             self.invoke(
#                 "cdx",
#                 [s1, s2, s3, s4, s5],
#             ),

#             self.invoke(
#                 "rdx",
#                 [s1, s2, s4, s3, s5],
#             ),

#             self.invoke(
#                 "bdx",
#                 [s1, s2, s4, s3, s5],
#             ),

#             self.invoke(
#                 "ndx",
#                 [s1, s2, s4, s3, s5],
#             ),

#             self.invoke(
#                 "mdx",
#                 [s1, s2, s4, s3, s5],
#             ),
#         ]

#         parsed_access_token = self.remove_indexes(
#             access_token,
#             access_indexes,
#             "accessToken",
#         )

#         # ----------------------------------------------------
#         # REFRESH TOKEN
#         # ----------------------------------------------------

#         refresh_indexes = [
#             self.invoke(
#                 "cdx",
#                 [s2, s1, s3, s5, s4],
#             ),

#             self.invoke(
#                 "rdx",
#                 [s2, s1, s3, s4, s5],
#             ),

#             self.invoke(
#                 "bdx",
#                 [s2, s1, s4, s3, s5],
#             ),

#             self.invoke(
#                 "ndx",
#                 [s2, s1, s4, s3, s5],
#             ),

#             self.invoke(
#                 "mdx",
#                 [s2, s1, s4, s3, s5],
#             ),
#         ]

#         parsed_refresh_token = self.remove_indexes(
#             refresh_token,
#             refresh_indexes,
#             "refreshToken",
#         )

#         return (
#             parsed_access_token,
#             parsed_refresh_token,
#         )


# # ============================================================
# # NEPSE CLIENT
# # ============================================================

# class Nepse:

#     def __init__(self):

#         self.token_parser = TokenParser()

#         self.access_token = None
#         self.refresh_token = None

#         self.salts = []

#         self.payload_date = None
#         self.payload_id = None

#         self.lock = threading.RLock()

#     # ========================================================
#     # AUTHENTICATION
#     # ========================================================

#     def authenticate(self):

#         print("Authenticating with NEPSE...")

#         response = session.get(
#             f"{BASE_URL}/api/authenticate/prove",
#             timeout=REQUEST_TIMEOUT,
#         )

#         response.raise_for_status()

#         token_response = response.json()

#         salts = []

#         for i in range(1, 6):

#             key = f"salt{i}"

#             if key not in token_response:
#                 raise RuntimeError(
#                     f"NEPSE authentication response missing {key}"
#                 )

#             value = int(token_response[key])

#             token_response[key] = value
#             salts.append(value)

#         access_token, refresh_token = (
#             self.token_parser.parse_token_response(
#                 token_response
#             )
#         )

#         if not access_token:
#             raise RuntimeError(
#                 "NEPSE returned an empty access token"
#             )

#         with self.lock:
#             self.salts = salts
#             self.access_token = access_token
#             self.refresh_token = refresh_token

#         print("NEPSE authentication successful.")

#     def get_token(self):

#         with self.lock:

#             if not self.access_token:
#                 self.authenticate()

#             return (
#                 self.access_token,
#                 self.refresh_token,
#             )

#     def reset_token(self):

#         with self.lock:
#             self.access_token = None
#             self.refresh_token = None
#             self.salts = []

#     # ========================================================
#     # HEADERS
#     # ========================================================

#     def get_headers(self):

#         access_token, _ = self.get_token()

#         return {
#             **session.headers,
#             "Authorization": f"Salter {access_token}",
#         }

#     # ========================================================
#     # URL
#     # ========================================================

#     @staticmethod
#     def build_url(path):

#         path = "/" + path.lstrip("/")

#         return f"{NEPSE_API}{path}"

#     # ========================================================
#     # GET
#     # ========================================================

#     def get(self, path):

#         url = self.build_url(path)

#         response = session.get(
#             url,
#             headers=self.get_headers(),
#             timeout=REQUEST_TIMEOUT,
#         )

#         if response.status_code != 401:
#             return (
#                 response.text,
#                 response.status_code,
#             )

#         print("Token expired. Re-authenticating...")

#         self.reset_token()

#         response = session.get(
#             url,
#             headers=self.get_headers(),
#             timeout=REQUEST_TIMEOUT,
#         )

#         return (
#             response.text,
#             response.status_code,
#         )

#     # ========================================================
#     # DUMMY ID
#     # ========================================================

#     def get_dummy_id(self):

#         current_date = now_np().date()

#         with self.lock:

#             if (
#                 self.payload_date == current_date
#                 and self.payload_id is not None
#             ):
#                 return self.payload_id

#         response, status = self.get(
#             "/nepse-data/market-open"
#         )

#         if status != 200:
#             raise RuntimeError(
#                 f"Could not get market-open. "
#                 f"HTTP {status}: {response[:500]}"
#             )

#         data = json.loads(response)

#         if not isinstance(data, dict):
#             raise RuntimeError(
#                 "Unexpected market-open response"
#             )

#         if "id" not in data:
#             raise RuntimeError(
#                 "market-open response does not contain id"
#             )

#         dummy_id = int(data["id"])

#         if dummy_id < 0:
#             raise RuntimeError(
#                 f"Invalid NEPSE payload id: {dummy_id}"
#             )

#         with self.lock:
#             self.payload_id = dummy_id
#             self.payload_date = current_date

#         return dummy_id

#     # ========================================================
#     # PROTECTED PAYLOAD DATA
#     # ========================================================

#     @staticmethod
#     def get_dummy_data():

#         return [
#             147, 117, 239, 143, 157, 312, 161, 612,
#             512, 804, 411, 527, 170, 511, 421, 667,
#             764, 621, 301, 106, 133, 793, 411, 511,
#             312, 423, 344, 346, 653, 758, 342, 222,
#             236, 811, 711, 611, 122, 447, 128, 199,
#             183, 135, 489, 703, 800, 745, 152, 863,
#             134, 211, 142, 564, 375, 793, 212, 153,
#             138, 153, 648, 611, 151, 649, 318, 143,
#             117, 756, 119, 141, 717, 113, 112, 146,
#             162, 660, 693, 261, 362, 354, 251, 641,
#             157, 178, 631, 192, 734, 445, 192, 883,
#             187, 122, 591, 731, 852, 384, 565, 596,
#             451, 772, 624, 691,
#         ]

#     def _payload_base(self):

#         dummy_id = self.get_dummy_id()
#         data = self.get_dummy_data()

#         # The NEPSE id is used as an index by the original
#         # payload algorithm. Validate it rather than allowing
#         # an obscure IndexError.
#         if dummy_id >= len(data):
#             raise RuntimeError(
#                 f"NEPSE payload id {dummy_id} is outside the "
#                 f"payload table (size={len(data)})"
#             )

#         now = now_np()

#         return (
#             data[dummy_id]
#             + dummy_id
#             + 2 * now.day
#         )

#     # ========================================================
#     # NORMAL POST PAYLOAD
#     # ========================================================

#     def get_post_payload_id(self):

#         return self._payload_base()

#     # ========================================================
#     # FLOORSHEET / TODAY PRICE PAYLOAD
#     # ========================================================

#     def get_floor_payload_id(self):

#         e = self._payload_base()

#         now = now_np()

#         with self.lock:
#             if len(self.salts) != 5:
#                 raise RuntimeError(
#                     "NEPSE salts are not initialized"
#                 )

#             salts = self.salts.copy()

#         salt_index = (
#             1 if e % 10 < 4
#             else 3
#         )

#         return (
#             e
#             + salts[salt_index] * now.day
#             - salts[salt_index - 1]
#         )

#     # ========================================================
#     # INDEX GRAPH PAYLOAD
#     # ========================================================

#     def get_index_payload_id(self):

#         e = self._payload_base()

#         now = now_np()

#         with self.lock:
#             if len(self.salts) != 5:
#                 raise RuntimeError(
#                     "NEPSE salts are not initialized"
#                 )

#             salts = self.salts.copy()

#         salt_index = (
#             3 if e % 10 < 5
#             else 1
#         )

#         return (
#             e
#             + salts[salt_index] * now.day
#             - salts[salt_index - 1]
#         )

#     # ========================================================
#     # POST
#     # ========================================================

#     def post(self, path, body=None):

#         url = self.build_url(path)

#         # Only generate the protected payload when the caller
#         # did not provide a body.
#         if body is None:

#             if (
#                 "/nepse-data/floorsheet" in path
#                 or "/nepse-data/today-price" in path
#             ):
#                 payload_id = (
#                     self.get_floor_payload_id()
#                 )

#             elif "/graph/index/" in path:
#                 payload_id = (
#                     self.get_index_payload_id()
#                 )

#             else:
#                 payload_id = (
#                     self.get_post_payload_id()
#                 )

#             body = {
#                 "id": payload_id,
#             }

#         headers = {
#             **self.get_headers(),
#             "Content-Type": "application/json",
#         }

#         response = session.post(
#             url,
#             headers=headers,
#             json=body,
#             timeout=REQUEST_TIMEOUT,
#         )

#         if response.status_code != 401:
#             return (
#                 response.text,
#                 response.status_code,
#             )

#         print("Token expired. Re-authenticating...")

#         self.reset_token()

#         headers = {
#             **self.get_headers(),
#             "Content-Type": "application/json",
#         }

#         response = session.post(
#             url,
#             headers=headers,
#             json=body,
#             timeout=REQUEST_TIMEOUT,
#         )

#         return (
#             response.text,
#             response.status_code,
#         )


# # ============================================================
# # SINGLE CLIENT
# # ============================================================

# nepse = Nepse()


# # ============================================================
# # HTTP HANDLER
# # ============================================================

# class Handler(BaseHTTPRequestHandler):

#     protocol_version = "HTTP/1.1"

#     # --------------------------------------------------------
#     # Reduce default server logging
#     # --------------------------------------------------------

#     def log_message(self, format, *args):
#         print(
#             "%s - %s"
#             % (
#                 self.address_string(),
#                 format % args,
#             )
#         )

#     # --------------------------------------------------------
#     # CORS
#     # --------------------------------------------------------

#     def cors(self):

#         self.send_header(
#             "Access-Control-Allow-Origin",
#             "*",
#         )

#         self.send_header(
#             "Access-Control-Allow-Methods",
#             "GET, POST, OPTIONS",
#         )

#         self.send_header(
#             "Access-Control-Allow-Headers",
#             "Content-Type, Authorization",
#         )

#     # --------------------------------------------------------
#     # RESPONSE
#     # --------------------------------------------------------

#     def response(self, data, status=200):

#         payload = json.dumps(
#             data,
#             ensure_ascii=False,
#         ).encode("utf-8")

#         self.send_response(status)

#         self.send_header(
#             "Content-Type",
#             "application/json; charset=utf-8",
#         )

#         self.send_header(
#             "Content-Length",
#             str(len(payload)),
#         )

#         self.send_header(
#             "Cache-Control",
#             "no-store",
#         )

#         self.cors()

#         self.end_headers()

#         try:
#             self.wfile.write(payload)
#         except (BrokenPipeError, ConnectionResetError):
#             pass

#     # --------------------------------------------------------
#     # OPTIONS
#     # --------------------------------------------------------

#     def do_OPTIONS(self):

#         self.send_response(204)

#         self.send_header(
#             "Content-Length",
#             "0",
#         )

#         self.cors()

#         self.end_headers()

#     # --------------------------------------------------------
#     # GET
#     # --------------------------------------------------------

#     def do_GET(self):

#         parsed = urlparse(self.path)
#         path = parsed.path

#         print("GET", self.path)

#         try:

#             # ==================================================
#             # HOME
#             # ==================================================

#             if path == "/":

#                 self.response(
#                     {
#                         "name": "Open NEPSE API",
#                         "status": "running",
#                         "timezone": "Asia/Kathmandu",
#                         "endpoints": [
#                             "/api/stocks",
#                             "/api/stocks/SYMBOL",
#                             "/api/market",
#                             "/api/index",
#                             "/api/status",
#                             "/api/gainers",
#                             "/api/losers",
#                             "/api/today-price",
#                             "/api/floorsheet",
#                         ],
#                     }
#                 )

#                 return

#             # ==================================================
#             # STOCKS
#             # ==================================================

#             # if path == "/api/stocks":

#             #     body, status = nepse.post(
#             #         "/nepse-data/today-price"
#             #     )

#             #     data = json_or_raw(body)

#             #     if isinstance(data, list):

#             #         data = [
#             #             normalize_stock(stock)
#             #             for stock in data
#             #         ]

#             #     self.response(
#             #         {
#             #             "success": status == 200,
#             #             "count": (
#             #                 len(data)
#             #                 if isinstance(data, list)
#             #                 else 0
#             #             ),
#             #             "data": data,
#             #         },
#             #         status,
#             #     )

#             #     return

#             # if path == "/api/stocks":

#             #     query = parse_qs(parsed.query)

#             #     page = int(query.get("page", ["0"])[0])
#             #     size = int(query.get("size", ["20"])[0])

#             #     if page < 0:
#             #         self.response(
#             #             {
#             #                 "success": False,
#             #                 "error": "page must be >= 0",
#             #             },
#             #             400,
#             #         )
#             #         return

#             #     if size < 1 or size > 100:
#             #         self.response(
#             #             {
#             #                 "success": False,
#             #                 "error": "size must be between 1 and 100",
#             #             },
#             #             400,
#             #         )
#             #         return

#             #     payload_id = nepse.get_floor_payload_id()

#             #     body, status = nepse.post(
#             #         "/nepse-data/today-price",
#             #         {
#             #             "id": payload_id,
#             #             "page": page,
#             #             "size": size,
#             #         },
#             #     )

#             #     data = json_or_raw(body)

#             #     if isinstance(data, dict) and "content" in data:

#             #         data["content"] = [
#             #             normalize_stock(stock)
#             #             for stock in data["content"]
#             #         ]

#             #     self.response(
#             #         {
#             #             "success": status == 200,
#             #             "page": page,
#             #             "size": size,
#             #             "data": data,
#             #         },
#             #         status,
#             #     )

#             #     return

#             if path == "/api/stocks":

#                 query = parse_qs(parsed.query)

#                 page = int(query.get("page", ["0"])[0])
#                 size = int(query.get("size", ["20"])[0])

#                 symbol = query.get("symbol", [""])[0]
#                 security_name = query.get("securityName", [""])[0]

#                 body, status = nepse.post(
#                     "/nepse-data/today-price",
#                     {
#                         "id": nepse.get_floor_payload_id(),
#                         "page": page,
#                         "size": size,
#                     },
#                 )

#                 data = json_or_raw(body)

#                 if isinstance(data, dict) and "content" in data:

#                     stocks = data["content"]

#                     stocks = [
#                         stock
#                         for stock in stocks
#                         if matches_stock(
#                             stock,
#                             symbol,
#                             security_name,
#                         )
#                     ]

#                     data["content"] = [
#                         normalize_stock(stock)
#                         for stock in stocks
#                     ]

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "page": page,
#                         "size": size,
#                         "data": data,
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # SINGLE STOCK
#             # ==================================================

#             if path.startswith("/api/stocks/"):

#                 symbol = unquote(
#                     path[len("/api/stocks/"):]
#                 ).strip().upper()

#                 if not symbol or "/" in symbol:
#                     self.response(
#                         {
#                             "success": False,
#                             "error": "Invalid stock symbol",
#                         },
#                         400,
#                     )
#                     return

#                 body, status = nepse.get(
#                     f"/security/{symbol}"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "symbol": symbol,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # MARKET
#             # ==================================================

#             if path == "/api/market":

#                 body, status = nepse.get(
#                     "/market-summary"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # INDEX
#             # ==================================================

#             if path == "/api/index":

#                 body, status = nepse.get(
#                     "/nepse-index"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # MARKET STATUS
#             # ==================================================

#             if path == "/api/status":

#                 body, status = nepse.get(
#                     "/nepse-data/market-open"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # GAINERS
#             # ==================================================

#             if path == "/api/gainers":

#                 body, status = nepse.get(
#                     "/top-ten/top-gainer?all=true"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # LOSERS
#             # ==================================================

#             if path == "/api/losers":

#                 body, status = nepse.get(
#                     "/top-ten/top-loser?all=true"
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(body),
#                     },
#                     status,
#                 )

#                 return

#             # ==================================================
#             # ORIGINAL NEPSE PROXY
#             # ==================================================

#             if path.startswith("/nepse/"):

#                 nepse_path = path[
#                     len("/nepse/") - 1:
#                 ]

#                 body, status = nepse.get(
#                     nepse_path
#                 )

#                 self.response(
#                     json_or_raw(body),
#                     status,
#                 )

#                 return

#             # ==================================================
#             # NOT FOUND
#             # ==================================================

#             self.response(
#                 {
#                     "success": False,
#                     "error": "Endpoint not found",
#                 },
#                 404,
#             )

#         except requests.RequestException as error:

#             print(
#                 "GET REQUEST ERROR:",
#                 repr(error),
#             )

#             self.response(
#                 {
#                     "success": False,
#                     "error": "NEPSE request failed",
#                     "details": str(error),
#                 },
#                 502,
#             )

#         except Exception as error:

#             print(
#                 "GET ERROR:",
#                 repr(error),
#             )

#             self.response(
#                 {
#                     "success": False,
#                     "error": str(error),
#                 },
#                 500,
#             )

#     # --------------------------------------------------------
#     # POST
#     # --------------------------------------------------------

#     def do_POST(self):

#         parsed = urlparse(self.path)
#         path = parsed.path

#         print("POST", self.path)

#         try:

#             content_length_header = (
#                 self.headers.get(
#                     "Content-Length"
#                 )
#             )

#             try:
#                 content_length = int(
#                     content_length_header or 0
#                 )
#             except ValueError:
#                 self.response(
#                     {
#                         "success": False,
#                         "error": "Invalid Content-Length",
#                     },
#                     400,
#                 )
#                 return

#             if content_length < 0:
#                 self.response(
#                     {
#                         "success": False,
#                         "error": "Invalid request body",
#                     },
#                     400,
#                 )
#                 return

#             body = None

#             if content_length:

#                 raw = self.rfile.read(
#                     content_length
#                 ).decode("utf-8")

#                 if raw.strip():

#                     try:
#                         body = json.loads(raw)
#                     except json.JSONDecodeError as error:

#                         self.response(
#                             {
#                                 "success": False,
#                                 "error": "Invalid JSON",
#                                 "details": str(error),
#                             },
#                             400,
#                         )
#                         return

#             # ------------------------------------------------
#             # TODAY PRICE
#             # ------------------------------------------------

#             # if path == "/api/today-price":

#             #     response, status = nepse.post(
#             #         "/nepse-data/today-price",
#             #         body,
#             #     )

#             #     data = json_or_raw(response)

#             #     if isinstance(data, list):

#             #         data = [
#             #             normalize_stock(stock)
#             #             for stock in data
#             #         ]

#             #     self.response(
#             #         {
#             #             "success": status == 200,
#             #             "count": (
#             #                 len(data)
#             #                 if isinstance(data, list)
#             #                 else 0
#             #             ),
#             #             "data": data,
#             #         },
#             #         status,
#             #     )

#             #     return
            

#             if path == "/api/today-price":

#                     response, status = nepse.post(
#                         "/nepse-data/today-price",
#                         body,
#                     )

#                     data = json_or_raw(response)

#                     if isinstance(data, dict) and "content" in data:
#                         data["content"] = [
#                             normalize_stock(stock)
#                             for stock in data["content"]
#                         ]

#                     self.response(
#                         {
#                             "success": status == 200,
#                             "data": data,
#                         },
#                         status,
#                     )

#                     return

#             # ------------------------------------------------
#             # FLOORSHEET
#             # ------------------------------------------------

#             if path == "/api/floorsheet":

#                 response, status = nepse.post(
#                     "/nepse-data/floorsheet",
#                     body,
#                 )

#                 self.response(
#                     {
#                         "success": status == 200,
#                         "data": json_or_raw(response),
#                     },
#                     status,
#                 )

#                 return

#             # ------------------------------------------------
#             # NOT FOUND
#             # ------------------------------------------------

#             self.response(
#                 {
#                     "success": False,
#                     "error": "POST endpoint not found",
#                 },
#                 404,
#             )

#         except requests.RequestException as error:

#             print(
#                 "POST REQUEST ERROR:",
#                 repr(error),
#             )

#             self.response(
#                 {
#                     "success": False,
#                     "error": "NEPSE request failed",
#                     "details": str(error),
#                 },
#                 502,
#             )

#         except Exception as error:

#             print(
#                 "POST ERROR:",
#                 repr(error),
#             )

#             self.response(
#                 {
#                     "success": False,
#                     "error": str(error),
#                 },
#                 500,
#             )


# # ============================================================
# # SERVER
# # ============================================================

# class ReusableThreadingHTTPServer(
#     ThreadingHTTPServer
# ):
#     allow_reuse_address = True
#     daemon_threads = True


# def main():

#     server = ReusableThreadingHTTPServer(
#         ("0.0.0.0", PORT),
#         Handler,
#     )

#     print()
#     print("==========================================")
#     print("             OPEN NEPSE API")
#     print("==========================================")
#     print()
#     print(
#         f"Server: {API_URL}"
#     )
#     print()
#     print(
#         f"Stocks: {API_URL}/api/stocks"
#     )
#     print(
#         f"Market: {API_URL}/api/market"
#     )
#     print(
#         f"Index:  {API_URL}/api/index"
#     )
#     print(
#         f"Status: {API_URL}/api/status"
#     )
#     print(
#         f"Today:  {API_URL}/api/today-price"
#     )
#     print()
#     print("Press CTRL+C to stop.")
#     print("==========================================")
#     print()

#     try:
#         server.serve_forever()

#     except KeyboardInterrupt:
#         print("\nStopping server...")

#     finally:
#         server.server_close()


# if __name__ == "__main__":
#     main()


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

# NEPSE currently has around 344 securities.
# 100 is kept below the API's usual maximum page size.
NEPSE_PAGE_SIZE = 100

# Safety limit so a broken NEPSE pagination response
# cannot create an infinite loop.
MAX_STOCK_PAGES = 100

# Cache TTL for the full stock list (seconds)
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
    """
    Return the first value whose key exists and whose value
    is not None.

    Unlike `a or b`, this preserves valid values such as 0.
    """

    for key in keys:

        if key in mapping and mapping[key] is not None:
            return mapping[key]

    return None


def matches_stock(
    stock,
    symbol=None,
    security_name=None,
):
    """
    Match a stock against symbol and/or securityName.

    Matching is case-insensitive and uses partial matching.

    Examples:

        symbol=NGPL
        symbol=ngpl

        securityName=bank
        securityName=development bank
    """

    symbol = (
        str(symbol or "")
        .strip()
        .lower()
    )

    security_name = (
        str(security_name or "")
        .strip()
        .lower()
    )

    if not symbol and not security_name:
        return True

    stock_symbol = str(
        first_present(
            stock,
            "symbol",
        ) or ""
    ).lower()

    stock_security_name = str(
        first_present(
            stock,
            "securityName",
            "companyName",
            "securityNameNepali",
        ) or ""
    ).lower()

    symbol_match = True
    security_name_match = True

    if symbol:
        symbol_match = symbol in stock_symbol

    if security_name:
        security_name_match = (
            security_name in stock_security_name
        )

    # If both are supplied, BOTH must match.
    return symbol_match and security_name_match


def normalize_stock(stock):
    """
    Convert NEPSE stock object into a smaller consistent object.
    """

    if not isinstance(stock, dict):
        return stock

    return {
        "symbol": first_present(
            stock,
            "symbol",
        ),

        "securityName": first_present(
            stock,
            "securityName",
            "companyName",
            "securityNameNepali",
        ),

        "ltp": first_present(
            stock,
            "lastTradedPrice",
            "ltp",
        ),

        "open": first_present(
            stock,
            "openPrice",
            "open",
        ),

        "high": first_present(
            stock,
            "highPrice",
            "high",
        ),

        "low": first_present(
            stock,
            "lowPrice",
            "low",
        ),

        "previousClose": first_present(
            stock,
            "previousClose",
            "previousClosingPrice",
        ),

        "change": first_present(
            stock,
            "change",
            "difference",
        ),

        "percentageChange": first_present(
            stock,
            "percentageChange",
            "percentChange",
        ),

        "volume": first_present(
            stock,
            "totalTradeQuantity",
            "volume",
        ),

        "turnover": first_present(
            stock,
            "totalTradeValue",
            "turnover",
        ),

        "trades": first_present(
            stock,
            "totalTrades",
            "numberOfTrades",
        ),

        "timestamp": now_np().isoformat(),
    }


def safe_int(value, default=None):
    """
    Safely convert a value to int.
    """

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# TOKEN PARSER
# ============================================================

class TokenParser:

    def __init__(self, wasm_file=WASM_FILE):

        wasm_file = Path(wasm_file)

        if not wasm_file.is_file():
            raise FileNotFoundError(
                f"WASM file not found: {wasm_file}"
            )

        self.runtime = pywasm.core.Runtime()

        self.wasm_module = (
            self.runtime.instance_from_file(
                str(wasm_file)
            )
        )

    def invoke(
        self,
        function_name,
        args,
    ):

        result = self.runtime.invocate(
            self.wasm_module,
            function_name,
            args,
        )

        if not result:
            raise RuntimeError(
                "WASM function returned no value: "
                f"{function_name}"
            )

        return int(result[0])

    @staticmethod
    def remove_indexes(
        token,
        indexes,
        token_name,
    ):
        """
        Remove characters at supplied indexes.
        """

        if not isinstance(token, str):
            raise TypeError(
                f"{token_name} must be a string"
            )

        if len(indexes) != 5:
            raise ValueError(
                f"{token_name}: expected 5 indexes"
            )

        if any(
            i < 0 or i >= len(token)
            for i in indexes
        ):
            raise ValueError(
                f"{token_name}: WASM produced an "
                f"invalid token index. "
                f"token length={len(token)}, "
                f"indexes={indexes}"
            )

        if len(set(indexes)) != len(indexes):
            raise ValueError(
                f"{token_name}: duplicate token indexes: "
                f"{indexes}"
            )

        chars = list(token)

        for index in sorted(
            indexes,
            reverse=True,
        ):
            del chars[index]

        return "".join(chars)

    def parse_token_response(
        self,
        token,
    ):

        required = [
            "salt1",
            "salt2",
            "salt3",
            "salt4",
            "salt5",
            "accessToken",
            "refreshToken",
        ]

        missing = [
            key
            for key in required
            if key not in token
        ]

        if missing:
            raise ValueError(
                "Authentication response is missing: "
                + ", ".join(missing)
            )

        s1 = int(token["salt1"])
        s2 = int(token["salt2"])
        s3 = int(token["salt3"])
        s4 = int(token["salt4"])
        s5 = int(token["salt5"])

        access_token = token["accessToken"]
        refresh_token = token["refreshToken"]

        # ----------------------------------------------------
        # ACCESS TOKEN
        # ----------------------------------------------------

        access_indexes = [
            self.invoke(
                "cdx",
                [s1, s2, s3, s4, s5],
            ),

            self.invoke(
                "rdx",
                [s1, s2, s4, s3, s5],
            ),

            self.invoke(
                "bdx",
                [s1, s2, s4, s3, s5],
            ),

            self.invoke(
                "ndx",
                [s1, s2, s4, s3, s5],
            ),

            self.invoke(
                "mdx",
                [s1, s2, s4, s3, s5],
            ),
        ]

        parsed_access_token = (
            self.remove_indexes(
                access_token,
                access_indexes,
                "accessToken",
            )
        )

        # ----------------------------------------------------
        # REFRESH TOKEN
        # ----------------------------------------------------

        refresh_indexes = [
            self.invoke(
                "cdx",
                [s2, s1, s3, s5, s4],
            ),

            self.invoke(
                "rdx",
                [s2, s1, s3, s4, s5],
            ),

            self.invoke(
                "bdx",
                [s2, s1, s4, s3, s5],
            ),

            self.invoke(
                "ndx",
                [s2, s1, s4, s3, s5],
            ),

            self.invoke(
                "mdx",
                [s2, s1, s4, s3, s5],
            ),
        ]

        parsed_refresh_token = (
            self.remove_indexes(
                refresh_token,
                refresh_indexes,
                "refreshToken",
            )
        )

        return (
            parsed_access_token,
            parsed_refresh_token,
        )


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

        # Cache for the full stock list (thread‑safe)
        self._stock_cache = None          # list of stock dicts
        self._stock_cache_time = None     # timestamp (seconds since epoch)
        self._cache_lock = threading.RLock()

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def authenticate(self):

        print("Authenticating with NEPSE...")

        response = session.get(
            f"{BASE_URL}/api/authenticate/prove",
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        token_response = response.json()

        salts = []

        for i in range(1, 6):

            key = f"salt{i}"

            if key not in token_response:
                raise RuntimeError(
                    f"NEPSE authentication response "
                    f"missing {key}"
                )

            value = int(
                token_response[key]
            )

            token_response[key] = value

            salts.append(value)

        (
            access_token,
            refresh_token,
        ) = self.token_parser.parse_token_response(
            token_response
        )

        if not access_token:
            raise RuntimeError(
                "NEPSE returned an empty access token"
            )

        with self.lock:

            self.salts = salts

            self.access_token = (
                access_token
            )

            self.refresh_token = (
                refresh_token
            )

        print(
            "NEPSE authentication successful."
        )

    def get_token(self):

        with self.lock:

            if not self.access_token:
                self.authenticate()

            return (
                self.access_token,
                self.refresh_token,
            )

    def reset_token(self):

        with self.lock:

            self.access_token = None
            self.refresh_token = None
            self.salts = []

    # ========================================================
    # HEADERS
    # ========================================================

    def get_headers(self):

        access_token, _ = (
            self.get_token()
        )

        return {
            **session.headers,
            "Authorization": (
                f"Salter {access_token}"
            ),
        }

    # ========================================================
    # URL
    # ========================================================

    @staticmethod
    def build_url(path):

        path = "/" + path.lstrip("/")

        return f"{NEPSE_API}{path}"

    # ========================================================
    # GET
    # ========================================================

    def get(self, path):

        url = self.build_url(path)

        response = session.get(
            url,
            headers=self.get_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 401:

            return (
                response.text,
                response.status_code,
            )

        print(
            "Token expired. Re-authenticating..."
        )

        self.reset_token()

        response = session.get(
            url,
            headers=self.get_headers(),
            timeout=REQUEST_TIMEOUT,
        )

        return (
            response.text,
            response.status_code,
        )

    # ========================================================
    # DUMMY ID
    # ========================================================

    def get_dummy_id(self):

        current_date = now_np().date()

        with self.lock:

            if (
                self.payload_date
                == current_date
                and self.payload_id is not None
            ):
                return self.payload_id

        response, status = self.get(
            "/nepse-data/market-open"
        )

        if status != 200:
            raise RuntimeError(
                "Could not get market-open. "
                f"HTTP {status}: "
                f"{response[:500]}"
            )

        data = json.loads(response)

        if not isinstance(data, dict):
            raise RuntimeError(
                "Unexpected market-open response"
            )

        if "id" not in data:
            raise RuntimeError(
                "market-open response does not "
                "contain id"
            )

        dummy_id = int(
            data["id"]
        )

        if dummy_id < 0:
            raise RuntimeError(
                f"Invalid NEPSE payload id: "
                f"{dummy_id}"
            )

        with self.lock:

            self.payload_id = dummy_id
            self.payload_date = current_date

        return dummy_id

    # ========================================================
    # PROTECTED PAYLOAD DATA
    # ========================================================

    @staticmethod
    def get_dummy_data():

        return [
            147, 117, 239, 143, 157, 312,
            161, 612, 512, 804, 411, 527,
            170, 511, 421, 667, 764, 621,
            301, 106, 133, 793, 411, 511,
            312, 423, 344, 346, 653, 758,
            342, 222, 236, 811, 711, 611,
            122, 447, 128, 199, 183, 135,
            489, 703, 800, 745, 152, 863,
            134, 211, 142, 564, 375, 793,
            212, 153, 138, 153, 648, 611,
            151, 649, 318, 143, 117, 756,
            119, 141, 717, 113, 112, 146,
            162, 660, 693, 261, 362, 354,
            251, 641, 157, 178, 631, 192,
            734, 445, 192, 883, 187, 122,
            591, 731, 852, 384, 565, 596,
            451, 772, 624, 691,
        ]

    def _payload_base(self):

        dummy_id = self.get_dummy_id()

        data = self.get_dummy_data()

        if dummy_id >= len(data):

            raise RuntimeError(
                f"NEPSE payload id {dummy_id} "
                f"is outside payload table "
                f"(size={len(data)})"
            )

        now = now_np()

        return (
            data[dummy_id]
            + dummy_id
            + 2 * now.day
        )

    # ========================================================
    # NORMAL POST PAYLOAD
    # ========================================================

    def get_post_payload_id(self):

        return self._payload_base()

    # ========================================================
    # FLOORSHEET / TODAY PRICE PAYLOAD
    # ========================================================

    def get_floor_payload_id(self):

        e = self._payload_base()

        now = now_np()

        with self.lock:

            if len(self.salts) != 5:
                raise RuntimeError(
                    "NEPSE salts are not initialized"
                )

            salts = self.salts.copy()

        salt_index = (
            1
            if e % 10 < 4
            else 3
        )

        return (
            e
            + salts[salt_index] * now.day
            - salts[salt_index - 1]
        )

    # ========================================================
    # INDEX GRAPH PAYLOAD
    # ========================================================

    def get_index_payload_id(self):

        e = self._payload_base()

        now = now_np()

        with self.lock:

            if len(self.salts) != 5:
                raise RuntimeError(
                    "NEPSE salts are not initialized"
                )

            salts = self.salts.copy()

        salt_index = (
            3
            if e % 10 < 5
            else 1
        )

        return (
            e
            + salts[salt_index] * now.day
            - salts[salt_index - 1]
        )

    # ========================================================
    # POST
    # ========================================================

    def post(
        self,
        path,
        body=None,
    ):

        url = self.build_url(path)

        # Generate protected payload only
        # when caller didn't supply body.
        if body is None:

            if (
                "/nepse-data/floorsheet"
                in path
                or
                "/nepse-data/today-price"
                in path
            ):

                payload_id = (
                    self.get_floor_payload_id()
                )

            elif "/graph/index/" in path:

                payload_id = (
                    self.get_index_payload_id()
                )

            else:

                payload_id = (
                    self.get_post_payload_id()
                )

            body = {
                "id": payload_id,
            }

        headers = {
            **self.get_headers(),
            "Content-Type": (
                "application/json"
            ),
        }

        response = session.post(
            url,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 401:

            return (
                response.text,
                response.status_code,
            )

        print(
            "Token expired. Re-authenticating..."
        )

        self.reset_token()

        headers = {
            **self.get_headers(),
            "Content-Type": (
                "application/json"
            ),
        }

        response = session.post(
            url,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )

        return (
            response.text,
            response.status_code,
        )

    # ========================================================
    # FETCH ONE STOCK PAGE
    # ========================================================

    def get_stock_page(
        self,
        page=0,
        size=100,
    ):
        """
        Fetch one page from NEPSE today-price.
        """

        payload_id = (
            self.get_floor_payload_id()
        )

        body, status = self.post(
            "/nepse-data/today-price",
            {
                "id": payload_id,
                "page": page,
                "size": size,
            },
        )

        if status != 200:

            raise RuntimeError(
                f"Could not fetch stock page "
                f"{page}. HTTP {status}: "
                f"{body[:500]}"
            )

        data = json_or_raw(body)

        if not isinstance(data, dict):

            raise RuntimeError(
                f"Unexpected today-price "
                f"response on page {page}"
            )

        content = data.get(
            "content",
            [],
        )

        if not isinstance(content, list):

            raise RuntimeError(
                f"Invalid content on page "
                f"{page}"
            )

        return data

    # ========================================================
    # FETCH ALL STOCKS (with caching)
    # ========================================================

    def get_all_stocks(
        self,
        page_size=NEPSE_PAGE_SIZE,
        force_refresh=False,
    ):
        """
        Fetch every page from NEPSE and return one combined list,
        with thread‑safe caching.

        This is the important part for search.

        Search MUST NOT be performed against only page 0.
        """

        # Check cache first
        with self._cache_lock:
            now = time.time()
            if (
                not force_refresh
                and self._stock_cache is not None
                and self._stock_cache_time is not None
                and (now - self._stock_cache_time) < STOCK_CACHE_TTL
            ):
                print("Using cached stock list")
                return self._stock_cache

        # Cache miss or expired – fetch all pages
        all_stocks = []
        stock_map = {}          # deduplicate by symbol
        page = 0

        while page < MAX_STOCK_PAGES:

            print(
                f"Fetching NEPSE stock page "
                f"{page}..."
            )

            data = self.get_stock_page(
                page=page,
                size=page_size,
            )

            content = data.get(
                "content",
                [],
            )

            # Add stocks to map (deduplicate by symbol)
            for stock in content:
                symbol = stock.get("symbol")
                if symbol:
                    stock_map[symbol] = stock
                else:
                    # If no symbol, keep it anyway (fallback)
                    all_stocks.append(stock)

            # Determine pagination information
            total_pages = safe_int(
                data.get("totalPages")
            )

            total_elements = safe_int(
                data.get("totalElements")
            )

            current_page = safe_int(
                data.get("number")
            )

            if current_page is None:
                current_page = page

            print(
                f"NEPSE page {page}: "
                f"{len(content)} stocks"
            )

            # Best case: NEPSE tells us totalPages.
            if (
                total_pages is not None
                and total_pages > 0
            ):

                if (
                    current_page
                    >= total_pages - 1
                ):
                    break

                page += 1
                continue

            # If totalElements is available, stop when we have enough.
            if (
                total_elements is not None
                and len(stock_map) + len(all_stocks)
                >= total_elements
            ):
                break

            # Fallback: if returned records are fewer than requested page size,
            # we reached the end.
            if len(content) < page_size:
                break

            # Empty page = definitely finished.
            if not content:
                break

            page += 1

        if page >= MAX_STOCK_PAGES:

            print(
                "WARNING: maximum stock page "
                "limit reached."
            )

        # Combine deduplicated stocks and any without symbol
        final_stocks = list(stock_map.values()) + all_stocks

        print(
            f"Fetched {len(final_stocks)} "
            f"stocks from NEPSE (after dedup)."
        )

        # Update cache
        with self._cache_lock:
            self._stock_cache = final_stocks
            self._stock_cache_time = time.time()

        return final_stocks


# ============================================================
# SINGLE CLIENT
# ============================================================

nepse = Nepse()


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):

    protocol_version = "HTTP/1.1"

    # --------------------------------------------------------
    # SERVER LOGGING
    # --------------------------------------------------------

    def log_message(
        self,
        format,
        *args,
    ):

        print(
            "%s - %s"
            % (
                self.address_string(),
                format % args,
            )
        )

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    def cors(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization",
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    def response(
        self,
        data,
        status=200,
    ):

        payload = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(payload)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.cors()

        self.end_headers()

        try:

            self.wfile.write(
                payload
            )

        except (
            BrokenPipeError,
            ConnectionResetError,
        ):
            pass

    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(
            "Content-Length",
            "0",
        )

        self.cors()

        self.end_headers()

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        print(
            "GET",
            self.path,
        )

        try:

            # ==================================================
            # HOME
            # ==================================================

            if path == "/":

                self.response(
                    {
                        "name": (
                            "Open NEPSE API"
                        ),
                        "status": "running",
                        "timezone": (
                            "Asia/Kathmandu"
                        ),
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
                    }
                )

                return

            # ==================================================
            # SEARCH ALL STOCKS
            # ==================================================

            if path == "/api/search":

                query = parse_qs(
                    parsed.query
                )

                q = query.get(
                    "q",
                    [""],
                )[0].strip()

                if not q:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "q is required"
                            ),
                        },
                        400,
                    )

                    return

                try:

                    page = int(
                        query.get(
                            "page",
                            ["0"],
                        )[0]
                    )

                    size = int(
                        query.get(
                            "size",
                            ["20"],
                        )[0]
                    )

                except ValueError:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "page and size "
                                "must be integers"
                            ),
                        },
                        400,
                    )

                    return

                if page < 0:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "page must be >= 0"
                            ),
                        },
                        400,
                    )

                    return

                if size < 1 or size > 100:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "size must be "
                                "between 1 and 100"
                            ),
                        },
                        400,
                    )

                    return

                # ------------------------------------------------
                # IMPORTANT:
                # Fetch ALL NEPSE pages (cached).
                # ------------------------------------------------

                all_stocks = (
                    nepse.get_all_stocks(
                        page_size=100
                    )
                )

                search_text = q.lower()

                # ------------------------------------------------
                # Search across ALL stocks.
                # ------------------------------------------------

                matches = []

                for stock in all_stocks:

                    if not isinstance(
                        stock,
                        dict,
                    ):
                        continue

                    symbol = str(
                        first_present(
                            stock,
                            "symbol",
                        ) or ""
                    )

                    security_name = str(
                        first_present(
                            stock,
                            "securityName",
                            "companyName",
                            "securityNameNepali",
                        ) or ""
                    )

                    if (
                        search_text
                        in symbol.lower()
                        or
                        search_text
                        in security_name.lower()
                    ):

                        matches.append(
                            stock
                        )

                # ------------------------------------------------
                # PAGINATE SEARCH RESULTS
                # ------------------------------------------------

                total = len(matches)

                start = (
                    page * size
                )

                end = (
                    start + size
                )

                paginated = matches[
                    start:end
                ]

                total_pages = (
                    (
                        total + size - 1
                    ) // size
                    if total > 0
                    else 0
                )

                self.response(
                    {
                        "success": True,
                        "query": q,
                        "page": page,
                        "size": size,
                        "total": total,
                        "totalPages": (
                            total_pages
                        ),
                        "hasNext": (
                            page + 1
                            < total_pages
                        ),
                        "hasPrevious": (
                            page > 0
                        ),
                        "count": len(
                            paginated
                        ),
                        "data": [
                            normalize_stock(
                                stock
                            )
                            for stock in paginated
                        ],
                    }
                )

                return

            # ==================================================
            # STOCKS WITH CROSS-PAGE FILTERING
            # ==================================================

            if path == "/api/stocks":

                query = parse_qs(
                    parsed.query
                )

                try:

                    page = int(
                        query.get(
                            "page",
                            ["0"],
                        )[0]
                    )

                    size = int(
                        query.get(
                            "size",
                            ["20"],
                        )[0]
                    )

                except ValueError:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "page and size "
                                "must be integers"
                            ),
                        },
                        400,
                    )

                    return

                if page < 0:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "page must be >= 0"
                            ),
                        },
                        400,
                    )

                    return

                if size < 1 or size > 100:

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "size must be "
                                "between 1 and 100"
                            ),
                        },
                        400,
                    )

                    return

                symbol = query.get(
                    "symbol",
                    [""],
                )[0].strip()

                security_name = query.get(
                    "securityName",
                    [""],
                )[0].strip()

                # ------------------------------------------------
                # NO FILTER:
                # preserve normal NEPSE pagination.
                # ------------------------------------------------

                if (
                    not symbol
                    and not security_name
                ):

                    data = (
                        nepse.get_stock_page(
                            page=page,
                            size=size,
                        )
                    )

                    if (
                        isinstance(
                            data,
                            dict,
                        )
                        and
                        "content" in data
                    ):

                        data["content"] = [
                            normalize_stock(
                                stock
                            )
                            for stock
                            in data[
                                "content"
                            ]
                        ]

                    self.response(
                        {
                            "success": True,
                            "page": page,
                            "size": size,
                            "data": data,
                        }
                    )

                    return

                # ------------------------------------------------
                # FILTER:
                # fetch ALL pages first (cached).
                # ------------------------------------------------

                all_stocks = (
                    nepse.get_all_stocks(
                        page_size=100
                    )
                )

                matches = [
                    stock
                    for stock in all_stocks
                    if matches_stock(
                        stock,
                        symbol,
                        security_name,
                    )
                ]

                total = len(
                    matches
                )

                start = (
                    page * size
                )

                end = (
                    start + size
                )

                paginated = matches[
                    start:end
                ]

                total_pages = (
                    (
                        total + size - 1
                    ) // size
                    if total > 0
                    else 0
                )

                self.response(
                    {
                        "success": True,
                        "page": page,
                        "size": size,
                        "total": total,
                        "totalPages": (
                            total_pages
                        ),
                        "hasNext": (
                            page + 1
                            < total_pages
                        ),
                        "hasPrevious": (
                            page > 0
                        ),
                        "count": len(
                            paginated
                        ),
                        "data": [
                            normalize_stock(
                                stock
                            )
                            for stock in paginated
                        ],
                    }
                )

                return

            # ==================================================
            # SINGLE STOCK
            # ==================================================

            if path.startswith(
                "/api/stocks/"
            ):

                symbol = unquote(
                    path[
                        len("/api/stocks/"):
                    ]
                ).strip().upper()

                if (
                    not symbol
                    or "/" in symbol
                ):

                    self.response(
                        {
                            "success": False,
                            "error": (
                                "Invalid stock "
                                "symbol"
                            ),
                        },
                        400,
                    )

                    return

                body, status = nepse.get(
                    f"/security/{symbol}"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "symbol": symbol,
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # MARKET
            # ==================================================

            if path == "/api/market":

                body, status = nepse.get(
                    "/market-summary"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # INDEX
            # ==================================================

            if path == "/api/index":

                body, status = nepse.get(
                    "/nepse-index"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # MARKET STATUS
            # ==================================================

            if path == "/api/status":

                body, status = nepse.get(
                    "/nepse-data/market-open"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # GAINERS
            # ==================================================

            if path == "/api/gainers":

                body, status = nepse.get(
                    "/top-ten/top-gainer?all=true"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # LOSERS
            # ==================================================

            if path == "/api/losers":

                body, status = nepse.get(
                    "/top-ten/top-loser?all=true"
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            body
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # ORIGINAL NEPSE PROXY
            # ==================================================

            if path.startswith(
                "/nepse/"
            ):

                nepse_path = path[
                    len("/nepse/") - 1:
                ]

                body, status = nepse.get(
                    nepse_path
                )

                self.response(
                    json_or_raw(body),
                    status,
                )

                return

            # ==================================================
            # NOT FOUND
            # ==================================================

            self.response(
                {
                    "success": False,
                    "error": (
                        "Endpoint not found"
                    ),
                },
                404,
            )

        except requests.RequestException as error:

            print(
                "GET REQUEST ERROR:",
                repr(error),
            )

            self.response(
                {
                    "success": False,
                    "error": (
                        "NEPSE request failed"
                    ),
                    "details": str(error),
                },
                502,
            )

        except Exception as error:

            print(
                "GET ERROR:",
                repr(error),
            )

            self.response(
                {
                    "success": False,
                    "error": str(error),
                },
                500,
            )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def do_POST(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        print(
            "POST",
            self.path,
        )

        try:

            # ------------------------------------------------
            # CONTENT LENGTH
            # ------------------------------------------------

            content_length_header = (
                self.headers.get(
                    "Content-Length"
                )
            )

            try:

                content_length = int(
                    content_length_header or 0
                )

            except ValueError:

                self.response(
                    {
                        "success": False,
                        "error": (
                            "Invalid "
                            "Content-Length"
                        ),
                    },
                    400,
                )

                return

            if content_length < 0:

                self.response(
                    {
                        "success": False,
                        "error": (
                            "Invalid request "
                            "body"
                        ),
                    },
                    400,
                )

                return

            body = None

            # ------------------------------------------------
            # READ BODY
            # ------------------------------------------------

            if content_length:

                raw = (
                    self.rfile.read(
                        content_length
                    )
                    .decode("utf-8")
                )

                if raw.strip():

                    try:

                        body = json.loads(
                            raw
                        )

                    except json.JSONDecodeError as error:

                        self.response(
                            {
                                "success": False,
                                "error": (
                                    "Invalid JSON"
                                ),
                                "details": str(
                                    error
                                ),
                            },
                            400,
                        )

                        return

            # ==================================================
            # TODAY PRICE
            # ==================================================

            if path == "/api/today-price":

                response, status = (
                    nepse.post(
                        "/nepse-data/today-price",
                        body,
                    )
                )

                data = json_or_raw(
                    response
                )

                if (
                    isinstance(
                        data,
                        dict,
                    )
                    and
                    "content" in data
                ):

                    data["content"] = [
                        normalize_stock(
                            stock
                        )
                        for stock
                        in data[
                            "content"
                        ]
                    ]

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": data,
                    },
                    status,
                )

                return

            # ==================================================
            # FLOORSHEET
            # ==================================================

            if path == "/api/floorsheet":

                response, status = (
                    nepse.post(
                        "/nepse-data/floorsheet",
                        body,
                    )
                )

                self.response(
                    {
                        "success": (
                            status == 200
                        ),
                        "data": json_or_raw(
                            response
                        ),
                    },
                    status,
                )

                return

            # ==================================================
            # NOT FOUND
            # ==================================================

            self.response(
                {
                    "success": False,
                    "error": (
                        "POST endpoint "
                        "not found"
                    ),
                },
                404,
            )

        except requests.RequestException as error:

            print(
                "POST REQUEST ERROR:",
                repr(error),
            )

            self.response(
                {
                    "success": False,
                    "error": (
                        "NEPSE request failed"
                    ),
                    "details": str(error),
                },
                502,
            )

        except Exception as error:

            print(
                "POST ERROR:",
                repr(error),
            )

            self.response(
                {
                    "success": False,
                    "error": str(error),
                },
                500,
            )


# ============================================================
# SERVER
# ============================================================

class ReusableThreadingHTTPServer(
    ThreadingHTTPServer
):

    allow_reuse_address = True
    daemon_threads = True


def main():

    server = (
        ReusableThreadingHTTPServer(
            (
                "0.0.0.0",
                PORT,
            ),
            Handler,
        )
    )

    print()
    print(
        "=========================================="
    )
    print(
        "             OPEN NEPSE API"
    )
    print(
        "=========================================="
    )
    print()

    print(
        f"Server: {API_URL}"
    )

    print()

    print(
        f"Stocks: "
        f"{API_URL}/api/stocks"
    )

    print(
        f"Search: "
        f"{API_URL}/api/search?q=NGPL"
    )

    print(
        f"Market: "
        f"{API_URL}/api/market"
    )

    print(
        f"Index:  "
        f"{API_URL}/api/index"
    )

    print(
        f"Status: "
        f"{API_URL}/api/status"
    )

    print(
        f"Today:  "
        f"{API_URL}/api/today-price"
    )

    print()

    print(
        "Press CTRL+C to stop."
    )

    print(
        "=========================================="
    )

    print()

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nStopping server..."
        )

    finally:

        server.server_close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
