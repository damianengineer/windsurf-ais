from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Body, Query
import asyncio
import os
import json
from dotenv import load_dotenv
import websockets
import sys
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime, timedelta
import math
import numpy as np
import logging
import requests
from fastapi.middleware.cors import CORSMiddleware

# Import your existing code components
# Rather than importing from the module which can cause circular imports,
# we'll use simplified versions of the key functions we need

def parse_mmsi(mmsi):
    """Simplified parse MMSI function"""
    return {"mmsi": mmsi, "flag": None, "mid": None}
    
def get_grid_cell(lat, lon):
    """Simplified grid cell function"""
    lat_idx = int(lat / GRID_SIZE)
    lon_idx = int(lon / GRID_SIZE)
    return (lat_idx, lon_idx)

# Define a simplified process_ais_message function that just forwards the message
async def process_ais_message(msg):
    """Process and forward AIS message"""
    # Simply record it for forwarding to clients
    return msg

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
API_KEY = os.getenv("AIS_STREAM_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BBOX_SF_BAY = [[38.2, -123.0], [37.2, -121.5]]
WS_URL = "wss://stream.aisstream.io/v0/stream"

DEBUG_FIRST_ONLY = "--debug-first" in sys.argv

app = FastAPI()

# Add CORS middleware for API calls - be explicit about allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5001",
        "http://127.0.0.1:5001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Serve static files
app.mount("/static", StaticFiles(directory=".", html=True), name="static")

# Variables from your original server
vessels = {}
vessel_history = {}
vessel_history_index = {}
spatial_index = {}
GRID_SIZE = 0.1
clients = set()
vessel_profiles = {}
PROFILE_WINDOW = 100
ais_message_queue = None

# Chat data store
vessel_data_cache = {}

# AIS Stream Handling
async def ais_stream_task():
    """Connect to AIS stream and forward data to clients"""
    subscription_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [BBOX_SF_BAY]
    }
    
    retry_delay = 5  # Initial retry delay in seconds
    max_retry_delay = 60  # Maximum retry delay in seconds
    
    while True:
        try:
            logger.info("Connecting to AIS stream...")
            async with websockets.connect(WS_URL) as ws:
                subscription_json = json.dumps(subscription_msg)
                logger.info(f"Sending subscription: {subscription_json}")
                await ws.send(subscription_json)
                logger.info("Subscribed to AIS stream for SF Bay Area")
                
                # Reset retry delay on successful connection
                retry_delay = 5
                
                message_count = 0
                async for message in ws:
                    message_count += 1
                    if message_count % 10 == 0:
                        logger.info(f"Received {message_count} messages so far")
                    
                    # Parse message and then stringify in a consistent way
                    try:
                        data = json.loads(message)
                        logger.debug(f"Received AIS message type: {list(data.keys())}")
                    except Exception as e:
                        logger.error(f"Failed to parse message: {e}")
                    
                    # Process message through existing pipeline
                    await process_ais_message(data)
                    
                    # Update vessel data cache for chat interface
                    if "history_point" in data:
                        hp = data["history_point"]
                        # Extract vessel data for the chat interface
                        mmsi = hp["meta"]["MMSI"] if hp.get("meta") else hp.get("mmsi")
                        if mmsi:
                            # Store essential data for the chat interface
                            lat, lon, sog, heading = None, None, None, None
                            name = None
                            
                            # Extract position data based on message type
                            if hp.get("raw_position_report"):
                                rpr = hp["raw_position_report"]
                                lat = rpr.get("Latitude")
                                lon = rpr.get("Longitude")
                                sog = rpr.get("Sog")
                                heading = rpr.get("TrueHeading", rpr.get("Cog"))
                            elif hp.get("raw_standard_class_b_position_report"):
                                rscbpr = hp["raw_standard_class_b_position_report"]
                                lat = rscbpr.get("Latitude")
                                lon = rscbpr.get("Longitude")
                                sog = rscbpr.get("Sog")
                                heading = rscbpr.get("TrueHeading", rscbpr.get("Cog"))
                            
                            # Extract name from various possible locations
                            name = hp.get("ship_name")
                            if not name and hp.get("meta"):
                                name = hp["meta"].get("ShipName")
                            if not name and hp.get("raw_static_data"):
                                name = hp["raw_static_data"].get("ShipName")
                            
                            # Update the vessel data cache
                            vessel_data_cache[mmsi] = {
                                "mmsi": mmsi,
                                "name": name or "Unknown Vessel",
                                "position": [lat, lon] if lat is not None and lon is not None else None,
                                "speed": float(sog) if sog is not None else None,
                                "heading": heading,
                                "lastUpdate": datetime.utcnow().isoformat(),
                                "raw_data": hp
                            }
                    
                    # Forward to all connected clients as a properly formatted string
                    if clients:
                        # Take a closer look at the message content for debugging
                        if 'history_point' in data:
                            mmsi = None
                            if 'meta' in data['history_point'] and 'MMSI' in data['history_point']['meta']:
                                mmsi = data['history_point']['meta']['MMSI']
                            logger.info(f"Found AIS data for MMSI: {mmsi}")
                        
                        # Convert data to a consistent JSON string format
                        json_str = json.dumps(data)
                        logger.debug(f"Forwarding to {len(clients)} clients")
                        try:
                            await asyncio.gather(
                                *[client.send_text(json_str) for client in clients.copy()]
                            )
                        except Exception as e:
                            logger.error(f"Error forwarding to clients: {e}")
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"AIS stream connection closed: {e}")
        except Exception as e:
            logger.error(f"Error in AIS stream: {e}")
        
        # Exponential backoff for retry
        logger.info(f"Retrying connection in {retry_delay} seconds...")
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, max_retry_delay)

# WebSocket endpoint for clients
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        logger.info(f"Client connected: {websocket.client.host}")
        
        # Log the client connection
        logger.info(f"Currently connected clients: {len(clients)}")
        
        # Keep connection open
        while True:
            # Wait for messages from the client (not used in this implementation)
            # but helps to detect disconnection
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {websocket.client.host}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket)

# API endpoint for chat interface
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Handle chat queries from the frontend"""
    try:
        # Log the incoming request
        logger.info("Received chat API request")
        
        # Get request data
        data = await request.json()
        logger.info(f"Request data: {json.dumps(data)[:200]}...")
        
        if not data or "query" not in data:
            logger.error("Invalid request: missing query")
            return JSONResponse({"error": "Invalid request"}, status_code=400)
        
        query = data["query"]
        logger.info(f"Processing query: {query}")
        map_bounds = data.get("mapBounds", {})
        visible_vessels = data.get("visibleVessels", [])
        
        # If no visible vessels provided, use vessels from data cache in current map bounds
        if not visible_vessels and map_bounds:
            try:
                sw = map_bounds.get("_southWest", {})
                ne = map_bounds.get("_northEast", {})
                min_lat = sw.get("lat")
                min_lon = sw.get("lng")
                max_lat = ne.get("lat")
                max_lon = ne.get("lng")
                
                if all(x is not None for x in [min_lat, min_lon, max_lat, max_lon]):
                    # Filter vessels in the current map bounds
                    visible_vessels = [
                        vessel for vessel in vessel_data_cache.values()
                        if vessel.get("position") and
                        min_lat <= vessel["position"][0] <= max_lat and
                        min_lon <= vessel["position"][1] <= max_lon
                    ][:50]  # Limit to 50 vessels
            except Exception as e:
                logger.error(f"Error filtering vessels by map bounds: {e}")
        
        # Call OpenAI API
        response = await call_openai_api(query, visible_vessels, map_bounds)
        return JSONResponse(response)
    
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return JSONResponse({"response": f"Error: {str(e)}"}, status_code=500)

async def call_openai_api(query, vessel_context, map_bounds):
    """Call OpenAI API to process the query"""
    try:
        # First check if API key is configured
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not found in environment variables")
            return {"response": "I'm sorry, but my connection to the language model is not configured. Please add your OpenAI API key to the .env file."}
        # Create a system message with context about the map and vessels
        system_message = f"""
You are an AIS Map Assistant, helping users interact with real-time maritime vessel data.
The user is viewing a map of the San Francisco Bay Area.

Current map boundaries: {json.dumps(map_bounds)}

There are {len(vessel_context)} visible vessels on the map currently.
Here's data about some of these vessels:
{json.dumps(vessel_context[:10], indent=2)}

Respond to the user's query about the AIS data. If relevant, you can recommend actions like:
- Focusing on specific vessels (providing their MMSI)
- Highlighting vessels that match certain criteria
- Explaining maritime terminology
- Analyzing vessel patterns or unusual behavior

Keep responses concise, informative, and helpful.
"""

        # Log that we're calling OpenAI
        logger.info("Calling OpenAI API...")
        
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        payload = {
            "model": "gpt-4o",  # Or your preferred model
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            "temperature": 0.2,
            "max_tokens": 500
        }
        
        logger.info("Sending request to OpenAI API")
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        logger.info(f"OpenAI API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            text_response = result["choices"][0]["message"]["content"]
            
            # Extract actions if present (assuming the LLM might include JSON-formatted actions)
            actions = []
            try:
                # Check if the response contains a JSON block with actions
                if "```json" in text_response and "```" in text_response:
                    json_block = text_response.split("```json")[1].split("```")[0].strip()
                    action_data = json.loads(json_block)
                    if isinstance(action_data, dict) and "actions" in action_data:
                        actions = action_data["actions"]
                        # Remove the JSON block from the text response
                        text_response = text_response.replace(f"```json{json_block}```", "").strip()
            except Exception as e:
                logger.error(f"Error parsing actions: {e}")
            
            return {
                "response": text_response,
                "actions": actions
            }
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return {"response": "I'm having trouble connecting to my knowledge base. Please try again later."}
    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return {"response": "An error occurred while processing your request."}

# Default route to serve the HTML file
@app.get("/")
async def read_root():
    return HTMLResponse(open("ais_map.html").read())

# Startup event to initialize the AIS stream task
@app.on_event("startup")
async def startup_event():
    # Log API key status (partially masked for security)
    if API_KEY:
        masked_key = API_KEY[:5] + "*****" + API_KEY[-5:]
        logger.info(f"Using AIS Stream API key: {masked_key}")
    else:
        logger.error("No AIS_STREAM_KEY found in .env file!")
    
    # Start the AIS data forwarding task
    ais_task = asyncio.create_task(ais_stream_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
