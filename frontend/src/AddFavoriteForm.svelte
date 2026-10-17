<script>
  import FormDialog from './FormDialog.svelte'

  // Zone groups ({ id, name, scenes }) holding only scenes not already in
  // Favorites, empty groups dropped — the caller (App.svelte) builds this
  // from its zoneGroups, same division of labor as CreateSceneForm. Grouping
  // matters because many scenes share a name across zones.
  let { groups, onAdd, onClose } = $props()

  let dialogEl = $state(null)
  let selectedIds = $state([])
  let submitting = $state(false)
  let error = $state(null)

  let canSubmit = $derived(selectedIds.length > 0 && !submitting)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return
    submitting = true
    error = null
    try {
      await onAdd(selectedIds)
      dialogEl?.close()
    } catch (err) {
      error = err.message
      submitting = false
    }
  }
</script>

<FormDialog bind:dialogEl {onClose}>
  <form class="dialog-form" onsubmit={handleSubmit}>
    <h2>Add to Favorites</h2>

    {#if groups.length === 0}
      <p class="hint">Every scene is already in Favorites.</p>
    {:else}
      <fieldset class="field">
        <legend>Scenes</legend>
        <div class="option-list tall">
          {#each groups as group (group.id)}
            <div class="option-group-heading">{group.name}</div>
            {#each group.scenes as scene (scene.id)}
              <label class="option-row">
                <input type="checkbox" bind:group={selectedIds} value={scene.id} />
                {scene.name}
              </label>
            {/each}
          {/each}
        </div>
      </fieldset>
    {/if}

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button type="button" onclick={() => dialogEl?.close()}>Cancel</button>
      <button type="submit" class="primary" disabled={!canSubmit}>
        {submitting ? 'Adding…' : 'Add'}
      </button>
    </div>
  </form>
</FormDialog>
