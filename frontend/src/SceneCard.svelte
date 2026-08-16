<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { scene, lights, onActivate } = $props()

  // Standalone LightScenes (no group_id) can't be activated via the
  // group-action endpoint (see HUE_API.md's Scenes section) — render them
  // as non-interactive instead of wiring up a click handler.
  let activatable = $derived(scene.group_id != null)

  // The bridge has no concept of "is this scene active" or "what's this
  // scene's current brightness" (confirmed directly against a real bridge —
  // group.action never records which scene, if any, was last recalled, and
  // a scene's own stored lightstates reflect creation time, not now). So
  // rather than asking the bridge, derive both from the same live
  // /api/lights data the Bulbs section already shows, matched against this
  // scene's light_ids — that's always accurate and free (no extra
  // request), and updates automatically whenever `lights` does (a bulb
  // toggle, or App's refreshLights() after any scene activation).
  let sceneLights = $derived(lights.filter((light) => scene.light_ids.includes(light.id)))
  let onLights = $derived(sceneLights.filter((light) => light.on))

  // Only "off" once lights have actually loaded (sceneLights is briefly
  // empty before that, at which point this stays false, leaving the slider
  // enabled and at the fallback below rather than flashing "off").
  let off = $derived(sceneLights.length > 0 && onLights.length === 0)

  // Average brightness across just the on lights, clamped to 1 (the bridge
  // and BrightnessSlider's min never accept 0). Falls back to 100 while
  // lights haven't loaded yet, or if the scene isn't on.
  let liveBrightnessPct = $derived(
    onLights.length > 0
      ? Math.max(Math.round(onLights.reduce((sum, light) => sum + light.brightness_pct, 0) / onLights.length), 1)
      : 100
  )

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
    {#if scene.activateError}
      <span class="badge error-badge">{scene.activateError}</span>
    {/if}
  </button>

  <BrightnessSlider
    value={liveBrightnessPct}
    label="{scene.name} brightness"
    disabled={!activatable || pending || off}
    showValue={!off}
    onChange={activate}
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
    box-shadow: 0 1px 2px light-dark(rgba(0, 0, 0, 0.04), rgba(0, 0, 0, 0.2));
    transition: box-shadow 0.15s ease;
  }

  .card:not(.inactive):hover {
    box-shadow: 0 2px 8px light-dark(rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.3));
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
