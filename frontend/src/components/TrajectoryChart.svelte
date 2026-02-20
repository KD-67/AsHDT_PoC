<script>
  import { onMount } from 'svelte'
  import Plotly from 'plotly.js-dist-min'
  import { currentReport } from '../lib/stores.js'

  let chartDiv

  const QUALITY_SIZE = { good: 12, degraded: 8, bad: 5 }
  const ZONE_COLOR   = { non_pathology: '#22c55e', vulnerability: '#f59e0b', pathology: '#ef4444' }

  // Horner's method for polynomial evaluation
  function polyval(coeffs, x) {
    return coeffs.reduce((acc, c) => acc * x + c, 0)
  }

  function buildTraces(report) {
    const { data_points, fit_metadata } = report
    const { coefficients, t0_iso, zone_boundaries, normalization } = fit_metadata
    const vm = zone_boundaries.vulnerability_margin
    const t0 = new Date(t0_iso)

    // Raw scatter
    const scatter = {
      name: 'Raw data',
      type: 'scatter',
      mode: 'markers',
      x: data_points.map(d => d.timestamp),
      y: data_points.map(d => d.health_score),
      marker: {
        size: data_points.map(d => QUALITY_SIZE[d.data_quality] ?? 8),
        color: data_points.map(d => ZONE_COLOR[d.zone]),
        line: { width: 1, color: '#fff' },
      },
      hovertemplate: '%{x}<br>h = %{y:.4f}<extra></extra>',
    }

    // Fitted curve (120 points, evaluated client-side)
    const xMin = data_points[0].x_hours
    const xMax = data_points[data_points.length - 1].x_hours
    const curveX = Array.from({ length: 120 }, (_, i) => xMin + (i / 119) * (xMax - xMin))
    const curveTimestamps = curveX.map(x => new Date(t0.getTime() + x * 3_600_000).toISOString())
    const curveY = curveX.map(x => polyval(coefficients, x))

    const fittedCurve = {
      name: 'Fitted curve',
      type: 'scatter',
      mode: 'lines',
      x: curveTimestamps,
      y: curveY,
      line: { color: '#3b82f6', width: 2, dash: 'dash' },
      hoverinfo: 'skip',
    }

    // f′ trace on secondary y-axis
    const fPrime = {
      name: "f′ (h/hr)",
      type: 'scatter',
      mode: 'lines',
      x: data_points.map(d => d.timestamp),
      y: data_points.map(d => d.f_prime),
      yaxis: 'y2',
      line: { color: '#94a3b8', width: 1.5, dash: 'dot' },
      hovertemplate: "f′ = %{y:.5f}<extra></extra>",
    }

    return [scatter, fittedCurve, fPrime]
  }

  function buildLayout(report) {
    const vm = report.fit_metadata.zone_boundaries.vulnerability_margin

    const zoneShapes = [
      {
        type: 'rect', xref: 'paper', yref: 'y',
        x0: 0, x1: 1, y0: vm, y1: 1.15,
        fillcolor: 'rgba(34,197,94,0.12)', line: { width: 0 }, layer: 'below',
      },
      {
        type: 'rect', xref: 'paper', yref: 'y',
        x0: 0, x1: 1, y0: -vm, y1: vm,
        fillcolor: 'rgba(245,158,11,0.15)', line: { width: 0 }, layer: 'below',
      },
      {
        type: 'rect', xref: 'paper', yref: 'y',
        x0: 0, x1: 1, y0: -1.15, y1: -vm,
        fillcolor: 'rgba(239,68,68,0.12)', line: { width: 0 }, layer: 'below',
      },
    ]

    return {
      shapes: zoneShapes,
      margin: { t: 30, r: 80, b: 60, l: 60 },
      xaxis: { type: 'date', title: 'Time' },
      yaxis: { title: 'Health Score (h)', range: [-1.2, 1.2], zeroline: true },
      yaxis2: {
        title: "f′ (h-units/hr)",
        overlaying: 'y',
        side: 'right',
        showgrid: false,
        zeroline: false,
      },
      legend: { orientation: 'h', y: -0.15 },
    }
  }

  $effect(() => {
    const report = $currentReport
    if (!report || !chartDiv) return
    Plotly.react(chartDiv, buildTraces(report), buildLayout(report), { responsive: true })
  })
</script>

<div bind:this={chartDiv} style="width:100%; height:480px; margin-bottom:2rem;"></div>
