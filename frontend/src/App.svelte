<script>
  import { onMount } from 'svelte'
  import { registry, subjects, currentReport } from './lib/stores.js'
  import { getRegistry, getSubjects } from './lib/api.js'
  import TimeGraphForm from './components/TimeGraphForm.svelte'
  import TrajectoryChart from './components/TrajectoryChart.svelte'
  import TrajectoryTable from './components/TrajectoryTable.svelte'

  onMount(async () => {
    const [reg, subs] = await Promise.all([getRegistry(), getSubjects()])
    registry.set(reg)
    subjects.set(subs)
  })
</script>

<main>
  <h1>AsHDT</h1>
  <TimeGraphForm />
  {#if $currentReport}
    <TrajectoryChart />
    <TrajectoryTable />
  {/if}
</main>

<style>
  main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
    font-family: sans-serif;
  }
  h1 {
    margin-bottom: 1.5rem;
  }
</style>
