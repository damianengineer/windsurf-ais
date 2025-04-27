import os
import asyncio
import json
from dotenv import load_dotenv
import websockets

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
API_KEY = os.getenv("AIS_STREAM_KEY")
print("Loaded API_KEY:", API_KEY)
assert API_KEY, "API_KEY not loaded from .env"

# Bounding box for the larger San Francisco Bay Area
# Format: [[lat1, lon1], [lat2, lon2]]
BBOX_SF_BAY = [[38.2, -123.0], [37.2, -121.5]]

WS_URL = "wss://stream.aisstream.io/v0/stream"

async def stream_ais():
    subscription_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [BBOX_SF_BAY]
    }
    async with websockets.connect(WS_URL) as ws:
        # Send subscription message within 3 seconds
        await ws.send(json.dumps(subscription_msg))
        print("Subscribed to AIS stream for SF Bay Area.")
        async for message in ws:
            print(message)

if __name__ == "__main__":
    asyncio.run(stream_ais())
