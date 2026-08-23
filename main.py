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
#         f"Server: http://localhost:{PORT}"
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




import datetime
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import requests
import pywasm
import pytz


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://www.nepalstock.com.np"
API_URL = "https://nepalstock-api-qycd.onrender.com"
NEPSE_API = f"{BASE_URL}/api/nots"

PORT = int(os.getenv("PORT", "5000"))

TZ_NP = pytz.timezone("Asia/Kathmandu")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")
WASM_FILE = os.path.join(BASE_DIR, "css.wasm")


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
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
})


# ============================================================
# TOKEN PARSER
# ============================================================

class TokenParser:

    def __init__(self):

        if not os.path.exists(WASM_FILE):
            raise FileNotFoundError(
                f"Missing WASM file: {WASM_FILE}"
            )

        self.runtime = pywasm.core.Runtime()

        self.wasm_module = (
            self.runtime.instance_from_file(WASM_FILE)
        )

    def call(self, function_name, values):

        return self.runtime.invocate(
            self.wasm_module,
            function_name,
            values
        )[0]

    def parse_token_response(self, token):

        s1 = int(token["salt1"])
        s2 = int(token["salt2"])
        s3 = int(token["salt3"])
        s4 = int(token["salt4"])
        s5 = int(token["salt5"])

        access_token = token["accessToken"]
        refresh_token = token["refreshToken"]

        # ====================================================
        # ACCESS TOKEN
        # ====================================================

        n = self.call(
            "cdx",
            [s1, s2, s3, s4, s5]
        )

        l = self.call(
            "rdx",
            [s1, s2, s4, s3, s5]
        )

        o = self.call(
            "bdx",
            [s1, s2, s4, s3, s5]
        )

        p = self.call(
            "ndx",
            [s1, s2, s4, s3, s5]
        )

        q = self.call(
            "mdx",
            [s1, s2, s4, s3, s5]
        )

        indexes = [n, l, o, p, q]

        parsed_access_token = self.remove_positions(
            access_token,
            indexes
        )

        # ====================================================
        # REFRESH TOKEN
        # ====================================================

        a = self.call(
            "cdx",
            [s2, s1, s3, s5, s4]
        )

        b = self.call(
            "rdx",
            [s2, s1, s3, s4, s5]
        )

        c = self.call(
            "bdx",
            [s2, s1, s4, s3, s5]
        )

        d = self.call(
            "ndx",
            [s2, s1, s4, s3, s5]
        )

        e = self.call(
            "mdx",
            [s2, s1, s4, s3, s5]
        )

        indexes = [a, b, c, d, e]

        parsed_refresh_token = self.remove_positions(
            refresh_token,
            indexes
        )

        return (
            parsed_access_token,
            parsed_refresh_token
        )

    @staticmethod
    def remove_positions(value, indexes):

        # Remove characters from right to left so indexes
        # remain valid.
        result = value

        for index in sorted(indexes, reverse=True):

            if 0 <= index < len(result):
                result = (
                    result[:index]
                    + result[index + 1:]
                )

        return result


# ============================================================
# NEPSE CLIENT
# ============================================================

class Nepse:

    def __init__(self):

        self.token_parser = TokenParser()

        self.access_token = None
        self.refresh_token = None

        self.salts = []

        self.payload_day = None
        self.payload_id = None

        self.lock = threading.RLock()

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def authenticate(self):

        print("Authenticating with NEPSE...")

        response = session.get(
            f"{BASE_URL}/api/authenticate/prove",
            timeout=30
        )

        response.raise_for_status()

        token_response = response.json()

        self.salts = []

        for i in range(1, 6):

            key = f"salt{i}"

            value = int(
                token_response[key]
            )

            token_response[key] = value

            self.salts.append(value)

        (
            self.access_token,
            self.refresh_token
        ) = self.token_parser.parse_token_response(
            token_response
        )

        print("NEPSE authentication successful.")

    # ========================================================
    # TOKEN
    # ========================================================

    def get_token(self):

        with self.lock:

            if not self.access_token:
                self.authenticate()

            return (
                self.access_token,
                self.refresh_token
            )

    def reset_token(self):

        with self.lock:

            self.access_token = None
            self.refresh_token = None

            self.payload_day = None
            self.payload_id = None

    # ========================================================
    # HEADERS
    # ========================================================

    def get_headers(self):

        access_token, _ = self.get_token()

        return {
            **session.headers,
            "Authorization": f"Salter {access_token}",
        }

    # ========================================================
    # URL
    # ========================================================

    def build_url(self, path):

        path = path.lstrip("/")

        return f"{NEPSE_API}/{path}"

    # ========================================================
    # GET
    # ========================================================

    def get(self, path, params=None):

        url = self.build_url(path)

        headers = self.get_headers()

        response = session.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code == 401:

            print(
                "Token expired. Re-authenticating..."
            )

            self.reset_token()

            headers = self.get_headers()

            response = session.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )

        return (
            response.text,
            response.status_code
        )

    # ========================================================
    # CURRENT MARKET ID
    #
    # This is NOT stock data.
    #
    # NEPSE uses it as part of its protected POST
    # request mechanism.
    # ========================================================

    def get_payload_id(self):

        now = datetime.datetime.now(TZ_NP)

        current_day = now.strftime("%Y-%m-%d")

        with self.lock:

            if (
                self.payload_day == current_day
                and self.payload_id is not None
            ):
                return self.payload_id

            response, status = self.get(
                "/nepse-data/market-open"
            )

            if status != 200:

                raise RuntimeError(
                    "Could not get market-open. "
                    f"HTTP {status}: {response[:500]}"
                )

            data = json.loads(response)

            if not isinstance(data, dict):

                raise RuntimeError(
                    "Unexpected market-open response."
                )

            if "id" not in data:

                raise RuntimeError(
                    f"market-open response has no id: {data}"
                )

            self.payload_id = int(data["id"])

            self.payload_day = current_day

            return self.payload_id

    # ========================================================
    # PAYLOAD CALCULATION
    #
    # IMPORTANT:
    #
    # This is request-signing data, NOT dummy market data.
    #
    # Do not replace it with stock prices.
    # ========================================================

    def get_payload_seed(self):

        payload_id = self.get_payload_id()

        now = datetime.datetime.now(TZ_NP)

        # NEPSE's current protected POST mechanism uses
        # a calculated value based on the market-open ID.
        #
        # We derive the request value from the current ID
        # rather than hard-coding stock-price data.

        return (
            payload_id
            + 2 * now.day
        )

    # ========================================================
    # POST
    # ========================================================

    def post(self, path, body=None):

        url = self.build_url(path)

        # ----------------------------------------------------
        # If caller provides body, send it directly.
        # ----------------------------------------------------

        if body is None:

            body = {
                "id": self.get_payload_seed()
            }

        headers = {
            **self.get_headers(),
            "Content-Type": "application/json",
        }

        response = session.post(
            url,
            headers=headers,
            json=body,
            timeout=30
        )

        # ----------------------------------------------------
        # Retry authentication once
        # ----------------------------------------------------

        if response.status_code == 401:

            print(
                "POST token expired. "
                "Re-authenticating..."
            )

            self.reset_token()

            headers = {
                **self.get_headers(),
                "Content-Type": "application/json",
            }

            response = session.post(
                url,
                headers=headers,
                json=body,
                timeout=30
            )

        return (
            response.text,
            response.status_code
        )


# ============================================================
# GLOBAL NEPSE CLIENT
# ============================================================

nepse = Nepse()


# ============================================================
# JSON
# ============================================================

def parse_json(text):

    try:
        return json.loads(text)

    except Exception:

        return {
            "raw": text
        }


# ============================================================
# NUMBER HELPER
# ============================================================

def first_value(data, *keys):

    for key in keys:

        value = data.get(key)

        if value is not None:
            return value

    return None


# ============================================================
# NORMALIZE STOCK
# ============================================================

def normalize_stock(stock):

    if not isinstance(stock, dict):
        return stock

    ltp = first_value(
        stock,
        "lastTradedPrice",
        "lastUpdatedPrice",
        "ltp",
        "closePrice"
    )

    previous_close = first_value(
        stock,
        "previousDayClosePrice",
        "previousClose",
        "previousClosingPrice"
    )

    change = first_value(
        stock,
        "change",
        "difference"
    )

    percentage_change = first_value(
        stock,
        "percentageChange",
        "percentChange"
    )

    # Calculate change if NEPSE didn't return it.

    if (
        change is None
        and ltp is not None
        and previous_close is not None
    ):

        try:

            change = float(ltp) - float(previous_close)

        except Exception:
            pass

    # Calculate percentage if missing.

    if (
        percentage_change is None
        and change is not None
        and previous_close not in (None, 0)
    ):

        try:

            percentage_change = (
                float(change)
                / float(previous_close)
                * 100
            )

        except Exception:
            pass

    return {
        "securityId": stock.get("securityId"),

        "symbol": stock.get("symbol"),

        "securityName": first_value(
            stock,
            "securityName",
            "companyName",
            "securityNameNepali"
        ),

        "businessDate": stock.get(
            "businessDate"
        ),

        "ltp": ltp,

        "open": first_value(
            stock,
            "openPrice",
            "open"
        ),

        "high": first_value(
            stock,
            "highPrice",
            "high"
        ),

        "low": first_value(
            stock,
            "lowPrice",
            "low"
        ),

        "close": first_value(
            stock,
            "closePrice",
            "closingPrice"
        ),

        "previousClose": previous_close,

        "change": change,

        "percentageChange": percentage_change,

        "volume": first_value(
            stock,
            "totalTradedQuantity",
            "totalTradeQuantity",
            "volume"
        ),

        "turnover": first_value(
            stock,
            "totalTradedValue",
            "totalTradeValue",
            "turnover"
        ),

        "trades": first_value(
            stock,
            "totalTrades",
            "numberOfTrades"
        ),

        "averageTradedPrice": stock.get(
            "averageTradedPrice"
        ),

        "fiftyTwoWeekHigh": stock.get(
            "fiftyTwoWeekHigh"
        ),

        "fiftyTwoWeekLow": stock.get(
            "fiftyTwoWeekLow"
        ),

        "marketCapitalization": stock.get(
            "marketCapitalization"
        ),

        "lastUpdatedTime": stock.get(
            "lastUpdatedTime"
        ),

        "timestamp": (
            datetime.datetime
            .now(TZ_NP)
            .isoformat()
        )
    }


# ============================================================
# FETCH ONE PAGE OF STOCKS
# ============================================================

def fetch_stock_page(page=0, size=20):

    # NEPSE expects page/size query parameters for the
    # paginated today-price response.

    path = (
        "/nepse-data/today-price"
        f"?page={page}"
        f"&size={size}"
    )

    body, status = nepse.post(path)

    data = parse_json(body)

    if status != 200:

        raise RuntimeError(
            f"NEPSE returned HTTP {status}: {data}"
        )

    return data


# ============================================================
# FETCH ALL STOCKS
# ============================================================

def fetch_all_stocks():

    first_page = fetch_stock_page(
        page=0,
        size=100
    )

    if not isinstance(first_page, dict):

        return {
            "content": [],
            "totalElements": 0,
            "totalPages": 0
        }

    content = first_page.get(
        "content",
        []
    )

    total_pages = int(
        first_page.get(
            "totalPages",
            1
        )
    )

    page_size = int(
        first_page.get(
            "size",
            100
        )
    )

    # If NEPSE ignored size and returned only 20,
    # request remaining pages using the returned size.

    if page_size <= 0:
        page_size = 20

    all_stocks = list(content)

    # --------------------------------------------------------
    # Get remaining pages
    # --------------------------------------------------------

    for page in range(1, total_pages):

        print(
            f"Fetching stock page "
            f"{page + 1}/{total_pages}..."
        )

        page_data = fetch_stock_page(
            page=page,
            size=page_size
        )

        if not isinstance(page_data, dict):
            continue

        page_content = page_data.get(
            "content",
            []
        )

        if isinstance(page_content, list):

            all_stocks.extend(
                page_content
            )

    return {
        "content": all_stocks,
        "totalElements": len(all_stocks),
        "totalPages": total_pages
    }


# ============================================================
# FIND STOCK
# ============================================================

def find_stock(symbol):

    symbol = symbol.upper()

    data = fetch_all_stocks()

    stocks = data.get(
        "content",
        []
    )

    for stock in stocks:

        if (
            str(stock.get("symbol", ""))
            .upper()
            == symbol
        ):

            return normalize_stock(stock)

    return None


# ============================================================
# HTTP HANDLER
# ============================================================

class Handler(BaseHTTPRequestHandler):

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    def log_message(self, format, *args):

        print(
            "%s - %s"
            % (
                self.address_string(),
                format % args
            )
        )

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    def cors(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization"
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    def response(
        self,
        data,
        status=200,
        content_type="application/json; charset=utf-8"
    ):

        self.send_response(status)

        self.send_header(
            "Content-Type",
            content_type
        )

        self.cors()

        self.end_headers()

        if isinstance(data, bytes):

            output = data

        elif isinstance(data, str):

            output = data.encode(
                "utf-8"
            )

        else:

            output = json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ).encode("utf-8")

        self.wfile.write(output)

    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

    def do_OPTIONS(self):

        self.response({}, 200)

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def do_GET(self):

        parsed = urlparse(
            self.path
        )

        path = parsed.path

        query = parse_qs(
            parsed.query
        )

        print(
            "GET",
            self.path
        )

        try:

            # =================================================
            # BROWSER FRONTEND
            # =================================================

            if path == "/":

                if os.path.exists(INDEX_FILE):

                    with open(
                        INDEX_FILE,
                        "rb"
                    ) as file:

                        html = file.read()

                    self.response(
                        html,
                        200,
                        "text/html; charset=utf-8"
                    )

                else:

                    self.response(
                        {
                            "name": "Open NEPSE API",
                            "status": "running",
                            "message": (
                                "index.html not found"
                            )
                        }
                    )

                return

            # =================================================
            # API INFO
            # =================================================

            if path == "/api":

                self.response({
                    "name": "Open NEPSE API",
                    "status": "running",
                    "timezone": "Asia/Kathmandu",
                    "endpoints": {
                        "stocks": "/api/stocks",
                        "singleStock": (
                            "/api/stocks/ADBL"
                        ),
                        "market": "/api/market",
                        "index": "/api/index",
                        "status": "/api/status",
                        "gainers": "/api/gainers",
                        "losers": "/api/losers"
                    }
                })

                return

            # =================================================
            # ALL STOCKS
            # =================================================

            if path == "/api/stocks":

                all_mode = (
                    query.get(
                        "all",
                        ["false"]
                    )[0]
                    .lower()
                    == "true"
                )

                page = int(
                    query.get(
                        "page",
                        ["0"]
                    )[0]
                )

                size = int(
                    query.get(
                        "size",
                        ["20"]
                    )[0]
                )

                # Safety limits

                if size < 1:
                    size = 20

                if size > 500:
                    size = 500

                # ------------------------------------------------
                # ALL
                # ------------------------------------------------

                if all_mode:

                    print(
                        "Fetching ALL NEPSE stocks..."
                    )

                    result = fetch_all_stocks()

                    stocks = [
                        normalize_stock(stock)
                        for stock in result[
                            "content"
                        ]
                    ]

                    self.response({
                        "success": True,
                        "count": len(stocks),
                        "totalElements": len(stocks),
                        "data": stocks
                    })

                    return

                # ------------------------------------------------
                # PAGINATED
                # ------------------------------------------------

                data = fetch_stock_page(
                    page=page,
                    size=size
                )

                if isinstance(data, dict):

                    content = data.get(
                        "content",
                        []
                    )

                    data["content"] = [
                        normalize_stock(stock)
                        for stock in content
                    ]

                self.response(
                    {
                        "success": True,
                        "data": data
                    }
                )

                return

            # =================================================
            # SINGLE STOCK
            # =================================================

            if path.startswith(
                "/api/stocks/"
            ):

                symbol = (
                    path
                    .split("/")
                    [-1]
                    .upper()
                )

                stock = find_stock(
                    symbol
                )

                if stock is None:

                    self.response(
                        {
                            "success": False,
                            "symbol": symbol,
                            "error": (
                                "Stock not found"
                            )
                        },
                        404
                    )

                    return

                self.response({
                    "success": True,
                    "symbol": symbol,
                    "data": stock
                })

                return

            # =================================================
            # MARKET SUMMARY
            # =================================================

            if path == "/api/market":

                body, status = nepse.get(
                    "/market-summary"
                )

                self.response(
                    {
                        "success": status == 200,
                        "data": parse_json(body)
                    },
                    status
                )

                return

            # =================================================
            # NEPSE INDEX
            # =================================================

            if path == "/api/index":

                body, status = nepse.get(
                    "/nepse-index"
                )

                self.response(
                    {
                        "success": status == 200,
                        "data": parse_json(body)
                    },
                    status
                )

                return

            # =================================================
            # MARKET STATUS
            # =================================================

            if path == "/api/status":

                body, status = nepse.get(
                    "/nepse-data/market-open"
                )

                self.response(
                    {
                        "success": status == 200,
                        "data": parse_json(body)
                    },
                    status
                )

                return

            # =================================================
            # GAINERS
            # =================================================

            if path == "/api/gainers":

                body, status = nepse.get(
                    "/top-ten/top-gainer?all=true"
                )

                self.response(
                    {
                        "success": status == 200,
                        "data": parse_json(body)
                    },
                    status
                )

                return

            # =================================================
            # LOSERS
            # =================================================

            if path == "/api/losers":

                body, status = nepse.get(
                    "/top-ten/top-loser?all=true"
                )

                self.response(
                    {
                        "success": status == 200,
                        "data": parse_json(body)
                    },
                    status
                )

                return

            # =================================================
            # ORIGINAL NEPSE PROXY
            # =================================================

            if path.startswith("/nepse/"):

                nepse_path = path.replace(
                    "/nepse/",
                    "/",
                    1
                )

                body, status = nepse.get(
                    nepse_path
                )

                self.response(
                    parse_json(body),
                    status
                )

                return

            # =================================================
            # 404
            # =================================================

            self.response(
                {
                    "success": False,
                    "error": "Endpoint not found"
                },
                404
            )

        except Exception as error:

            print(
                "GET ERROR:",
                repr(error)
            )

            self.response(
                {
                    "success": False,
                    "error": str(error)
                },
                500
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
            self.path
        )

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            body = None

            if content_length > 0:

                raw = self.rfile.read(
                    content_length
                ).decode(
                    "utf-8"
                )

                if raw.strip():

                    body = json.loads(
                        raw
                    )

            # =================================================
            # TODAY PRICE
            # =================================================

            if path == "/api/today-price":

                response, status = nepse.post(
                    "/nepse-data/today-price",
                    body
                )

                data = parse_json(
                    response
                )

                if isinstance(data, dict):

                    content = data.get(
                        "content"
                    )

                    if isinstance(
                        content,
                        list
                    ):

                        data["content"] = [
                            normalize_stock(
                                stock
                            )
                            for stock in content
                        ]

                elif isinstance(
                    data,
                    list
                ):

                    data = [
                        normalize_stock(
                            stock
                        )
                        for stock in data
                    ]

                self.response(
                    {
                        "success": status == 200,
                        "data": data
                    },
                    status
                )

                return

            # =================================================
            # FLOORSHEET
            # =================================================

            if path == "/api/floorsheet":

                response, status = nepse.post(
                    "/nepse-data/floorsheet",
                    body
                )

                self.response(
                    parse_json(response),
                    status
                )

                return

            # =================================================
            # 404
            # =================================================

            self.response(
                {
                    "success": False,
                    "error": (
                        "POST endpoint not found"
                    )
                },
                404
            )

        except Exception as error:

            print(
                "POST ERROR:",
                repr(error)
            )

            self.response(
                {
                    "success": False,
                    "error": str(error)
                },
                500
            )


# ============================================================
# SERVER
# ============================================================

def main():

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
        "NEPSE:",
        BASE_URL
    )

    print(
        "Server:",
        f"{API_URL}"
    )

    print()

    print(
        "Browser:",
        f"{API_URL}/"
    )

    print(
        "All stocks:",
        f"{API_URL}/api/stocks?all=true"
    )

    print(
        "Stocks page:",
        f"{API_URL}/api/stocks?page=0&size=20"
    )

    print(
        "ADBL:",
        f"{API_URL}/api/stocks/ADBL"
    )

    print(
        "Market:",
        f"{API_URL}/api/market"
    )

    print(
        "Index:",
        f"{API_URL}/api/index"
    )

    print(
        "Status:",
        f"{API_URL}/api/status"
    )

    print(
        "Gainers:",
        f"{API_URL}/api/gainers"
    )

    print(
        "Losers:",
        f"{API_URL}/api/losers"
    )

    print()
    print(
        "Press CTRL+C to stop."
    )
    print(
        "=========================================="
    )
    print()

    server = ThreadingHTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        Handler
    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nStopping server..."
        )

        server.shutdown()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
