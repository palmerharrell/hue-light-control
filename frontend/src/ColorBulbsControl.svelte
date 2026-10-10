<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  // `colorLights` is already filtered to supports_color bulbs by the caller.
  let { colorLights, onRandomize, onSetBrightness } = $props()

  // Average across just the bulbs that are on, like ZoneBrightnessSlider —
  // an off bulb's stored brightness isn't what the user is looking at.
  // Falls back to 100 when every color bulb is off.
  let onLights = $derived(colorLights.filter((light) => light.on))
  let liveBrightnessPct = $derived(
    onLights.length > 0
      ? Math.round(onLights.reduce((sum, light) => sum + light.brightness_pct, 0) / onLights.length)
      : 100
  )

  let pending = $state(false)
  let error = $state(null)

  async function runUpdate(action) {
    if (pending) return
    pending = true
    error = null
    try {
      await action()
    } catch (err) {
      error = err.message
    } finally {
      pending = false
    }
  }
</script>

<div class="color-bulbs-control">
  <div class="title">Color bulbs ({colorLights.length})</div>
  <button type="button" class="randomize-button" disabled={pending} onclick={() => runUpdate(onRandomize)}>
    Randomize colors
  </button>
  <BrightnessSlider
    value={liveBrightnessPct}
    label="Color bulbs brightness"
    disabled={pending}
    onChange={(pct) => runUpdate(() => onSetBrightness(pct))}
  />
  {#if error}
    <span class="badge error-badge">{error}</span>
  {/if}
</div>

<style>
  .color-bulbs-control {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    background: var(--surface);
    box-shadow: 0 1px 2px var(--shadow-color);
    margin-bottom: 0.75rem;
  }

  .title {
    font-weight: 600;
  }

  .randomize-button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.4rem 0.9rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    cursor: pointer;
    width: fit-content;
  }

  .randomize-button:hover:not(:disabled) {
    filter: brightness(0.95);
  }

  .randomize-button:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-pill);
    width: fit-content;
  }

  .error-badge {
    background: var(--error-bg);
    color: var(--error-text);
  }
</style>
