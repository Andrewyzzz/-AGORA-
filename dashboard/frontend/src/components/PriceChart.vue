<template>
  <div>
    <!-- Market selector -->
    <div class="flex gap-2 mb-4 flex-wrap">
      <button v-for="m in markets" :key="m.address"
              @click="selected = m.address"
              class="px-3 py-1 rounded-lg text-xs font-medium transition-all truncate max-w-xs"
              :class="selected === m.address
                ? 'text-white'
                : ''"
              :style="selected === m.address
                ? { background: 'rgba(77,142,255,0.3)', color: '#adc6ff', border: '1px solid #4d8eff' }
                : { background: 'rgba(255,255,255,0.04)', color: 'var(--color-on-surface-variant)', border: '1px solid transparent' }">
        {{ m.question.slice(0, 40) }}{{ m.question.length > 40 ? '…' : '' }}
      </button>
    </div>

    <!-- Chart -->
    <div class="glass-panel p-5">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h3 class="font-semibold text-sm">{{ currentMarket?.question }}</h3>
          <div class="flex items-center gap-3 mt-1">
            <span class="text-xs" style="color: #4ae176">
              YES <span class="tabular-nums font-bold">{{ currentPrice }}</span>
            </span>
            <span class="micro-label">{{ candles.length }} candles · {{ intervalLabel }}</span>
          </div>
        </div>
        <!-- Interval selector -->
        <div class="flex gap-1">
          <button v-for="iv in intervals" :key="iv.s"
                  @click="interval = iv.s"
                  class="px-2 py-1 rounded text-xs transition-all"
                  :style="interval === iv.s
                    ? { background: 'rgba(77,142,255,0.2)', color: '#adc6ff' }
                    : { color: 'var(--color-on-surface-variant)' }">
            {{ iv.label }}
          </button>
        </div>
      </div>

      <!-- Canvas -->
      <div style="height: 280px; position: relative">
        <canvas ref="chartCanvas"></canvas>
        <div v-if="!candles.length"
             class="absolute inset-0 flex items-center justify-center text-sm"
             style="color: var(--color-on-surface-variant)">
          Collecting price data — updates every step (~5 min)
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  Chart, CategoryScale, LinearScale, TimeScale,
  Tooltip, Legend
} from 'chart.js'
import { CandlestickController, CandlestickElement, OhlcController, OhlcElement } from 'chartjs-chart-financial'
import 'chartjs-adapter-luxon'
import axios from 'axios'

Chart.register(
  CategoryScale, LinearScale, TimeScale,
  Tooltip, Legend,
  CandlestickController, CandlestickElement,
  OhlcController, OhlcElement
)

const props = defineProps({ markets: { type: Array, default: () => [] } })

const selected  = ref('')
const candles   = ref([])
const interval  = ref(300)
const chartCanvas = ref(null)
let chartInstance = null
let timer = null

const intervals = [
  { label: '1m',  s: 60   },
  { label: '5m',  s: 300  },
  { label: '15m', s: 900  },
  { label: '1h',  s: 3600 },
]

const intervalLabel = computed(() => intervals.find(i => i.s === interval.value)?.label ?? '5m')

const currentMarket = computed(() => props.markets.find(m => m.address === selected.value))

const currentPrice = computed(() => {
  if (!candles.value.length) return '—'
  return (candles.value.at(-1).c * 100).toFixed(1) + '%'
})

async function fetchCandles() {
  if (!selected.value) return
  try {
    const r = await axios.get(`/api/ohlc?market_id=${selected.value}&interval=${interval.value}`)
    candles.value = r.data
    await nextTick()
    renderChart()
  } catch (e) {
    console.error(e)
  }
}

function renderChart() {
  if (!chartCanvas.value) return
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }

  const ctx = chartCanvas.value.getContext('2d')
  chartInstance = new Chart(ctx, {
    type: 'candlestick',
    data: {
      datasets: [{
        label: 'YES Price',
        data: candles.value,
        color: {
          up:   '#4ae176',
          down: '#ff5451',
          unchanged: '#8c909f',
        },
        borderColor: {
          up:   '#4ae176',
          down: '#ff5451',
          unchanged: '#8c909f',
        },
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: {
          type: 'time',
          time: { unit: interval.value < 3600 ? 'minute' : 'hour' },
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { color: '#8c909f', maxTicksLimit: 8 },
        },
        y: {
          min: 0,
          max: 1,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: {
            color: '#8c909f',
            callback: v => (v * 100).toFixed(0) + '%',
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(30,32,36,0.95)',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          callbacks: {
            label: ctx => {
              const d = ctx.raw
              return [
                `O: ${(d.o*100).toFixed(1)}%`,
                `H: ${(d.h*100).toFixed(1)}%`,
                `L: ${(d.l*100).toFixed(1)}%`,
                `C: ${(d.c*100).toFixed(1)}%`,
              ]
            }
          }
        }
      }
    }
  })
}

// Auto-select first market
watch(() => props.markets, (ms) => {
  if (ms.length && !selected.value) selected.value = ms[0].address
}, { immediate: true })

watch([selected, interval], fetchCandles)

onMounted(() => {
  fetchCandles()
  timer = setInterval(fetchCandles, 30000)
})
onUnmounted(() => {
  clearInterval(timer)
  if (chartInstance) chartInstance.destroy()
})
</script>
