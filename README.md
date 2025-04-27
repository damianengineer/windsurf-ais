## 📊 Technical Reference (Presentation Support)

<details>
<summary><b>AIS Navigational Status Codes</b> (click to expand)</summary>

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
<summary><b>API Endpoints Reference</b> (click to expand)</summary>

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
<summary><b>AIS Standards & References</b> (click to expand)</summary>

This project is informed by several key AIS standards and protocols:

- **International Telecommunication Union (ITU). (2014).** Recommendation ITU-R M.1371-5: Technical characteristics for an automatic identification system using time division multiple access in the VHF maritime mobile frequency band.
- **Raymond, E. S.** "AIVDM/AIVDO protocol decoding." GPSD Documentation. [Read online](https://gpsd.gitlab.io/gpsd/AIVDM.html)
- **National Marine Electronics Association.** NMEA 0183 Standard. [Specifications](https://www.nmea.org/)
</details># Maritime AIS Visualization & Anomaly Detection
## A Learning Project with Windsurf IDE

![AIS Bay Area Screenshot](screenshot.png)

## 📚 Project Context & Acknowledgments

This project was developed as an educational exercise during the National Security Hackathon, with generous support from:
- [Cerebral Valley](https://cerebralvalley.ai/) for organizing the hackathon
- [Shield Capital](https://shieldcap.com/) for their mentorship and support
- [Windsurf](https://windsurf.com/) for providing Pro subscription access during the event

The system attempts to visualize maritime Automatic Identification System (AIS) data for the San Francisco Bay Area, with a focus on exploring anomaly detection techniques. This represents an educational prototype rather than a production-ready system.

**⚠️ Important Note:** This project is provided for educational purposes only and is not intended for production use. For production maritime tracking needs, consider commercial SaaS alternatives such as [myshiptracking.com](https://www.myshiptracking.com/).

**Built upon the work of:**
- [aisstream.io](https://aisstream.io/) for providing the AIS data API
- [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/about) for mapping capabilities
- Numerous open-source AIS data processing techniques and research

## 🛠️ Project Implementation 

The prototype system consists of:

### System Components
- A FastAPI backend that processes AIS messages
- A web frontend that displays vessel positions on an interactive map
- An anomaly simulation tool for testing detection capabilities

### Technical Approach
- **Data Acquisition**: Integration with aisstream.io's WebSocket API
- **Processing Pipeline**: Backend parsing of AIS message types into structured data
- **Visualization**: Map-based representation of vessel positions and movements
- **Anomaly Detection**: Basic algorithms to identify potentially unusual vessel behavior

This work represents an early exploration rather than a comprehensive solution, with many opportunities for improvement in data processing, anomaly detection sophistication, and system architecture.

## 🧠 Windsurf IDE: Development Environment

The project provided an opportunity to explore [Windsurf IDE](https://windsurf.com/)'s capabilities for software development:

### Learning Aspects
- Exploring collaboration between developer and AI assistant
- Testing real-time feedback loops during development
- Attempting to integrate domain knowledge with technical implementation

### Educational Value
- Understanding the potential and limitations of AI assistance in coding
- Learning to articulate development requirements clearly
- Gaining experience with WebSocket communication patterns
- Practicing geospatial data visualization techniques

This project does not represent the full capabilities of Windsurf IDE, but rather our initial exploration as beginners with the platform.

## 🔮 Lessons Learned & Future Work

### What We Learned
- Practical challenges in handling live maritime data streams
- Basic approaches to anomaly detection in movement patterns
- Development workflow considerations when using AI assistance

### Future Improvements
Building on this initial prototype, future work might include:
- **Improved Data Security**: Secure storage for API credentials
- **Additional Data Sources**: Integration with supplementary maritime information
- **Code Quality**: Comprehensive testing and refactoring
- **Enhanced Architecture**: Restructuring for maintainability
- **Standards Compliance**: Integration with established AIS parser libraries

### Quick Demo Guide
For demonstration purposes:
```sh
pip install -r requirements.txt
uvicorn ais_websocket_server:app --reload
# Open http://localhost:8000/static/ais_map.html
```

---

### References & Acknowledgments
This project builds upon numerous open-source tools and standards:

- **AIS Data**: [aisstream.io](https://aisstream.io/)
- **Mapping**: [Leaflet.js](https://leafletjs.com/) and [OpenStreetMap](https://www.openstreetmap.org/copyright)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/)
- **Development Environment**: [Windsurf IDE](https://windsurf.com/)

**Special thanks** to all the hackathon mentors, open-source contributors, and fellow participants who provided guidance and inspiration.

**Project Status**: Educational prototype
**License**: MIT