<script>
  // The bridge (and backend validation) rejects brightness_pct below 1 — 0
  // isn't a meaningful "on" brightness. Callers that want a 0 rung (e.g. the
  // zone slider, where 0 means "turn off") pass min={0} and must translate a
  // 0 onChange into an off command themselves rather than brightness_pct: 0.
  let { value, min = 1, max = 100, disabled = false, showValue = true, label, onChange } = $props()
  let localValue = $state(value)
  $effect(() => { localValue = value })
</script>

<div class="brightness">
  <input
    type="range"
    {min} {max}
    bind:value={localValue}
    {disabled}
    aria-label={label}
    onchange={() => onChange(Number(localValue))}
  />
  {#if showValue}
    <span class="brightness-label">{localValue}%</span>
  {/if}
</div>

<style>
  .brightness {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  input[type='range'] {
    flex: 1;
    appearance: none;
    -webkit-appearance: none;
    height: 0.4rem;
    border-radius: var(--radius-pill);
    background: var(--surface-alt);
    outline: none;
  }

  input[type='range']:disabled {
    opacity: 0.55;
  }

  input[type='range']::-webkit-slider-thumb {
    appearance: none;
    -webkit-appearance: none;
    width: 0.9rem;
    height: 0.9rem;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
  }

  input[type='range']::-moz-range-thumb {
    width: 0.9rem;
    height: 0.9rem;
    border: none;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
  }

  input[type='range']::-moz-range-progress {
    background: var(--accent);
    border-radius: var(--radius-pill);
    height: 0.4rem;
  }

  .brightness-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    width: 2.5rem;
    text-align: right;
  }
</style>
