<script>
  import { onMount } from 'svelte'

  // Shared <dialog> mechanism for CreateSceneForm and AddFavoriteForm:
  // opens itself on mount, and closes on a genuine backdrop click. The
  // caller owns the dialog element (bind:dialogEl) so its own submit/cancel
  // handlers can call dialogEl.close() directly, same as before this was
  // extracted.
  let { onClose, dialogEl = $bindable(null), children } = $props()

  onMount(() => {
    dialogEl?.showModal()
  })

  function handleBackdropClick(event) {
    // Any click that doesn't land on a child element (backdrop AND the
    // dialog's own padding around the form) reports target === dialog — so
    // that check alone can't tell a real backdrop click from one that
    // landed in the card's padding (visually still inside the card).
    // Compare coordinates against the dialog's own rendered box instead
    // (its border box, which includes the padding): only a click outside
    // that box is a real click on the backdrop.
    const rect = dialogEl.getBoundingClientRect()
    const outside =
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    if (outside) {
      dialogEl.close()
    }
  }
</script>

<dialog bind:this={dialogEl} onclose={onClose} onclick={handleBackdropClick}>
  {@render children()}
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
</style>
