<script>
  import FormDialog from './FormDialog.svelte'

  // `sceneGroups`: zone groups ({ id, name, scenes }) holding only scenes not
  // already in Favorites, empty groups dropped. `lights`: lights not already
  // in Favorites. The caller (App.svelte) builds both from its own state,
  // same division of labor as CreateSceneForm. Grouping scenes matters
  // because many scenes share a name across zones.
  let { sceneGroups, lights, onAdd, onClose } = $props()

  let dialogEl = $state(null)
  let selectedSceneIds = $state([])
  let selectedLightIds = $state([])
  let submitting = $state(false)
  let error = $state(null)

  // An item can vanish from the lists while the dialog is open (refresh, or
  // favorited elsewhere); only submit ids the user can still see ticked.
  let chosenSceneIds = $derived.by(() => {
    const visible = new Set(sceneGroups.flatMap((group) => group.scenes.map((scene) => scene.id)))
    return selectedSceneIds.filter((id) => visible.has(id))
  })

  let chosenLightIds = $derived.by(() => {
    const visible = new Set(lights.map((light) => light.id))
    return selectedLightIds.filter((id) => visible.has(id))
  })

  let canSubmit = $derived(chosenSceneIds.length + chosenLightIds.length > 0 && !submitting)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return
    submitting = true
    error = null
    try {
      await onAdd(chosenSceneIds, chosenLightIds)
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

    {#if sceneGroups.length === 0 && lights.length === 0}
      <p class="hint">Everything is already in Favorites.</p>
    {/if}

    {#if lights.length > 0}
      <fieldset class="field">
        <legend>Lights</legend>
        <div class="option-list">
          {#each lights as light (light.id)}
            <label class="option-row">
              <input type="checkbox" bind:group={selectedLightIds} value={light.id} />
              {light.name}
            </label>
          {/each}
        </div>
      </fieldset>
    {/if}

    {#if sceneGroups.length > 0}
      <fieldset class="field">
        <legend>Scenes</legend>
        <div class="option-list tall">
          {#each sceneGroups as group (group.id)}
            <div class="option-group" role="group" aria-labelledby="favorite-group-{group.id}">
              <div class="option-group-heading" id="favorite-group-{group.id}">{group.name}</div>
              {#each group.scenes as scene (scene.id)}
                <label class="option-row">
                  <input type="checkbox" bind:group={selectedSceneIds} value={scene.id} />
                  {scene.name}
                </label>
              {/each}
            </div>
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
