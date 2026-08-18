<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { zone, lights, onSetBrightness, onSetZoneOn } = $props()

  // Same derivation SceneCard used to do per-scene (issue #47's whole
  // point: scenes in the same zone share bulbs, so this is the one true
  // brightness for the zone) — matched against the zone's own light_ids
  // rather than any particular scene's, so it stays accurate even when the
  // zone has no scenes yet.
  let zoneLights = $derived(lights.filter((light) => zone.lightIds.includes(light.id)))
  let onLights = $derived(zoneLights.filter((light) => light.on))

  // Only "off" once lights have actually loaded (zoneLights is briefly
  // empty before that, at which point this stays false, leaving the slider
  // at the fallback below rather than flashing "off").
  let off = $derived(zoneLights.length > 0 && onLights.length === 0)

  // Average brightness across just the on lights. 0 when the zone is off —
  // the slider's min is 0 here (unlike BrightnessSlider's own default of 1)
  // specifically so "off" has a slider position, and dragging back up is how
  // the zone turns back on. Falls back to 100 while lights haven't loaded yet.
  let liveBrightnessPct = $derived(
    off
      ? 0
      : onLights.length > 0
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

  // Dragging to 0 is an off command, not brightness_pct: 0 (the bridge
  // rejects that). Dragging up from a fully-off zone is the explicit
  // "turn back on" gesture and applies to every light (turnOn: true) —
  // otherwise (some lights already on) it's a plain adjustment that must
  // only touch the already-on lights, per onSetBrightness's contract.
  function setBrightness(pct) {
    runUpdate(() => {
      if (pct === 0) return onSetZoneOn(zone.id, false)
      return onSetBrightness(zone.id, pct, { turnOn: off })
    })
  }

  function turnOff() {
    runUpdate(() => onSetZoneOn(zone.id, false))
  }
</script>

<div class="zone-brightness">
  <BrightnessSlider
    value={liveBrightnessPct}
    label="{zone.name} brightness"
    min={0}
    disabled={pending || zoneLights.length === 0}
    onChange={setBrightness}
  />
  <button type="button" class="zone-off-button" disabled={pending || off || zoneLights.length === 0} onclick={turnOff}>
    Off
  </button>
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
    background: var(--error-bg);
    color: var(--error-text);
  }

  .zone-off-button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface-alt);
    cursor: pointer;
    flex-shrink: 0;
  }

  .zone-off-button:hover:not(:disabled) {
    filter: brightness(0.95);
  }

  .zone-off-button:disabled {
    opacity: 0.55;
    cursor: default;
  }
</style>
