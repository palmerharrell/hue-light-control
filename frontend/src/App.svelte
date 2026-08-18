<script>
  import { onMount } from 'svelte'
  import LightCard from './LightCard.svelte'
  import SceneCard from './SceneCard.svelte'
  import ZoneBrightnessSlider from './ZoneBrightnessSlider.svelte'
  import CreateSceneForm from './CreateSceneForm.svelte'
  import AddFavoriteForm from './AddFavoriteForm.svelte'
  import ImportThemeForm from './ImportThemeForm.svelte'
  import { deleteJson, fetchJson, postJson, putJson } from './api.js'
  import { applyTheme, builtInThemes, DEFAULT_THEME_ID } from './themes.js'

  let lights = $state([])
  let lightsLoading = $state(true)
  let lightsError = $state(null)

  let scenes = $state([])
  let scenesLoading = $state(true)
  let scenesError = $state(null)

  let zones = $state([])
  let zonesLoading = $state(true)
  let zonesError = $state(null)

  // Favorited scene ids (issue #58) — a local UI preference stored server-
  // side (see backend/app/main.py's /api/favorites), not bridge data. A
  // load failure degrades to "no favorites" rather than blocking the rest
  // of the page, same treatment as zonesError below.
  let favoriteSceneIds = $state([])
  let favoritesError = $state(null)

  async function loadFavorites() {
    favoritesError = null
    try {
      favoriteSceneIds = await fetchJson('/api/favorites')
    } catch (err) {
      favoritesError = err.message
    }
  }

  // Persisted so the panel stays collapsed/expanded across reloads rather
  // than resetting every time the app is opened. localStorage access is
  // wrapped in try/catch since it can throw in restrictive browser
  // configurations (e.g. Safari with all cookies/storage blocked) — that
  // should just fall back to non-persisted state, not crash the app.
  function readBulbsCollapsed() {
    try {
      return localStorage.getItem('bulbsCollapsed') === 'true'
    } catch {
      return false
    }
  }

  let bulbsCollapsed = $state(readBulbsCollapsed())
  $effect(() => {
    try {
      localStorage.setItem('bulbsCollapsed', bulbsCollapsed)
    } catch {
      // Ignore — persistence is a nice-to-have, not required for the panel to work.
    }
  })

  // Theme (issue #21, replacing the warm/cool toggle from issue #20).
  // Built-in themes ship as app code (see themes.js); imported ones are
  // fetched from the backend below, same split as favorites/scenes (local
  // preference vs. bridge/app data).
  let customThemes = $state([])
  let themesError = $state(null)

  async function loadThemes() {
    themesError = null
    try {
      customThemes = await fetchJson('/api/themes')
    } catch (err) {
      themesError = err.message
    }
  }

  let allThemes = $derived([...builtInThemes, ...customThemes])

  function readThemeId() {
    try {
      return localStorage.getItem('themeId') ?? DEFAULT_THEME_ID
    } catch {
      return DEFAULT_THEME_ID
    }
  }

  let themeId = $state(readThemeId())
  // Falls back to the default theme if the persisted id no longer resolves
  // to anything — e.g. a previously-imported theme was removed elsewhere.
  let activeTheme = $derived(
    allThemes.find((t) => t.id === themeId) ?? allThemes.find((t) => t.id === DEFAULT_THEME_ID)
  )

  $effect(() => {
    if (!activeTheme) return
    applyTheme(activeTheme)
    try {
      localStorage.setItem('themeId', themeId)
    } catch {
      // Ignore — persistence is a nice-to-have, not required for the theme to apply.
    }
  })

  // Whether the "Import Theme" dialog is open (same one-dialog-at-a-time
  // shape as addFavoriteFormOpen).
  let importThemeFormOpen = $state(false)

  async function importTheme(theme) {
    const imported = await postJson('/api/themes', theme)
    customThemes = [...customThemes, imported]
    themeId = imported.id
  }

  // Only ever offered for a custom (imported) theme — see the template,
  // built-in themes have no delete control. Falls back to the default
  // theme if the one just deleted was active.
  //
  // Guarded against overlapping double-click requests and surfaces a
  // failure via themesError, same pattern as SceneCard's removeFavorite
  // (removePending/removeError) — otherwise a double-click's second DELETE
  // 404s (the first already removed it) and fails silently.
  let deletingThemeId = $state(null)

  async function deleteTheme(id) {
    if (deletingThemeId) return
    deletingThemeId = id
    themesError = null
    try {
      await deleteJson(`/api/themes/${id}`)
      customThemes = customThemes.filter((t) => t.id !== id)
      if (themeId === id) themeId = DEFAULT_THEME_ID
    } catch (err) {
      themesError = err.message
    } finally {
      deletingThemeId = null
    }
  }

  async function loadLights() {
    lightsLoading = true
    lightsError = null
    try {
      lights = await fetchJson('/api/lights')
    } catch (err) {
      lightsError = err.message
    } finally {
      lightsLoading = false
    }
  }

  // Same fetch as loadLights, but silent (no loading-state flicker in the
  // Bulbs section) — used after a scene activation, since that changes
  // multiple lights at once on the bridge and the local `lights` array
  // otherwise has no way to know. Scene cards derive their on/off and
  // brightness display from this same `lights` array (see SceneCard), so
  // this is also what keeps a scene's shown brightness from going stale
  // after another scene (or a manual brightness override) changes its
  // lights out from under it.
  //
  // Merges into the existing light objects in place rather than replacing
  // `lights` wholesale: toggleLight/setLightBrightness capture a specific
  // light object by reference and mutate it on PUT failure to revert/report
  // an error. If this ran concurrently with one of those and swapped in
  // fresh objects, a failure arriving afterward would mutate a now-detached
  // object — invisible to the UI, silently swallowing the revert/error.
  async function refreshLights() {
    try {
      const fresh = await fetchJson('/api/lights')
      const existingById = new Map(lights.map((light) => [light.id, light]))
      for (const updated of fresh) {
        const existing = existingById.get(updated.id)
        if (existing) {
          Object.assign(existing, updated)
        } else {
          lights.push(updated)
        }
      }
    } catch {
      // Leave the last-known lights in place; the existing Retry button
      // on the Bulbs section covers a genuinely failing bridge.
    }
  }

  async function loadScenes() {
    scenesLoading = true
    scenesError = null
    try {
      scenes = await fetchJson('/api/scenes')
    } catch (err) {
      scenesError = err.message
    } finally {
      scenesLoading = false
    }
  }

  // Same silent-refetch-and-merge shape as refreshLights, and for the same
  // reason: a scene's playing/speed (from CLIP v2's status.active, see
  // hue_client.get_scenes) can change on the bridge as a side effect of a
  // plain v1 activate — scenes authored with auto_dynamic start animating
  // immediately, with no play button involved — so activateScene needs a
  // way to resync without a loading-state flicker across the whole list.
  // Merges into existing scene objects in place, same reasoning as
  // refreshLights: playScene/stopScene/setSceneSpeed capture a specific
  // scene object by reference for their own optimistic-update-with-revert,
  // and a wholesale array replacement here could detach one mid-flight.
  async function refreshScenes() {
    try {
      const fresh = await fetchJson('/api/scenes')
      const existingById = new Map(scenes.map((scene) => [scene.id, scene]))
      for (const updated of fresh) {
        const existing = existingById.get(updated.id)
        if (existing) {
          Object.assign(existing, updated)
        } else {
          scenes.push(updated)
        }
      }
    } catch {
      // Leave the last-known scenes in place — same reasoning as refreshLights.
    }
  }

  async function loadZones() {
    zonesLoading = true
    zonesError = null
    try {
      zones = await fetchJson('/api/zones')
    } catch (err) {
      zonesError = err.message
    } finally {
      zonesLoading = false
    }
  }

  onMount(() => {
    loadLights()
    loadScenes()
    loadZones()
    loadFavorites()
    loadThemes()
  })

  // Buckets scenes under the zone they belong to. Scenes tied to a Room, an
  // Entertainment area, or no group at all (standalone LightScenes) don't
  // match any zone and land in "Other" — as does every scene if zones failed
  // to load. Every real zone is kept even with no scenes yet (isZone: true),
  // so its "New Scene" button (issue #30) has somewhere to live; "Other"
  // isn't a real zone (no per-zone create button applies to it) and is
  // dropped when empty.
  //
  // Favorites (issue #58) is a virtual zone prepended ahead of every real
  // one: not backed by a bridge group (isZone: false, so it gets no
  // ZoneBrightnessSlider — there's no single set of bulbs to control), but
  // always kept like a real zone (its own "+ Add" button needs somewhere to
  // live even with zero favorites yet). Its scenes are the actual Scene
  // objects from `scenes`, in favoriteSceneIds order, so activating one
  // still goes through that scene's own real group_id — Favorites is just a
  // curated view, not a separate copy.
  let zoneGroups = $derived.by(() => {
    const byId = new Map(
      zones.map((zone) => [
        zone.id,
        { id: zone.id, name: zone.name, lightIds: zone.light_ids, scenes: [], isZone: true },
      ])
    )
    const other = { id: 'other', name: 'Other', scenes: [], isZone: false }
    for (const scene of scenes) {
      const group = byId.get(scene.group_id) ?? other
      group.scenes.push(scene)
    }
    const scenesById = new Map(scenes.map((scene) => [scene.id, scene]))
    const favorites = {
      id: 'favorites',
      name: 'Favorites',
      scenes: favoriteSceneIds.map((id) => scenesById.get(id)).filter(Boolean),
      isZone: false,
      isFavorites: true,
    }
    return [favorites, ...byId.values(), other].filter(
      (group) => group.isZone || group.isFavorites || group.scenes.length > 0
    )
  })

  // Per-zone-group collapse state (issue #57), keyed by group id. Absent
  // means "use the default" rather than "expanded" — Favorites defaults
  // open, everything else defaults collapsed (issue #58) — so a group only
  // needs an entry here once the user has actually toggled it.
  let collapsedGroupIds = $state({})

  function isGroupCollapsed(groupId) {
    return collapsedGroupIds[groupId] ?? groupId !== 'favorites'
  }

  function toggleGroupCollapsed(groupId) {
    collapsedGroupIds[groupId] = !isGroupCollapsed(groupId)
  }

  // Note: a bridge write can succeed here (200) for a light that's
  // temporarily unreachable — Hue queues state changes for offline Zigbee
  // devices rather than rejecting them. In that case the optimistic value
  // below sticks even though the bulb hasn't physically changed yet; it
  // reconciles on the next /api/lights refetch. Not gating the toggle on
  // reachable is intentional (see LightCard) — this staleness window is an
  // accepted tradeoff of that.
  async function toggleLight(lightId, on) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = light.on
    light.on = on
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { on })
    } catch (err) {
      light.on = prev
      light.toggleError = err.message
    }
  }

  // Same optimistic-update-with-revert pattern as toggleLight. Dragging
  // brightness up implies the light is on, since a bulb reporting bri>0
  // while off wouldn't visually reflect the change until turned on.
  //
  // Unlike the toggle button, BrightnessSlider isn't disabled while a
  // request is in flight (that would fight the user mid-drag), so rapid
  // successive commits can leave overlapping PUTs in flight. Track the
  // latest request per light and only let a request revert/report an
  // error if it's still the latest one — otherwise an older request that
  // fails after a newer one already succeeded would stomp the newer,
  // already-applied value.
  const latestBrightnessRequest = new Map()

  async function setLightBrightness(lightId, pct) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = { on: light.on, brightness_pct: light.brightness_pct }
    const token = Symbol()
    latestBrightnessRequest.set(lightId, token)
    light.brightness_pct = pct
    light.on = true
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { brightness_pct: pct, on: true })
    } catch (err) {
      if (latestBrightnessRequest.get(lightId) === token) {
        Object.assign(light, prev)
        light.toggleError = err.message
      }
    }
  }

  // Same optimistic-update-with-revert-if-still-latest pattern as
  // setLightBrightness, tracked separately so an in-flight color request
  // isn't stomped by a color-temp request racing it (or vice versa).
  const latestColorRequest = new Map()
  const latestColorTempRequest = new Map()

  async function setLightColor(lightId, hex) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = { on: light.on, color: light.color }
    const token = Symbol()
    latestColorRequest.set(lightId, token)
    light.color = hex
    light.on = true
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { color: hex, on: true })
    } catch (err) {
      if (latestColorRequest.get(lightId) === token) {
        Object.assign(light, prev)
        light.toggleError = err.message
      }
    }
  }

  async function setLightColorTemp(lightId, pct) {
    const light = lights.find((l) => l.id === lightId)
    if (!light) return
    const prev = { on: light.on, color_temp_pct: light.color_temp_pct }
    const token = Symbol()
    latestColorTempRequest.set(lightId, token)
    light.color_temp_pct = pct
    light.on = true
    light.toggleError = null
    try {
      await putJson(`/api/lights/${lightId}/state`, { color_temp_pct: pct, on: true })
      // Unlike setLightBrightness/setLightColor, the optimistic update above
      // only sets color_temp_pct — it can't also approximate the header
      // swatch's `color` (rendered from whatever colormode the bulb reports),
      // so that would otherwise sit stale until some other action happens to
      // refresh `lights`. Refetch to pick up the bridge's recomputed color.
      await refreshLights()
    } catch (err) {
      if (latestColorTempRequest.get(lightId) === token) {
        Object.assign(light, prev)
        light.toggleError = err.message
      }
    }
  }

  // Which zone's "New Scene" dialog is open, if any (issue #30 — one button
  // per zone rather than a single global one).
  let createFormZone = $state(null)

  async function createScene(name, lightIds, groupId) {
    const scene = await postJson('/api/scenes', { name, light_ids: lightIds, group_id: groupId })
    scenes = [...scenes, scene]
  }

  // Whether the "Add to Favorites" dialog is open (issue #58's Favorites
  // footer button — same one-dialog-at-a-time shape as createFormZone).
  let addFavoriteFormOpen = $state(false)

  // addFavorites/removeFavorite can be triggered from independent controls
  // (the Add dialog, and a remove button on each favorited SceneCard) that
  // don't share an in-flight guard the way a single control's own
  // pending/submitting flag would. Without serializing, two overlapping
  // calls would each compute `updated` from the same stale favoriteSceneIds
  // snapshot, and whichever PUT resolves last would silently overwrite the
  // other's change (both locally and in the persisted config.yaml). Queuing
  // every mutation onto one promise chain ensures each only runs (and reads
  // favoriteSceneIds) after the previous one has fully applied.
  let favoritesQueue = Promise.resolve()

  function queueFavoritesUpdate(computeUpdated) {
    const run = favoritesQueue.then(async () => {
      const updated = computeUpdated(favoriteSceneIds)
      await putJson('/api/favorites', { scene_ids: updated })
      favoriteSceneIds = updated
    })
    // Keep the chain alive even after a failed update — the caller below
    // still sees the rejection via `run`, but the *next* queued mutation
    // shouldn't be blocked forever by an earlier one's error.
    favoritesQueue = run.catch(() => {})
    return run
  }

  async function addFavorites(sceneIds) {
    await queueFavoritesUpdate((current) => [...new Set([...current, ...sceneIds])])
  }

  async function removeFavorite(sceneId) {
    await queueFavoritesUpdate((current) => current.filter((id) => id !== sceneId))
  }

  // Unlike toggleLight, there's no meaningful "prior value" to optimistically
  // set and revert for a one-shot action like activating a scene — just
  // surface a per-card error on failure. SceneCard guards against overlapping
  // double-click requests itself (same pattern as LightCard's toggle button).
  async function activateScene(sceneId, groupId) {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return
    scene.activateError = null
    // Also clears any stale play/stop/speed error — a fresh activate makes
    // whatever previously failed there moot, and refreshScenes below is
    // about to report the current real state regardless.
    scene.playError = null
    try {
      await postJson(`/api/scenes/${sceneId}/activate`, { group_id: groupId })
      // Also resyncs playing/speed, not just lights: a recall can itself
      // start a dynamic animation for an auto_dynamic scene (see
      // refreshScenes), which this app has no way to predict client-side.
      await Promise.all([refreshLights(), refreshScenes()])
    } catch (err) {
      scene.activateError = err.message
    }
  }

  // Scenes in the same zone share the same bulbs, so there's no such thing
  // as a scene-specific brightness (issue #47) — this sets the zone's
  // brightness directly, independent of any scene. Errors are surfaced by
  // ZoneBrightnessSlider itself (it awaits this call), not stashed here.
  //
  // turnOn distinguishes two gestures that look the same (dragging the
  // slider up) but should behave differently: turnOn is only set when the
  // zone was fully off, where the drag is the explicit "turn the zone back
  // on" gesture and should apply to every light. Otherwise (some lights
  // already on) it's a plain brightness adjustment and must NOT force `on`
  // — the backend then only touches lights that are already on, leaving any
  // individually-off bulb in that zone alone rather than waking it up.
  async function setZoneBrightness(zoneId, pct, { turnOn = false } = {}) {
    await putJson(`/api/zones/${zoneId}/state`, { brightness_pct: pct, ...(turnOn ? { on: true } : {}) })
    await refreshLights()
  }

  async function setZoneOn(zoneId, on) {
    await putJson(`/api/zones/${zoneId}/state`, { on })
    await refreshLights()
  }

  // Play/stop/speed are dynamic-palette-only (CLIP v2) and don't affect the
  // v1-derived `lights` array the way activate/toggle do, so unlike
  // activateScene these don't refreshLights afterward — the resulting
  // per-color animation isn't representable in that model anyway.
  //
  // scene.playing/scene.speed are the bridge's own CLIP v2 status (see
  // hue_client.get_scenes) — not a client guess — so these optimistically
  // set them the same way toggleLight optimistically sets light.on, and
  // revert + surface scene.playError on failure. SceneCard reads
  // scene.playing/scene.speed directly rather than tracking its own copy.
  //
  // All three share one latest-request-wins guard, same pattern (and same
  // reason) as setLightBrightness's latestBrightnessRequest: they all touch
  // the same scene.playing/scene.speed fields, so e.g. a slow /play POST
  // failing after a since-succeeded speed drag must not revert that newer
  // speed — not just an older speed change racing a newer one.
  const latestSceneRequest = new Map()

  async function playScene(sceneId, speed) {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return
    const prev = { playing: scene.playing, speed: scene.speed }
    const token = Symbol()
    latestSceneRequest.set(sceneId, token)
    scene.playing = true
    scene.speed = speed
    scene.playError = null
    try {
      await postJson(`/api/scenes/${sceneId}/play`, { speed })
    } catch (err) {
      if (latestSceneRequest.get(sceneId) === token) {
        Object.assign(scene, prev)
        scene.playError = err.message
      }
    }
  }

  async function stopScene(sceneId) {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return
    const prev = scene.playing
    const token = Symbol()
    latestSceneRequest.set(sceneId, token)
    scene.playing = false
    scene.playError = null
    try {
      await postJson(`/api/scenes/${sceneId}/stop`, {})
    } catch (err) {
      if (latestSceneRequest.get(sceneId) === token) {
        scene.playing = prev
        scene.playError = err.message
      }
    }
  }

  async function setSceneSpeed(sceneId, speed) {
    const scene = scenes.find((s) => s.id === sceneId)
    if (!scene) return
    const prev = scene.speed
    const token = Symbol()
    latestSceneRequest.set(sceneId, token)
    scene.speed = speed
    try {
      await putJson(`/api/scenes/${sceneId}/speed`, { speed })
    } catch (err) {
      if (latestSceneRequest.get(sceneId) === token) {
        scene.speed = prev
        scene.playError = err.message
      }
    }
  }
</script>

<main>
  <div class="page-header">
    <div>
      <h1>Hue Light Control</h1>
      <p class="subtitle">Bulbs and scenes on your local Hue bridge</p>
    </div>
    <div class="theme-picker">
      <label class="select-wrap">
        <span class="sr-only">Theme</span>
        <select bind:value={themeId} aria-label="Theme">
          {#each builtInThemes as theme (theme.id)}
            <option value={theme.id}>{theme.name}</option>
          {/each}
          {#if customThemes.length > 0}
            <optgroup label="Imported">
              {#each customThemes as theme (theme.id)}
                <option value={theme.id}>{theme.name}</option>
              {/each}
            </optgroup>
          {/if}
        </select>
      </label>
      {#if customThemes.some((t) => t.id === themeId)}
        <button
          type="button"
          onclick={() => deleteTheme(themeId)}
          disabled={deletingThemeId === themeId}
          aria-label="Delete current theme"
        >
          Delete
        </button>
      {/if}
      <button type="button" onclick={() => (importThemeFormOpen = true)}>+ Import</button>
    </div>
  </div>

  {#if themesError}
    <p class="error">
      Couldn't load imported themes ({themesError}).
      <button onclick={loadThemes}>Retry</button>
    </p>
  {/if}

  {#if importThemeFormOpen}
    <ImportThemeForm onImport={importTheme} onClose={() => (importThemeFormOpen = false)} />
  {/if}

  <div class="layout">
    <aside class="bulbs-panel" class:collapsed={bulbsCollapsed}>
      <div class="section-header">
        <h2>Bulbs</h2>
        <button
          class="collapse-toggle"
          onclick={() => (bulbsCollapsed = !bulbsCollapsed)}
          aria-expanded={!bulbsCollapsed}
          aria-label={bulbsCollapsed ? 'Expand bulbs panel' : 'Collapse bulbs panel'}
        >
          <span class="chevron" class:collapsed={bulbsCollapsed}>▾</span>
        </button>
      </div>
      {#if !bulbsCollapsed}
        {#if lightsLoading}
          <p>Loading bulbs…</p>
        {:else if lightsError}
          <p class="error">{lightsError}</p>
          <button onclick={loadLights}>Retry</button>
        {:else if lights.length === 0}
          <p>No bulbs found.</p>
        {:else}
          <div class="bulbs-list">
            {#each lights as light (light.id)}
              <LightCard
                {light}
                onToggle={toggleLight}
                onBrightnessChange={setLightBrightness}
                onColorChange={setLightColor}
                onColorTempChange={setLightColorTemp}
              />
            {/each}
          </div>
        {/if}
      {/if}
    </aside>

    <section class="scenes-section">
      <div class="section-header">
        <h2>Scenes</h2>
      </div>
      {#if createFormZone}
        <CreateSceneForm
          {lights}
          {zones}
          fixedZone={createFormZone}
          onCreate={createScene}
          onClose={() => (createFormZone = null)}
        />
      {/if}
      {#if addFavoriteFormOpen}
        <AddFavoriteForm
          scenes={scenes.filter((scene) => !favoriteSceneIds.includes(scene.id))}
          onAdd={addFavorites}
          onClose={() => (addFavoriteFormOpen = false)}
        />
      {/if}
      {#if scenesLoading || zonesLoading}
        <p>Loading scenes…</p>
      {:else if scenesError}
        <p class="error">{scenesError}</p>
        <button onclick={loadScenes}>Retry</button>
      {:else}
        {#if zonesError}
          <p class="error">
            Couldn't load zones ({zonesError}) — showing scenes ungrouped.
            <button onclick={loadZones}>Retry</button>
          </p>
        {/if}
        {#if favoritesError}
          <p class="error">
            Couldn't load favorites ({favoritesError}).
            <button onclick={loadFavorites}>Retry</button>
          </p>
        {/if}
        {#if zoneGroups.length === 0}
          <p>No scenes found.</p>
        {/if}
        {#each zoneGroups as group (group.id)}
          <div class="zone-group">
            <div class="zone-header">
              <button
                class="collapse-toggle"
                onclick={() => toggleGroupCollapsed(group.id)}
                aria-expanded={!isGroupCollapsed(group.id)}
                aria-label={isGroupCollapsed(group.id) ? `Expand ${group.name}` : `Collapse ${group.name}`}
              >
                <span class="chevron" class:collapsed={isGroupCollapsed(group.id)}>▾</span>
              </button>
              <h3>{group.name}</h3>
              {#if group.isZone}
                <ZoneBrightnessSlider zone={group} {lights} onSetBrightness={setZoneBrightness} onSetZoneOn={setZoneOn} />
              {/if}
            </div>
            {#if !isGroupCollapsed(group.id)}
              {#if group.scenes.length === 0}
                <p class="hint">
                  {group.isFavorites ? 'No favorite scenes yet.' : 'No scenes in this zone yet.'}
                </p>
              {:else}
                <div class="grid">
                  {#each group.scenes as scene (scene.id)}
                    <SceneCard
                      {scene}
                      onActivate={activateScene}
                      onPlay={playScene}
                      onStop={stopScene}
                      onSpeedChange={setSceneSpeed}
                      onRemoveFavorite={group.isFavorites ? removeFavorite : undefined}
                    />
                  {/each}
                </div>
              {/if}
              {#if group.isZone}
                <div class="zone-group-footer">
                  <button onclick={() => (createFormZone = group)}>+ New Scene</button>
                </div>
              {/if}
              {#if group.isFavorites}
                <div class="zone-group-footer">
                  <button onclick={() => (addFavoriteFormOpen = true)}>+ Add</button>
                </div>
              {/if}
            {/if}
          </div>
        {/each}
      {/if}
    </section>
  </div>
</main>

<style>
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }

  h1 {
    margin: 0;
    font-size: 1.75rem;
    letter-spacing: -0.02em;
  }

  .subtitle {
    margin: 0.3rem 0 0;
    color: var(--text-muted);
    font-size: 0.95rem;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
  }

  .theme-picker {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  /* Native select arrows sit in a fixed browser-drawn gutter that ignores
     padding-right, so widening the padding alone left the arrow flush
     against the pill's edge. appearance: none drops that native icon in
     favor of a mask-drawn chevron below, positioned with real spacing from
     the edge and colored via currentColor so it still follows the theme. */
  .select-wrap {
    position: relative;
    display: inline-flex;
  }

  .select-wrap::after {
    content: '';
    position: absolute;
    top: 50%;
    right: 0.9rem;
    width: 0.65rem;
    height: 0.65rem;
    transform: translateY(-50%);
    background: var(--text-muted);
    /* Safari requires the -webkit- prefix for CSS masks (no autoprefixer
       in this build) — without it the chevron silently fails to render
       there, worse than before since appearance: none below already
       removes Safari's native arrow. */
    -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")
      center / contain no-repeat;
    mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E")
      center / contain no-repeat;
    pointer-events: none;
  }

  .theme-picker select {
    font: inherit;
    font-size: 0.85rem;
    padding: 0.35rem 2.3rem 0.35rem 0.9rem;
    min-width: 9rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: inherit;
    appearance: none;
    -webkit-appearance: none;
  }

  .theme-picker button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.35rem 0.9rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: inherit;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .theme-picker button:hover {
    filter: brightness(0.95);
  }

  .layout {
    display: flex;
    align-items: flex-start;
    gap: 2rem;
    margin-top: 2.5rem;
  }

  .bulbs-panel {
    flex: 0 0 18rem;
    min-width: 0;
  }

  .bulbs-panel.collapsed {
    flex-basis: auto;
  }

  .scenes-section {
    flex: 1 1 auto;
    min-width: 0;
  }

  @media (max-width: 55rem) {
    .layout {
      flex-direction: column;
    }

    .bulbs-panel {
      flex-basis: auto;
      width: 100%;
    }
  }

  .bulbs-panel h2,
  .scenes-section h2 {
    margin: 0 0 1.25rem;
    font-size: 1.15rem;
    letter-spacing: -0.01em;
  }

  .bulbs-panel .section-header {
    margin-bottom: 1.25rem;
  }

  .bulbs-panel .section-header h2 {
    margin-bottom: 0;
  }

  .collapse-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    padding: 0;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: inherit;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .collapse-toggle:hover {
    filter: brightness(0.95);
  }

  .chevron {
    display: inline-block;
    transition: transform 0.15s ease;
  }

  .chevron.collapsed {
    transform: rotate(-90deg);
  }

  .bulbs-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .zone-group-footer button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.4rem 0.9rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface-alt);
    color: inherit;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .zone-group-footer button:hover {
    filter: brightness(0.95);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
    gap: 1rem;
  }

  .zone-group {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface-alt);
    padding: 1.25rem;
  }

  .zone-group + .zone-group {
    margin-top: 1.5rem;
  }

  .zone-header {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 0.75rem;
  }

  .zone-header h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .zone-group-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
  }

  .hint {
    font-size: 0.85rem;
    color: var(--text-muted);
    margin: 0;
  }

  .error {
    color: var(--error-text);
  }
</style>
