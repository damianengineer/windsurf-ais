import requests
import time

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

if __name__ == "__main__":
    # Focus on just the first test vessel for this telemetry test
    mmsi, name = VESSEL_MMSIS[0], VESSEL_NAMES[0]
    inject_static_data(mmsi, name)
    time.sleep(0.2)
    inject_telemetry_then_teleport(mmsi, name, hold_minutes=5, interval_seconds=10)
    inject_speed_anomaly(mmsi, name)
    inject_course_change_anomaly(mmsi, name)
    inject_dark_period(mmsi, name)
    inject_identity_swap(mmsi, name)
    print("All anomaly simulations complete.")
