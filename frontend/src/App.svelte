<script>
  import { onMount } from 'svelte'
  import LightCard from './LightCard.svelte'
  import SceneCard from './SceneCard.svelte'
  import CreateSceneForm from './CreateSceneForm.svelte'
  import { fetchJson, postJson, putJson } from './api.js'

  let lights = $state([])
  let lightsLoading = $state(true)
  let lightsError = $state(null)

  let scenes = $state([])
  let scenesLoading = $state(true)
  let scenesError = $state(null)

  let zones = $state([])
  let zonesLoading = $state(true)
  let zonesError = $state(null)

  async function loadLights() {
    lightsLoading = true
    lightsError = null
    try {
      lights = await fetchJson('/api/lights')
    } catch (err) {
      lightsError = err.message
    } finally {
      lightsLoading = false
    }
  }

  // Same fetch as loadLights, but silent (no loading-state flicker in the
  // Bulbs section) — used after a scene activation, since that changes
  // multiple lights at once on the bridge and the local `lights` array
  // otherwise has no way to know. Scene cards derive their on/off and
  // brightness display from this same `lights` array (see SceneCard), so
  // this is also what keeps a scene's shown brightness from going stale
  // after another scene (or a manual brightness override) changes its
  // lights out from under it.
  //
  // Merges into the existing light objects in place rather than replacing
  // `lights` wholesale: toggleLight/setLightBrightness capture a specific
  // light object by reference and mutate it on PUT failure to revert/report
  // an error. If this ran concurrently with one of those and swapped in
  // fresh objects, a failure arriving afterward would mutate a now-detached
  // object — invisible to the UI, silently swallowing the revert/error.
  async function refreshLights() {
    try {
      const fresh = await fetchJson('/api/lights')
      const existingById = new Map(lights.map((light) => [light.id, light]))
      for (const updated of fresh) {
        const existing = existingById.get(updated.id)
        if (existing) {
          Object.assign(existing, updated)
        } else {
          lights.push(updated)
        }
      }
    } catch {
      // Leave the last-known lights in place; the existing Retry button
      // on the Bulbs section covers a genuinely failing bridge.
    }
  }

  async function loadScenes() {
    scenesLoading = true
    scenesError = null
    try {
      scenes = await fetchJson('/api/scenes')
    } catch (err) {
      scenesError = err.message
    } finally {
      scenesLoading = false
    }
  }

  async function loadZones() {
    zonesLoading = true
    zonesError = null
    try {
      zones = await fetchJson('/api/zones')
    } catch (err) {
      zonesError = err.message
    } finally {
      zonesLoading = false
    }
  }

  onMount(() => {
    loadLights()
    loadScenes()
    loadZones()
  })

  // Buckets scenes under the zone they belong to. Scenes tied to a Room, an
  // Entertainment area, or no group at all (standalone LightScenes) don't
  // match any zone and land in "Other" — as does every scene if zones failed
  // to load.
  let zoneGroups = $derived.by(() => {
    const byId = new Map(zones.map((zone) => [zone.id, { id: zone.id, name: zone.name, scenes: [] }]))
    const other = { id: 'other', name: 'Other', scenes: [] }
    for (const scene of scenes) {
      const group = byId.get(scene.group_id) ?? other
      group.scenes.push(scene)
    }
    return [...byId.values(), other].filter((group) => group.scenes.length > 0)
  })

  // Note: a bridge write can succeed here (200) for a light that's
  // temporarily unreachable — Hue queues state changes for offline Zigbee
  // devices rather than rejecting them. In that case the optimistic value
  // below sticks even though the bulb hasn't physically changed yet; it
  // reconciles on the next /api/lights refetch. Not gating the toggle on
  // reachable is intentional (see LightCard) — this staleness window is an
  // accepted tradeoff of that.
  async function toggleLight(lightId, on) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = light.on
    light.on = on
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { on })
    } catch (err) {
      light.on = prev
      light.toggleError = err.message
    }
  }

  // Same optimistic-update-with-revert pattern as toggleLight. Dragging
  // brightness up implies the light is on, since a bulb reporting bri>0
  // while off wouldn't visually reflect the change until turned on.
  //
  // Unlike the toggle button, BrightnessSlider isn't disabled while a
  // request is in flight (that would fight the user mid-drag), so rapid
  // successive commits can leave overlapping PUTs in flight. Track the
  // latest request per light and only let a request revert/report an
  // error if it's still the latest one — otherwise an older request that
  // fails after a newer one already succeeded would stomp the newer,
  // already-applied value.
  const latestBrightnessRequest = new Map()

  async function setLightBrightness(lightId, pct) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = { on: light.on, brightness_pct: light.brightness_pct }
    const token = Symbol()
    latestBrightnessRequest.set(lightId, token)
    light.brightness_pct = pct
    light.on = true
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { brightness_pct: pct, on: true })
    } catch (err) {
      if (latestBrightnessRequest.get(lightId) === token) {
        Object.assign(light, prev)
        light.toggleError = err.message
      }
    }
  }

  let showCreateForm = $state(false)

  async function createScene(name, lightIds, groupId) {
    const scene = await postJson('/api/scenes', { name, light_ids: lightIds, group_id: groupId })
    scenes = [...scenes, scene]
  }

  // Unlike toggleLight, there's no meaningful "prior value" to optimistically
  // set and revert for a one-shot action like activating a scene — just
  // surface a per-card error on failure. SceneCard guards against overlapping
  // double-click requests itself (same pattern as LightCard's toggle button).
  //
  // brightnessPct is optional: plain click-to-activate (issue #11) omits it,
  // the per-scene brightness slider (issue #14) passes it. There's no
  // "currently active scene brightness" tracked anywhere — moving the
  // slider just re-activates the scene at that brightness (see
  // HUE_API.md's "Activating a scene" section).
  async function activateScene(sceneId, groupId, brightnessPct) {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return
    scene.activateError = null
    try {
      const body =
        brightnessPct == null ? { group_id: groupId } : { group_id: groupId, brightness_pct: brightnessPct }
      await postJson(`/api/scenes/${sceneId}/activate`, body)
      await refreshLights()
    } catch (err) {
      scene.activateError = err.message
    }
  }
</script>

<main>
  <h1>Hue Light Control</h1>
  <p class="subtitle">Bulbs and scenes on your local Hue bridge</p>

  <section>
    <h2>Bulbs</h2>
    {#if lightsLoading}
      <p>Loading bulbs…</p>
    {:else if lightsError}
      <p class="error">{lightsError}</p>
      <button onclick={loadLights}>Retry</button>
    {:else if lights.length === 0}
      <p>No bulbs found.</p>
    {:else}
      <div class="grid">
        {#each lights as light (light.id)}
          <LightCard {light} onToggle={toggleLight} onBrightnessChange={setLightBrightness} />
        {/each}
      </div>
    {/if}
  </section>

  <section>
    <div class="section-header">
      <h2>Scenes</h2>
      <button onclick={() => (showCreateForm = true)}>+ New Scene</button>
    </div>
    {#if showCreateForm}
      <CreateSceneForm
        {lights}
        {zones}
        onCreate={createScene}
        onClose={() => (showCreateForm = false)}
      />
    {/if}
    {#if scenesLoading || zonesLoading}
      <p>Loading scenes…</p>
    {:else if scenesError}
      <p class="error">{scenesError}</p>
      <button onclick={loadScenes}>Retry</button>
    {:else if scenes.length === 0}
      <p>No scenes found.</p>
    {:else}
      {#if zonesError}
        <p class="error">
          Couldn't load zones ({zonesError}) — showing scenes ungrouped.
          <button onclick={loadZones}>Retry</button>
        </p>
      {/if}
      {#each zoneGroups as group (group.id)}
        <div class="zone-group">
          <h3>{group.name}</h3>
          <div class="grid">
            {#each group.scenes as scene (scene.id)}
              <SceneCard {scene} {lights} onActivate={activateScene} />
            {/each}
          </div>
        </div>
      {/each}
    {/if}
  </section>
</main>

<style>
  h1 {
    margin: 0;
    font-size: 1.75rem;
    letter-spacing: -0.02em;
  }

  .subtitle {
    margin: 0.3rem 0 0;
    color: light-dark(#666, #999);
    font-size: 0.95rem;
  }

  section {
    margin-top: 2.5rem;
  }

  section h2 {
    font-size: 1.15rem;
    letter-spacing: -0.01em;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .section-header h2 {
    margin: 0;
  }

  .section-header button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    background: light-dark(#eee, #333);
    color: inherit;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .section-header button:hover {
    filter: brightness(0.95);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }

  .zone-group {
    border: 1px solid light-dark(#dedede, #333);
    border-radius: 1rem;
    background: light-dark(#ebebe9, #1a1a1a);
    padding: 1.25rem;
  }

  .zone-group + .zone-group {
    margin-top: 1.5rem;
  }

  .zone-group h3 {
    margin: 0 0 0.75rem;
    font-size: 0.95rem;
    font-weight: 600;
    color: light-dark(#555, #aaa);
  }

  .error {
    color: light-dark(#a3392c, #f0958a);
  }
</style>
