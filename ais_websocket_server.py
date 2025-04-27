from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import os
import json
from dotenv import load_dotenv
import websockets
import sys
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from datetime import datetime
from fastapi import Query
import math
from fastapi import Body
from datetime import timedelta
from shiptype_lookup import get_shiptype_meaning
import numpy as np
from circle_fit import fit_circle

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
API_KEY = os.getenv("AIS_STREAM_KEY")
BBOX_SF_BAY = [[38.2, -123.0], [37.2, -121.5]]
WS_URL = "wss://stream.aisstream.io/v0/stream"

DEBUG_FIRST_ONLY = "--debug-first" in sys.argv

app = FastAPI()

# Serve static files from /static instead of /
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

# Store latest vessel positions by MMSI
vessels = {}
vessel_history = {}
vessel_history_index = {}  # {mmsi: {timestamp: history_point}}
# Geospatial index: {(lat_idx, lon_idx): set of MMSIs}
spatial_index = {}
GRID_SIZE = 0.1  # degrees
clients = set()

# Vessel normal profile storage: {mmsi: {"speed_mean": float, "speed_std": float, "heading_mean": float, "heading_std": float, "n": int}}
vessel_profiles = {}
PROFILE_WINDOW = 100  # Number of points to use for rolling profile

# MID (Maritime Identification Digits) to country mapping (partial, can be extended)
MID_TO_COUNTRY = {
    201: 'Albania', 202: 'Andorra', 203: 'Austria', 204: 'Azores', 205: 'Belgium',
    206: 'Belarus', 207: 'Bulgaria', 208: 'Vatican', 209: 'Cyprus', 210: 'Cyprus',
    211: 'Germany', 212: 'Cyprus', 213: 'Georgia', 214: 'Moldova', 215: 'Malta',
    218: 'Germany', 219: 'Denmark', 220: 'Denmark', 224: 'Spain', 225: 'Spain',
    226: 'France', 227: 'France', 228: 'France', 229: 'Malta', 230: 'Finland',
    231: 'Faeroe Islands', 232: 'United Kingdom', 233: 'United Kingdom', 234: 'United Kingdom',
    235: 'United Kingdom', 236: 'Gibraltar', 237: 'Greece', 238: 'Croatia', 239: 'Greece',
    240: 'Greece', 241: 'Greece', 242: 'Morocco', 243: 'Hungary', 244: 'Netherlands',
    245: 'Netherlands', 246: 'Netherlands', 247: 'Italy', 248: 'Malta', 249: 'Malta',
    250: 'Ireland', 251: 'Iceland', 252: 'Liechtenstein', 253: 'Luxembourg', 254: 'Monaco',
    255: 'Portugal', 256: 'Malta', 257: 'Norway', 258: 'Norway', 259: 'Norway',
    261: 'Poland', 262: 'Montenegro', 263: 'Portugal', 264: 'Romania', 265: 'Sweden',
    266: 'Sweden', 267: 'Slovakia', 268: 'San Marino', 269: 'Switzerland', 270: 'Czech Republic',
    271: 'Turkey', 272: 'Ukraine', 273: 'Russia', 274: 'Macedonia', 275: 'Latvia',
    276: 'Estonia', 277: 'Lithuania', 278: 'Slovenia', 279: 'Serbia', 301: 'Anguilla',
    303: 'Alaska', 305: 'Antigua and Barbuda', 306: 'Netherlands Antilles', 307: 'Aruba',
    308: 'Bahamas', 309: 'Bahamas', 310: 'Bermuda', 311: 'Bahamas', 316: 'Canada',
    319: 'Cayman Islands', 330: 'Greenland', 338: 'United States', 366: 'United States',
    367: 'United States', 368: 'United States', 369: 'United States', 370: 'Panama',
    371: 'Panama', 372: 'Panama', 373: 'Panama', 375: 'Saint Vincent and the Grenadines',
    376: 'Saint Vincent and the Grenadines', 377: 'Saint Vincent and the Grenadines',
    378: 'British Virgin Islands', 379: 'British Virgin Islands', 401: 'Afghanistan',
    403: 'Saudi Arabia', 405: 'Bangladesh', 408: 'Iran', 412: 'China', 413: 'China',
    414: 'China', 416: 'Taiwan', 417: 'Sri Lanka', 419: 'India', 422: 'Japan',
    423: 'Japan', 431: 'Hong Kong', 432: 'South Korea', 440: 'Azerbaijan', 441: 'Kazakhstan',
    450: 'Russian Federation', 451: 'Russian Federation', 452: 'Russian Federation',
    453: 'Russian Federation', 455: 'Mongolia', 456: 'North Korea', 457: 'North Korea',
    470: 'Turkey', 471: 'Syria', 472: 'Lebanon', 473: 'Jordan', 475: 'Yemen',
    477: 'Hong Kong', 478: 'Bosnia and Herzegovina', 501: 'Australia', 503: 'Australia',
    506: 'Myanmar', 508: 'Papua New Guinea', 510: 'Micronesia', 511: 'Palau',
    512: 'Nauru', 514: 'Tuvalu', 515: 'Cambodia', 516: 'Christmas Island',
    520: 'Thailand', 525: 'Singapore', 529: 'Malaysia', 533: 'Malaysia', 536: 'Brunei',
    538: 'Philippines', 542: 'South Pacific', 544: 'New Zealand', 546: 'New Zealand',
    548: 'Cook Islands', 553: 'Fiji', 555: 'Tonga', 557: 'New Caledonia',
    559: 'French Polynesia', 561: 'Wallis and Futuna', 563: 'Singapore', 564: 'Singapore',
    565: 'Singapore', 566: 'Singapore', 567: 'Singapore', 570: 'Solomon Islands',
    572: 'Vanuatu', 574: 'Guam', 576: 'Samoa', 577: 'American Samoa', 601: 'South Africa',
    603: 'Angola', 605: 'Algeria', 607: 'Saint Paul', 608: 'Ascension Island',
    609: 'Burundi', 610: 'Benin', 611: 'Botswana', 612: 'Central African Republic',
    613: 'Cameroon', 615: 'Congo', 616: 'Comoros', 617: 'Congo', 618: 'Djibouti',
    619: 'Egypt', 620: 'Ethiopia', 621: 'Gabon', 622: 'Gambia', 624: 'Ghana',
    625: 'Guinea', 626: 'Ivory Coast', 627: 'Kenya', 629: 'Madagascar', 630: 'Malawi',
    631: 'Mali', 632: 'Mauritania', 633: 'Mauritius', 634: 'Morocco', 635: 'Mozambique',
    636: 'Namibia', 637: 'Niger', 638: 'Nigeria', 642: 'Seychelles', 644: 'Sudan',
    645: 'Swaziland', 647: 'Tanzania', 649: 'Togo', 650: 'Tunisia', 654: 'Zambia',
    655: 'Zimbabwe', 657: 'South Sudan', 659: 'Eritrea', 660: 'Mayotte', 661: 'Réunion',
    662: 'Saint Pierre and Miquelon', 663: 'Saint Helena', 664: 'Saint Kitts and Nevis',
    665: 'Anguilla', 666: 'Antigua and Barbuda', 667: 'Aruba', 668: 'Bahamas',
    669: 'Barbados', 670: 'Bermuda', 672: 'British Virgin Islands', 674: 'Cayman Islands',
    675: 'Cuba', 676: 'Dominica', 677: 'Dominican Republic', 678: 'Grenada',
    679: 'Guadeloupe', 680: 'Haiti', 682: 'Jamaica', 683: 'Martinique', 684: 'Montserrat',
    685: 'Puerto Rico', 686: 'Saint Lucia', 687: 'Saint Vincent and the Grenadines',
    688: 'Trinidad and Tobago', 689: 'Turks and Caicos Islands', 690: 'Virgin Islands',
    700: 'Argentina', 701: 'Argentina', 710: 'Brazil', 720: 'Chile', 725: 'Paraguay',
    730: 'Peru', 735: 'Uruguay', 740: 'Suriname', 745: 'Venezuela', 750: 'Falkland Islands',
    755: 'Guyana', 760: 'Ecuador', 765: 'Bolivia', 770: 'Colombia', 775: 'Panama',
    780: 'Trinidad and Tobago', 800: 'Alaska', 803: 'Hawaii', 810: 'Guam', 820: 'Northern Mariana Islands',
    830: 'Palau', 850: 'United States', 857: 'United States', 870: 'United States', 875: 'United States',
    880: 'United States', 885: 'United States', 890: 'United States', 895: 'United States',
}

def parse_mmsi(mmsi):
    """Parse MMSI for country/flag and other attributes."""
    try:
        mmsi_str = str(mmsi)
        if len(mmsi_str) != 9 or not mmsi_str.isdigit():
            return {"mmsi": mmsi, "flag": None, "mid": None}
        mid = int(mmsi_str[0:3])
        flag = MID_TO_COUNTRY.get(mid, None)
        return {"mmsi": mmsi, "flag": flag, "mid": mid}
    except Exception:
        return {"mmsi": mmsi, "flag": None, "mid": None}

def get_grid_cell(lat, lon):
    lat_idx = int(lat / GRID_SIZE)
    lon_idx = int(lon / GRID_SIZE)
    return (lat_idx, lon_idx)

# --- Shared PositionReport processing logic for both stream and test injection ---
def process_position_report(msg, mmsi, meta, ais):
    lat = float(ais.get("Latitude"))
    lon = float(ais.get("Longitude"))
    ts = meta.get("time_utc") or datetime.utcnow().isoformat()
    nav_status = ais.get("NavigationalStatus")
    rate_of_turn = ais.get("RateOfTurn")
    sog = None
    try:
        sog = float(ais.get("Sog"))
    except Exception:
        pass
    heading = ais.get("TrueHeading")
    if heading is None or heading == 511:
        heading = ais.get("Cog")

    # --- Compute normal profile (speed/heading mean and std) ---
    speeds = []
    headings = []
    PROFILE_WINDOW = 100
    if mmsi in vessel_history:
        for pt in vessel_history[mmsi][-PROFILE_WINDOW:]:
            rp = pt.get("raw_position_report", {})
            s = rp.get("Sog")
            h = rp.get("TrueHeading")
            if s is not None:
                try:
                    s = float(s)
                    if not math.isnan(s) and s >= 0 and s < 102.2:
                        speeds.append(s)
                except Exception:
                    pass
            if h is not None and h != 511:
                try:
                    h = float(h)
                    if not math.isnan(h) and 0 <= h < 360:
                        headings.append(h)
                except Exception:
                    pass
    profile = {}
    if speeds:
        mean_speed = sum(speeds) / len(speeds)
        std_speed = (sum((s-mean_speed)**2 for s in speeds)/len(speeds))**0.5 if len(speeds) > 1 else 0.0
        profile["speed_mean"] = mean_speed
        profile["speed_std"] = std_speed
    if headings:
        mean_heading = sum(headings) / len(headings)
        std_heading = (sum((h-mean_heading)**2 for h in headings)/len(headings))**0.5 if len(headings) > 1 else 0.0
        profile["heading_mean"] = mean_heading
        profile["heading_std"] = std_heading
    profile["n"] = len(speeds)
    vessel_profiles[mmsi] = profile

    # --- Compute delta (first time derivative) for speed and heading ---
    delta_speed = None
    delta_heading = None
    if mmsi in vessel_history and vessel_history[mmsi]:
        prev_point = vessel_history[mmsi][-1]
        prev_rp = prev_point.get("raw_position_report", {})
        prev_sog = prev_rp.get("Sog")
        prev_heading = prev_rp.get("TrueHeading")
        if prev_sog is not None and sog is not None:
            try:
                prev_sog = float(prev_sog)
                delta_speed = sog - prev_sog
            except Exception:
                pass
        if prev_heading is not None and heading is not None and prev_heading != 511 and heading != 511:
            try:
                prev_heading = float(prev_heading)
                # Use minimal angular difference
                raw_diff = heading - prev_heading
                delta_heading = ((raw_diff + 180) % 360) - 180
            except Exception:
                pass

    time_diff = None
    if mmsi in vessel_history and vessel_history[mmsi]:
        prev_point = vessel_history[mmsi][-1]
        try:
            prev_ts = prev_point["timestamp"]
            prev_dt = datetime.fromisoformat(prev_ts.replace('Z', '+00:00'))
            curr_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            time_diff = (curr_dt - prev_dt).total_seconds()
        except Exception:
            time_diff = None
    alert = None
    # --- ANOMALY/DECEPTION DETECTION ---
    # 1. "Dark" period (transmission gap)
    if time_diff is not None and time_diff > 600:
        alert = {
            "mmsi": mmsi,
            "timestamp": ts,
            "type": "transmission_gap",
            "message": f"ALERT: Vessel {mmsi} went dark for {int(time_diff)//60} min near ({lat:.5f},{lon:.5f})"
        }
    # 2. "Teleportation" (large jump in position)
    if mmsi in vessel_history and len(vessel_history[mmsi]) > 1:
        prev_point = vessel_history[mmsi][-2]
        prev_lat = prev_point.get("raw_position_report", {}).get("Latitude")
        prev_lon = prev_point.get("raw_position_report", {}).get("Longitude")
        if prev_lat is not None and prev_lon is not None:
            dist = math.hypot(lat - prev_lat, lon - prev_lon) * 60  # rough NM
            if dist > 10:  # arbitrary threshold for demo
                alert = {
                    "mmsi": mmsi,
                    "timestamp": ts,
                    "type": "position_jump",
                    "message": f"ALERT: Vessel {mmsi} jumped {dist:.1f} NM at {ts} (possible spoofing)"
                }
    # 3. Identity swap (MMSI/ShipName change)
    if mmsi in vessel_history and len(vessel_history[mmsi]) > 1:
        prev_point = vessel_history[mmsi][-2]
        prev_name = prev_point.get("meta", {}).get("ShipName")
        curr_name = meta.get("ShipName")
        if prev_name and curr_name and prev_name != curr_name:
            alert = {
                "mmsi": mmsi,
                "timestamp": ts,
                "type": "identity_swap",
                "message": f"ALERT: Vessel {mmsi} changed name from '{prev_name}' to '{curr_name}' at {ts}"
            }
    # 4. Speed anomaly
    speed_threshold = 40  # knots, adjust as needed
    if sog is not None and sog > speed_threshold:
        alert = {
            "mmsi": mmsi,
            "timestamp": ts,
            "type": "speed_anomaly",
            "message": f"ALERT: Vessel {mmsi} reported implausible speed {sog:.1f} knots at {ts}"
        }
    # 5. Sudden course/heading change
    heading_change_threshold = 90  # degrees, adjust as needed
    if delta_heading is not None and abs(delta_heading) > heading_change_threshold:
        alert = {
            "mmsi": mmsi,
            "timestamp": ts,
            "type": "course_change_anomaly",
            "message": f"ALERT: Vessel {mmsi} changed heading by {delta_heading:.1f}° at {ts}"
        }
    # 6. Circle spoofing
    alert = detect_circle_spoofing(mmsi)
    if alert:
        alert["timestamp"] = ts
    # --- Tracking fields for map and icon ---
    history_point = {
        "timestamp": ts,
        "raw_position_report": ais,
        "meta": meta,
        "message_type": "PositionReport",
        "full_message": msg,
        "time_diff": time_diff,
        "alert": alert,
        "navigational_status": nav_status,
        "rate_of_turn": rate_of_turn,
        "sog": sog,
        "heading": heading,
        "lat": lat,
        "lon": lon,
        "normal_profile": profile,
        "delta_speed": delta_speed,
        "delta_heading": delta_heading
    }
    mmsi_info = parse_mmsi(mmsi)
    history_point["flag"] = mmsi_info.get("flag")
    history_point["mid"] = mmsi_info.get("mid")
    if mmsi not in vessel_history:
        vessel_history[mmsi] = []
    vessel_history[mmsi].append(history_point)
    # --- Update global vessel tracking for latest state ---
    vessels[mmsi] = {
        "lat": lat,
        "lon": lon,
        "sog": sog,
        "heading": heading,
        "navigational_status": nav_status,
        "rate_of_turn": rate_of_turn,
        "flag": mmsi_info.get("flag"),
        "ship_name": meta.get("ShipName"),
        "normal_profile": profile,
        "delta_speed": delta_speed,
        "delta_heading": delta_heading
    }
    return history_point

def process_standard_class_b_position_report(msg, mmsi, meta, ais):
    # Parse as with process_position_report, but may have slightly different fields
    lat = float(ais.get("Latitude"))
    lon = float(ais.get("Longitude"))
    ts = meta.get("time_utc") or datetime.utcnow().isoformat()
    nav_status = ais.get("NavigationalStatus")
    sog = None
    try:
        sog = float(ais.get("Sog"))
    except Exception:
        pass
    heading = ais.get("TrueHeading")
    if heading is None or heading == 511:
        heading = ais.get("Cog")
    # Minimal profile for now, can be extended
    history_point = {
        "timestamp": ts,
        "raw_standard_class_b_position_report": ais,
        "meta": meta,
        "message_type": "StandardClassBPositionReport",
        "full_message": msg,
        "navigational_status": nav_status,
        "sog": sog,
        "heading": heading,
        "lat": lat,
        "lon": lon
    }
    mmsi_info = parse_mmsi(mmsi)
    history_point["flag"] = mmsi_info.get("flag")
    history_point["mid"] = mmsi_info.get("mid")
    if mmsi not in vessel_history:
        vessel_history[mmsi] = []
    vessel_history[mmsi].append(history_point)
    vessels[mmsi] = {
        "lat": lat,
        "lon": lon,
        "sog": sog,
        "heading": heading,
        "navigational_status": nav_status,
        "flag": mmsi_info.get("flag"),
        "ship_name": meta.get("ShipName")
    }
    return history_point

# --- Static Data Parsing for High Fidelity ---
def parse_static_data_fields(static_data):
    # Extract key fields from static data message
    fields = {}
    if not static_data:
        return fields
    fields["imo"] = static_data.get("IMO")
    fields["callsign"] = static_data.get("Callsign")
    fields["ship_name"] = static_data.get("ShipName")
    fields["ship_type"] = static_data.get("ShipType")
    ship_type_val = static_data.get("ShipType")
    if ship_type_val is not None:
        fields["ship_type_meaning"] = get_shiptype_meaning(ship_type_val)
    fields["destination"] = static_data.get("Destination")
    fields["eta"] = static_data.get("ETA")
    fields["draught"] = static_data.get("Draught")
    # Dimensions
    try:
        to_bow = int(static_data.get("ToBow", 0))
        to_stern = int(static_data.get("ToStern", 0))
        to_port = int(static_data.get("ToPort", 0))
        to_starboard = int(static_data.get("ToStarboard", 0))
        fields["dim_bow"] = to_bow
        fields["dim_stern"] = to_stern
        fields["dim_port"] = to_port
        fields["dim_starboard"] = to_starboard
    except Exception:
        pass
    return fields

# --- ShipStaticData Parsing for High Fidelity ---
def parse_ship_static_data_fields(ship_static_data):
    # Extract key fields from ship static data message
    fields = {}
    if not ship_static_data:
        return fields
    fields["imo"] = ship_static_data.get("IMO")
    fields["callsign"] = ship_static_data.get("Callsign")
    fields["ship_name"] = ship_static_data.get("ShipName")
    fields["ship_type"] = ship_static_data.get("ShipType")
    ship_type_val = ship_static_data.get("ShipType")
    if ship_type_val is not None:
        fields["ship_type_meaning"] = get_shiptype_meaning(ship_type_val)
    fields["destination"] = ship_static_data.get("Destination")
    fields["eta"] = ship_static_data.get("ETA")
    fields["draught"] = ship_static_data.get("Draught")
    # Dimensions
    try:
        to_bow = int(ship_static_data.get("ToBow", 0))
        to_stern = int(ship_static_data.get("ToStern", 0))
        to_port = int(ship_static_data.get("ToPort", 0))
        to_starboard = int(ship_static_data.get("ToStarboard", 0))
        fields["dim_bow"] = to_bow
        fields["dim_stern"] = to_stern
        fields["dim_port"] = to_port
        fields["dim_starboard"] = to_starboard
    except Exception:
        pass
    return fields

# --- AidsToNavigationReport Parsing for High Fidelity ---
def parse_aids_to_navigation_fields(aids_data):
    # Extract key fields from aids to navigation message
    fields = {}
    if not aids_data:
        return fields
    fields["name"] = aids_data.get("Name")
    fields["type"] = aids_data.get("AidType")
    fields["lat"] = aids_data.get("Latitude")
    fields["lon"] = aids_data.get("Longitude")
    fields["status"] = aids_data.get("Status")
    return fields

# --- BaseStationReport Parsing for High Fidelity ---
def parse_base_station_report_fields(base_station):
    fields = {}
    if not base_station:
        return fields
    fields["lat"] = base_station.get("Latitude")
    fields["lon"] = base_station.get("Longitude")
    fields["epfd"] = base_station.get("EPFD")
    fields["base_station_id"] = base_station.get("BaseStationID")
    fields["timestamp"] = base_station.get("Timestamp")
    fields["sync_state"] = base_station.get("SyncState")
    fields["slot_timeout"] = base_station.get("SlotTimeout")
    fields["slot_offset"] = base_station.get("SlotOffset")
    return fields

# --- SafetyBroadcastMessage Parsing for High Fidelity ---
def parse_safety_broadcast_message_fields(safety_msg):
    fields = {}
    if not safety_msg:
        return fields
    fields["text"] = safety_msg.get("Text")
    fields["mmsi"] = safety_msg.get("MMSI")
    fields["timestamp"] = safety_msg.get("Timestamp")
    return fields

# --- AddressedSafetyMessage Parsing for High Fidelity ---
def parse_addressed_safety_message_fields(addr_msg):
    fields = {}
    if not addr_msg:
        return fields
    fields["text"] = addr_msg.get("Text")
    fields["mmsi"] = addr_msg.get("MMSI")
    fields["destination"] = addr_msg.get("DestinationMMSI")
    fields["timestamp"] = addr_msg.get("Timestamp")
    return fields

# --- GLOBAL STREAM QUEUE FOR HYBRID INJECTION ---
ais_message_queue = None

async def stream_processor():
    while True:
        msg = await ais_message_queue.get()
        await process_ais_message(msg)

@app.on_event("startup")
async def startup_event():
    global ais_message_queue
    ais_message_queue = asyncio.Queue()
    # Start the main processing loop
    asyncio.create_task(stream_processor())

async def ais_stream_task():
    global vessels
    subscription_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [BBOX_SF_BAY],
        "FilterMessageTypes": [
            "PositionReport","UnknownMessage","AddressedSafetyMessage","AddressedBinaryMessage","AidsToNavigationReport","AssignedModeCommand","BaseStationReport","BinaryAcknowledge","BinaryBroadcastMessage","ChannelManagement","CoordinatedUTCInquiry","DataLinkManagementMessage","DataLinkManagementMessageData","ExtendedClassBPositionReport","GroupAssignmentCommand","GnssBroadcastBinaryMessage","Interrogation","LongRangeAisBroadcastMessage","MultiSlotBinaryMessage","SafetyBroadcastMessage","ShipStaticData","SingleSlotBinaryMessage","StandardClassBPositionReport","StandardSearchAndRescueAircraftReport","StaticDataReport"
        ]
    }
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps(subscription_msg))
            print("Subscribed to AIS stream for SF Bay Area. Awaiting authentication response...")
            with open("ais_stream.log", "a") as logf:
                async for message in ws:
                    try:
                        msg = json.loads(message)
                    except Exception:
                        msg = message
                    print("[AIS STREAM]", json.dumps(msg, indent=2) if isinstance(msg, dict) else str(msg))
                    logf.write(json.dumps(msg) + "\n" if isinstance(msg, dict) else str(msg) + "\n")
                    logf.flush()
                    msg_type = msg.get("MessageType")
                    mmsi = None
                    meta = msg.get("MetaData", {})
                    if "MMSI" in meta:
                        mmsi = meta["MMSI"]
                    elif "UserID" in msg.get("Message", {}).get(msg_type, {}):
                        mmsi = msg["Message"][msg_type]["UserID"]
                    if not mmsi:
                        mmsi = meta.get("MMSI_String") or None
                    if msg_type == "PositionReport":
                        ais = msg["Message"]["PositionReport"]
                        try:
                            lat = float(ais.get("Latitude"))
                            lon = float(ais.get("Longitude"))
                            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                                raise ValueError("Coordinates out of bounds")
                        except Exception:
                            return
                        ais["Latitude"] = lat
                        ais["Longitude"] = lon
                        special_manoeuvre = ais.get("SpecialManoeuvreIndicator")
                        speed = ais.get("SOG")
                        try:
                            speed = float(speed)
                            if speed >= 102.2 or speed < 0:  
                                speed = None
                        except (ValueError, TypeError):
                            speed = None
                        heading = ais.get("TrueHeading")
                        if heading is None or heading == 511:
                            heading = ais.get("Cog")
                        ship_name = msg.get("MetaData", {}).get("ShipName")
                        vessels[mmsi] = {
                            "mmsi": mmsi,
                            "lat": lat,
                            "lon": lon,
                            "speed": speed,
                            "heading": heading,
                            "ship_name": ship_name,
                            "special_manoeuvre": special_manoeuvre
                        }
                        history_point = process_position_report(msg, mmsi, meta, ais)
                        await broadcast_vessel_update(history_point)
                        continue  # skip the rest (already handled)
                    elif msg_type == "StandardClassBPositionReport":
                        if mmsi:
                            if mmsi not in vessel_history:
                                vessel_history[mmsi] = []
                            vessel_history[mmsi].append({
                                "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                                "raw_standard_class_b_position_report": msg["Message"][msg_type],
                                "meta": meta,
                                "message_type": msg_type,
                                "full_message": msg
                            })
                    elif msg_type == "StaticDataReport" or msg_type == "ShipStaticData":
                        if mmsi:
                            if mmsi not in vessel_history:
                                vessel_history[mmsi] = []
                            vessel_history[mmsi].append({
                                "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                                "raw_static_data": msg["Message"][msg_type],
                                "meta": meta,
                                "message_type": msg_type,
                                "full_message": msg
                            })
                    elif msg_type == "BaseStationReport":
                        if mmsi:
                            if mmsi not in vessel_history:
                                vessel_history[mmsi] = []
                            vessel_history[mmsi].append({
                                "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                                "raw_base_station_report": msg["Message"][msg_type],
                                "meta": meta,
                                "message_type": msg_type,
                                "full_message": msg
                            })
                    elif msg_type == "DataLinkManagementMessage":
                        if mmsi:
                            if mmsi not in vessel_history:
                                vessel_history[mmsi] = []
                            vessel_history[mmsi].append({
                                "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                                "raw_data_link_management": msg["Message"][msg_type],
                                "meta": meta,
                                "message_type": msg_type,
                                "full_message": msg
                            })
                    elif msg_type == "AidsToNavigationReport":
                        aids_data = msg["Message"]["AidsToNavigationReport"]
                        history_point = {
                            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                            "raw_aids_to_navigation_report": aids_data,
                            "meta": meta,
                            "message_type": msg_type,
                            "full_message": msg
                        }
                        aids_fields = parse_aids_to_navigation_fields(aids_data)
                        vessels.setdefault(mmsi, {}).update(aids_fields)
                        if mmsi not in vessel_history:
                            vessel_history[mmsi] = []
                        vessel_history[mmsi].append(history_point)
                        await broadcast_vessel_update(history_point)
                    elif msg_type in ["UnknownMessage", "AddressedSafetyMessage", "AddressedBinaryMessage", "AssignedModeCommand", "BinaryAcknowledge", "BinaryBroadcastMessage", "ChannelManagement", "CoordinatedUTCInquiry", "DataLinkManagementMessageData", "ExtendedClassBPositionReport", "GroupAssignmentCommand", "GnssBroadcastBinaryMessage", "Interrogation", "LongRangeAisBroadcastMessage", "MultiSlotBinaryMessage", "SafetyBroadcastMessage", "ShipStaticData", "SingleSlotBinaryMessage", "StandardSearchAndRescueAircraftReport"]:
                        if mmsi:
                            if mmsi not in vessel_history:
                                vessel_history[mmsi] = []
                            vessel_history[mmsi].append({
                                "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
                                "raw_other": msg["Message"][msg_type],
                                "meta": meta,
                                "message_type": msg_type,
                                "full_message": msg
                            })
                    else:
                        print(f"WARNING: Unknown AIS message type encountered: {msg_type}")
                        print(json.dumps(msg, indent=2))
    except Exception as e:
        print("Websocket connection error:", e)

    # --- MODIFY STREAM INGESTION TO USE QUEUE ---
    # Instead of: await process_ais_message(msg)
    # Use: await ais_message_queue.put(msg)
    await ais_message_queue.put(msg)

async def broadcast_vessel_update(history_point):
    data = json.dumps({"type": "vessel_update", "history_point": history_point})
    to_remove = set()
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:
            to_remove.add(ws)
    for ws in to_remove:
        clients.remove(ws)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    for vessel_history_list in vessel_history.values():
        for history_point in vessel_history_list:
            await websocket.send_text(json.dumps({"type": "vessel_update", "history_point": history_point}))
    try:
        while True:
            await websocket.receive_text()  
    except WebSocketDisconnect:
        clients.remove(websocket)

@app.get("/history/{mmsi}")
def get_vessel_history(mmsi: int):
    return JSONResponse(content=vessel_history.get(mmsi, []))

@app.get("/spatial_query")
def spatial_query(
    min_lat: float = Query(...),
    max_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lon: float = Query(...)
):
    grid_cells = set()
    lat_idx_min = int(min_lat / GRID_SIZE)
    lat_idx_max = int(max_lat / GRID_SIZE)
    lon_idx_min = int(min_lon / GRID_SIZE)
    lon_idx_max = int(max_lon / GRID_SIZE)
    for lat_idx in range(lat_idx_min, lat_idx_max + 1):
        for lon_idx in range(lon_idx_min, lon_idx_max + 1):
            grid_cells.add((lat_idx, lon_idx))
    mmsis = set()
    for cell in grid_cells:
        mmsis.update(spatial_index.get(cell, set()))
    vessels_in_bbox = []
    for mmsi in mmsis:
        vessel = vessels.get(mmsi)
        if not vessel:
            continue
        lat = vessel.get("lat")
        lon = vessel.get("lon")
        if lat is not None and lon is not None and min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            vessels_in_bbox.append(vessel)
    return JSONResponse(content=vessels_in_bbox)

# --- TEST ENDPOINTS FOR ANOMALY INJECTION ---
from datetime import timedelta

@app.post("/inject/static_data")
async def inject_static_data(
    mmsi: int = Body(...),
    name: str = Body(...),
    imo: int = Body(...),
    callsign: str = Body(...),
    ship_type: str = Body(...),
    destination: str = Body(...),
    eta: str = Body(...),
    draught: float = Body(...),
    dim_a: int = Body(...),
    dim_b: int = Body(...),
    dim_c: int = Body(...),
    dim_d: int = Body(...)
):
    now = datetime.utcnow()
    meta = {"MMSI": mmsi, "ShipName": name, "time_utc": now.isoformat()}
    static_data = {
        "IMO": imo,
        "Callsign": callsign,
        "ShipName": name,
        "ShipType": ship_type,
        "Destination": destination,
        "ETA": eta,
        "Draught": draught,
        "ToBow": dim_a,
        "ToStern": dim_b,
        "ToPort": dim_c,
        "ToStarboard": dim_d
    }
    msg = {"MessageType": "StaticData", "Message": {"StaticData": static_data}, "MetaData": meta, "injected": True}
    await ais_message_queue.put(msg)
    return {"status": "static data injected", "mmsi": mmsi, "name": name}

@app.post("/reset_data")
def reset_data():
    """Clear all vessel and anomaly state for a fresh test."""
    global vessels, vessel_history, vessel_history_index, spatial_index, vessel_profiles
    vessels.clear()
    vessel_history.clear()
    vessel_history_index.clear()
    spatial_index.clear()
    vessel_profiles.clear()
    return {"status": "reset complete"}

@app.post("/inject/dark_period")
async def inject_dark_period(
    mmsi: int = Body(...),
    lat: float = Body(...),
    lon: float = Body(...),
    gap_seconds: int = Body(7200)
):
    now = datetime.utcnow()
    meta1 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}", "latitude": lat, "longitude": lon, "time_utc": now.isoformat()}
    meta2 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}", "latitude": lat+0.001, "longitude": lon+0.001, "time_utc": (now + timedelta(seconds=gap_seconds)).isoformat()}
    ais1 = {"Latitude": lat, "Longitude": lon, "Sog": 10, "Cog": 45, "TrueHeading": 45, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    ais2 = {"Latitude": lat+0.001, "Longitude": lon+0.001, "Sog": 10, "Cog": 45, "TrueHeading": 45, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    msg1 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais1}, "MetaData": meta1, "injected": True}
    msg2 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais2}, "MetaData": meta2, "injected": True}
    await ais_message_queue.put(msg1)
    await ais_message_queue.put(msg2)
    return {"status": "dark period anomaly injected"}

@app.post("/inject/teleport")
async def inject_teleport(
    mmsi: int = Body(...),
    lat1: float = Body(...),
    lon1: float = Body(...),
    lat2: float = Body(...),
    lon2: float = Body(...),
    seconds_apart: int = Body(60)
):
    now = datetime.utcnow()
    meta1 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}", "latitude": lat1, "longitude": lon1, "time_utc": now.isoformat()}
    meta2 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}", "latitude": lat2, "longitude": lon2, "time_utc": (now + timedelta(seconds=seconds_apart)).isoformat()}
    ais1 = {"Latitude": lat1, "Longitude": lon1, "Sog": 12, "Cog": 90, "TrueHeading": 90, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    ais2 = {"Latitude": lat2, "Longitude": lon2, "Sog": 12, "Cog": 90, "TrueHeading": 90, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    msg1 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais1}, "MetaData": meta1, "injected": True}
    msg2 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais2}, "MetaData": meta2, "injected": True}
    await ais_message_queue.put(msg1)
    await ais_message_queue.put(msg2)
    return {"status": "teleport anomaly injected"}

@app.post("/inject/identity_swap")
async def inject_identity_swap(
    mmsi: int = Body(...),
    lat: float = Body(...),
    lon: float = Body(...)
):
    now = datetime.utcnow()
    meta1 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}", "latitude": lat, "longitude": lon, "time_utc": now.isoformat()}
    meta2 = {"MMSI": mmsi, "ShipName": f"TestVessel{mmsi}_SWAP", "latitude": lat+0.001, "longitude": lon+0.001, "time_utc": (now + timedelta(seconds=60)).isoformat()}
    ais1 = {"Latitude": lat, "Longitude": lon, "Sog": 10, "Cog": 45, "TrueHeading": 45, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    ais2 = {"Latitude": lat+0.001, "Longitude": lon+0.001, "Sog": 10, "Cog": 45, "TrueHeading": 45, "MessageID": 1, "UserID": mmsi, "NavigationalStatus": 0}
    msg1 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais1}, "MetaData": meta1, "injected": True}
    msg2 = {"MessageType": "PositionReport", "Message": {"PositionReport": ais2}, "MetaData": meta2, "injected": True}
    await ais_message_queue.put(msg1)
    await ais_message_queue.put(msg2)
    return {"status": "identity swap anomaly injected"}

@app.post("/inject/telemetry")
async def inject_telemetry(
    mmsi: int = Body(...),
    lat: float = Body(...),
    lon: float = Body(...),
    navigational_status: int = Body(0)
):
    now = datetime.utcnow()
    meta = {
        "MMSI": mmsi,
        "ShipName": f"TestVessel{mmsi}",
        "latitude": lat,
        "longitude": lon,
        "time_utc": now.isoformat()
    }
    ais = {
        "Latitude": lat,
        "Longitude": lon,
        "Sog": 0,
        "Cog": 0,
        "TrueHeading": 0,
        "MessageID": 1,
        "UserID": mmsi,
        "NavigationalStatus": navigational_status
    }
    msg = {
        "MessageType": "PositionReport",
        "Message": {"PositionReport": ais},
        "MetaData": meta,
        "injected": True
    }
    await ais_message_queue.put(msg)
    return {"status": "telemetry injected"}

CIRCLE_DETECTION_WINDOW = 60 * 45  # seconds (45 min window)
CIRCLE_MIN_POINTS = 3  # LOWERED for testing
CIRCLE_MAX_RESIDUAL = 0.0001  # degrees, ~10m
CIRCLE_MIN_RADIUS = 0.1 / 60  # degrees (~0.1 nm)
CIRCLE_MAX_RADIUS = 2.0 / 60  # degrees (~2 nm)
CIRCLE_UNIFORMITY_THRESHOLD = 0.03  # radians
CIRCLE_SOG_STD_THRESHOLD = 0.5  # knots

def detect_circle_spoofing(mmsi):
    """
    Check if vessel's recent track forms a suspiciously perfect circle.
    Returns alert dict if detected, else None.
    """
    now = datetime.utcnow()
    history = vessel_history.get(mmsi, [])
    if len(history) < CIRCLE_MIN_POINTS:
        return None
    # Only use recent points
    cut_ts = (now - timedelta(seconds=CIRCLE_DETECTION_WINDOW)).isoformat()
    points = [pt for pt in history if pt.get("timestamp","") >= cut_ts and pt.get("lat") and pt.get("lon")]
    if len(points) < CIRCLE_MIN_POINTS:
        return None
    xs = [pt["lat"] for pt in points]
    ys = [pt["lon"] for pt in points]
    xc, yc, r, residual = fit_circle(xs, ys)
    if not (CIRCLE_MIN_RADIUS <= r <= CIRCLE_MAX_RADIUS):
        return None
    if residual > CIRCLE_MAX_RESIDUAL:
        return None
    # Uniformity: check angular spacing
    thetas = [np.arctan2(yc-y, xc-x) for x, y in zip(xs, ys)]
    thetas = np.unwrap(thetas)
    dthetas = np.diff(thetas)
    if np.std(dthetas) > CIRCLE_UNIFORMITY_THRESHOLD:
        return None
    # SOG uniformity
    sogs = [pt.get("sog") for pt in points if pt.get("sog") is not None]
    if len(sogs) < CIRCLE_MIN_POINTS:
        return None
    if np.std(sogs) > CIRCLE_SOG_STD_THRESHOLD:
        return None
    # Passed all checks
    alert = {
        "mmsi": mmsi,
        "timestamp": now.isoformat(),
        "type": "circle_spoofing",
        "message": f"ALERT: Vessel {mmsi} detected with possible circle spoofing pattern (r={r*60:.2f}nm)"
    }
    print(f"[DEBUG] Circle spoofing alert generated: {alert}")
    return alert

# Helper to process synthetic messages as if from stream
def process_ais_message_sync(msg):
    msg_type = msg.get("MessageType")
    mmsi = msg.get("MetaData", {}).get("MMSI")
    meta = msg.get("MetaData", {})
    if not mmsi:
        return
    if msg_type == "PositionReport":
        ais = msg["Message"]["PositionReport"]
        # Attach latest static and ship static data if available
        static_data = None
        ship_static_data = None
        for pt in reversed(vessel_history.get(mmsi, [])):
            if pt.get("raw_static_data") and not static_data:
                static_data = pt["raw_static_data"]
            if pt.get("raw_ship_static_data") and not ship_static_data:
                ship_static_data = pt["raw_ship_static_data"]
            if static_data and ship_static_data:
                break
        static_fields = parse_static_data_fields(static_data)
        ship_static_fields = parse_ship_static_data_fields(ship_static_data)
        meta = {**meta, **static_fields, **ship_static_fields}
        history_point = process_position_report(msg, mmsi, meta, ais)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "StandardClassBPositionReport":
        ais = msg["Message"]["StandardClassBPositionReport"]
        # Attach latest static and ship static data if available
        static_data = None
        ship_static_data = None
        for pt in reversed(vessel_history.get(mmsi, [])):
            if pt.get("raw_static_data") and not static_data:
                static_data = pt["raw_static_data"]
            if pt.get("raw_ship_static_data") and not ship_static_data:
                ship_static_data = pt["raw_ship_static_data"]
            if static_data and ship_static_data:
                break
        static_fields = parse_static_data_fields(static_data)
        ship_static_fields = parse_ship_static_data_fields(ship_static_data)
        meta = {**meta, **static_fields, **ship_static_fields}
        history_point = process_standard_class_b_position_report(msg, mmsi, meta, ais)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "StaticData":
        static_data = msg["Message"]["StaticData"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_static_data": static_data,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        static_fields = parse_static_data_fields(static_data)
        vessels.setdefault(mmsi, {}).update(static_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "ShipStaticData":
        ship_static_data = msg["Message"]["ShipStaticData"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_ship_static_data": ship_static_data,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        ship_static_fields = parse_ship_static_data_fields(ship_static_data)
        vessels.setdefault(mmsi, {}).update(ship_static_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "AidsToNavigationReport":
        aids_data = msg["Message"]["AidsToNavigationReport"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_aids_to_navigation_report": aids_data,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        aids_fields = parse_aids_to_navigation_fields(aids_data)
        vessels.setdefault(mmsi, {}).update(aids_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "BaseStationReport":
        base_station = msg["Message"]["BaseStationReport"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_base_station_report": base_station,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        base_fields = parse_base_station_report_fields(base_station)
        vessels.setdefault(mmsi, {}).update(base_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "SafetyBroadcastMessage":
        safety_msg = msg["Message"]["SafetyBroadcastMessage"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_safety_broadcast_message": safety_msg,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        safety_fields = parse_safety_broadcast_message_fields(safety_msg)
        vessels.setdefault(mmsi, {}).update(safety_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    elif msg_type == "AddressedSafetyMessage":
        addr_msg = msg["Message"]["AddressedSafetyMessage"]
        history_point = {
            "timestamp": meta.get("time_utc", datetime.utcnow().isoformat()),
            "raw_addressed_safety_message": addr_msg,
            "meta": meta,
            "message_type": msg_type,
            "full_message": msg
        }
        addr_fields = parse_addressed_safety_message_fields(addr_msg)
        vessels.setdefault(mmsi, {}).update(addr_fields)
        if mmsi not in vessel_history:
            vessel_history[mmsi] = []
        vessel_history[mmsi].append(history_point)
        asyncio.create_task(broadcast_vessel_update(history_point))
    # existing handling for other types ...

async def process_ais_message(msg):
    process_ais_message_sync(msg)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ais_stream_task())
