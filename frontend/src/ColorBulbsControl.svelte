<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  // `colorLights` is already filtered to supports_color bulbs by the caller.
  // `playing`/`speed` (0-1, like a scene's)/`palette` describe the color cycle
  // owned by App.svelte: while playing, the bulbs keep fading into new random
  // colors drawn from that palette.
  let {
    colorLights,
    playing,
    speed,
    palette,
    onRandomize,
    onSetBrightness,
    onTogglePlay,
    onSpeedChange,
    onPaletteChange,
  } = $props()

  // Average across just the bulbs that are on, like ZoneBrightnessSlider —
  // an off bulb's stored brightness isn't what the user is looking at.
  // Falls back to 100 when every color bulb is off.
  let onLights = $derived(colorLights.filter((light) => light.on))
  let liveBrightnessPct = $derived(
    onLights.length > 0
      ? Math.round(onLights.reduce((sum, light) => sum + light.brightness_pct, 0) / onLights.length)
      : 100
  )

  // [palette key, randomize button label, cycle selector label] — keys match
  // HUE_RANGES in App.svelte.
  const PALETTES = [
    ['all', 'Randomize colors', 'All colors'],
    ['warm', 'Randomize warm', 'Warm'],
    ['cool', 'Randomize cool', 'Cool'],
  ]

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
  <div class="color-actions">
    <!-- Own wrapping group so only these buttons wrap on a narrow card; the
         play toggle stays beside them instead of dropping onto its own line. -->
    <div class="randomize-buttons">
      {#each PALETTES as [key, label] (key)}
        <button type="button" class="randomize-button" disabled={pending} onclick={() => runUpdate(() => onRandomize(key))}>
          {label}
        </button>
      {/each}
    </div>
    <button
      type="button"
      class="play-toggle"
      class:playing
      title={playing ? 'Stop cycling colors' : 'Cycle through random colors'}
      aria-label={playing ? 'Stop cycling colors' : 'Cycle through random colors'}
      aria-pressed={playing}
      onclick={onTogglePlay}
    >
      {playing ? '⏸' : '▶'}
    </button>
  </div>
  <label class="cycle-palette">
    Cycle palette
    <select value={palette} onchange={(event) => onPaletteChange(event.currentTarget.value)}>
      {#each PALETTES as [key, , cycleLabel] (key)}
        <option value={key}>{cycleLabel}</option>
      {/each}
    </select>
  </label>
  {#if playing}
    <BrightnessSlider
      value={Math.round(speed * 100)}
      label="Color cycle speed"
      min={0}
      showValue={false}
      onChange={(pct) => onSpeedChange(pct / 100)}
    />
  {/if}
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

  .color-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .cycle-palette {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
  }

  .cycle-palette select {
    font: inherit;
    padding: 0.2rem 0.5rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: inherit;
  }

  .randomize-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .play-toggle {
    flex-shrink: 0;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface-alt);
    font-size: 0.75rem;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: inherit;
  }

  .play-toggle:hover {
    filter: brightness(0.95);
  }

  .play-toggle.playing {
    background: var(--accent-soft-bg);
    border-color: var(--accent-soft-border);
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
