import asyncio
import websockets
import json

async def test_ws():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBzZW50aW5lbGZsb3cuYWkiLCJyb2xlIjoiYWRtaW4iLCJ1c2VyX2lkIjoxLCJleHAiOjE3ODUzODE5MDMsInR5cGUiOiJhY2Nlc3MiLCJqdGkiOiJhNWRjZmE4MTA5ZDE1OTY3In0.tbAotnz9JHEOLN5e4C-IYf-Y48N5_LGw0VofGl37Eyw"
    uri = f"ws://127.0.0.1:8000/api/v1/ws/qa-session-99?token={token}"
    print(f"Connecting to {uri}...")
    async with websockets.connect(uri) as ws:
        print("Connected successfully!")
        for _ in range(2):
            msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
            print("Received event:", msg[:120], "...")

if __name__ == "__main__":
    asyncio.run(test_ws())
