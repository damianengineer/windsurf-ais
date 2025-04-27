#!/bin/bash

# Start the original AIS WebSocket server in the background
echo "Starting AIS WebSocket server..."
uvicorn ais_websocket_server:app --reload --port 8000 &
AIS_PID=$!

# Wait a moment to make sure the first server starts
sleep 2

# Start the Chat API server on a different port
echo "Starting Chat API server..."
uvicorn chat_enabled_server:app --reload --port 5001 &
CHAT_PID=$!

# Function to handle script termination
cleanup() {
  echo "Shutting down servers..."
  kill $AIS_PID
  kill $CHAT_PID
  exit 0
}

# Set trap for clean shutdown
trap cleanup INT TERM

echo "Both servers are running!"
echo "Access the map with chat at: http://localhost:8000/static/ais_map.html"
echo "The chat API is available at: http://localhost:5001/api/chat"
echo "Press Ctrl+C to stop both servers"

# Keep script running
wait
