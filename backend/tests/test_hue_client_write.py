import pytest
import respx
from httpx import Response

from app.hue_client import BridgeUnreachable, _bri_to_pct, _pct_to_bri, _request_bridge

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
