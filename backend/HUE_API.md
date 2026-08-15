# Hue Bridge API reference

Endpoints on the local Hue Bridge API (CLIP v1) that this app calls or
plans to call. All paths are relative to `http://<bridge-ip>/api`, where
`<bridge-ip>` is the address in `config.yaml` (gitignored, never
committed — see `config.example.yaml` for the shape).

`<username>` below is the API key minted once via `scripts/pair_bridge.py`
and stored in `config.yaml` as `api_key`.

## Pairing (already implemented — `scripts/pair_bridge.py`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api` | Mint a new API key. Body: `{"devicetype": "<app>#<device>"}`. Requires the bridge's physical link button to have been pressed within the last 30s, or returns error type 101. |

## Bridge info

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/config` | Unauthenticated subset: name, modelid, swversion, apiversion, bridgeid, mac. Used for discovery/sanity-checks before pairing. |
| GET | `/api/<username>/config` | Authenticated, fuller bridge config. |

## Lights (issue: display brightness/color/on-off per bulb)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/<username>/lights` | List all lights with current state. |
| GET | `/api/<username>/lights/<id>` | Single light's state. |
| PUT | `/api/<username>/lights/<id>/state` | Set `on` (bool), `bri` (1-254), color via `hue`+`sat`, `xy`, or `ct`. |

Relevant `state` fields returned per light: `on`, `bri`, `hue`, `sat`, `xy`,
`ct`, `colormode`, `reachable`.

## Groups (rooms/zones) (issue: get Zones, group Scenes by Zone)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/<username>/groups` | List groups and their member lights. |
| GET | `/api/<username>/groups/<id>` | Single group. |
| PUT | `/api/<username>/groups/<id>/action` | Apply state to every light in the group at once; also how a scene gets activated (see below). |

A group's `type` distinguishes what it represents: `Room` (one light belongs
to at most one room), `Zone` (user-defined, can span rooms and overlap),
`Entertainment` (entertainment areas), plus bridge/app-internal `LightGroup`s.
Only `Zone` groups are surfaced by this app's `/api/zones` endpoint.

## Scenes (issue: display Scenes; issue: group Scenes by Zone)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/<username>/scenes` | List configured scenes (id, name, member lights). |
| GET | `/api/<username>/scenes/<id>` | Scene detail, including per-light stored states. |
| PUT | `/api/<username>/groups/<id>/action` | Activate a scene: body `{"scene": "<scene-id>"}`. Hue has no dedicated "activate" endpoint — scenes are applied through the owning group's action endpoint. |

A `GroupScene` carries a `group` field naming the group (room, zone, or
other) it was created for; this app's `/api/scenes` passes that through as
`group_id` so the frontend can bucket scenes under their owning zone.
Standalone `LightScene`s have no `group` and surface with `group_id: null`.

## Notes

- This is the CLIP v1 local API (plain HTTP, no cert handling needed), not
  the newer CLIP v2/remote API. v1 is what `scripts/pair_bridge.py` already
  pairs against and is sufficient for LAN-only proxying.
- The backend is the only thing that ever holds `<username>`/`api_key` —
  per the architecture in CLAUDE.md, the browser only talks to the backend,
  never directly to the bridge.
