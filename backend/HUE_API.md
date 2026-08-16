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
| POST | `/api/<username>/scenes` | Create a scene from lights' *current* live state (see below). |
| DELETE | `/api/<username>/scenes/<id>` | Delete a scene. |
| PUT | `/api/<username>/groups/<id>/action` | Activate a scene: body `{"scene": "<scene-id>"}`. Hue has no dedicated "activate" endpoint — scenes are applied through the owning group's action endpoint. |

A `GroupScene` carries a `group` field naming the group (room, zone, or
other) it was created for; this app's `/api/scenes` passes that through as
`group_id` so the frontend can bucket scenes under their owning zone.
Standalone `LightScene`s have no `group` and surface with `group_id: null`.

### Creating a scene (issue: create Scenes)

Not documented anywhere the app previously referenced — confirmed directly
against a real bridge. `POST /api/<username>/scenes`, body shape depends on
whether the scene is tied to a group:

**Standalone `LightScene`** (no zone/group selected):
```json
{"name": "Reading", "lights": ["1", "2"], "recycle": false, "type": "LightScene"}
```
`lights` is required and non-empty (omitting it returns error type 5,
"invalid/missing parameters in body"). `type` can be omitted — the bridge
defaults an untyped create to `LightScene` — but is sent explicitly here
for clarity. `recycle: false` marks it a user-visible scene rather than an
app-internal state snapshot (see the `recycle` filter in `get_scenes`).

**`GroupScene`** (tied to a zone):
```json
{"name": "Movie Night", "recycle": false, "type": "GroupScene", "group": "3"}
```
Critically, **`lights` must be omitted entirely** — including it alongside
`group` (even with a value that exactly matches the group's own members)
is rejected with `{"error": {"type": 14, "description": "Conflicting
parameter, type: GroupScenes"}}`. A GroupScene's membership is derived
solely from the group at creation time; there's no way to create it with a
subset of the group's lights. This means a light-picker in the UI is only
meaningful for a standalone `LightScene` — once a zone is selected, the
resulting scene captures *every* light currently in that zone, regardless
of what was checked.

**Response** (both cases), matching the standard write-response shape:
```json
[{"success": {"id": "<bridge-assigned-scene-id>"}}]
```
or an error list like `[{"error": {"type": ..., "description": "..."}}]`.

**Name length**: capped at 32 characters. A 33-character name is rejected
with `{"error": {"type": 7, "description": "invalid value, ..., for
parameter, name"}}`; 32 succeeds. (This is CLIP v1's traditional cap,
confirmed exactly by binary-testing 32 vs. 33 chars against a real bridge.)

**No target values**: the create body has no fields for target on/bri/xy/
etc. — a scene always snapshots the involved lights' state *as it is at
creation time* (confirmed via `GET /scenes/<id>` immediately after
creating one: `lightstates` matched the lights' actual current state).
There is no way to create a scene with lights set to values other than
whatever they're currently at.

### Activating a scene (issue: activate Scenes)

Confirms what the Groups section above already documents: there's no
scene-specific "activate" endpoint. The app's `POST
/api/scenes/<id>/activate` route (body: `{"group_id": "<id>", "brightness_pct":
<1-100, optional>}`) turns around and issues `PUT
/api/<username>/groups/<group_id>/action` with `{"scene": "<id>"}` — the
same call the Groups/Scenes sections describe. `group_id` must be supplied
by the caller (the frontend gets it from the scene's own `group_id`, which
is null for a standalone `LightScene` — those can't be activated this way
and the frontend disables them).

Since activation is a PUT (idempotent — resending "activate this scene"
twice is harmless), it goes through the normal rediscovery-retry path,
unlike scene creation's POST.

`brightness_pct`, when given, is sent as `bri` in the same body alongside
`scene`. This combination has **not** been verified against a real
bridge — whether the bridge actually applies both, or silently drops one,
is unconfirmed. It's accepted now for forward-compatibility with a future
per-scene-brightness feature but isn't exercised by the frontend yet.

## Notes

- This is the CLIP v1 local API (plain HTTP, no cert handling needed), not
  the newer CLIP v2/remote API. v1 is what `scripts/pair_bridge.py` already
  pairs against and is sufficient for LAN-only proxying.
- The backend is the only thing that ever holds `<username>`/`api_key` —
  per the architecture in CLAUDE.md, the browser only talks to the backend,
  never directly to the bridge.
