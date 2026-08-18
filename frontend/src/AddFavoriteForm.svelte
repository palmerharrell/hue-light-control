<script>
  import { onMount } from 'svelte'

  // scenes not already in Favorites — the caller (App.svelte) filters this
  // down before passing it in, same division of labor as CreateSceneForm.
  let { scenes, onAdd, onClose } = $props()

  let dialog = $state(null)
  let selectedIds = $state([])
  let submitting = $state(false)
  let error = $state(null)

  let canSubmit = $derived(selectedIds.length > 0 && !submitting)

  onMount(() => {
    dialog?.showModal()
  })

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return
    submitting = true
    error = null
    try {
      await onAdd(selectedIds)
      dialog?.close()
    } catch (err) {
      error = err.message
      submitting = false
    }
  }

  function handleBackdropClick(event) {
    // Same coordinate-based backdrop check as CreateSceneForm — a click
    // landing in the dialog's own padding also reports target === dialog.
    const rect = dialog.getBoundingClientRect()
    const outside =
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    if (outside) {
      dialog.close()
    }
  }
</script>

<dialog bind:this={dialog} onclose={onClose} onclick={handleBackdropClick}>
  <form onsubmit={handleSubmit}>
    <h2>Add to Favorites</h2>

    {#if scenes.length === 0}
      <p class="hint">Every scene is already in Favorites.</p>
    {:else}
      <fieldset class="field">
        <legend>Scenes</legend>
        <div class="scene-list">
          {#each scenes as scene (scene.id)}
            <label class="scene-option">
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
      <button type="button" onclick={() => dialog?.close()}>Cancel</button>
      <button type="submit" class="primary" disabled={!canSubmit}>
        {submitting ? 'Adding…' : 'Add'}
      </button>
    </div>
  </form>
</dialog>

<style>
  dialog {
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    border-radius: 0.75rem;
    padding: 1.25rem;
    background: light-dark(#fff, #1e1e1e);
    color: inherit;
    width: min(24rem, 90vw);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  }

  dialog::backdrop {
    background: rgba(0, 0, 0, 0.4);
  }

  button.primary:hover:not(:disabled) {
    filter: brightness(1.08);
  }

  .actions button:not(.primary):hover {
    filter: brightness(0.95);
  }

  h2 {
    margin: 0 0 1rem;
    font-size: 1.1rem;
  }

  form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    border: none;
    padding: 0;
    margin: 0;
  }

  .field legend {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0;
  }

  .scene-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    max-height: 14rem;
    overflow-y: auto;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: light-dark(#f7f7f7, #262626);
  }

  .scene-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }

  .hint {
    font-size: 0.8rem;
    color: light-dark(#666, #aaa);
    margin: 0;
  }

  .error {
    font-size: 0.85rem;
    color: light-dark(#a3392c, #f0958a);
    margin: 0;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  button {
    font: inherit;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    background: light-dark(#eee, #333);
    color: inherit;
    cursor: pointer;
  }

  button.primary {
    background: light-dark(#1c7a2e, #1f3d24);
    color: light-dark(#fff, #7fe396);
    border-color: transparent;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
