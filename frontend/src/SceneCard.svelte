<script>
  let { scene, onActivate } = $props()

  // Standalone LightScenes (no group_id) can't be activated via the
  // group-action endpoint (see HUE_API.md's Scenes section) — render them
  // as non-interactive instead of wiring up a click handler.
  let activatable = $derived(scene.group_id != null)

  // Serializes activation clicks for this card: while a request is in
  // flight the button is disabled, so a fast double-click can't fire a
  // second overlapping activate request.
  let pending = $state(false)

  async function activate() {
    if (pending || !activatable) return
    pending = true
    try {
      await onActivate(scene.id, scene.group_id)
    } finally {
      pending = false
    }
  }
</script>

<div class="card" class:inactive={!activatable}>
  <button
    type="button"
    class="activate"
    disabled={!activatable || pending}
    title={activatable ? undefined : "Can't activate — not part of a zone"}
    onclick={() => activate()}
  >
    <span class="name">{scene.name}</span>
    {#if scene.activateError}
      <span class="badge error-badge">{scene.activateError}</span>
    {/if}
  </button>
</div>

<style>
  .card {
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    border-radius: 0.75rem;
    display: flex;
    flex-direction: column;
    background: light-dark(#fff, #1e1e1e);
    width: 100%;
    box-shadow: 0 1px 2px light-dark(rgba(0, 0, 0, 0.04), rgba(0, 0, 0, 0.2));
    transition: box-shadow 0.15s ease;
  }

  .card:not(.inactive):hover {
    box-shadow: 0 2px 8px light-dark(rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.3));
  }

  .card.inactive {
    opacity: 0.55;
  }

  .activate {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 0.6rem;
    width: 100%;
    height: 100%;
    flex: 1;
    border: none;
    border-radius: inherit;
    padding: 1rem;
    margin: 0;
    background: none;
    font: inherit;
    text-align: left;
    color: inherit;
    cursor: pointer;
  }

  .activate:hover:not(:disabled) {
    filter: brightness(0.97);
  }

  .activate:focus-visible {
    outline: 2px solid light-dark(#1c7a2e, #7fe396);
    outline-offset: -2px;
  }

  .activate:disabled {
    cursor: default;
  }

  .name {
    font-weight: 600;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    background: light-dark(#eee, #333);
    color: light-dark(#555, #ccc);
    width: fit-content;
  }

  .error-badge {
    background: light-dark(#fbe3e0, #3d211f);
    color: light-dark(#a3392c, #f0958a);
  }
</style>
