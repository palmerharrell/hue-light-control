<script>
  // "Classic" recreates the old app's single-screen layout (issue #77) —
  // deliberately feature-reduced (no favorites, no dynamic-scene controls)
  // and NOT part of the CSS-variable theme token system the other themes
  // share (see themes.js): every color/size below is the literal value from
  // the design handoff, not a var(--token). This view fully replaces
  // App.svelte's normal header+layout while Classic is active.
  let {
    lights,
    zones,
    scenes,
    themeId,
    builtInThemes,
    onThemeChange,
    onToggleLight,
    onSetBrightness,
    onZoneOn,
    onActivateScene,
    onRefresh,
    onAllOn,
    onAllOff,
    onOverallBrightness,
  } = $props()

  // Fixed at 2 per the handoff ("ship 2"); the prototype exposes this as a
  // 1-3 design prop, but nothing in the real app needs it configurable.
  const SCENE_COLUMN_COUNT = 2

  // Client-side only, per the handoff's State Management section: the Hue
  // API doesn't report an "active scene", so this is just local UI
  // highlighting, keyed by zone id and cleared on refresh.
  let activeScenes = $state({})

  // Not derived from `lights` — the handoff explicitly allows keeping this
  // write-only rather than deriving it from bridge state.
  let master = $state(50)

  // Real zones joined with their scenes by group_id — no Favorites, no
  // "Other" bucket for ungrouped scenes, unlike the normal theme's
  // zoneGroups in App.svelte. That's intentional feature-reduction, not an
  // oversight: Classic only shows what the old app showed.
  let zoneGroups = $derived(
    zones.map((zone) => ({
      ...zone,
      scenes: scenes.filter((scene) => scene.group_id === zone.id),
    }))
  )

  // Balanced, count-based column split (not masonry) per the handoff:
  // perCol = ceil(zoneCount / N), taken in order.
  let columns = $derived.by(() => {
    if (zoneGroups.length === 0) return []
    const perCol = Math.ceil(zoneGroups.length / SCENE_COLUMN_COUNT)
    const cols = []
    for (let c = 0; c < SCENE_COLUMN_COUNT; c++) {
      const slice = zoneGroups.slice(c * perCol, (c + 1) * perCol)
      if (slice.length > 0) cols.push(slice)
    }
    return cols
  })

  async function handleRefresh() {
    activeScenes = {}
    await onRefresh()
  }

  async function handleActivate(zone, scene) {
    await onActivateScene(scene.id, zone.id)
    // activateScene (App.svelte) swallows its own errors into
    // scene.activateError rather than rethrowing (same pattern as the
    // normal theme's SceneCard), so a failed activation resolves here
    // just like a successful one — check the mutated scene object itself
    // rather than treating a resolved await as success.
    if (scene.activateError) return
    activeScenes = { ...activeScenes, [zone.id]: scene.id }
  }

  // Dragging the master slider fires many `input` events; sending a full
  // round of per-light PUTs (see setOverallBrightness) on every tick would
  // flood the bridge. Throttled to at most one in-flight commit per
  // interval, with the trailing value always sent on `change` (drag
  // release) so the final position is never dropped by the throttle.
  const MASTER_COMMIT_INTERVAL_MS = 150
  let lastMasterCommitAt = 0

  function handleMasterInput(event) {
    master = Number(event.currentTarget.value)
    const now = Date.now()
    if (now - lastMasterCommitAt < MASTER_COMMIT_INTERVAL_MS) return
    lastMasterCommitAt = now
    onOverallBrightness(master)
  }

  function handleMasterChange(event) {
    master = Number(event.currentTarget.value)
    lastMasterCommitAt = Date.now()
    onOverallBrightness(master)
  }

  // Zone on/off has no optimistic value to revert (unlike toggleLight), so
  // there's nothing to undo on failure — just make sure a rejected PUT
  // (setZoneOn in App.svelte has no try/catch of its own) doesn't become an
  // unhandled promise rejection, and give the user something rather than
  // silent failure.
  let zoneError = $state(null)

  async function handleZoneOn(zone, on) {
    zoneError = null
    try {
      await onZoneOn(zone.id, on)
    } catch (err) {
      zoneError = `${zone.name}: ${err.message}`
    }
  }
</script>

<div class="classic">
  <div class="master-wrap">
    <div class="master">
      <div class="master-row">
        <div class="title">Master</div>
        <div class="master-buttons">
          <button type="button" class="pill pill-dark" onclick={onAllOff}>All Off</button>
          <button type="button" class="pill pill-dark" onclick={onAllOn}>All On</button>
        </div>
        <div class="master-right">
          <label class="theme-select-wrap">
            <span class="sr-only">Theme</span>
            <select
              class="theme-select"
              value={themeId}
              onchange={(event) => onThemeChange(event.currentTarget.value)}
              aria-label="Theme"
            >
              {#each builtInThemes as theme (theme.id)}
                <option value={theme.id}>{theme.name}</option>
              {/each}
            </select>
          </label>
          <button type="button" class="pill pill-mid" onclick={handleRefresh}>Load/Refresh Lights</button>
        </div>
      </div>
      <div class="master-caption">Overall Brightness</div>
      <input
        class="slider slider-master"
        type="range"
        min="0"
        max="100"
        value={master}
        oninput={handleMasterInput}
        onchange={handleMasterChange}
        aria-label="Overall brightness"
      />
    </div>
  </div>

  {#if zoneError}
    <p class="zone-error">{zoneError}</p>
  {/if}

  <div class="body">
    <div class="panel scenes-panel">
      <div class="panel-heading">Scenes</div>
      <div class="columns">
        {#each columns as column, i (i)}
          <div class="column">
            {#each column as zone (zone.id)}
              <div class="zone-card">
                <div class="zone-header">
                  <div class="zone-name">{zone.name}</div>
                  <div class="zone-onoff">
                    <button type="button" class="zone-off" onclick={() => handleZoneOn(zone, false)}>Off</button>
                    <button type="button" class="zone-on" onclick={() => handleZoneOn(zone, true)}>On</button>
                  </div>
                </div>
                <div class="scene-tiles">
                  {#each zone.scenes as scene (scene.id)}
                    <button
                      type="button"
                      class="scene-tile"
                      class:active={activeScenes[zone.id] === scene.id}
                      onclick={() => handleActivate(zone, scene)}
                    >
                      {scene.name}
                    </button>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {/each}
      </div>
    </div>

    <div class="panel lights-panel">
      <div class="panel-heading">Lights</div>
      <div class="lights-list">
        {#each lights as light (light.id)}
          <div class="light-row">
            <div class="light-top">
              <button type="button" class="light-name" onclick={() => onToggleLight(light.id, !light.on)}>
                {light.name}
              </button>
              <span
                class="swatch"
                class:on={light.on}
                style:background={light.on ? (light.color ?? '#ffe9b3') : undefined}
                style:box-shadow={light.on ? `0 0 10px ${light.color ?? '#ffe9b3'}` : undefined}
              ></span>
            </div>
            <input
              class="slider slider-light"
              type="range"
              min="0"
              max="100"
              value={light.brightness_pct}
              onchange={(event) => onSetBrightness(light.id, Number(event.currentTarget.value))}
              aria-label="{light.name} brightness"
            />
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .classic {
    min-height: 100vh;
    background: #0d181f;
    font-family: 'Helvetica Neue', Helvetica, -apple-system, system-ui, sans-serif;
    color: #eef4f7;
    padding: 0 24px 64px;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
  }

  .master-wrap {
    position: sticky;
    top: 0;
    z-index: 20;
    padding-top: 20px;
    display: flex;
    justify-content: center;
    pointer-events: none;
  }

  .master {
    pointer-events: auto;
    width: 100%;
    max-width: 1280px;
    background: #69a3a4;
    border: 2px solid #16242e;
    border-radius: 28px;
    padding: 16px 20px 18px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .master-row {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .title {
    flex: 0 0 auto;
    font-size: 30px;
    font-weight: 400;
    color: #14232c;
    letter-spacing: -0.01em;
  }

  .master-buttons {
    flex: 1 1 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
  }

  .master-right {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .pill {
    font: inherit;
    font-size: 15px;
    color: #eef4f7;
    border-radius: 999px;
    cursor: pointer;
  }

  .pill-dark {
    background: #16242e;
    border: 1px solid #0f1c25;
    padding: 10px 26px;
  }

  .pill-dark:hover {
    background: #1e3140;
  }

  .pill-mid {
    background: #2b3d4b;
    border: 1px solid #16242e;
    padding: 10px 22px;
  }

  .pill-mid:hover {
    background: #354a5b;
  }

  .theme-select-wrap {
    display: inline-flex;
    align-items: center;
  }

  .theme-select {
    font: inherit;
    font-size: 14px;
    color: #eef4f7;
    background-color: #2b3d4b;
    border: 1px solid #16242e;
    border-radius: 999px;
    padding: 9px 38px 9px 16px;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5 L6 6.5 L11 1.5 Z' fill='%23eef4f7'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 16px center;
    background-size: 11px 8px;
  }

  .master-caption {
    text-align: center;
    font-size: 15px;
    color: #14232c;
  }

  .slider {
    -webkit-appearance: none;
    appearance: none;
    background: transparent;
    cursor: pointer;
  }

  .slider::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 999px;
    background: #0f1c25;
    border: 1px solid #223543;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 32px;
    height: 20px;
    margin-top: -9px;
    border-radius: 4px;
    background: #5b7f96;
    border: 1px solid #16242e;
  }

  .slider::-moz-range-track {
    height: 4px;
    border-radius: 999px;
    background: #0f1c25;
    border: 1px solid #223543;
  }

  .slider::-moz-range-thumb {
    width: 32px;
    height: 20px;
    border-radius: 4px;
    background: #5b7f96;
    border: 1px solid #16242e;
  }

  .slider-master {
    width: 100%;
    height: 30px;
  }

  .slider-master::-webkit-slider-runnable-track {
    height: 26px;
    border-radius: 999px;
    background: #0f1c25;
    border: 2px solid #16242e;
  }

  .slider-master::-webkit-slider-thumb {
    width: 16px;
    height: 34px;
    margin-top: -6px;
    border-radius: 5px;
    background: #5b7f96;
    border: 1px solid #0d181f;
  }

  .slider-master::-moz-range-track {
    height: 26px;
    border-radius: 999px;
    background: #0f1c25;
    border: 2px solid #16242e;
  }

  .slider-master::-moz-range-thumb {
    width: 16px;
    height: 34px;
    border-radius: 5px;
    background: #5b7f96;
    border: 1px solid #0d181f;
  }

  .zone-error {
    max-width: 1280px;
    margin: 12px auto 0;
    color: #f0958a;
    font-size: 14px;
  }

  .body {
    display: flex;
    align-items: flex-start;
    gap: 24px;
    max-width: 1280px;
    margin: 28px auto 0;
    flex-wrap: wrap;
  }

  .panel {
    background: #69a3a4;
    border: 2px solid #16242e;
    border-radius: 28px;
    padding: 18px 20px 24px;
  }

  .scenes-panel {
    flex: 1 1 620px;
    min-width: 0;
  }

  .lights-panel {
    flex: 0 1 340px;
    min-width: 260px;
  }

  .panel-heading {
    font-size: 28px;
    color: #14232c;
    margin: 0 0 14px 6px;
  }

  .columns {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 18px;
    align-items: start;
  }

  .column {
    display: flex;
    flex-direction: column;
    gap: 18px;
    min-width: 0;
  }

  .zone-card {
    background: #15222c;
    border-radius: 22px;
    padding: 12px 14px 16px;
  }

  .zone-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .zone-name {
    font-size: 15px;
    color: #8fb9bf;
    padding-left: 4px;
  }

  .zone-onoff {
    display: flex;
    overflow: hidden;
    border-radius: 0 0 12px 12px;
    margin-top: -12px;
    flex: 0 0 auto;
  }

  .zone-onoff button {
    font: inherit;
    font-size: 13px;
    color: #eef4f7;
    border: none;
    padding: 6px 18px;
    cursor: pointer;
  }

  .zone-off {
    background: #253744;
  }

  .zone-off:hover {
    background: #2e4252;
  }

  .zone-on {
    background: #2b3d4b;
  }

  .zone-on:hover {
    background: #354a5b;
  }

  .scene-tiles {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
  }

  .scene-tile {
    font: inherit;
    font-size: 15px;
    text-align: left;
    color: #eef4f7;
    background: #2b3d4b;
    border: 1px solid #2b3d4b;
    border-radius: 999px;
    padding: 12px 14px;
    cursor: pointer;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .scene-tile:hover {
    background: #354a5b;
  }

  .scene-tile.active {
    background: #3f5a6d;
    border-color: #8fb9bf;
  }

  .lights-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .light-row {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .light-top {
    display: flex;
    align-items: center;
  }

  .light-name {
    flex: 1 1 auto;
    min-width: 0;
    font: inherit;
    font-size: 15px;
    text-align: left;
    color: #dfeef2;
    background: #16232c;
    border: none;
    border-radius: 14px;
    padding: 13px 40px 13px 16px;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .light-name:hover {
    background: #1e3140;
  }

  .swatch {
    width: 52px;
    height: 52px;
    box-sizing: border-box;
    border-radius: 50%;
    margin-left: -30px;
    flex: 0 0 auto;
    background: #16232c;
    border: 4px solid #69a3a4;
  }

  .swatch.on {
    border: none;
  }

  .slider-light {
    width: calc(100% - 44px);
    height: 20px;
    margin-top: -1px;
  }
</style>
