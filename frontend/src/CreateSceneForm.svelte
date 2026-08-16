<script>
  import { onMount } from 'svelte'

  let { lights, zones, onCreate, onClose } = $props()

  let dialog = $state(null)
  let name = $state('')
  let selectedLightIds = $state([])
  let selectedZoneId = $state('')
  let submitting = $state(false)
  let error = $state(null)

  // Once a zone is selected, the created scene captures the zone's actual
  // membership regardless of what's checked below (see the hint text and
  // HUE_API.md) — so light selection is only required when creating a
  // standalone scene with no zone.
  let canSubmit = $derived(
    name.trim().length > 0 && (selectedZoneId || selectedLightIds.length > 0) && !submitting
  )

  onMount(() => {
    dialog?.showModal()
  })

  async function handleSubmit(event) {
    event.preventDefault()
    if (!canSubmit) return
    submitting = true
    error = null
    try {
      await onCreate(name.trim(), selectedLightIds, selectedZoneId || null)
      dialog?.close()
    } catch (err) {
      error = err.message
      submitting = false
    }
  }

  function handleBackdropClick(event) {
    // Any click that doesn't land on a child element (backdrop AND the
    // dialog's own padding around <form>) reports target === dialog — so
    // that check alone can't tell a real backdrop click from one that
    // landed in the card's padding (visually still inside the card).
    // Compare coordinates against the dialog's own rendered box instead
    // (its border box, which includes the padding): only a click outside
    // that box is a real click on the backdrop.
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
    <h2>New Scene</h2>

    <label class="field">
      <span>Name</span>
      <input type="text" bind:value={name} maxlength="32" placeholder="e.g. Movie Night" />
    </label>

    <fieldset class="field">
      <legend>Lights</legend>
      {#if lights.length === 0}
        <p class="hint">No lights available.</p>
      {:else}
        <div class="light-list">
          {#each lights as light (light.id)}
            <label class="light-option">
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

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button type="button" onclick={() => dialog?.close()}>Cancel</button>
      <button type="submit" class="primary" disabled={!canSubmit}>
        {submitting ? 'Creating…' : 'Create Scene'}
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
  }

  dialog::backdrop {
    background: rgba(0, 0, 0, 0.4);
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

  .field > span,
  .field legend {
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0;
  }

  input[type='text'],
  select {
    font: inherit;
    padding: 0.4rem 0.5rem;
    border-radius: 0.5rem;
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    background: light-dark(#fff, #262626);
    color: inherit;
  }

  .light-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    max-height: 10rem;
    overflow-y: auto;
    padding: 0.5rem;
    border-radius: 0.5rem;
    background: light-dark(#f7f7f7, #262626);
  }

  .light-option {
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
