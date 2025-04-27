import requests
import time
import math
import sys
import websocket
import threading
import json

API_URL = "http://localhost:8000"
# No absolute paths in this script, so nothing else to change.

# Star Trek vessel names for test data
VESSEL_NAMES = [
    "USS Enterprise NCC-1701",
    "USS Voyager NCC-74656",
    "USS Defiant NX-74205",
    "USS Discovery NCC-1031",
    "USS Excelsior NCC-2000",
    "USS Reliant NCC-1864"
]

# Example MMSIs for simulation (arbitrary, but unique)
VESSEL_MMSIS = [1011701, 1074656, 1074205, 1103101, 1200000, 1186400]

# Bounding box for SF Bay Area (adjust as needed)
BAY_MIN_LAT, BAY_MAX_LAT = 37.2, 38.2
BAY_MIN_LON, BAY_MAX_LON = -123.0, -121.5

# Helper to get a real vessel from the Bay Area
def get_real_vessel():
    try:
        resp = requests.get(f"{API_URL}/spatial_query", params={
            "min_lat": BAY_MIN_LAT,
            "max_lat": BAY_MAX_LAT,
            "min_lon": BAY_MIN_LON,
            "max_lon": BAY_MAX_LON
        })
        vessels = resp.json()
        if vessels and isinstance(vessels, list) and len(vessels) > 0:
            v = vessels[0]
            mmsi = v.get("mmsi") or v.get("MMSI")
            name = v.get("ship_name") or v.get("ShipName") or v.get("name") or f"Vessel_{mmsi}"
            return mmsi, name
    except Exception as e:
        print(f"Error querying real vessels: {e}")
    return None, None

# Helper to inject static data (vessel name)
def inject_static_data(mmsi, name):
    print(f"Injecting static data for {name} ({mmsi})...")
    resp = requests.post(f"{API_URL}/inject/static_data", json={
        "mmsi": mmsi,
        "name": name,
        "imo": mmsi + 1000000,
        "callsign": name.replace(' ', '')[:7],
        "ship_type": "Cargo",
        "destination": "Risa",
        "eta": "2025-05-01T12:00:00Z",
        "draught": 8.0,
        "dim_a": 100,
        "dim_b": 20,
        "dim_c": 10,
        "dim_d": 10
    })
    print("Response:", resp.text)

# Update anomaly injectors to use names
def inject_dark_period(mmsi, name):
    print(f"Injecting dark period anomaly for {name}...")
    resp = requests.post(f"{API_URL}/inject/dark_period", json={
        "mmsi": mmsi,
        "lat": 37.8,
        "lon": -122.4,
        "gap_seconds": 7200
    })
    print("Response:", resp.text)

def inject_teleport(mmsi, name):
    print(f"Injecting impossible movement (teleportation) anomaly for {name}...")
    resp = requests.post(f"{API_URL}/inject/teleport", json={
        "mmsi": mmsi,
        "lat1": 37.8,
        "lon1": -122.4,
        "lat2": 38.8,
        "lon2": -123.4,
        "seconds_apart": 60
    })
    print("Response:", resp.text)

def inject_identity_swap(mmsi, name):
    print(f"Injecting identity swap anomaly for {name}...")
    resp = requests.post(f"{API_URL}/inject/identity_swap", json={
        "mmsi": mmsi,
        "lat": 37.8,
        "lon": -122.4
    })
    print("Response:", resp.text)

def inject_telemetry_sequence(mmsi, name, duration_minutes=5, interval_seconds=10):
    """
    Simulate a vessel broadcasting regular position reports for a given duration.
    Use a reserved value for NavigationalStatus to trigger special icon in frontend.
    """
    print(f"Injecting {duration_minutes} min of telemetry for {name} ({mmsi})...")
    num_points = int((duration_minutes * 60) / interval_seconds)
    lat, lon = 37.8, -122.4
    dlat, dlon = 0.01, 0.01
    for i in range(num_points):
        t = i * interval_seconds
        resp = requests.post(f"{API_URL}/inject/teleport", json={
            "mmsi": mmsi,
            "lat1": lat + dlat * i,
            "lon1": lon + dlon * i,
            "lat2": lat + dlat * (i+1),
            "lon2": lon + dlon * (i+1),
            "seconds_apart": interval_seconds,
            "navigational_status": 15  # Reserved/unusual value for test vessel
        })
        print(f"[t+{t}s] Teleport {i}: Response:", resp.text)
        time.sleep(0.1)

def inject_telemetry_then_teleport(mmsi, name, hold_minutes=5, interval_seconds=10):
    """
    Simulate a vessel broadcasting regular position reports at a fixed location for a duration,
    then teleport to a new location (anomaly).
    The stationary telemetry will use a reserved/unusual navigational status (15).
    """
    print(f"Injecting {hold_minutes} min of stationary telemetry for {name} ({mmsi}) before teleport...")
    num_points = int((hold_minutes * 60) / interval_seconds)
    lat, lon = 37.8, -122.4
    unusual_nav_status = 15  # Reserved/unusual value
    for i in range(num_points):
        t = i * interval_seconds
        resp = requests.post(f"{API_URL}/inject/telemetry", json={
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "navigational_status": unusual_nav_status
        })
        print(f"[t+{t}s] Stationary telemetry {i}: Response:", resp.text)
        time.sleep(0.1)
    print("Stationary period complete, injecting teleport anomaly...")
    inject_teleport(mmsi, name)

def inject_speed_anomaly(mmsi, name, normal_speed=12, anomaly_speed=50, interval_seconds=10):
    """
    Simulate a vessel with normal speed, then a sudden implausible speed jump.
    """
    print(f"Injecting speed anomaly for {name}...")
    lat, lon = 37.8, -122.4
    # Normal speed
    resp = requests.post(f"{API_URL}/inject/telemetry", json={
        "mmsi": mmsi,
        "lat": lat,
        "lon": lon,
        "navigational_status": 0,
        "sog": normal_speed
    })
    print("Normal speed response:", resp.text)
    time.sleep(0.1)
    # Anomalous speed
    resp = requests.post(f"{API_URL}/inject/telemetry", json={
        "mmsi": mmsi,
        "lat": lat + 0.01,
        "lon": lon + 0.01,
        "navigational_status": 0,
        "sog": anomaly_speed
    })
    print("Anomalous speed response:", resp.text)
    time.sleep(0.1)


def inject_course_change_anomaly(mmsi, name, normal_heading=90, anomaly_heading=270, interval_seconds=10):
    """
    Simulate a vessel with a normal heading, then a sudden large course change.
    """
    print(f"Injecting course change anomaly for {name}...")
    lat, lon = 37.8, -122.4
    # Normal heading
    resp = requests.post(f"{API_URL}/inject/telemetry", json={
        "mmsi": mmsi,
        "lat": lat,
        "lon": lon,
        "navigational_status": 0,
        "heading": normal_heading
    })
    print("Normal heading response:", resp.text)
    time.sleep(0.1)
    # Anomalous heading
    resp = requests.post(f"{API_URL}/inject/telemetry", json={
        "mmsi": mmsi,
        "lat": lat + 0.01,
        "lon": lon + 0.01,
        "navigational_status": 0,
        "heading": anomaly_heading
    })
    print("Anomalous heading response:", resp.text)
    time.sleep(0.1)

def inject_circle_spoofing(mmsi, name, center_lat=37.8, center_lon=-122.4, radius_nm=0.5, duration_minutes=30, interval_seconds=30):
    """
    Simulate a vessel moving in a near-perfect circle (circle spoofing).
    duration_minutes: total wall-clock duration of spoofing
    interval_seconds: interval between each telemetry transmission
    """
    print(f"Injecting circle spoofing for {name} ({mmsi})...")
    radius_deg = radius_nm / 60.0
    num_points = int((duration_minutes * 60) / interval_seconds)
    for i in range(num_points):
        theta = 2 * math.pi * i / num_points
        lat = center_lat + radius_deg * math.cos(theta)
        lon = center_lon + (radius_deg * math.sin(theta)) / math.cos(math.radians(center_lat))
        heading = (math.degrees(theta) + 90) % 360  # Tangent to circle
        sog = 6.0  # knots, constant
        resp = requests.post(f"{API_URL}/inject/telemetry", json={
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "navigational_status": 0,
            "heading": heading,
            "sog": sog
        })
        print(f"[circle {i}] Response:", resp.text)
        time.sleep(interval_seconds)

def get_fallback_vessel():
    """
    Use a known test MMSI to retrieve vessel name and MMSI from /history/{mmsi} endpoint.
    Returns (mmsi, name) if found, else (None, None).
    """
    test_mmsi = 1011701  # USS Enterprise NCC-1701
    try:
        resp = requests.get(f"{API_URL}/history/{test_mmsi}")
        history = resp.json()
        if history and isinstance(history, list) and len(history) > 0:
            entry = history[0]
            mmsi = entry.get("meta", {}).get("MMSI") or entry.get("mmsi")
            name = entry.get("meta", {}).get("ShipName") or entry.get("ship_name") or f"Vessel_{mmsi}"
            return mmsi, name
    except Exception as e:
        print(f"Error querying fallback vessel: {e}")
    return None, None

def get_any_vessel():
    """
    Query /spatial_query with a global bounding box to get any vessel in the backend.
    Returns (mmsi, name) if found, else (None, None).
    """
    try:
        resp = requests.get(f"{API_URL}/spatial_query", params={
            "min_lat": -90,
            "max_lat": 90,
            "min_lon": -180,
            "max_lon": 180
        })
        vessels = resp.json()
        if vessels and isinstance(vessels, list) and len(vessels) > 0:
            v = vessels[0]
            mmsi = v.get("mmsi") or v.get("MMSI")
            name = v.get("ship_name") or v.get("ShipName") or v.get("name") or f"Vessel_{mmsi}"
            return mmsi, name
    except Exception as e:
        print(f"Error querying any vessel: {e}")
    return None, None

def get_first_vessel_from_ws():
    """
    Connect to the /ws websocket endpoint and return the first vessel MMSI and name seen in the feed.
    Returns (mmsi, name) if found, else (None, None).
    """
    ws_url = "ws://localhost:8000/ws"
    vessel_info = {}
    def on_message(ws, message):
        try:
            msg = json.loads(message)
            hp = msg.get("history_point")
            if not hp:
                return
            meta = hp.get("meta", {})
            mmsi = meta.get("MMSI") or hp.get("mmsi")
            name = meta.get("ShipName") or hp.get("ship_name") or hp.get("ShipName")
            if mmsi and name:
                vessel_info['mmsi'] = mmsi
                vessel_info['name'] = name
                ws.close()
        except Exception as e:
            print(f"WebSocket parse error: {e}")
            ws.close()
    def on_error(ws, error):
        print(f"WebSocket error: {error}")
    def on_close(ws, close_status_code, close_msg):
        pass
    ws = websocket.WebSocketApp(ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    # Wait up to 10 seconds for a vessel
    for _ in range(100):
        if 'mmsi' in vessel_info and 'name' in vessel_info:
            return vessel_info['mmsi'], vessel_info['name']
        time.sleep(0.1)
    print("No vessel found via WebSocket feed.")
    return None, None

if __name__ == "__main__":
    # Try to get vessel from WebSocket feed
    print("Attempting to get vessel from /ws WebSocket feed...")
    mmsi, name = get_first_vessel_from_ws()
    if not mmsi or not name:
        print("No vessel found via WebSocket. Aborting simulation.")
        sys.exit(1)
    print(f"Simulating circle spoofing for vessel: {name} ({mmsi})")
    # Do NOT inject static data (since vessel already exists)
    time.sleep(0.2)
    # Use realistic wall-clock duration and interval
    inject_circle_spoofing(mmsi, name, center_lat=37.8, center_lon=-122.4, radius_nm=0.5, duration_minutes=30, interval_seconds=30)
    print("Circle spoofing simulation complete.")
