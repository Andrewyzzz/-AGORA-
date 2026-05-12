<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-1" style="font-family: var(--font-headline)">Markets</h1>
    <p class="text-sm mb-6" style="color: var(--color-on-surface-variant)">All prediction markets created by AI agents</p>

    <!-- Filter bar -->
    <div class="flex gap-2 mb-6">
      <button v-for="f in filters" :key="f.value" @click="filter = f.value"
        class="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
        :style="filter === f.value ? f.activeStyle : inactiveStyle">
        {{ f.label(markets) }}
      </button>
    </div>

    <!-- Card grid -->
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(340px, 1fr))">
      <div v-for="m in filteredMarkets" :key="m.address"
           class="glass-panel cursor-pointer transition-all duration-200 overflow-hidden"
           :class="expanded === m.address ? 'glow-secondary' : ''"
           @click="toggle(m)">

        <!-- Card header -->
        <div class="p-5">
          <!-- State badge + resolves -->
          <div class="flex items-center justify-between mb-3">
            <span class="badge text-xs" :class="m.state === 'ACTIVE' ? 'badge-green' : 'badge-gray'">
              {{ m.state }}
            </span>
            <span class="text-xs tabular-nums" style="color: var(--color-on-surface-variant)">
              Resolves {{ new Date(m.resolution_timestamp * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'}) }}
            </span>
          </div>

          <!-- Question -->
          <p class="font-semibold leading-snug mb-4" style="font-size: 0.92rem; min-height: 2.8em">
            {{ m.question }}
          </p>

          <!-- YES/NO price bar -->
          <div class="mb-3">
            <div class="flex justify-between text-xs mb-1">
              <span class="tabular-nums font-bold" style="color: #4ae176">YES {{ (m.yes_price * 100).toFixed(1) }}%</span>
              <span class="tabular-nums font-bold" style="color: #ff5451">NO {{ (m.no_price * 100).toFixed(1) }}%</span>
            </div>
            <div class="h-2 rounded-full overflow-hidden" style="background: rgba(255,84,81,0.2)">
              <div class="h-full rounded-full transition-all duration-700"
                   :style="{ width: (m.yes_price * 100) + '%', background: 'linear-gradient(90deg,#22c55e,#4ade80)' }"/>
            </div>
          </div>

          <!-- Stats row -->
          <div class="flex gap-4 text-xs" style="color: var(--color-on-surface-variant)">
            <span>💧 {{ m.collateral_balance.toFixed(0) }} AGORA</span>
            <span>📊 b = {{ m.b }}</span>
            <span class="ml-auto" style="color: var(--color-on-surface-variant)">
              {{ expanded === m.address ? '▲ collapse' : '▼ details' }}
            </span>
          </div>
        </div>

        <!-- Expanded panel -->
        <transition name="slide">
          <div v-if="expanded === m.address" class="border-t" style="border-color: var(--color-outline-variant)">

            <!-- K-line chart -->
            <div class="p-5 pb-0">
              <div class="micro-label mb-3">Price History</div>
              <div v-if="ohlcLoading" class="text-center py-6 text-sm" style="color: var(--color-on-surface-variant)">Loading chart…</div>
              <div v-else-if="ohlcData.length === 0" class="text-center py-6 text-sm" style="color: var(--color-on-surface-variant)">No price data yet</div>
              <MiniChart v-else :data="ohlcData" style="height:140px"/>
            </div>

            <!-- Agent positions -->
            <div class="p-5 pb-0">
              <div class="micro-label mb-3">Agent Positions</div>
              <div v-if="positionsLoading" class="text-sm py-2" style="color: var(--color-on-surface-variant)">Loading…</div>
              <div v-else-if="positions.length === 0" class="text-sm py-2" style="color: var(--color-on-surface-variant)">No positions yet</div>
              <div v-else class="space-y-2">
                <div v-for="p in positions" :key="p.agent_id"
                     class="flex items-center justify-between glass-card px-3 py-2 text-sm">
                  <span class="font-medium">{{ p.agent_id }}</span>
                  <div class="flex gap-3 tabular-nums text-xs">
                    <span v-if="p.yes_tokens > 0" style="color: #4ae176">+{{ p.yes_tokens }} YES</span>
                    <span v-if="p.no_tokens  > 0" style="color: #ff5451">+{{ p.no_tokens }} NO</span>
                    <span v-if="p.yes_tokens <= 0 && p.no_tokens <= 0" style="color: var(--color-on-surface-variant)">No position</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Trade history -->
            <div class="p-5">
              <div class="micro-label mb-3">Trade History</div>
              <div v-if="tradesLoading" class="text-sm py-2" style="color: var(--color-on-surface-variant)">Loading…</div>
              <div v-else-if="trades.length === 0" class="text-sm py-2" style="color: var(--color-on-surface-variant)">No trades yet</div>
              <div v-else class="space-y-2 max-h-64 overflow-y-auto pr-1">
                <div v-for="t in trades" :key="t.tx_hash"
                     class="glass-card px-3 py-2 text-xs">
                  <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold">{{ t.agent_id }}</span>
                      <span class="px-1.5 py-0.5 rounded text-xs font-bold"
                            :style="t.action_type.includes('YES')
                              ? {background:'rgba(74,225,118,0.15)', color:'#4ae176'}
                              : {background:'rgba(255,84,81,0.15)',  color:'#ff5451'}">
                        {{ t.action_type.replace('_', ' ') }}
                      </span>
                      <span class="tabular-nums">{{ t.amount_tokens?.toFixed(1) }} tokens</span>
                    </div>
                    <span class="tabular-nums" style="color: var(--color-on-surface-variant)">
                      {{ new Date(t.timestamp * 1000).toLocaleString('en-US', {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}) }}
                    </span>
                  </div>
                  <div class="flex items-center gap-2" style="color: var(--color-on-surface-variant)">
                    <span>{{ (t.price_before * 100).toFixed(1) }}% → {{ (t.price_after * 100).toFixed(1) }}%</span>
                    <span class="truncate italic">{{ t.reasoning?.slice(0, 80) }}…</span>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </transition>
      </div>

      <div v-if="filteredMarkets.length === 0" class="glass-panel p-16 text-center col-span-full"
           style="color: var(--color-on-surface-variant)">
        {{ markets.length ? 'No markets in this filter' : 'Loading markets…' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { getMarkets } from '../api/client.js'
import MiniChart from '../components/MiniChart.vue'

const api = axios.create({ baseURL: '/api' })

const markets   = ref([])
const filter    = ref('active')
const expanded  = ref(null)
const ohlcData  = ref([])
const positions = ref([])
const trades    = ref([])
const ohlcLoading      = ref(false)
const positionsLoading = ref(false)
const tradesLoading    = ref(false)
let timer

const inactiveStyle = { background: 'rgba(255,255,255,0.04)', color: 'var(--color-on-surface-variant)' }
const filters = [
  { value: 'active',   label: m => `Active (${m.filter(x=>x.state==='ACTIVE').length})`,   activeStyle: { background:'rgba(74,225,118,0.2)',  color:'#4ae176', border:'1px solid #4ae176' } },
  { value: 'resolved', label: m => `Resolved (${m.filter(x=>x.state==='RESOLVED').length})`,activeStyle: { background:'rgba(140,144,159,0.2)', color:'#8c909f', border:'1px solid #8c909f' } },
  { value: 'all',      label: m => `All (${m.length})`,                                     activeStyle: { background:'rgba(77,142,255,0.2)',  color:'#adc6ff', border:'1px solid #4d8eff' } },
]

const filteredMarkets = computed(() => {
  if (filter.value === 'active')   return markets.value.filter(m => m.state === 'ACTIVE')
  if (filter.value === 'resolved') return markets.value.filter(m => m.state === 'RESOLVED')
  return markets.value
})

async function toggle(m) {
  if (expanded.value === m.address) { expanded.value = null; return }
  expanded.value = m.address
  ohlcData.value = []; positions.value = []; trades.value = []

  ohlcLoading.value = true
  positionsLoading.value = true
  tradesLoading.value = true

  const [ohlcRes, posRes, tradeRes] = await Promise.all([
    api.get(`/ohlc?market_id=${m.address}&interval=300`).catch(() => ({ data: [] })),
    api.get(`/markets/${m.address}/positions`).catch(() => ({ data: [] })),
    api.get(`/markets/${m.address}/trades?limit=30`).catch(() => ({ data: [] })),
  ])

  ohlcData.value        = ohlcRes.data
  ohlcLoading.value     = false
  positions.value       = posRes.data
  positionsLoading.value = false
  trades.value          = tradeRes.data
  tradesLoading.value   = false
}

async function refresh() {
  const r = await getMarkets()
  markets.value = r.data
}

onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.slide-enter-active, .slide-leave-active { transition: max-height 0.3s ease, opacity 0.3s ease; overflow: hidden; }
.slide-enter-from, .slide-leave-to { max-height: 0; opacity: 0; }
.slide-enter-to, .slide-leave-from { max-height: 2000px; opacity: 1; }
</style>
