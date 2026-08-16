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

  async function toggleLight(lightId, on) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = light.on
    light.on = on
    try {
      await putJson(`/api/lights/${lightId}/state`, { on })
    } catch {
      light.on = prev
    }
  }

  let showCreateForm = $state(false)

  async function createScene(name, lightIds, groupId) {
    const scene = await postJson('/api/scenes', { name, light_ids: lightIds, group_id: groupId })
    scenes = [...scenes, scene]
  }
</script>

<main>
  <h1>Hue Light Control</h1>

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
          <LightCard {light} onToggle={toggleLight} />
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
              <SceneCard {scene} />
            {/each}
          </div>
        </div>
      {/each}
    {/if}
  </section>
</main>

<style>
  section + section {
    margin-top: 2rem;
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
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    background: light-dark(#eee, #333);
    color: inherit;
    cursor: pointer;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }

  .zone-group + .zone-group {
    margin-top: 1.5rem;
  }

  .zone-group h3 {
    margin: 0 0 0.75rem;
    font-size: 0.95rem;
    color: light-dark(#555, #aaa);
  }

  .error {
    color: light-dark(#a3392c, #f0958a);
  }
</style>
