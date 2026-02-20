<script>
  import { registry, subjects, currentReport } from '../lib/stores.js'
  import { postTimegraph } from '../lib/api.js'

  let subjectId = $state('')
  let moduleId = $state('')
  let markerId = $state('')
  let startTime = $state('')
  let endTime = $state('')
  let healthyMin = $state('')
  let healthyMax = $state('')
  let vulnerabilityMargin = $state(0.1)
  let polynomialDegree = $state(2)
  let loading = $state(false)
  let error = $state('')

  let selectedModule = $derived(
    $registry?.modules?.find(m => m.module_id === moduleId) ?? null
  )
  let markerOptions = $derived(selectedModule?.markers ?? [])

  function onModuleChange() {
    markerId = markerOptions[0]?.marker_id ?? ''
  }

  // Convert datetime-local string ("2026-01-05T08:00") to ISO UTC string
  function toISO(localStr) {
    if (!localStr) return ''
    return new Date(localStr).toISOString()
  }

  async function handleSubmit(e) {
    e.preventDefault()
    error = ''
    loading = true
    try {
      const result = await postTimegraph({
        subject_id: subjectId,
        module_id: moduleId,
        marker_id: markerId,
        timeframe: {
          start_time: toISO(startTime),
          end_time: toISO(endTime),
        },
        zone_boundaries: {
          healthy_min: parseFloat(healthyMin),
          healthy_max: parseFloat(healthyMax),
          vulnerability_margin: parseFloat(vulnerabilityMargin),
        },
        fitting: {
          polynomial_degree: parseInt(polynomialDegree),
        },
      })
      currentReport.set(result)
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }
</script>

<form onsubmit={handleSubmit}>
  <fieldset>
    <legend>Subject / Marker</legend>
    <label>
      Subject
      <select bind:value={subjectId} required>
        <option value="" disabled>Select subject</option>
        {#each $subjects as s}
          <option value={s}>{s}</option>
        {/each}
      </select>
    </label>

    <label>
      Module
      <select bind:value={moduleId} onchange={onModuleChange} required>
        <option value="" disabled>Select module</option>
        {#each $registry?.modules ?? [] as m}
          <option value={m.module_id}>{m.module_id}</option>
        {/each}
      </select>
    </label>

    <label>
      Marker
      <select bind:value={markerId} required>
        <option value="" disabled>Select marker</option>
        {#each markerOptions as mk}
          <option value={mk.marker_id}>{mk.marker_id}</option>
        {/each}
      </select>
    </label>
  </fieldset>

  <fieldset>
    <legend>Timeframe</legend>
    <label>
      From
      <input type="datetime-local" bind:value={startTime} required />
    </label>
    <label>
      To
      <input type="datetime-local" bind:value={endTime} required />
    </label>
  </fieldset>

  <fieldset>
    <legend>Zone Boundaries</legend>
    <label>
      Healthy Min
      <input type="number" step="any" bind:value={healthyMin} required />
    </label>
    <label>
      Healthy Max
      <input type="number" step="any" bind:value={healthyMax} required />
    </label>
    <label>
      Vulnerability Margin (h-space)
      <input type="number" step="any" bind:value={vulnerabilityMargin} required />
    </label>
  </fieldset>

  <fieldset>
    <legend>Fitting</legend>
    <label>
      Polynomial Degree
      <input type="number" min="1" max="10" bind:value={polynomialDegree} required />
    </label>
  </fieldset>

  <div class="actions">
    <button type="submit" disabled={loading}>
      {loading ? 'Running…' : 'Run Analysis'}
    </button>
    {#if error}
      <span class="error">{error}</span>
    {/if}
  </div>
</form>

<style>
  form {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
  }
  fieldset {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-width: 200px;
  }
  legend {
    font-weight: 600;
    font-size: 0.85rem;
    color: #555;
  }
  label {
    display: flex;
    flex-direction: column;
    font-size: 0.85rem;
    gap: 0.2rem;
  }
  input, select {
    padding: 0.3rem 0.4rem;
    border: 1px solid #bbb;
    border-radius: 3px;
    font-size: 0.9rem;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    align-self: flex-end;
    padding-bottom: 0.5rem;
  }
  button {
    padding: 0.5rem 1.2rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.95rem;
  }
  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .error {
    color: #dc2626;
    font-size: 0.85rem;
  }
</style>
