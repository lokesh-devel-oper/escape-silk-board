import asyncio

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.store import InMemorySessionStore


def make_client() -> TestClient:
    return TestClient(create_app(InMemorySessionStore()))


def test_health_and_session_lifecycle():
    with make_client() as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        created = client.post("/api/game/new", json={"player_name": "Maya", "random_seed": 99})
        assert created.status_code == 201
        session_id = created.json()["session_id"]

        fetched = client.get(f"/api/game/state/{session_id}")
        assert fetched.status_code == 200
        assert fetched.json()["player_name"] == "Maya"

        reset = client.post(f"/api/game/reset/{session_id}")
        assert reset.status_code == 200
        assert reset.json()["session_id"] == session_id
        assert reset.json()["turn_count"] == 0


def test_world_and_context_are_backend_driven():
    with make_client() as client:
        world = client.get("/api/world")
        assert world.status_code == 200
        payload = world.json()
        assert payload["version"] == "1.0"
        assert {location["id"] for location in payload["locations"]} >= {
            "silk_board",
            "kempegowda_international_airport",
        }
        assert any(
            route["origin"] == "silk_board" and route["destination"] == "madiwala"
            for route in payload["routes"]
        )

        state = client.post("/api/game/new", json={"player_name": "Dynamic"}).json()
        context = client.get(f"/api/game/context/{state['session_id']}")
        assert context.status_code == 200
        actions = context.json()["available_actions"]
        walk_targets = {
            action["target"] for action in actions if action["action_id"] == "walk"
        }
        assert walk_targets == {"btm_layout", "madiwala"}


def test_development_loopback_origins_pass_cors_preflight():
    with make_client() as client:
        for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
            response = client.options(
                "/api/game/new",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )
            assert response.status_code == 200
            assert response.headers["access-control-allow-origin"] == origin


def test_missing_session_is_404():
    with make_client() as client:
        response = client.get("/api/game/state/missing")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_two_sessions_remain_isolated():
    with make_client() as client:
        first = client.post("/api/game/new", json={"player_name": "One"}).json()
        second = client.post("/api/game/new", json={"player_name": "Two"}).json()
        response = client.post("/api/game/action", json={
            "session_id": first["session_id"],
            "player_input": "sell the samosa",
            "request_id": "trade-1",
        })
        assert response.status_code == 200
        first_state = client.get(f"/api/game/state/{first['session_id']}").json()
        second_state = client.get(f"/api/game/state/{second['session_id']}").json()
    assert first_state["cash"] == 530
    assert second_state["cash"] == 500
    assert second_state["inventory"] == ["cold_samosa"]


def test_duplicate_request_does_not_double_spend_or_advance():
    with make_client() as client:
        state = client.post("/api/game/new", json={"player_name": "Ida"}).json()
        payload = {
            "session_id": state["session_id"],
            "player_input": "take the bus",
            "request_id": "same-request",
        }
        first = client.post("/api/game/action", json=payload).json()
        second = client.post("/api/game/action", json=payload).json()
    assert not first["duplicate"]
    assert second["duplicate"]
    assert second["state"]["cash"] == 450
    assert second["state"]["turn_count"] == 1
    assert second["state"]["current_time"] == first["state"]["current_time"]


def test_reused_request_id_with_different_input_is_409():
    with make_client() as client:
        state = client.post("/api/game/new", json={"player_name": "Conflict"}).json()
        first = client.post("/api/game/action", json={
            "session_id": state["session_id"],
            "player_input": "take the bus",
            "request_id": "reused-id",
        })
        conflict = client.post("/api/game/action", json={
            "session_id": state["session_id"],
            "player_input": "take a cab",
            "request_id": "reused-id",
        })
        final = client.get(f"/api/game/state/{state['session_id']}").json()
    assert first.status_code == 200
    assert conflict.status_code == 409
    assert "different player input" in conflict.json()["detail"]
    assert final["turn_count"] == 1
    assert final["cash"] == 450


def test_concurrent_requests_are_serialized():
    async def scenario():
        store = InMemorySessionStore()
        state = await store.create("Concurrent", random_seed=1)
        first, second = await asyncio.gather(
            store.process(state.session_id, "sell the samosa", "one"),
            store.process(state.session_id, "sell the samosa", "two"),
        )
        final = await store.get(state.session_id)
        return first, second, final

    first, second, final = asyncio.run(scenario())
    assert sum(result.accepted for result in (first, second)) == 1
    assert final.cash == 530
    assert final.turn_count == 1
    assert "cold_samosa" not in final.inventory


def test_request_validation_limits_input():
    with make_client() as client:
        state = client.post("/api/game/new", json={"player_name": "Valid"}).json()
        response = client.post("/api/game/action", json={
            "session_id": state["session_id"],
            "player_input": "x" * 501,
            "request_id": "too-long",
        })
    assert response.status_code == 422

