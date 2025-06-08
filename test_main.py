from fastapi.testclient import TestClient
from pydantic import UUID4
from main import app

client = TestClient(app)

def test_create_guest():
    response = client.post("/guest")
    assert response.status_code == 200
    response = response.json()
    guest_session_cookie = response.cookies.get("guest_session")
    guest_id_cookie = response.cookies.get("guest_id")

    assert "id" in response
    assert "username" in response
    assert isinstance(response["id"], str), "ID is not a string"
    assert UUID4(response["id"]), "ID is not a valid UUID"
    assert isinstance(response["username"], str)

def test_create_guest_gamesession():
    response = client.post('/guest/gamesession', headers={"X-Token": "coneofsilence"})
    assert response.status_code == 200