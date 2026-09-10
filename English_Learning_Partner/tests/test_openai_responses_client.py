import json

import pytest
import requests

from english_learning_partner.domain.errors import LocalModelConnectionError, LocalModelResponseError
from english_learning_partner.services.openai_responses_client import OpenAIResponsesClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error
        self.requests: list[tuple[str, dict, int]] = []

    def post(self, url: str, json: dict, timeout: int):
        self.requests.append((url, json, timeout))
        if self.error:
            raise self.error
        return self.response


def test_extracts_json_from_responses_output() -> None:
    client = OpenAIResponsesClient("http://localhost:23333/api/openai/v1")
    session = FakeSession(FakeResponse({"output": [{"type": "message", "content": [{"type": "output_text", "text": '```json\n{"translation":"跟进"}\n```'}]}]}))
    client._session = session

    result = client.generate_json("gpt-5.4", "test")

    assert result == {"translation": "跟进"}
    assert session.requests[0][0].endswith("/api/openai/v1/responses")
    assert session.requests[0][1]["input"][1]["content"] == "test"


def test_converts_connectivity_error() -> None:
    client = OpenAIResponsesClient("http://localhost:23333/api/openai/v1")
    client._session = FakeSession(error=requests.ConnectionError())

    with pytest.raises(LocalModelConnectionError):
        client.generate_json("gpt-5.4", "test")


def test_rejects_missing_text_output() -> None:
    client = OpenAIResponsesClient("http://localhost:23333/api/openai/v1")
    client._session = FakeSession(FakeResponse({"output": []}))

    with pytest.raises(LocalModelResponseError):
        client.generate_json("gpt-5.4", "test")
