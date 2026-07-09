import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.websocket.manager import ws_connection_manager
from app.websocket.handlers import handle_client_message
from app.models.models import User
from app.core.security import hash_password

@pytest.fixture(autouse=True)
def reset_ws_manager():
    # Clear ConnectionManager dictionaries before each test to guarantee isolation
    ws_connection_manager.active_sockets.clear()
    ws_connection_manager.user_sessions.clear()
    ws_connection_manager.session_users.clear()
    ws_connection_manager.session_subscriptions.clear()
    ws_connection_manager.incident_subscribers.clear()
    ws_connection_manager.session_filters.clear()
    ws_connection_manager.offline_queues.clear()

@pytest.mark.asyncio
async def test_websocket_ping_keepalive():
    # Mock WebSocket connection
    ws_mock = AsyncMock()
    ws_connection_manager.active_sockets["sess-1"] = ws_mock
    
    # Process ping
    ping_payload = json.dumps({"action": "ping"})
    await handle_client_message("sess-1", ping_payload)
    
    # Assert socket got a pong back
    ws_mock.send_text.assert_called_once()
    sent_data = json.loads(ws_mock.send_text.call_args[0][0])
    assert sent_data["type"] == "pong"

@pytest.mark.asyncio
async def test_websocket_oversized_payload():
    ws_mock = AsyncMock()
    ws_connection_manager.active_sockets["sess-1"] = ws_mock
    
    # Payload over 1MB (1,048,577 bytes)
    oversized = "a" * (1024 * 1024 + 1)
    await handle_client_message("sess-1", oversized)
    
    # Assert it was rejected and send_text was not called
    ws_mock.send_text.assert_not_called()

@pytest.mark.asyncio
async def test_websocket_concurrency_rate_limit():
    user_id = 99
    
    # Connect 5 sessions successfully
    for i in range(5):
        ws_mock = AsyncMock()
        session_id = f"sess-{i}"
        await ws_connection_manager.connect(ws_mock, user_id, session_id)
        assert session_id in ws_connection_manager.active_sockets
        
    # Attempt 6th session
    ws_mock_6 = AsyncMock()
    await ws_connection_manager.connect(ws_mock_6, user_id, "sess-6")
    
    # Assert connection closed with code 4003 (Max concurrent sessions exceeded)
    ws_mock_6.close.assert_called_with(code=4003, reason="Max concurrent sessions exceeded")
    assert "sess-6" not in ws_connection_manager.active_sockets

@pytest.mark.asyncio
async def test_websocket_offline_queueing():
    user_id = 100
    msg_data = {"alert": "CpuSpike"}
    
    # Send message when user is offline (no active sessions)
    delivered = await ws_connection_manager.send_to_user_local(user_id, "CriticalAlert", msg_data)
    assert delivered is False
    
    # Verify queued in offline queue
    assert user_id in ws_connection_manager.offline_queues
    assert len(ws_connection_manager.offline_queues[user_id]) == 1
    
    # Connect session
    ws_mock = AsyncMock()
    await ws_connection_manager.connect(ws_mock, user_id, "sess-online")
    
    # Verify mock socket received the queued message
    ws_mock.send_text.assert_called_once()
    sent_data = json.loads(ws_mock.send_text.call_args[0][0])
    assert sent_data["type"] == "CriticalAlert"
    assert sent_data["data"]["alert"] == "CpuSpike"


@pytest.mark.asyncio
async def test_websocket_incident_subscription_and_broadcast():
    ws_mock = AsyncMock()
    user_id = 101
    session_id = "sess-sub"
    
    # Connect user
    await ws_connection_manager.connect(ws_mock, user_id, session_id)
    
    # Subscribe to incident 42
    subscribe_payload = json.dumps({"action": "subscribe", "incident_id": 42})
    await handle_client_message(session_id, subscribe_payload)
    
    # Verify subscription state
    assert session_id in ws_connection_manager.incident_subscribers[42]
    assert 42 in ws_connection_manager.session_subscriptions[session_id]
    
    # Broadcast message to incident 42
    await ws_connection_manager.broadcast_incident_local(42, "AgentActivity", {"progress": 75})
    
    # Assert mock socket received the broadcast payload
    ws_mock.send_text.assert_called_once()
    sent_data = json.loads(ws_mock.send_text.call_args[0][0])
    assert sent_data["type"] == "AgentActivity"
    assert sent_data["data"]["progress"] == 75
