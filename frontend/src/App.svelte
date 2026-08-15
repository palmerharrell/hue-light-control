<script>
  import { onMount } from 'svelte'
  import LightCard from './LightCard.svelte'
  import SceneCard from './SceneCard.svelte'

  let lights = $state([])
  let lightsLoading = $state(true)
  let lightsError = $state(null)

  let scenes = $state([])
  let scenesLoading = $state(true)
  let scenesError = $state(null)

  async function loadLights() {
    lightsLoading = true
    lightsError = null
    try {
      const res = await fetch('/api/lights')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Request failed (${res.status})`)
      }
      lights = await res.json()
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
      const res = await fetch('/api/scenes')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Request failed (${res.status})`)
      }
      scenes = await res.json()
    } catch (err) {
      scenesError = err.message
    } finally {
      scenesLoading = false
    }
  }

  onMount(() => {
    loadLights()
    loadScenes()
  })
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
          <LightCard {light} />
        {/each}
      </div>
    {/if}
  </section>

  <section>
    <h2>Scenes</h2>
    {#if scenesLoading}
      <p>Loading scenes…</p>
    {:else if scenesError}
      <p class="error">{scenesError}</p>
      <button onclick={loadScenes}>Retry</button>
    {:else if scenes.length === 0}
      <p>No scenes found.</p>
    {:else}
      <div class="grid">
        {#each scenes as scene (scene.id)}
          <SceneCard {scene} />
        {/each}
      </div>
    {/if}
  </section>
</main>

<style>
  section + section {
    margin-top: 2rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }

  .error {
    color: light-dark(#a3392c, #f0958a);
  }
</style>
