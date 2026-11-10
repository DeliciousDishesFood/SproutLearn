"""P2 Jev 测试：schema、双路、阈值边界、score 归一。"""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.llm.jev_client import JevAnswer, JevClient, JevUnavailable

FAKE_KEY = "test-key-not-real"
STATE = "题干：1+1\n标准答案：2\n学生答案：2"
QUESTIONS = {"q1": {"type": "noul", "instructions": "等价?", "criteria": {"true": "是", "false": "否"}}}
ANSWER_BODY = {
    "model": "JevK5-V0.3",
    "answers": {
        "q1": {
            "type": "noul",
            "confidence": 0.9135,
            "noul": 0.9135,
            "probabilities": {"true": 0.9135, "false": 0.0865},
        }
    },
    "usage": {"input_tokens": 12, "output_tokens": 0},
    "latency_ms": 10.5,
}


def _client(handler):
    return JevClient(
        enabled=True,
        base_url="https://jev.example.test",
        gateway_url="https://gateway.example.test/3627-1",
        appkey=FAKE_KEY,
        model="JevK5-V0.3",
        timeout_seconds=2,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_jev_bearer_schema_and_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json=ANSWER_BODY)

    result = _client(handler).evaluate(state=STATE, questions=QUESTIONS, transport="bearer")
    payload = seen["payload"]
    assert "/v1/systemone" in seen["url"]
    assert seen["auth"] == f"Bearer {FAKE_KEY}"
    assert payload["state"] == STATE
    assert payload["questions"] == QUESTIONS
    assert "messages" not in payload
    assert result.answers["q1"].as_bool(0.85) is True
    assert result.answers["q1"].confidence == 0.9135
    assert "test-key-not-real" not in json.dumps(result.raw, ensure_ascii=False)


def test_jev_gateway_uses_appkey_query_and_not_messages():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json=ANSWER_BODY)

    result = _client(handler).evaluate(state=STATE, questions=QUESTIONS, transport="gateway")
    assert "appKey=" in seen["url"]
    assert FAKE_KEY in seen["url"]
    assert "messages" not in seen["payload"]
    assert result.transport == "gateway"


def test_jev_auto_falls_back_to_gateway():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "/v1/systemone" in str(request.url):
            return httpx.Response(500, json={"error": "server"})
        return httpx.Response(200, json=ANSWER_BODY)

    result = _client(handler).evaluate(state=STATE, questions=QUESTIONS, transport="auto")
    assert len(calls) == 2
    assert result.transport == "gateway"


def test_jev_noul_threshold_boundary_0850_true_0849_false():
    assert JevAnswer(key="q", type="noul", confidence=0.85, noul=0.850).as_bool(0.85) is True
    assert JevAnswer(key="q", type="noul", confidence=0.849, noul=0.849).as_bool(0.85) is False


def test_jev_score_to_full_matches_contract_sample():
    assert JevAnswer(key="q", type="score", confidence=1.0, score=1.5535).score_to_full(2) == 1.55
    assert JevAnswer(key="q", type="score", confidence=1.0, score=0.77675).score_to_full(2) == 1.55


def test_jev_disabled_is_unavailable():
    client = JevClient(
        enabled=False,
        base_url="https://jev.example.test",
        gateway_url="https://gateway.example.test/3627-1",
        appkey=FAKE_KEY,
        model="JevK5-V0.3",
        timeout_seconds=2,
    )
    with pytest.raises(JevUnavailable):
        client.evaluate(state=STATE, questions=QUESTIONS)
