<script>
  // The bridge (and backend validation) rejects brightness_pct below 1 —
  // 0 isn't a meaningful "on" brightness, off is the separate toggle.
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
    border-radius: 999px;
    background: light-dark(#eee, #333);
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
    background: light-dark(#333, #ddd);
    cursor: pointer;
  }

  input[type='range']::-moz-range-thumb {
    width: 0.9rem;
    height: 0.9rem;
    border: none;
    border-radius: 50%;
    background: light-dark(#333, #ddd);
    cursor: pointer;
  }

  input[type='range']::-moz-range-progress {
    background: light-dark(#333, #ddd);
    border-radius: 999px;
    height: 0.4rem;
  }

  .brightness-label {
    font-size: 0.75rem;
    color: light-dark(#666, #aaa);
    width: 2.5rem;
    text-align: right;
  }
</style>
