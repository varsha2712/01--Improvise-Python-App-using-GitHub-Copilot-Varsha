"""Exercise the API through FastAPI's TestClient, without a running server."""

import hashlib

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_welcome(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome, Varsha! Your Text Token API is ready."
    }


def test_generate_single_token(client):
    response = client.get("/generate", params={"text": "hello"})
    assert response.status_code == 200
    assert response.json() == {
        "token": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    }


def test_generate_requires_query_text(client):
    assert client.get("/generate").status_code == 422


@pytest.mark.parametrize(
    ("text", "tokens"),
    [
        ("hello world", ["hello", "world"]),
        ("  hello\tworld\n", ["hello", "world"]),
        ("", []),
        (" \t\n", []),
        ("hello, world!", ["hello,", "world!"]),
        ("caf\u00e9\u2003\u4f60\u597d", ["caf\u00e9", "\u4f60\u597d"]),
    ],
)
def test_generate_json(client, text, tokens):
    response = client.post("/generate", json={"text": text})
    assert response.status_code == 200
    assert response.json() == {
        "tokens": tokens,
        "checksum": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    assert response.json()["checksum"] == client.get(
        "/generate", params={"text": text}
    ).json()["token"]


def test_checksum_preserves_whitespace(client):
    plain = client.post("/generate", json={"text": "hello world"}).json()
    padded = client.post("/generate", json={"text": " hello  world "}).json()
    assert plain["tokens"] == padded["tokens"]
    assert plain["checksum"] != padded["checksum"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"text": None}, {"text": 123}, {"text": True}, {"text": []},
     {"text": {}}, {"text": "hello", "extra": "not allowed"}, ["hello"]],
)
def test_generate_rejects_invalid_json_fields(client, payload):
    assert client.post("/generate", json=payload).status_code == 422


def test_generate_rejects_missing_body(client):
    assert client.post("/generate").status_code == 422


def test_generate_rejects_malformed_json(client):
    response = client.post(
        "/generate", content='{"text":', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_openapi_documents_json_endpoint(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    operation = schema["paths"]["/generate"]["post"]
    assert operation["requestBody"]["required"] is True
    assert "application/json" in operation["requestBody"]["content"]
    assert schema["components"]["schemas"]["TextRequest"]["required"] == ["text"]
    assert schema["components"]["schemas"]["TextRequest"]["additionalProperties"] is False
