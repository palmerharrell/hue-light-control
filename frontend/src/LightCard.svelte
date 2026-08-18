<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { light, onToggle, onBrightnessChange, onColorChange, onColorTempChange } = $props()

  // Serializes toggle clicks for this card: while a PUT is in flight the
  // button is disabled, so a fast double-click can't fire a second request
  // that resolves out of order with the first and leaves the optimistic
  // on/off state permanently diverged from the bridge.
  let pending = $state(false)

  async function handleToggle() {
    if (pending) return
    pending = true
    try {
      await onToggle(light.id, !light.on)
    } finally {
      pending = false
    }
  }

  // The swatch, brightness slider, color picker, and color-temp slider are
  // their own interactive/decorative regions, not part of the toggle target
  // — a click that lands in any of them (checked via closest, since the
  // actual input elements are what's clicked) shouldn't also toggle the
  // light.
  const CONTROL_SELECTOR = '.swatch, .slider-wrap, .color-wrap, .ct-wrap'

  function handleCardClick(event) {
    if (event.target.closest(CONTROL_SELECTOR)) return
    handleToggle()
  }

  function handleKeydown(event) {
    if (event.target.closest(CONTROL_SELECTOR)) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleToggle()
    }
  }
</script>

<div
  class="card"
  class:unreachable={!light.reachable}
  role="button"
  tabindex="0"
  aria-pressed={light.on}
  aria-disabled={pending}
  onclick={handleCardClick}
  onkeydown={handleKeydown}
>
  <div class="header">
    <span
      class="swatch"
      style:background-color={light.on ? (light.color ?? '#ffe9b3') : undefined}
      style:box-shadow={light.on ? `0 0 0.5rem ${light.color ?? '#ffe9b3'}` : undefined}
    ></span>
    <span class="name">{light.name}</span>
  </div>

  {#if !light.reachable || light.toggleError}
    <div class="status">
      {#if !light.reachable}
        <span class="badge unreachable-badge">Unreachable</span>
      {/if}
      {#if light.toggleError}
        <span class="badge error-badge">{light.toggleError}</span>
      {/if}
    </div>
  {/if}

  <div class="slider-wrap">
    <BrightnessSlider
      value={light.brightness_pct}
      label="{light.name} brightness"
      onChange={(pct) => onBrightnessChange(light.id, pct)}
    />
  </div>

  {#if light.supports_color}
    <div class="color-wrap">
      <input
        type="color"
        class="color-input"
        value={light.color ?? '#ffe9b3'}
        aria-label="{light.name} color"
        onchange={(event) => onColorChange(light.id, event.target.value)}
      />
    </div>
  {/if}

  {#if light.supports_color_temp}
    <div class="ct-wrap">
      <BrightnessSlider
        value={light.color_temp_pct ?? 50}
        min={0}
        max={100}
        showValue={false}
        label="{light.name} color temperature"
        onChange={(pct) => onColorTempChange(light.id, pct)}
      />
    </div>
  {/if}
</div>

<style>
  .card {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    background: var(--surface);
    box-shadow: 0 1px 2px var(--shadow-color);
    transition: box-shadow 0.15s ease, background-color 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
  }

  .card:hover {
    box-shadow: 0 2px 8px var(--shadow-color);
  }

  .card:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  .card[aria-disabled='true'] {
    cursor: default;
  }

  .card.unreachable {
    opacity: 0.55;
  }

  .header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .swatch {
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 50%;
    border: 1px solid var(--border);
    background: var(--surface-alt);
    flex-shrink: 0;
    cursor: default;
    transition: box-shadow 0.2s ease, background-color 0.2s ease;
  }

  .slider-wrap,
  .color-wrap,
  .ct-wrap {
    cursor: default;
  }

  .color-input {
    width: 100%;
    height: 1.75rem;
    border: 1px solid var(--border);
    border-radius: 0.4rem;
    padding: 0;
    background: none;
    cursor: pointer;
  }

  .ct-wrap :global(input[type='range']) {
    background: linear-gradient(to right, #ffb347, #cfe8ff);
  }

  .name {
    font-weight: 600;
  }

  .status {
    display: flex;
    gap: 0.4rem;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: var(--radius-pill);
    background: var(--surface-alt);
    color: var(--text-muted);
    width: fit-content;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .unreachable-badge,
  .error-badge {
    background: var(--error-bg);
    color: var(--error-text);
  }
</style>
