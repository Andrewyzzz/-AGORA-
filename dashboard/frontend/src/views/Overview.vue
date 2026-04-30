<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-2xl font-bold mb-1" style="font-family: var(--font-headline)">Overview</h1>
        <p class="text-sm" style="color: var(--color-on-surface-variant)">
          Real-time AI agent economy on Base Sepolia
        </p>
      </div>
      <div class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg"
           style="background: rgba(74,225,118,0.1); color: #4ae176; border: 1px solid rgba(74,225,118,0.2)">
        <div class="live-dot" style="width:6px;height:6px"></div>
        Auto-refresh 30s
      </div>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-4 gap-4 mb-8">
      <div v-for="stat in statCards" :key="stat.label" class="glass-card p-5">
        <div class="micro-label mb-2">{{ stat.label }}</div>
        <div class="text-3xl font-bold tabular-nums mb-1"
             :style="{ fontFamily: 'var(--font-headline)', color: stat.color }">
          {{ stat.value }}
        </div>
        <div class="text-xs" style="color: var(--color-on-surface-variant)">{{ stat.sub }}</div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-6">
      <!-- Active Markets -->
      <div class="col-span-2 glass-panel p-6">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-semibold" style="font-family: var(--font-headline)">Active Markets</h2>
          <router-link to="/markets" class="text-xs" style="color: var(--color-primary)">View all →</router-link>
        </div>
        <div class="space-y-3">
          <div v-for="m in markets.slice(0,5)" :key="m.address" class="glass-card p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate mb-2">{{ m.question }}</p>
                <div class="flex items-center gap-3">
                  <div class="flex-1 h-1.5 rounded-full" style="background: var(--color-surface-highest)">
                    <div class="h-full rounded-full transition-all duration-700"
                         :style="{ width: (m.yes_price*100)+'%', background: 'linear-gradient(90deg, #22c55e, #4ade80)' }">
                    </div>
                  </div>
                  <span class="text-xs tabular-nums" style="color: #4ae176; min-width:36px">
                    {{ (m.yes_price*100).toFixed(1) }}%
                  </span>
                </div>
              </div>
              <div class="text-right flex-shrink-0">
                <div class="badge" :class="m.state === 'ACTIVE' ? 'badge-green' : 'badge-gray'">
                  {{ m.state }}
                </div>
                <div class="text-xs mt-1 tabular-nums" style="color: var(--color-on-surface-variant)">
                  {{ m.collateral_balance.toFixed(0) }} AGORA
                </div>
              </div>
            </div>
          </div>
          <div v-if="!markets.length" class="text-center py-8 text-sm" style="color: var(--color-on-surface-variant)">
            Loading markets...
          </div>
        </div>
      </div>

      <!-- Recent Trades -->
      <div class="glass-panel p-6">
        <div class="flex items-center justify-between mb-5">
          <h2 class="font-semibold" style="font-family: var(--font-headline)">Recent Trades</h2>
          <router-link to="/trades" class="text-xs" style="color: var(--color-primary)">All →</router-link>
        </div>
        <div class="space-y-2">
          <div v-for="t in recentTrades" :key="t.timestamp + t.tx_hash"
               class="flex items-center gap-3 p-3 rounded-lg"
               style="background: rgba(255,255,255,0.02)">
            <div class="badge text-xs" :class="t.action_type.includes('YES') ? 'badge-green' : 'badge-red'">
              {{ t.action_type.replace('buy_','') }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium truncate">{{ t.agent_id }}</div>
              <div class="text-xs truncate" style="color: var(--color-on-surface-variant)">
                {{ t.amount_tokens?.toFixed(1) }} tokens
              </div>
            </div>
            <div class="text-xs tabular-nums" style="color: var(--color-on-surface-variant)">
              {{ timeAgo(t.timestamp) }}
            </div>
          </div>
          <div v-if="!recentTrades.length" class="text-center py-6 text-sm" style="color: var(--color-on-surface-variant)">
            No trades yet
          </div>
        </div>
      </div>
    </div>

    <!-- Agent summary row -->
    <div class="grid grid-cols-3 gap-4 mt-6">
      <div v-for="agent in agents" :key="agent.id"
           class="glass-card p-5 border-l-4"
           :style="{ borderLeftColor: agentColor(agent.id) }">
        <div class="flex items-center justify-between mb-3">
          <div>
            <div class="font-semibold text-sm">{{ agent.id }}</div>
            <div class="micro-label">{{ agent.model }}</div>
          </div>
          <div class="text-xs px-2 py-1 rounded"
               style="background: rgba(255,255,255,0.05); color: var(--color-on-surface-variant)">
            {{ agent.persona.split(' ')[0] }}
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3 text-center">
          <div>
            <div class="text-xl font-bold tabular-nums" :style="{ color: agentColor(agent.id) }">
              {{ agent.total_trades }}
            </div>
            <div class="micro-label">Trades</div>
          </div>
          <div>
            <div class="text-xl font-bold tabular-nums" style="color: #4ae176">
              {{ agent.yes_trades }}
            </div>
            <div class="micro-label">YES</div>
          </div>
          <div>
            <div class="text-xl font-bold tabular-nums" style="color: #ff5451">
              {{ agent.no_trades }}
            </div>
            <div class="micro-label">NO</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getStats, getMarkets, getAgents, getTrades } from '../api/client.js'

const stats   = ref({})
const markets = ref([])
const agents  = ref([])
const trades  = ref([])
let timer

const statCards = computed(() => [
  { label: 'Active Markets',  value: stats.value.total_markets   ?? '—', color: '#adc6ff', sub: 'on Base Sepolia' },
  { label: 'Total Trades',    value: stats.value.total_trades    ?? '—', color: '#4ae176', sub: 'by all agents'   },
  { label: 'Proposals',       value: stats.value.total_proposals ?? '—', color: '#ffb3ad', sub: 'governance votes' },
  { label: 'Block',           value: stats.value.block ?? '—',           color: '#8c909f', sub: stats.value.network ?? '' },
])

const recentTrades = computed(() =>
  trades.value.filter(t => t.action_type && !t.action_type.includes('hold')).slice(0, 8)
)

function agentColor(id) {
  return { 'Agent-A': '#adc6ff', 'Agent-B': '#4ae176', 'Agent-C': '#ffb3ad' }[id] ?? '#8c909f'
}

function timeAgo(ts) {
  const diff = Date.now()/1000 - ts
  if (diff < 60)  return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`
  return `${Math.floor(diff/3600)}h ago`
}

async function refresh() {
  const [s, m, a, t] = await Promise.all([getStats(), getMarkets(), getAgents(), getTrades(20)])
  stats.value   = s.data
  markets.value = m.data
  agents.value  = a.data
  trades.value  = t.data
}

onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
