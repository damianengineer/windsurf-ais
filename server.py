import os
import json
from dotenv import load_dotenv
import websockets
import asyncio
from flask import Flask, request, jsonify, send_from_directory
import requests
from concurrent.futures import ThreadPoolExecutor
import logging

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv("AIS_STREAM_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
executor = ThreadPoolExecutor(max_workers=4)

# Add route for serving static files like before
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# Vessel data cache
vessel_data_cache = {}

# Websocket clients
connected_clients = set()

async def forward_ais_data():
    """Forward AIS data from AISStream.io to connected websocket clients"""
    # Bounding box for the San Francisco Bay Area
    BBOX_SF_BAY = [[38.2, -123.0], [37.2, -121.5]]
    WS_URL = "wss://stream.aisstream.io/v0/stream"
    
    subscription_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [BBOX_SF_BAY]
    }
    
    while True:
        try:
            logger.info("Connecting to AIS stream...")
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps(subscription_msg))
                logger.info("Subscribed to AIS stream for SF Bay Area")
                
                async for message in ws:
                    data = json.loads(message)
                    
                    # Process the message
                    if "history_point" in data:
                        hp = data["history_point"]
                        mmsi = hp["meta"]["MMSI"] if hp.get("meta") else hp.get("mmsi")
                        
                        if mmsi:
                            # Update the vessel cache
                            vessel_data_cache[mmsi] = data
                    
                    # Forward the message to all connected clients
                    if connected_clients:
                        await asyncio.gather(
                            *[client.send(message) for client in connected_clients.copy()]
                        )
        except Exception as e:
            logger.error(f"Error in AIS stream: {e}")
            await asyncio.sleep(5)  # Wait before reconnecting

async def websocket_handler(websocket, path):
    """Handle websocket connections from clients"""
    # Log the connection and path
    logger.info(f"Client connected: {websocket.remote_address}, Path: {path}")
    
    # Add to connected clients
    connected_clients.add(websocket)
    
    try:
        # Send a welcome message to confirm the connection is working
        await websocket.send(json.dumps({"status": "connected", "message": "WebSocket connection established"}))
        
        # Keep the connection open and waiting for close
        await websocket.wait_closed()
    except Exception as e:
        logger.error(f"Websocket error: {e}")
    finally:
        connected_clients.remove(websocket)
        logger.info(f"Client disconnected: {websocket.remote_address}")

@app.route('/')
def index():
    return send_from_directory('.', 'ais_map.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests from the frontend"""
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    query = data['query']
    map_bounds = data.get('mapBounds', {})
    visible_vessels = data.get('visibleVessels', [])
    
    # Use ThreadPoolExecutor to avoid blocking the main thread
    def process_query():
        try:
            # Prepare context for the LLM
            vessel_context = []
            for vessel in visible_vessels:
                vessel_context.append({
                    "mmsi": vessel.get("mmsi"),
                    "name": vessel.get("name", "Unknown"),
                    "position": vessel.get("position"),
                    "speed": vessel.get("speed"),
                    "heading": vessel.get("heading")
                })
            
            # Call OpenAI API (or your preferred LLM provider)
            if OPENAI_API_KEY:
                response = call_openai_api(query, vessel_context, map_bounds)
            else:
                response = {"response": "API key not configured. Please add your OPENAI_API_KEY to the .env file."}
            
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {"response": f"Error: {str(e)}"}
    
    # Run the query processing in a separate thread
    result = executor.submit(process_query).result()
    return jsonify(result)

def call_openai_api(query, vessel_context, map_bounds):
    """Call OpenAI API to process the query"""
    try:
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
            "temperature":.2,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
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

async def start_server():
    """Start the server with both Flask and websocket handlers"""
    # Start the websocket server
    websocket_server = await websockets.serve(
        websocket_handler, 
        "0.0.0.0", 
        8001
    )
    
    # Start the AIS data forwarding task
    ais_task = asyncio.create_task(forward_ais_data())
    
    # Keep the server running
    await asyncio.gather(
        websocket_server.wait_closed(),
        ais_task
    )

if __name__ == "__main__":
    # Create a new event loop for running both Flask and websockets
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start Flask in a separate thread
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False))
    flask_thread.daemon = True
    flask_thread.start()
    
    # Start the websocket server in the main thread
    logger.info("Starting server...")
    try:
        loop.run_until_complete(start_server())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        loop.close()
