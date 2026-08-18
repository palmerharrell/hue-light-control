<script>
  import FormDialog from './FormDialog.svelte'

  // scenes not already in Favorites — the caller (App.svelte) filters this
  // down before passing it in, same division of labor as CreateSceneForm.
  let { scenes, onAdd, onClose } = $props()

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

    {#if scenes.length === 0}
      <p class="hint">Every scene is already in Favorites.</p>
    {:else}
      <fieldset class="field">
        <legend>Scenes</legend>
        <div class="option-list tall">
          {#each scenes as scene (scene.id)}
            <label class="option-row">
              <input type="checkbox" bind:group={selectedIds} value={scene.id} />
              {scene.name}
            </label>
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
