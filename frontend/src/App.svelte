<script>
  import { onMount } from 'svelte'
  import LightCard from './LightCard.svelte'

  let lights = $state([])
  let loading = $state(true)
  let error = $state(null)

  async function loadLights() {
    loading = true
    error = null
    try {
      const res = await fetch('/api/lights')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail ?? `Request failed (${res.status})`)
      }
      lights = await res.json()
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }

  onMount(loadLights)
</script>

<main>
  <h1>Hue Light Control</h1>

  {#if loading}
    <p>Loading bulbs…</p>
  {:else if error}
    <p class="error">{error}</p>
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
</main>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }

  .error {
    color: light-dark(#a3392c, #f0958a);
  }
</style>
