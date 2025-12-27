#!/usr/bin/env python3
import json
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

"""
A fake API server that simulates the /api/pv1/device/lastmeasurement endpoint of the Mobile Alerts / data199 service. It responds to POST requests with dummy temperature data for requested device IDs.
At the moment, only temperature sensor data (t1, t2) is simulated, no humidity or other values.

The official API documentation can be found at:
https://mobile-alerts.eu/info/public_server_api_documentation.pdf
"""


class LastMeasurementHandler(BaseHTTPRequestHandler):
    # Disable default noisy logging
    def log_message(self, format, *args):
        return

    def _send_json(self, obj, status=200):
        payload = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path != "/api/pv1/device/lastmeasurement":
            self._send_json(
                {"success": False, "error": "Unknown endpoint"},
                status=404,
            )
            return

        # Read and parse POST body as x-www-form-urlencoded
        content_length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(content_length)
        body_str = body_bytes.decode("utf-8")
        form = parse_qs(body_str)

        deviceids_param = form.get("deviceids")
        if not deviceids_param:
            self._send_json(
                {"success": False, "error": "Missing 'deviceids' parameter"},
                status=400,
            )
            return

        # deviceids is a single comma-separated string
        deviceids_raw = deviceids_param[0]
        device_ids = [d.strip() for d in deviceids_raw.split(",") if d.strip()]

        devices = [get_response_for_one_device(device_id) for device_id in device_ids]

        response = {
            "devices": devices,
            "success": True,
        }

        self._send_json(response, status=200)


def get_response_for_one_device(device_id: str) -> dict:
    now = int(time.time())  # current UTC timestamp as int

    # Deterministic choice:
    # Divisible by 2 -> has t2
    # Divisible by 3 -> has h
    # Otherwise only t1
    has_t2 = False
    has_h = False
    if device_id:
        try:
            device_id_int = int(device_id, 16)
            has_t2 = device_id_int % 2 == 0
            has_h = device_id_int % 3 == 0
        except ValueError:
            has_t2 = False
            has_h = False

    measurement = {
        "idx": random.randint(1, 500_000),
        "ts": now,
        "c": now,
        "lb": False,
        "t1": round(random.uniform(10.0, 30.0), 1),
    }
    if has_t2:
        measurement["t2"] = round(random.uniform(10.0, 30.0), 1)
    if has_h:
        measurement["h"] = round(random.uniform(10.0, 90.0))

    result =  {
            "deviceid": device_id,
            "lastseen": now,
            "lowbattery": False,
            "measurement": measurement,
        }
    return result


def run(host="0.0.0.0", port=8000):
    server_address = (host, port)
    httpd = HTTPServer(server_address, LastMeasurementHandler)
    print(f"Fake API server running on http://{host}:{port}")
    print("Endpoint: POST /api/pv1/device/lastmeasurement")
    print('Example:')
    print(
        f'  curl -X POST "http://{host}:{port}/api/pv1/device/lastmeasurement" '
        '-d "deviceids=DEADBEEF1234,C0FFEE56789A"'
    )
    httpd.serve_forever()


if __name__ == "__main__":
    run()
