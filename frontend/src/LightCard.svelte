<script>
  let { light, onToggle } = $props()

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
</script>

<div class="card" class:unreachable={!light.reachable}>
  <div class="header">
    <span
      class="swatch"
      style:background-color={light.on ? (light.color ?? '#ffe9b3') : undefined}
    ></span>
    <span class="name">{light.name}</span>
  </div>

  <div class="status">
    <button
      type="button"
      class="badge toggle"
      class:on={light.on}
      aria-pressed={light.on}
      disabled={pending}
      onclick={handleToggle}
    >
      {light.on ? 'On' : 'Off'}
    </button>
    {#if !light.reachable}
      <span class="badge unreachable-badge">Unreachable</span>
    {/if}
    {#if light.toggleError}
      <span class="badge error-badge">{light.toggleError}</span>
    {/if}
  </div>

  <div class="brightness">
    <div class="brightness-track">
      <div class="brightness-fill" style:width="{light.brightness_pct}%"></div>
    </div>
    <span class="brightness-label">{light.brightness_pct}%</span>
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
  }

  .badge.on {
    background: light-dark(#dcf5df, #1f3d24);
    color: light-dark(#1c7a2e, #7fe396);
  }

  .toggle {
    font: inherit;
    font-size: 0.75rem;
    border: none;
    cursor: pointer;
  }

  .toggle:hover {
    filter: brightness(0.95);
  }

  .toggle:focus-visible {
    outline: 2px solid light-dark(#1c7a2e, #7fe396);
    outline-offset: 2px;
  }

  .toggle:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .unreachable-badge,
  .error-badge {
    background: light-dark(#fbe3e0, #3d211f);
    color: light-dark(#a3392c, #f0958a);
  }

  .brightness {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .brightness-track {
    flex: 1;
    height: 0.4rem;
    border-radius: 999px;
    background: light-dark(#eee, #333);
    overflow: hidden;
  }

  .brightness-fill {
    height: 100%;
    background: light-dark(#333, #ddd);
  }

  .brightness-label {
    font-size: 0.75rem;
    color: light-dark(#666, #aaa);
    width: 2.5rem;
    text-align: right;
  }
</style>
