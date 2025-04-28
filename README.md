# Maritime AIS Bay Area Visualization, Anomaly Alert System, and Interactive Chat Assistant

![AIS Bay Area Screenshot](screenshot.png)

[▶️ Watch the demo video](./demo720.mov)

## Project Overview

This educational project provides a visualization of maritime Automatic Identification System (AIS) data for the San Francisco Bay Area, focusing on detecting and displaying anomalous vessel behaviors. The system includes:

- A FastAPI backend for processing and broadcasting AIS messages
- A web frontend for map-based vessel visualization with an alert ticker
- An anomaly simulation tool for generating test cases

**⚠️ Important Note:** This project is intended for educational purposes only and not for production use without additional testing and code review. For production maritime tracking needs, consider commercial alternatives such as [myshiptracking.com](https://www.myshiptracking.com/).

<details>
<summary><b>Project Motivation</b> (click to expand)</summary>

This project was inspired by Maritime Pattern Analysis problem sets explored during the National Security Hackathon. It provided an opportunity to learn and experiment with [Windsurf IDE](https://windsurf.com/) and agentic AI coding workflows through a practical maritime application.

**Special thanks to [Cerebral Valley](https://cerebralvalley.ai/), [Shield Capital](https://shieldcap.com/), and [Windsurf](https://windsurf.com/) for organizing, supporting, and inspiring this work!**
</details>

## Installation & Setup

<details>
<summary><b>Prerequisites</b> (click to expand)</summary>

- Python 3.8+
- Node.js (for advanced frontend development, optional)
- [Windsurf IDE](https://windsurf.com/) (recommended for AI-assisted development)
</details>

<details>
<summary><b>Quick Start</b> (click to expand)</summary>

```sh
# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn ais_websocket_server:app --reload

# View the application
# Open http://localhost:8000/static/ais_map.html in your browser
```

To test anomaly detection:
```sh
python anomaly_simulation.py
```
</details>

## Troubleshooting

<details>
<summary><b>Troubleshooting</b> (click to expand)</summary>

**Purging Data When Launching Backend:**
- To clear all vessel and anomaly state for a fresh test, use the backend's `/reset_data` endpoint. You can do this with curl:
  ```sh
  curl -X POST http://localhost:8000/reset_data
  ```
  This will clear all in-memory vessel state, history, and spatial index. It is useful if you want to start with a clean slate or encounter stale/duplicate vessel data.

**Other Troubleshooting Tips:**
- If the map or chat assistant is not updating, ensure the backend is running and accessible at the expected port (default: 8000).
- If you encounter CORS or WebSocket connection issues, make sure your browser and backend are both using the correct hostname and port.
- To force reload vessel data, refresh the browser after resetting the backend data.
- For persistent issues, check backend logs for errors or stack traces.
- If the chat assistant cannot connect, ensure the chat server is running on port 5001 and that your `.env` file contains a valid OpenAI API key.

</details>

## Data Sources & Processing

### Live AIS Data via aisstream.io

This project uses [aisstream.io](https://aisstream.io/) to receive live AIS vessel data for the San Francisco Bay Area.

<details>
<summary><b>Getting Your Own API Key</b> (click to expand)</summary>

To run the project with live AIS data:
1. Register for a free account at [aisstream.io](https://aisstream.io/)
2. Navigate to your account dashboard and generate an API key
3. Copy your API key into a `.env` file in the project root:
   ```
   AISSTREAM_API_KEY=your_actual_key_here
   ```
4. Restart the backend server to begin streaming live data
</details>

<details>
<summary><b>Subscription Logic</b> (click to expand)</summary>

The subscription request includes a geographic bounding box for the Bay Area and requests comprehensive AIS message types including position reports, static data, and aids to navigation.

Example subscription payload:
```json
{
  "APIKey": "<YOUR_API_KEY>",
  "BoundingBoxes": [[minLat, minLon, maxLat, maxLon]],
  "FilterMessageTypes": [
    "PositionReport", "StandardClassBPositionReport", "StaticDataReport", 
    "ShipStaticData", "AidsToNavigationReport", "BaseStationReport"
  ]
}
```
</details>

### AIS Data Reference Tables

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
| 14   | AIS-SART (active), MOB-AIS, EPIRB-AIS | 🆘        |
| 15   | Unusual/Reserved/Test               | ⚠️         |
</details>

<details>
<summary><b>AIS Ship Type Lookup Table</b> (click to expand)</summary>

AIS ship type codes provide a standardized classification for vessels. Common codes include:

| Code | Meaning                        |
|------|--------------------------------|
| 30   | Fishing                        |
| 31-32| Towing                         |
| 36   | Sailing                        |
| 37   | Pleasure craft                 |
| 50   | Pilot vessel                   |
| 52   | Tug                            |
| 60   | Passenger ship                 |
| 70   | Cargo ship                     |
| 80   | Tanker                         |

For a complete list, see official [IMO/AIS documentation](https://www.navcen.uscg.gov/?pageName=AISMessages#shiptype).
</details>

<details>
<summary><b>MMSI to Flag (Country) Parsing</b> (click to expand)</summary>

The first 3 digits of an MMSI (Maritime Mobile Service Identity) represent the vessel's Maritime Identification Digits (MID), which indicate the country of registration. Example MIDs:

| MMSI Prefix | Country          | Flag Emoji |
|-------------|------------------|------------|
| 366-369     | United States    | 🇺🇸        |
| 316         | Canada           | 🇨🇦        |
| 232-235     | United Kingdom   | 🇬🇧        |
| 636         | Liberia          | 🇱🇷        |

The system uses a lookup table to convert MMSI prefixes to country names and emoji flags.
</details>

## Anomaly Detection System

The project includes a basic system for detecting unusual vessel behavior patterns:

<details>
<summary><b>Anomaly Types</b> (click to expand)</summary>

| Anomaly Type | Description | Detection Method |
|--------------|-------------|------------------|
| Teleportation | Vessel position jumps impossibly far in a short time | Distance/time threshold |
| Circle Spoofing | Vessel moves in an unnaturally perfect circular path | Circular pattern detection |
| Speed Anomaly | Vessel speed changes dramatically or exceeds physical limits | Statistical deviation from typical speeds |
| Dark Period | Vessel stops transmitting for suspicious duration | Time since last update |
| Identity Swap | Vessel appears to change identity | MMSI inconsistency detection |
</details>

<details>
<summary><b>Anomaly Simulator</b> (click to expand)</summary>

The anomaly simulator (`anomaly_simulation.py`) is designed to:
- Inject synthetic AIS anomalies via backend endpoints
- Exercise the alert ticker and detection logic
- Provide a repeatable way to test detection features
</details>

<details>
<summary><b>About Circle Spoofing</b> (click to expand)</summary>

Circle spoofing is a maritime AIS anomaly in which a vessel appears to move in an unnaturally perfect circular path, often the result of deliberate manipulation to mask a vessel's true movements. For more information, see [AIS Spoofing Explained by Pole Star Global](https://www.polestarglobal.com/resources/ais-spoofing/)
</details>

## Technical Documentation

<details>
<summary><b>Backend Data Structure</b> (click to expand)</summary>

- **vessels**: Latest state for each MMSI
- **vessel_history**: List of all received reports per MMSI
- **vessel_profiles**: Rolling statistics for speed/heading
- **spatial_index**: Geospatial lookup for vessels
- **ais_message_queue**: Async queue for processing messages
</details>

<details>
<summary><b>API Endpoints</b> (click to expand)</summary>

| Endpoint                | Method | Purpose                                            |
|------------------------|--------|---------------------------------------------------|
| `/ws`                  | WS     | WebSocket for real-time updates                    |
| `/inject/telemetry`    | POST   | Inject synthetic telemetry                         |
| `/inject/teleport`     | POST   | Inject a teleportation anomaly                     |
| `/inject/dark_period`  | POST   | Inject a dark period anomaly                       |
| `/inject/identity_swap`| POST   | Inject an identity swap anomaly                     |
| `/inject/static_data`  | POST   | Inject static vessel metadata                      |
| `/reset_data`          | POST   | Clear all vessel/anomaly state                      |
| `/spatial_query`       | GET    | Query vessels in a bounding box                    |
</details>

<details>
<summary><b>Map Source and Attribution</b> (click to expand)</summary>

This project uses [Leaflet.js](https://leafletjs.com/) for interactive map rendering and [OpenStreetMap](https://www.openstreetmap.org/copyright) as the map data provider.

**Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).**
</details>

## LLM-Enabled Chat Server

This project includes an LLM-enabled chat server to provide interactive vessel and map chat capabilities using OpenAI or compatible APIs. This server is separate from the main AIS backend and must be started independently.

### Starting the Chat Server

```
uvicorn chat_enabled_server:app --reload --port 5001
```

- The chat server will be available at http://localhost:5001
- Ensure your `.env` file contains a valid OpenAI API key (e.g., `OPENAI_API_KEY=your_key_here`)
- The frontend will connect to this server for chat assistant features

## Known Issues & Future Work

<details>
<summary><b>Known Issues & Future Work</b> (click to expand)</summary>

- Dynamic testing to proxy Windsurf messages, allowing for review of the data and formats being sent to Windsurf and Codium Cloud.
- Investigate and resolve missing or unprocessed AIS data fields (e.g., vessel destination, type, dimensions) to improve data completeness and visualization.
- Containerize and scale application functions for robust, cloud-native deployment.
- Apply machine learning to enrich, classify, and detect anomalies in AIS and related maritime data streams.
- Visualize first and second order time derivatives (velocity, acceleration) for vessel movement to enable richer analytics.
- Incorporate additional normalized data sources (e.g., geospatial imaging) for cross-correlation and advanced enrichment.
- Integrate more robust error handling, logging, and testing for reliability.
- Support improved vessel type filtering, area-based spoofing/anomaly scenarios, and collaborative map annotation.
- Enhance UI/UX for alert visualization, vessel details, and user interaction (including chat).
- Enable advanced anomaly and threat detection based on use cases supported by enriched and multi-modal data sets.

</details>

## References

<details>
<summary><b>AIS Standards & References</b> (click to expand)</summary>

This project is informed by several key AIS standards and protocols:

- **International Telecommunication Union (ITU). (2014).** Recommendation ITU-R M.1371-5: Technical characteristics for an automatic identification system using time division multiple access in the VHF maritime mobile frequency band.
- **Raymond, E. S.** "AIVDM/AIVDO protocol decoding." GPSD Documentation. [Read online](https://gpsd.gitlab.io/gpsd/AIVDM.html)
- **National Marine Electronics Association.** NMEA 0183 Standard. [Specifications](https://www.nmea.org/)
</details>

## Learning with Windsurf IDE

This project served as a practical exercise to explore [Windsurf IDE](https://windsurf.com/)'s capabilities for AI-assisted development.

<details>
<summary><b>Learning Outcomes</b> (click to expand)</summary>

Through this project, we gained experience with:
- Collaborative coding between human developers and AI assistants
- Real-time feedback loops in development
- Integration of domain knowledge with technical implementation
- WebSocket communication patterns
- Geospatial data visualization

This represents our initial exploration of AI-assisted development rather than a demonstration of Windsurf's full capabilities.
</details>

<details>
<summary><b>Windsurf IDE Features Used</b> (click to expand)</summary>

- Real-time code editing and debugging
- AI collaboration for implementing features
- Running and visualizing both backend and frontend components locally
- Anomaly simulation and testing
</details>

---

### Acknowledgments

This project builds upon numerous open-source tools and standards:

- **AIS Data**: [aisstream.io](https://aisstream.io/)
- **Mapping**: [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/copyright)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **Development Environment**: [Windsurf IDE](https://windsurf.com/)

**Special thanks** to [Cerebral Valley](https://cerebralvalley.ai/), [Shield Capital](https://shieldcap.com/), and all the hackathon mentors, open-source contributors, and fellow participants who provided guidance and inspiration.

**Major contributor:** [sockcymbal](https://github.com/sockcymbal) — for key features including the interactive map chat assistant and substantial improvements to user experience.

**Project Status**: Educational prototype  
**License**: MIT
