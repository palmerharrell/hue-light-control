<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { zone, lights, onSetBrightness } = $props()

  // Same derivation SceneCard used to do per-scene (issue #47's whole
  // point: scenes in the same zone share bulbs, so this is the one true
  // brightness for the zone) — matched against the zone's own light_ids
  // rather than any particular scene's, so it stays accurate even when the
  // zone has no scenes yet.
  let zoneLights = $derived(lights.filter((light) => zone.lightIds.includes(light.id)))
  let onLights = $derived(zoneLights.filter((light) => light.on))

  // Only "off" once lights have actually loaded (zoneLights is briefly
  // empty before that, at which point this stays false, leaving the slider
  // enabled and at the fallback below rather than flashing "off").
  let off = $derived(zoneLights.length > 0 && onLights.length === 0)

  // Average brightness across just the on lights, clamped to 1 (the bridge
  // and BrightnessSlider's min never accept 0). Falls back to 100 while
  // lights haven't loaded yet, or if the zone isn't on.
  let liveBrightnessPct = $derived(
    onLights.length > 0
      ? Math.max(Math.round(onLights.reduce((sum, light) => sum + light.brightness_pct, 0) / onLights.length), 1)
      : 100
  )

  let pending = $state(false)
  let error = $state(null)

  async function setBrightness(pct) {
    if (pending) return
    pending = true
    error = null
    try {
      await onSetBrightness(zone.id, pct)
    } catch (err) {
      error = err.message
    } finally {
      pending = false
    }
  }
</script>

<div class="zone-brightness">
  <BrightnessSlider
    value={liveBrightnessPct}
    label="{zone.name} brightness"
    disabled={pending || off || zoneLights.length === 0}
    showValue={!off}
    onChange={setBrightness}
  />
  {#if error}
    <span class="badge error-badge">{error}</span>
  {/if}
</div>

<style>
  .zone-brightness {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1 1 12rem;
    min-width: 8rem;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    width: fit-content;
    flex-shrink: 0;
  }

  .error-badge {
    background: light-dark(#fbe3e0, #3d211f);
    color: light-dark(#a3392c, #f0958a);
  }
</style>
