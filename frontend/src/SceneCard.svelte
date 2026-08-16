<script>
  import BrightnessSlider from './BrightnessSlider.svelte'

  let { scene, onActivate, onPlay, onStop, onSpeedChange } = $props()

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
      // onActivate also refreshes this scene's playing/speed from the
      // bridge afterward — a plain v1 recall can itself start a dynamic
      // animation for scenes authored with `auto_dynamic: true` (see
      // App.svelte's activateScene), so `scene.playing` isn't something
      // this card can infer client-side; it has to ask the bridge.
      await onActivate(scene.id, scene.group_id)
    } finally {
      pending = false
    }
  }

  // The card used to be a single <button>, but it now contains a nested
  // play/stop <button> and a range input — both invalid/unreliable inside
  // a <button> element (the HTML parser doesn't actually nest a <button>
  // inside another). It's a role="button" div instead, with the same
  // keyboard activation (Enter/Space) a real button gets for free.
  function activateOnKey(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      activate()
    }
  }

  // scene.playing/scene.speed are bridge ground truth (CLIP v2's
  // status.active — see hue_client.get_scenes), not a client guess: some
  // scenes are authored with auto_dynamic and start animating from a plain
  // activate, with no play button involved, so this card can't derive
  // "is it playing" on its own. onPlay/onStop/onSpeedChange (App.svelte)
  // own the optimistic mutation of the scene object and revert-on-error;
  // this card just reflects scene.playing/scene.speed and tracks its own
  // in-flight state for disabling the button mid-request.
  let playPending = $state(false)

  // Stops both click and keydown from reaching the outer card's
  // activate handler — needed on both event types since a keyboard
  // Enter/Space on this button dispatches a keydown that would otherwise
  // bubble to the card's onkeydown and also recall the whole scene.
  function stopBubble(event) {
    event.stopPropagation()
  }

  async function togglePlay(event) {
    event.stopPropagation()
    if (playPending) return
    playPending = true
    try {
      if (scene.playing) {
        await onStop(scene.id)
      } else {
        await onPlay(scene.id, scene.speed ?? 0.5)
      }
    } finally {
      playPending = false
    }
  }

  function changeSpeed(value) {
    onSpeedChange(scene.id, Number(value) / 100)
  }
</script>

<div class="card" class:inactive={!activatable}>
  <div
    class="activate"
    class:disabled={!activatable || pending}
    role="button"
    tabindex={activatable && !pending ? 0 : -1}
    aria-disabled={!activatable || pending}
    title={activatable ? undefined : "Can't activate — not part of a zone"}
    onclick={() => activate()}
    onkeydown={activateOnKey}
  >
    <span class="name-row">
      <span class="name">{scene.name}</span>
      <button
        type="button"
        class="play-toggle"
        class:playing={scene.playing}
        disabled={playPending}
        title={scene.playing ? 'Stop dynamic effect' : 'Play dynamic effect'}
        onclick={togglePlay}
        onkeydown={stopBubble}
      >
        {scene.playing ? '⏸' : '▶'}
      </button>
    </span>
    {#if scene.playing}
      <div
        class="speed-row"
        role="group"
        aria-label="{scene.name} speed control"
        onclick={stopBubble}
        onkeydown={stopBubble}
      >
        <BrightnessSlider
          value={Math.round((scene.speed ?? 0.5) * 100)}
          label="{scene.name} speed"
          min={0}
          showValue={false}
          onChange={changeSpeed}
        />
      </div>
    {/if}
    {#if scene.activateError}
      <span class="badge error-badge">{scene.activateError}</span>
    {/if}
    {#if scene.playError}
      <span class="badge error-badge">{scene.playError}</span>
    {/if}
  </div>
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

  .activate:hover:not(.disabled) {
    filter: brightness(0.97);
  }

  .activate:focus-visible {
    outline: 2px solid light-dark(#1c7a2e, #7fe396);
    outline-offset: -2px;
  }

  .activate.disabled {
    cursor: default;
  }

  .name-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    width: 100%;
  }

  .name {
    font-weight: 600;
  }

  .play-toggle {
    flex-shrink: 0;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 50%;
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    background: light-dark(#f4f4f4, #2a2a2a);
    font-size: 0.75rem;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: inherit;
  }

  .play-toggle:hover:not(:disabled) {
    filter: brightness(0.95);
  }

  .play-toggle:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .play-toggle.playing {
    background: light-dark(#dff0e0, #1f3a26);
    border-color: light-dark(#9fd6a8, #2f5a3b);
  }

  .speed-row {
    width: 100%;
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
