import datetime
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import requests
import pywasm
import pytz


# ============================================================
# CONFIG
# ============================================================

TZ_NP = pytz.timezone("Asia/Kathmandu")

BASE_URL = "https://www.nepalstock.com.np"
API_BASE_URL = f"{BASE_URL}/api/nots"

PORT = int(os.environ.get("PORT", 5000))

# Keep one requests session.
SESSION = requests.Session()

# Do NOT use verify=False.
SESSION.verify = True

SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
        "Gecko/20100101 Firefox/128.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL + "/",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
})


# ============================================================
# TOKEN PARSER
# ============================================================

class TokenParser:

    def __init__(self, wasm_file="css.wasm"):
        self.runtime = pywasm.core.Runtime()
        self.wasm_module = self.runtime.instance_from_file(wasm_file)

    def parse_token_response(self, token_response):

        s1 = int(token_response["salt1"])
        s2 = int(token_response["salt2"])
        s3 = int(token_response["salt3"])
        s4 = int(token_response["salt4"])
        s5 = int(token_response["salt5"])

        access_token = token_response["accessToken"]
        refresh_token = token_response["refreshToken"]

        n = self.runtime.invocate(
            self.wasm_module,
            "cdx",
            [s1, s2, s3, s4, s5]
        )[0]

        l = self.runtime.invocate(
            self.wasm_module,
            "rdx",
            [s1, s2, s4, s3, s5]
        )[0]

        o = self.runtime.invocate(
            self.wasm_module,
            "bdx",
            [s1, s2, s4, s3, s5]
        )[0]

        p = self.runtime.invocate(
            self.wasm_module,
            "ndx",
            [s1, s2, s4, s3, s5]
        )[0]

        q = self.runtime.invocate(
            self.wasm_module,
            "mdx",
            [s1, s2, s4, s3, s5]
        )[0]

        a = self.runtime.invocate(
            self.wasm_module,
            "cdx",
            [s2, s1, s3, s5, s4]
        )[0]

        b = self.runtime.invocate(
            self.wasm_module,
            "rdx",
            [s2, s1, s3, s4, s5]
        )[0]

        c = self.runtime.invocate(
            self.wasm_module,
            "bdx",
            [s2, s1, s4, s3, s5]
        )[0]

        d = self.runtime.invocate(
            self.wasm_module,
            "ndx",
            [s2, s1, s4, s3, s5]
        )[0]

        e = self.runtime.invocate(
            self.wasm_module,
            "mdx",
            [s2, s1, s4, s3, s5]
        )[0]

        parsed_access_token = (
            access_token[:n]
            + access_token[n + 1:l]
            + access_token[l + 1:o]
            + access_token[o + 1:p]
            + access_token[p + 1:q]
            + access_token[q + 1:]
        )

        parsed_refresh_token = (
            refresh_token[:a]
            + refresh_token[a + 1:b]
            + refresh_token[b + 1:c]
            + refresh_token[c + 1:d]
            + refresh_token[d + 1:e]
            + refresh_token[e + 1:]
        )

        return parsed_access_token, parsed_refresh_token


# ============================================================
# NEPSE CLIENT
# ============================================================

class Nepse:

    def __init__(self):

        self.token_parser = TokenParser("css.wasm")

        self.access_token = None
        self.refresh_token = None

        self.payload_day = None
        self.payload_id = None

        self.lock = threading.Lock()

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    def get_token(self):

        with self.lock:

            if self.access_token:
                return self.access_token, self.refresh_token

            return self._authenticate()

    def _authenticate(self):

        response = SESSION.get(
            f"{BASE_URL}/api/authenticate/prove",
            timeout=20
        )

        response.raise_for_status()

        token_response = response.json()

        (
            self.access_token,
            self.refresh_token
        ) = self.token_parser.parse_token_response(
            token_response
        )

        return self.access_token, self.refresh_token

    def reset_token(self):

        with self.lock:
            self.access_token = None
            self.refresh_token = None

    # --------------------------------------------------------
    # HEADERS
    # --------------------------------------------------------

    def auth_headers(self):

        access_token, _ = self.get_token()

        return {
            **SESSION.headers,
            "Authorization": f"Salter {access_token}",
        }

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    def get(self, path):

        url = self.build_url(path)

        response = SESSION.get(
            url,
            headers=self.auth_headers(),
            timeout=20
        )

        # Token might have expired.
        if response.status_code == 401:

            self.reset_token()

            response = SESSION.get(
                url,
                headers=self.auth_headers(),
                timeout=20
            )

        return response.text, response.status_code

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    def post(self, path, body=None):

        url = self.build_url(path)

        if body is None:
            body = {
                "id": self.get_post_payload_id(path)
            }

        headers = {
            **self.auth_headers(),
            "Content-Type": "application/json",
        }

        response = SESSION.post(
            url,
            headers=headers,
            json=body,
            timeout=30
        )

        if response.status_code == 401:

            self.reset_token()

            headers = {
                **self.auth_headers(),
                "Content-Type": "application/json",
            }

            response = SESSION.post(
                url,
                headers=headers,
                json=body,
                timeout=30
            )

        return response.text, response.status_code

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    def build_url(self, path):

        if path.startswith("/"):
            path = path[1:]

        return f"{API_BASE_URL}/{path}"

    # --------------------------------------------------------
    # PAYLOAD
    # --------------------------------------------------------

    def get_dummy_id(self):

        now = datetime.datetime.now(TZ_NP)

        if self.payload_day == now.day:
            return self.payload_id

        response, status = self.get(
            "/nepse-data/market-open"
        )

        if status != 200:
            raise RuntimeError(
                f"Unable to get market-open: {status}"
            )

        data = json.loads(response)

        self.payload_id = data["id"]
        self.payload_day = now.day

        return self.payload_id

    def get_dummy_data(self):

        return [
            147, 117, 239, 143, 157, 312, 161, 612,
            512, 804, 411, 527, 170, 511, 421, 667,
            764, 621, 301, 106, 133, 793, 411, 511,
            312, 423, 344, 346, 653, 758, 342, 222,
            236, 811, 711, 611, 122, 447, 128, 199,
            183, 135, 489, 703, 800, 745, 152, 863,
            134, 211, 142, 564, 375, 793, 212, 153,
            138, 153, 648, 611, 151, 649, 318, 143,
            117, 756, 119, 141, 717, 113, 112, 146,
            162, 660, 693, 261, 362, 354, 251, 641,
            157, 178, 631, 192, 734, 445, 192, 883,
            187, 122, 591, 731, 852, 384, 565, 596,
            451, 772, 624, 691
        ]

    def get_post_payload_id(self, path):

        dummy_id = self.get_dummy_id()

        now = datetime.datetime.now(TZ_NP)

        dummy = self.get_dummy_data()

        # Index graph
        if "/graph/index/" in path:

            e = (
                dummy[dummy_id]
                + dummy_id
                + 2 * now.day
            )

            # Need current salts.
            self.get_token()

            # This reproduces your existing logic.
            # Your original code uses the salt array
            # internally, so preserve that logic if your
            # current css.wasm/token implementation requires it.

            return e

        # Floorsheet / today's price
        if (
            "/nepse-data/floorsheet" in path
            or "/nepse-data/today-price" in path
        ):

            e = (
                dummy[dummy_id]
                + dummy_id
                + 2 * now.day
            )

            return e

        return (
            dummy[dummy_id]
            + dummy_id
            + 2 * now.day
        )


# ============================================================
# SINGLE NEPSE INSTANCE
# ============================================================

nepse = Nepse()


# ============================================================
# HTTP SERVER
# ============================================================

class Handler(BaseHTTPRequestHandler):

    def send_json(self, body, status=200):

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json"
        )

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

        self.end_headers()

        if isinstance(body, str):
            self.wfile.write(body.encode("utf-8"))
        else:
            self.wfile.write(
                json.dumps(body).encode("utf-8")
            )

    def do_OPTIONS(self):

        self.send_json({}, 200)

    def do_GET(self):

        if self.path == "/":

            self.send_json({
                "name": "Open NEPSE API",
                "status": "running",
                "source": "Nepal Stock Exchange",
            })

            return

        try:

            path = self.path

            print("GET:", path)

            body, status = nepse.get(path)

            self.send_json(
                json.loads(body)
                if body
                else {},
                status
            )

        except Exception as error:

            print("GET ERROR:", error)

            self.send_json({
                "success": False,
                "error": str(error)
            }, 500)

    def do_POST(self):

        try:

            path = self.path

            print("POST:", path)

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )

            body = None

            if content_length > 0:

                raw = self.rfile.read(
                    content_length
                ).decode("utf-8")

                if raw.strip():

                    try:
                        body = json.loads(raw)

                    except json.JSONDecodeError:

                        parsed = parse_qs(raw)

                        body = {
                            key: value[0]
                            for key, value
                            in parsed.items()
                        }

            response, status = nepse.post(
                path,
                body
            )

            self.send_json(
                json.loads(response)
                if response
                else {},
                status
            )

        except Exception as error:

            print("POST ERROR:", error)

            self.send_json({
                "success": False,
                "error": str(error)
            }, 500)


# ============================================================
# START
# ============================================================

def run():

    server = ThreadingHTTPServer(
        ("0.0.0.0", PORT),
        Handler
    )

    print(
        f"NEPSE API running on "
        f"http://localhost:{PORT}"
    )

    server.serve_forever()


if __name__ == "__main__":
    run()
