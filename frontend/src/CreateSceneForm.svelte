<script>
  import FormDialog from './FormDialog.svelte'

  // fixedZone, when set, pins the scene to that zone (issue #30's per-zone
  // "New Scene" button) — the zone dropdown and light checkboxes below are
  // irrelevant in that case, since a zone scene always captures the zone's
  // actual membership (see the hint text and HUE_API.md).
  let { lights, zones, fixedZone = null, onCreate, onClose } = $props()

  let dialogEl = $state(null)
  let name = $state('')
  let selectedLightIds = $state([])
  let selectedZoneId = $state(fixedZone?.id ?? '')
  let submitting = $state(false)
  let error = $state(null)

  // Once a zone is selected, the created scene captures the zone's actual
  // membership regardless of what's checked below (see the hint text and
  // HUE_API.md) — so light selection is only required when creating a
  // standalone scene with no zone.
  let canSubmit = $derived(
    name.trim().length > 0 && (selectedZoneId || selectedLightIds.length > 0) && !submitting
  )

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return
    submitting = true
    error = null
    try {
      await onCreate(name.trim(), selectedLightIds, selectedZoneId || null)
      dialogEl?.close()
    } catch (err) {
      error = err.message
      submitting = false
    }
  }
</script>

<FormDialog bind:dialogEl {onClose}>
  <form class="dialog-form" onsubmit={handleSubmit}>
    <h2>{fixedZone ? `New Scene — ${fixedZone.name}` : 'New Scene'}</h2>

    <label class="field">
      <span>Name</span>
      <input type="text" bind:value={name} maxlength="32" placeholder="e.g. Movie Night" />
    </label>

    {#if fixedZone}
      <p class="hint">
        This scene will capture every light currently in <strong>{fixedZone.name}</strong>.
      </p>
    {:else}
      <fieldset class="field">
        <legend>Lights</legend>
        {#if lights.length === 0}
          <p class="hint">No lights available.</p>
        {:else}
          <div class="option-list">
            {#each lights as light (light.id)}
              <label class="option-row">
                <input type="checkbox" bind:group={selectedLightIds} value={light.id} />
                {light.name}
              </label>
            {/each}
          </div>
        {/if}
      </fieldset>

      <label class="field">
        <span>Zone</span>
        <select bind:value={selectedZoneId}>
          <option value="">No zone</option>
          {#each zones as zone (zone.id)}
            <option value={zone.id}>{zone.name}</option>
          {/each}
        </select>
      </label>

      {#if selectedZoneId}
        <p class="hint">
          This scene will capture every light currently in this zone — the light selection above
          is ignored once a zone is set.
        </p>
      {/if}
    {/if}

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button type="button" onclick={() => dialogEl?.close()}>Cancel</button>
      <button type="submit" class="primary" disabled={!canSubmit}>
        {submitting ? 'Creating…' : 'Create Scene'}
      </button>
    </div>
  </form>
</FormDialog>
