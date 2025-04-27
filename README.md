# Maritime AIS Bay Area Visualization and Anomaly Alert System

![AIS Bay Area Screenshot](screenshot.png)

## Project Overview
This project provides a real-time visualization of maritime Automatic Identification System (AIS) data for the San Francisco Bay Area, with a focus on detecting and displaying anomalous vessel behaviors. The system includes:
- A FastAPI backend for ingesting, parsing, and broadcasting AIS messages
- A modern web frontend for map-based vessel visualization and a bottom alert ticker for anomalies
- An anomaly simulation tool for generating synthetic test cases to exercise and test anomaly detection features, including circle spoofing and other vessel movement anomalies
- **Created as an example project to learn [Windsurf IDE](https://windsurf.com/). Not intended for production use without additional testing and code review.**
- _For production use, consider a commercial SaaS alternative such as [myshiptracking.com](https://www.myshiptracking.com/)._

<details>
<summary><b>Project Motivation</b> (click to expand)</summary>

This project was inspired by Maritime Pattern Analysis problem sets explored during the National Security Hackathon. It provided a compelling real-world context to learn and experiment with [Windsurf IDE](https://windsurf.com/) and agentic AI coding workflows. By building a maritime AIS visualization and anomaly detection system, the project serves as a practical testbed for evaluating the capabilities of Windsurf IDE.

Additionally, the name "Windsurf" inspired the project's nautical theme. Just as windsurfing involves navigating dynamic waters, this project focuses on navigating, visualizing, and monitoring maritime vessel data—making the nautical setting a natural fit for exploring Windsurf IDE's capabilities.

**Special thanks to [Cerebral Valley](https://cerebralvalley.ai/), [Shield Capital](https://shieldcap.com/), and [Windsurf](https://windsurf.com/) (for providing a Pro subscription credit during the hackathon) for organizing, supporting, and inspiring this work!**
</details>

## Live AIS Data via aisstream.io
This project uses [aisstream.io](https://aisstream.io/) to receive live AIS vessel data. The backend connects to the aisstream.io WebSocket API to ingest real-time messages for vessels operating in the San Francisco Bay Area.

<details>
<summary><b>Subscription Logic</b> (click to expand)</summary>

- **Geographic Limiting:**
  - The subscription request includes a bounding box that restricts data to the Bay Area, reducing bandwidth and focusing analysis on relevant vessels.
- **Message Types:**
  - The subscription requests a comprehensive set of AIS message types, including `PositionReport`, `StandardClassBPositionReport`, `StaticDataReport`, `ShipStaticData`, `AidsToNavigationReport`, `BaseStationReport`, and others. This ensures the system receives both dynamic (position, speed, heading) and static (name, type, destination) vessel information, as well as navigation aids and base station updates.
- **Example Subscription Payload:**
```json
{
  "APIKey": "<YOUR_API_KEY>",
  "BoundingBoxes": [[minLat, minLon, maxLat, maxLon]],
  "FilterMessageTypes": [
    "PositionReport", "StandardClassBPositionReport", "StaticDataReport", "ShipStaticData", "AidsToNavigationReport", "BaseStationReport", ...
  ]
}
```
</details>

<details>
<summary><b>Getting Your Own API Key</b> (click to expand)</summary>

To run the project with live AIS data:
1. Register for a free account at [aisstream.io](https://aisstream.io/)
2. Navigate to your account dashboard and generate an API key
3. Copy your API key into a `.env` file in the project root as follows:
   ```
   AISSTREAM_API_KEY=your_actual_key_here
   ```
4. Restart the backend server to begin streaming live data
</details>

<details>
<summary><b>AIS Navigational Status Lookup Table</b> (click to expand)</summary>

| Code | Meaning                             | Emoji/Icon |
|------|-------------------------------------|------------|
| 0    | Under way using engine              | 🚢         |
| 1    | At anchor                           | ⚓         |
| 2    | Not under command                   | ❗         |
| 3    | Restricted manoeuverability         | ⛔         |
| 4    | Constrained by her draught          | 🛑         |
| 5    | Moored                              | 🪢         |
| 6    | Aground                             | ⛱️         |
| 7    | Engaged in fishing                  | 🎣         |
| 8    | Under way sailing                   | ⛵         |
| 9    | Reserved for future amendment       |            |
| 10   | Reserved for future amendment       |            |
| 11   | Power-driven vessel towing astern   | 🛳️         |
| 12   | Power-driven vessel pushing ahead or towing alongside | 🛥️ |
| 13   | Reserved for future use             |            |
| 14   | AIS-SART (active), MOB-AIS, EPIRB-AIS | 🆘        |
| 15   | Unusual/Reserved/Test               | ⚠️         |
</details>

<details>
<summary><b>AIS Ship Type Lookup Table</b> (click to expand)</summary>

The AIS ship type code provides a standardized classification for vessels. Below are the most common codes and their meanings, as parsed by `shiptype_lookup.py`:

| Code | Meaning                        |
|------|--------------------------------|
| 20   | Wing in ground                 |
| 30   | Fishing                        |
| 31   | Towing                         |
| 32   | Towing (large)                 |
| 33   | Dredging or underwater ops     |
| 34   | Diving ops                     |
| 35   | Military ops                   |
| 36   | Sailing                        |
| 37   | Pleasure craft                 |
| 40   | High-speed craft               |
| 50   | Pilot vessel                   |
| 52   | Tug                            |
| 53   | Port tender                    |
| 54   | Anti-pollution equipment       |
| 55   | Law enforcement                |
| 60   | Passenger ship                 |
| 70   | Cargo ship                     |
| 80   | Tanker                         |
| 90   | Other type                     |

For a more complete list, see official [IMO/AIS documentation](https://www.navcen.uscg.gov/?pageName=AISMessages#shiptype).
</details>

<details>
<summary><b>MMSI to Flag (Country) Parsing</b> (click to expand)</summary>

The first 3 digits of an MMSI (Maritime Mobile Service Identity) represent the vessel's Maritime Identification Digits (MID), which indicate the country of registration. The backend parses the flag by looking up this MID.

| MMSI Prefix (MID) | Country          | Example Flag Emoji |
|-------------------|------------------|--------------------|
| 316               | Canada           | 🇨🇦               |
| 366, 367, 368, 369| United States    | 🇺🇸               |
| 232, 233, 234, 235| United Kingdom   | 🇬🇧               |
| 538               | Marshall Islands | 🇲🇭               |
| 636               | Liberia          | 🇱🇷               |
| 248               | Malta            | 🇲🇹               |
| 563               | Singapore        | 🇸🇬               |
| ...               | ...              | ...                |

The system uses a lookup table (see `countryToFlagEmoji` in the code) to convert the MMSI prefix to a country name and emoji. If the prefix is not recognized, it defaults to 'Unknown' (🏳️).
</details>

<details>
<summary><b>Map Source and Attribution</b> (click to expand)</summary>

This project uses [Leaflet.js](https://leafletjs.com/) for interactive map rendering and [OpenStreetMap](https://www.openstreetmap.org/about) as the map tile/data provider. Map tiles are loaded from `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` and displayed in accordance with the [OpenStreetMap Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/).

**Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).**
</details>

## Unique Capabilities of Windsurf IDE

<details>
<summary><b>Key Features</b> (click to expand)</summary>

[Windsurf IDE](https://windsurf.com/) stands out from other AI coding environments and assistants due to:
- **Agentic Coding:** Windsurf enables AI agents to perform multi-step, autonomous coding actions, such as searching, editing, running, and debugging code, not just generating code snippets.
- **Full-Stack Context:** The AI has access to your entire project, including backend, frontend, and configuration files, allowing for holistic understanding and changes.
- **Live Code Execution:** You can run servers, scripts, and tests directly in the IDE, with AI able to observe outputs and iterate based on real results.
- **Persistent Memory:** The AI remembers project context, design decisions, and user preferences across sessions, enabling more personalized and effective assistance.
- **Seamless Collaboration:** Human users and AI agents can work together in real-time, making it easy to prototype, debug, and document complex systems.
- **Rich UI Integration:** Features like browser previews, file explorers, and terminal access are tightly integrated, making development and troubleshooting more interactive and visual.

Compared to other AI assistants, Windsurf IDE is more autonomous, context-aware, and collaborative, making it ideal for rapid prototyping and learning.
</details>

<details>
<summary><b>Using Windsurf IDE</b> (click to expand)</summary>

[Windsurf IDE](https://windsurf.com/) enables:
- Real-time code editing, debugging, and visualization of backend/frontend changes
- Seamless collaboration with AI for implementing features, troubleshooting, and understanding code structure
- Running and visualizing the project locally, including live map updates and anomaly alert ticker

**Workflow Example:**
1. Open the project in Windsurf IDE
2. Inspect, modify, and run backend or frontend code directly in the IDE
3. Visualize live vessel data and anomaly alerts in the browser
4. Use the anomaly simulator to generate test cases and observe system response
</details>

<details>
<summary><b>AIS Message/Data Type Parsing</b> (click to expand)</summary>

| Message/Data Type                | Backend Parser Function            | Key Fields Parsed                       | Example Values                  |
|----------------------------------|------------------------------------|-----------------------------------------|---------------------------------|
| PositionReport                   | process_position_report            | Latitude, Longitude, SOG, Heading, NavStatus | 37.8, -122.4, 12.0, 90, 0       |
| StandardClassBPositionReport     | process_standard_class_b_position_report | Latitude, Longitude, SOG, Heading     | 37.8, -122.4, 10.0, 45          |
| StaticData                       | parse_static_data_fields           | ShipName, IMO, Callsign, ShipType, Destination | USS Enterprise, 2011701, NCC1701, Cargo, Risa |
| ShipStaticData                   | parse_ship_static_data_fields      | ShipType, Draught, Dimensions           | Cargo, 8.0, 100x20x10x10        |
| AidsToNavigationReport           | parse_aids_to_navigation_fields    | Name, Latitude, Longitude               | Buoy 1, 37.9, -122.5            |
| BaseStationReport                | parse_base_station_report_fields   | Latitude, Longitude, EPFD, BaseStationID | 37.7, -122.3, GPS, 12345        |
</details>

## Installation & Running the App

<details>
<summary><b>Prerequisites</b> (click to expand)</summary>

- Python 3.8+
- Node.js (for advanced frontend development, optional)
- [Windsurf IDE](https://windsurf.com/) (recommended for full AI/IDE experience)
</details>

<details>
<summary><b>Setup Instructions</b> (click to expand)</summary>

### Install Python Dependencies
```sh
pip install -r requirements.txt
```

### Running the Backend
```sh
uvicorn ais_websocket_server:app --reload
```

### Running the Frontend
- Open your browser to: `http://localhost:8000/static/ais_map.html`
- Do **not** open the HTML file directly; always use the local server

### Simulating Anomalies
```sh
python anomaly_simulation.py
```
This will inject various vessel anomalies for alert testing.
</details>

## Anomaly Detection Features

<details>
<summary><b>Anomaly Simulator</b> (click to expand)</summary>

The anomaly simulator (`anomaly_simulation.py`) is designed to:
- Inject synthetic AIS anomalies (teleportation, speed jumps, course changes, identity swaps, dark periods, and circle spoofing) via backend endpoints
- Exercise the alert ticker and backend detection logic for robust system testing
- Provide a repeatable way to validate alerting and visualization features
</details>

<details>
<summary><b>About Circle Spoofing</b> (click to expand)</summary>

Circle spoofing is a maritime AIS anomaly in which a vessel appears to move in an unnaturally perfect circular path. This pattern is often the result of deliberate manipulation of AIS signals and can be used to mask a vessel's true movements or intent. The backend includes logic to detect this behavior and generate alerts. For more information, see this reference: [AIS Spoofing Explained by Pole Star Global](https://www.polestarglobal.com/resources/ais-spoofing/)
</details>

<details>
<summary><b>Backend Data Structure</b> (click to expand)</summary>

- **vessels**: Latest state for each MMSI (position, speed, heading, etc.)
- **vessel_history**: List of all received reports per MMSI
- **vessel_profiles**: Rolling statistics for speed/heading per vessel
- **spatial_index**: Geospatial lookup for vessels
- **ais_message_queue**: Async queue for processing both live and injected AIS messages
</details>

<details>
<summary><b>API Endpoints</b> (click to expand)</summary>

| Endpoint                | Method | Purpose                                                     |
|------------------------|--------|-------------------------------------------------------------|
| `/ws`                  | WS     | WebSocket for real-time vessel and alert updates            |
| `/inject/telemetry`    | POST   | Inject synthetic telemetry (position report)                |
| `/inject/teleport`     | POST   | Inject a teleportation anomaly                              |
| `/inject/dark_period`  | POST   | Inject a dark period (loss of signal) anomaly               |
| `/inject/identity_swap`| POST   | Inject an identity swap anomaly                             |
| `/inject/static_data`  | POST   | Inject static vessel metadata                               |
| `/reset_data`          | POST   | Clear all vessel/anomaly state for a fresh test             |
| `/spatial_query`       | GET    | Query vessels in a bounding box                             |
</details>

## Technical References & Future Development

<details>
<summary><b>AIS Standards & References</b> (click to expand)</summary>

This project is informed by several key AIS standards, protocols, and open-source libraries:

- **International Telecommunication Union (ITU). (2014).** Recommendation ITU-R M.1371-5: Technical characteristics for an automatic identification system using time division multiple access in the VHF maritime mobile frequency band.
- **Raymond, E. S.** "AIVDM/AIVDO protocol decoding." GPSD Documentation. [Read online](https://gpsd.gitlab.io/gpsd/AIVDM.html)
- **Moritz Eilfort.** "pyais: AIS message decoding and encoding in Python." [GitHub Repository](https://github.com/M0r13n/pyais)
- **Schwehr, K.** "libais: C++ decoder for Automatic Identification System for tracking ships and decoding maritime information." [GitHub Repository](https://github.com/schwehr/libais)
- **National Marine Electronics Association.** NMEA 0183 Standard. [Specifications](https://www.nmea.org/)
</details>

<details>
<summary><b>Project Purpose</b> (click to expand)</summary>

- Enable rapid prototyping and visualization of maritime vessel data
- Provide a robust anomaly detection and alerting system for maritime security and safety
- Serve as a foundation for further research, testing, and development in maritime situational awareness
</details>

<details>
<summary><b>Future Work</b> (click to expand)</summary>

The following improvements and enhancements are planned for future development:
- **Retrieve API keys from a secure vault** instead of storing them in the `.env` file for better security
- **Add support for additional intelligence sources** to enrich vessel tracking and anomaly detection
- **Unit test all the things:** Comprehensive unit test coverage for backend and frontend logic
- **Re-scaffold as a proper Pythonic app:** Refactor the codebase to follow best practices for Python application structure and maintainability
- **Incorporate established AIS parser libraries** such as [pyais](https://github.com/M0r13n/pyais), [libais](https://github.com/schwehr/libais), or [GPSD AIVDM/AIVDO](https://gpsd.gitlab.io/gpsd/AIVDM.html) for improved robustness and standards compliance
</details>

## Contact & Contribution
For questions or contributions, please use [Windsurf IDE](https://windsurf.com/)'s collaboration features or contact the project maintainer.