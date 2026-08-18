<script>
  import FormDialog from './FormDialog.svelte'
  import { missingTokens } from './themes.js'

  let { onImport, onClose } = $props()

  let dialogEl = $state(null)
  let fileName = $state(null)
  let theme = $state(null)
  let submitting = $state(false)
  let error = $state(null)

  async function handleFileChange(event) {
    error = null
    theme = null
    const file = event.target.files?.[0]
    if (!file) return
    fileName = file.name
    let parsed
    try {
      parsed = JSON.parse(await file.text())
    } catch {
      error = 'That file is not valid JSON.'
      return
    }
    if (typeof parsed?.id !== 'string' || !parsed.id) {
      error = 'Theme is missing an "id".'
      return
    }
    if (typeof parsed?.name !== 'string' || !parsed.name) {
      error = 'Theme is missing a "name".'
      return
    }
    const missing = missingTokens(parsed.tokens)
    if (missing.length > 0) {
      error = `Theme is missing required tokens: ${missing.join(', ')}`
      return
    }
    theme = parsed
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!theme || submitting) return
    submitting = true
    error = null
    try {
      await onImport(theme)
      dialogEl?.close()
    } catch (err) {
      error = err.message
      submitting = false
    }
  }
</script>

<FormDialog bind:dialogEl {onClose}>
  <form class="dialog-form" onsubmit={handleSubmit}>
    <h2>Import Theme</h2>

    <label class="field">
      <span>Theme JSON file</span>
      <input type="file" accept="application/json,.json" onchange={handleFileChange} />
    </label>

    {#if fileName && !error}
      <p class="hint">"{theme?.name}" ready to import.</p>
    {/if}

    {#if error}
      <p class="error">{error}</p>
    {/if}

    <div class="actions">
      <button type="button" onclick={() => dialogEl?.close()}>Cancel</button>
      <button type="submit" class="primary" disabled={!theme || submitting}>
        {submitting ? 'Importing…' : 'Import'}
      </button>
    </div>
  </form>
</FormDialog>
