<template>
  <div class="p-8 max-w-5xl mx-auto">
    <!-- Back -->
    <button @click="$router.back()" class="flex items-center gap-2 text-sm mb-6 transition-opacity hover:opacity-70"
            style="color:var(--color-on-surface-variant)">
      ← Back to Markets
    </button>

    <div v-if="!market || !market.question" class="glass-panel p-16 text-center" style="color:var(--color-on-surface-variant)">
      Loading…
    </div>

    <template v-else>
      <!-- Header -->
      <div class="glass-panel p-6 mb-6">
        <div class="flex items-start justify-between gap-4 mb-4">
          <span class="badge" :class="market.state==='ACTIVE' ? 'badge-green' : 'badge-gray'">{{ market.state }}</span>
          <span class="text-xs tabular-nums" style="color:var(--color-on-surface-variant)">
            Resolves {{ new Date(market.resolution_timestamp*1000).toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}) }}
          </span>
        </div>
        <h1 class="text-xl font-bold mb-3 leading-snug" style="font-family:var(--font-headline)">
          {{ market.question }}
        </h1>
        <p class="text-sm mb-5" style="color:var(--color-on-surface-variant)">{{ market.resolution_criteria }}</p>

        <!-- Price bar -->
        <div class="mb-4">
          <div class="flex justify-between text-sm mb-2">
            <span class="font-bold tabular-nums" style="color:#4ae176">YES {{ (market.yes_price*100).toFixed(1) }}%</span>
            <span class="font-bold tabular-nums" style="color:#ff5451">NO {{ (market.no_price*100).toFixed(1) }}%</span>
          </div>
          <div class="h-3 rounded-full overflow-hidden" style="background:rgba(255,84,81,0.2)">
            <div class="h-full rounded-full transition-all duration-700"
                 :style="{width:(market.yes_price*100)+'%', background:'linear-gradient(90deg,#22c55e,#4ade80)'}"/>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-3 text-center">
          <div class="glass-card p-3">
            <div class="text-lg font-bold tabular-nums" style="color:#adc6ff">{{ market.b }}</div>
            <div class="micro-label">Liquidity (b)</div>
          </div>
          <div class="glass-card p-3">
            <div class="text-lg font-bold tabular-nums" style="color:#4ae176">{{ market.q_yes.toFixed(1) }}</div>
            <div class="micro-label">YES Shares</div>
          </div>
          <div class="glass-card p-3">
            <div class="text-lg font-bold tabular-nums" style="color:#ff5451">{{ market.q_no.toFixed(1) }}</div>
            <div class="micro-label">NO Shares</div>
          </div>
        </div>
      </div>

      <!-- K-line chart -->
      <div class="glass-panel p-6 mb-6">
        <div class="micro-label mb-4">Price History</div>
        <div v-if="ohlcLoading" class="py-12 text-center text-sm" style="color:var(--color-on-surface-variant)">Loading chart…</div>
        <div v-else-if="ohlcData.length === 0" class="py-12 text-center text-sm" style="color:var(--color-on-surface-variant)">
          No price data yet — data accumulates as agents trade
        </div>
        <div v-else style="height:220px">
          <MiniChart :data="ohlcData" style="height:100%"/>
        </div>
      </div>

      <!-- Agent positions -->
      <div class="glass-panel p-6 mb-6">
        <div class="micro-label mb-4">Agent Positions</div>
        <div v-if="posLoading" class="text-sm py-2" style="color:var(--color-on-surface-variant)">Loading…</div>
        <div v-else-if="positions.length === 0" class="text-sm py-2" style="color:var(--color-on-surface-variant)">No positions yet</div>
        <div v-else class="grid gap-3" style="grid-template-columns:repeat(auto-fill,minmax(200px,1fr))">
          <div v-for="p in positions" :key="p.agent_id" class="glass-card p-4 text-center">
            <div class="font-semibold mb-2 text-sm">{{ p.agent_id }}</div>
            <div v-if="p.yes_tokens > 0" class="tabular-nums font-bold text-lg" style="color:#4ae176">
              +{{ p.yes_tokens }} YES
            </div>
            <div v-if="p.no_tokens > 0" class="tabular-nums font-bold text-lg" style="color:#ff5451">
              +{{ p.no_tokens }} NO
            </div>
            <div v-if="p.yes_tokens <= 0 && p.no_tokens <= 0" class="text-sm" style="color:var(--color-on-surface-variant)">
              No position
            </div>
          </div>
        </div>
      </div>

      <!-- Trade history -->
      <div class="glass-panel p-6">
        <div class="micro-label mb-4">Trade History ({{ trades.length }})</div>
        <div v-if="tradesLoading" class="text-sm py-2" style="color:var(--color-on-surface-variant)">Loading…</div>
        <div v-else-if="trades.length === 0" class="text-sm py-4 text-center" style="color:var(--color-on-surface-variant)">No trades yet</div>
        <div v-else class="space-y-3">
          <div v-for="t in trades" :key="t.tx_hash" class="glass-card p-4">
            <!-- Row 1: agent, action, amount, time -->
            <div class="flex items-center justify-between mb-2 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-sm">{{ t.agent_id }}</span>
                <span class="px-2 py-0.5 rounded text-xs font-bold"
                      :style="t.action_type.includes('YES')
                        ? {background:'rgba(74,225,118,0.15)',color:'#4ae176'}
                        : {background:'rgba(255,84,81,0.15)', color:'#ff5451'}">
                  {{ t.action_type.replace('_', ' ') }}
                </span>
                <span class="tabular-nums text-sm font-medium">{{ t.amount_tokens?.toFixed(1) }} tokens</span>
              </div>
              <span class="text-xs tabular-nums" style="color:var(--color-on-surface-variant)">
                {{ new Date(t.timestamp*1000).toLocaleString('en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) }}
              </span>
            </div>
            <!-- Row 2: price change -->
            <div class="flex items-center gap-2 text-xs mb-2">
              <span class="tabular-nums px-2 py-0.5 rounded" style="background:rgba(255,255,255,0.05)">
                {{ (t.price_before*100).toFixed(1) }}% → {{ (t.price_after*100).toFixed(1) }}%
              </span>
              <span :style="t.price_after > t.price_before ? {color:'#4ae176'} : {color:'#ff5451'}">
                {{ t.price_after > t.price_before ? '▲' : '▼' }}
                {{ Math.abs((t.price_after - t.price_before)*100).toFixed(1) }}%
              </span>
            </div>
            <!-- Row 3: reasoning -->
            <p v-if="t.reasoning" class="text-xs italic leading-relaxed"
               style="color:var(--color-on-surface-variant)">
              "{{ t.reasoning }}"
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import MiniChart from '../components/MiniChart.vue'

const api   = axios.create({ baseURL: '/api' })
const route = useRoute()
const addr  = route.params.address

const market    = ref(null)
const ohlcData  = ref([])
const positions = ref([])
const trades    = ref([])
const ohlcLoading    = ref(true)
const posLoading     = ref(true)
const tradesLoading  = ref(true)

onMounted(async () => {
  const [mRes, ohlcRes, posRes, tradeRes] = await Promise.all([
    api.get(`/markets/${addr}`).catch(() => ({ data: null })),
    api.get(`/ohlc?market_id=${addr}&interval=300`).catch(() => ({ data: [] })),
    api.get(`/markets/${addr}/positions`).catch(() => ({ data: [] })),
    api.get(`/markets/${addr}/trades?limit=50`).catch(() => ({ data: [] })),
  ])
  market.value   = mRes.data
  ohlcData.value = ohlcRes.data;  ohlcLoading.value   = false
  positions.value = posRes.data;  posLoading.value    = false
  trades.value   = tradeRes.data; tradesLoading.value = false
})
</script>
