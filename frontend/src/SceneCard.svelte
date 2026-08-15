<script>
  let { scene } = $props()
</script>

<div class="card">
  <span class="name">{scene.name}</span>
  <span class="badge">{scene.light_count} {scene.light_count === 1 ? 'light' : 'lights'}</span>
</div>

<style>
  .card {
    border: 1px solid light-dark(#d8d8d8, #3a3a3a);
    border-radius: 0.75rem;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    background: light-dark(#fff, #1e1e1e);
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
</style>
