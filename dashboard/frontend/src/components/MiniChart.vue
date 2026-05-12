<template>
  <div style="position: relative; width: 100%; height: 100%">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import {
  Chart, CategoryScale, LinearScale, TimeScale,
  Tooltip, LineElement, PointElement, LineController, Filler
} from 'chart.js'
import 'chartjs-adapter-luxon'

Chart.register(CategoryScale, LinearScale, TimeScale, Tooltip, LineElement, PointElement, LineController, Filler)

const props = defineProps({ data: { type: Array, default: () => [] } })
const canvas = ref(null)
let chart = null

function build() {
  if (!canvas.value || !props.data.length) return
  const points = props.data.map(c => ({ x: c.t, y: +(c.c * 100).toFixed(2) }))

  if (chart) { chart.destroy(); chart = null }

  chart = new Chart(canvas.value, {
    type: 'line',
    data: {
      datasets: [{
        data: points,
        borderColor: '#4ae176',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        backgroundColor: 'rgba(74,225,118,0.08)',
        tension: 0.3,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: ctx => `YES ${ctx.parsed.y.toFixed(1)}%` }
      }},
      scales: {
        x: { type: 'time', time: { unit: 'hour' },
             grid: { color: 'rgba(255,255,255,0.04)' },
             ticks: { color: 'rgba(255,255,255,0.35)', maxTicksLimit: 5, font: { size: 10 } } },
        y: { min: 0, max: 100,
             grid: { color: 'rgba(255,255,255,0.04)' },
             ticks: { color: 'rgba(255,255,255,0.35)', callback: v => v + '%', font: { size: 10 } } },
      }
    }
  })
}

watch(() => props.data, build, { deep: true })
onMounted(build)
onUnmounted(() => { if (chart) chart.destroy() })
</script>
