import httpx
import pytest
import respx
from httpx import Response

from app.config import BridgeConfig
from app.hue_client import BridgeUnreachable, _bri_to_pct, _bridge_request, _pct_to_bri, _request_bridge

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


@respx.mock
async def test_write_success_list_does_not_raise():
    respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/bri": 100}}])
    )

    result = await _request_bridge(
        "192.168.x.x", "test-api-key", "lights/1/state", method="PUT", json_body={"bri": 100}
    )

    assert result == [{"success": {"/lights/1/state/bri": 100}}]


@respx.mock
async def test_write_error_list_raises_bridge_unreachable():
    respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"error": {"description": "parameter not available"}}])
    )

    with pytest.raises(BridgeUnreachable, match="parameter not available"):
        await _request_bridge(
            "192.168.x.x", "test-api-key", "lights/1/state", method="PUT", json_body={"bri": 999}
        )


@respx.mock
async def test_get_error_list_still_raises():
    respx.get(f"{BRIDGE_URL}/lights").mock(
        return_value=Response(200, json=[{"error": {"description": "unauthorized user"}}])
    )

    with pytest.raises(BridgeUnreachable, match="unauthorized user"):
        await _request_bridge("192.168.x.x", "test-api-key", "lights")


@respx.mock
async def test_get_dict_response_returns_normally():
    respx.get(f"{BRIDGE_URL}/lights").mock(return_value=Response(200, json={"1": {"name": "Lamp"}}))

    result = await _request_bridge("192.168.x.x", "test-api-key", "lights")

    assert result == {"1": {"name": "Lamp"}}


@respx.mock
async def test_get_empty_list_raises():
    # The bridge's GET replies for lights/scenes/groups are always dicts
    # keyed by id — a list (even an empty one) is always an error condition,
    # unlike a write's legitimate [{"success": ...}] shape.
    respx.get(f"{BRIDGE_URL}/lights").mock(return_value=Response(200, json=[]))

    with pytest.raises(BridgeUnreachable):
        await _request_bridge("192.168.x.x", "test-api-key", "lights")


@respx.mock
async def test_status_error_skips_rediscovery(monkeypatch):
    # A 4xx means the request itself was invalid (e.g. a bad write body),
    # not that the bridge is unreachable — don't burn time on SSDP/cloud
    # rediscovery or retry the same bad body.
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    async def fail_if_called(api_key):
        raise AssertionError("rediscovery should not run for a request-validation error")

    monkeypatch.setattr("app.hue_client.rediscover_bridge_ip", fail_if_called)

    respx.put(f"{BRIDGE_URL}/lights/1/state").mock(return_value=Response(400, json={"error": "bad request"}))

    with pytest.raises(BridgeUnreachable, match="bridge rejected the request"):
        await _bridge_request(config, "lights/1/state", method="PUT", json_body={"bri": 999})


@respx.mock
async def test_network_error_triggers_rediscovery(monkeypatch):
    # A genuine connectivity failure (as opposed to an HTTP status error)
    # should still trigger the rediscovery/retry path.
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    monkeypatch.setattr("app.hue_client.load_config", lambda: config)
    monkeypatch.setattr("app.hue_client.update_bridge_ip", lambda ip: None)

    async def fake_rediscover(api_key):
        return "192.168.x.y"

    monkeypatch.setattr("app.hue_client.rediscover_bridge_ip", fake_rediscover)

    respx.put(f"{BRIDGE_URL}/lights/1/state").mock(side_effect=httpx.ConnectError("connection refused"))
    respx.put("http://192.168.x.y/api/test-api-key/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/bri": 50}}])
    )

    result = await _bridge_request(config, "lights/1/state", method="PUT", json_body={"bri": 50})

    assert result == [{"success": {"/lights/1/state/bri": 50}}]


@respx.mock
async def test_post_network_error_skips_rediscovery(monkeypatch):
    # Unlike GET/PUT, a POST (e.g. create_scene) is not idempotent — blindly
    # resending the same body after a network failure could create a
    # duplicate scene if the original request actually reached the bridge
    # before the connection dropped. So a POST should raise directly on a
    # network error rather than attempting rediscovery-and-resend.
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    async def fail_if_called(api_key):
        raise AssertionError("rediscovery should not run for a POST network error")

    monkeypatch.setattr("app.hue_client.rediscover_bridge_ip", fail_if_called)

    respx.post(f"{BRIDGE_URL}/scenes").mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(BridgeUnreachable, match="could not reach the bridge"):
        await _bridge_request(config, "scenes", method="POST", json_body={"name": "Test"})


@pytest.mark.parametrize(
    ("pct", "bri"),
    [
        (0, 1),
        (1, 3),
        (50, 127),
        (100, 254),
    ],
)
def test_pct_to_bri(pct, bri):
    assert _pct_to_bri(pct) == bri


def test_pct_to_bri_never_returns_zero():
    assert _pct_to_bri(0) == 1


@pytest.mark.parametrize(
    ("bri", "pct"),
    [
        (1, 0),
        (127, 50),
        (254, 100),
    ],
)
def test_bri_to_pct(bri, pct):
    assert _bri_to_pct(bri) == pct
