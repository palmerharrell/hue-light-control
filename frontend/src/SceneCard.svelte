<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { scene, onActivate } = $props()

  // Standalone LightScenes (no group_id) can't be activated via the
  // group-action endpoint (see HUE_API.md's Scenes section) — render them
  // as non-interactive instead of wiring up a click handler.
  let activatable = $derived(scene.group_id != null)

  // Local, ephemeral UI state — there's no concept of "the currently
  // active scene's brightness" tracked anywhere (scenes aren't stateful
  // like that in this app). Resets to 100 on reload; that's expected.
  // Moving the slider re-activates the scene at that brightness rather
  // than live-adjusting an already-active scene.
  let sceneBrightness = $state(100)

  // Serializes both activation paths (plain click and the brightness
  // slider) for this card: while a request is in flight both controls are
  // disabled, so a fast click-then-drag (or vice versa) can't fire a
  // second overlapping activate request.
  let pending = $state(false)

  async function activate(brightnessPct) {
    if (pending || !activatable) return
    pending = true
    try {
      await onActivate(scene.id, scene.group_id, brightnessPct)
    } finally {
      pending = false
    }
  }

  function handleBrightnessChange(pct) {
    sceneBrightness = pct
    activate(pct)
  }
</script>

<div class="card" class:inactive={!activatable}>
  <button
    type="button"
    class="activate"
    disabled={!activatable || pending}
    title={activatable ? undefined : "Can't activate — not part of a zone"}
    onclick={() => activate()}
  >
    <span class="name">{scene.name}</span>
    <span class="badge">{scene.light_count} {scene.light_count === 1 ? 'light' : 'lights'}</span>
    {#if scene.activateError}
      <span class="badge error-badge">{scene.activateError}</span>
    {/if}
  </button>

  <BrightnessSlider
    value={sceneBrightness}
    label="{scene.name} brightness"
    disabled={!activatable || pending}
    onChange={handleBrightnessChange}
  />
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
    width: 100%;
  }

  .card.inactive {
    opacity: 0.55;
  }

  .activate {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.6rem;
    width: 100%;
    border: none;
    padding: 0;
    margin: 0;
    background: none;
    font: inherit;
    text-align: left;
    color: inherit;
    cursor: pointer;
  }

  .activate:hover:not(:disabled) {
    filter: brightness(0.97);
  }

  .activate:focus-visible {
    outline: 2px solid light-dark(#1c7a2e, #7fe396);
    outline-offset: 2px;
  }

  .activate:disabled {
    cursor: default;
  }

  .name {
    font-weight: 600;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    background: light-dark(#eee, #333);
    color: light-dark(#555, #ccc);
    width: fit-content;
  }

  .error-badge {
    background: light-dark(#fbe3e0, #3d211f);
    color: light-dark(#a3392c, #f0958a);
  }
</style>
