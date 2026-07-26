import pytest
import json
from unittest.mock import AsyncMock
from app.websocket.manager import ws_connection_manager
from app.websocket.handlers import handle_client_message

@pytest.fixture(autouse=True)
def reset_ws_manager():
    ws_connection_manager.active_sockets.clear()
    ws_connection_manager.user_sessions.clear()
    ws_connection_manager.session_users.clear()
    ws_connection_manager.session_subscriptions.clear()
    ws_connection_manager.incident_subscribers.clear()
    ws_connection_manager.session_filters.clear()
    ws_connection_manager.offline_queues.clear()

@pytest.mark.asyncio
async def test_websocket_connection_broadcast_disconnect_reconnect():
    """Integration test verifying WebSocket connection, event broadcast, disconnect cleanup, and reconnection offline queue delivery."""
    user_id = 201
    session_1 = "sess-client-1"
    ws_mock_1 = AsyncMock()

    # 1. Connect first session
    await ws_connection_manager.connect(ws_mock_1, user_id, session_1)
    assert session_1 in ws_connection_manager.active_sockets
    assert user_id in ws_connection_manager.user_sessions

    # 2. Subscribe to incident 105 & set event filter
    sub_msg = json.dumps({"action": "subscribe", "incident_id": 105})
    await handle_client_message(session_1, sub_msg)
    assert session_1 in ws_connection_manager.incident_subscribers[105]

    # 3. Broadcast event to subscribed incident
    event_data = {"incident_id": 105, "status": "ANALYZING", "step": "RCA_INGEST"}
    await ws_connection_manager.broadcast_incident_local(105, "IncidentUpdate", event_data)

    ws_mock_1.send_text.assert_called_once()
    payload = json.loads(ws_mock_1.send_text.call_args[0][0])
    assert payload["type"] == "IncidentUpdate"
    assert payload["data"]["step"] == "RCA_INGEST"

    # 4. Disconnect session_1
    ws_connection_manager.disconnect(session_1)
    assert session_1 not in ws_connection_manager.active_sockets

    assert session_1 not in ws_connection_manager.session_subscriptions

    # 5. Broadcast while offline — verify message is queued in offline queue
    offline_event = {"incident_id": 105, "status": "EXECUTED"}
    delivered = await ws_connection_manager.send_to_user_local(user_id, "IncidentExecuted", offline_event)
    assert delivered is False
    assert len(ws_connection_manager.offline_queues[user_id]) == 1

    # 6. Reconnect with new session_2 — verify offline queue flush
    session_2 = "sess-client-2"
    ws_mock_2 = AsyncMock()
    await ws_connection_manager.connect(ws_mock_2, user_id, session_2)

    assert session_2 in ws_connection_manager.active_sockets
    ws_mock_2.send_text.assert_called_once()
    reconnect_payload = json.loads(ws_mock_2.send_text.call_args[0][0])
    assert reconnect_payload["type"] == "IncidentExecuted"
    assert reconnect_payload["data"]["status"] == "EXECUTED"
    assert len(ws_connection_manager.offline_queues.get(user_id, [])) == 0

