<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { light, onToggle, onBrightnessChange } = $props()

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

  // The swatch and brightness slider are their own interactive/decorative
  // regions, not part of the toggle target — a click that lands in either
  // (checked via closest, since the slider's range input is what's actually
  // clicked) shouldn't also toggle the light.
  function handleCardClick(event) {
    if (event.target.closest('.swatch, .slider-wrap')) return
    handleToggle()
  }

  function handleKeydown(event) {
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
</div>

<style>
  .card {
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    border-radius: 0.75rem;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    background: light-dark(#fff, #1e1e1e);
    box-shadow: 0 1px 2px light-dark(rgba(0, 0, 0, 0.04), rgba(0, 0, 0, 0.2));
    transition: box-shadow 0.15s ease;
    cursor: pointer;
  }

  .card:hover {
    box-shadow: 0 2px 8px light-dark(rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.3));
  }

  .card:focus-visible {
    outline: 2px solid light-dark(#1c7a2e, #7fe396);
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
    border: 1px solid light-dark(rgba(0, 0, 0, 0.15), rgba(255, 255, 255, 0.25));
    background: light-dark(#e2e2e2, #2a2a2a);
    flex-shrink: 0;
    cursor: default;
    transition: box-shadow 0.2s ease, background-color 0.2s ease;
  }

  .slider-wrap {
    cursor: default;
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
    border-radius: 999px;
    background: light-dark(#eee, #333);
    color: light-dark(#555, #ccc);
    width: fit-content;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .unreachable-badge,
  .error-badge {
    background: light-dark(#fbe3e0, #3d211f);
    color: light-dark(#a3392c, #f0958a);
  }
</style>
