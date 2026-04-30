<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-2" style="font-family: var(--font-headline)">Trades</h1>
    <p class="text-sm mb-8" style="color: var(--color-on-surface-variant)">Complete on-chain trade history with agent reasoning</p>

    <!-- Filter bar -->
    <div class="flex gap-2 mb-6">
      <button v-for="f in filters" :key="f"
              @click="active = f"
              class="px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
              :class="active === f
                ? 'text-white'
                : 'text-sm'"
              :style="active === f
                ? { background: agentColor(f), color: '#111317' }
                : { background: 'rgba(255,255,255,0.04)', color: 'var(--color-on-surface-variant)' }">
        {{ f }}
      </button>
    </div>

    <!-- Trade table -->
    <div class="glass-panel overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr style="border-bottom: 1px solid var(--color-outline-variant)">
            <th class="micro-label text-left px-5 py-3">Time</th>
            <th class="micro-label text-left px-4 py-3">Agent</th>
            <th class="micro-label text-left px-4 py-3">Action</th>
            <th class="micro-label text-left px-4 py-3">Amount</th>
            <th class="micro-label text-left px-4 py-3">Price →</th>
            <th class="micro-label text-left px-4 py-3">Confidence</th>
            <th class="micro-label text-left px-4 py-3">Tx</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="t in filteredTrades" :key="t.timestamp + t.tx_hash">
            <tr class="border-b cursor-pointer hover:bg-white/[0.02] transition-colors"
                style="border-color: rgba(255,255,255,0.04)"
                @click="expand = expand === t.tx_hash ? null : t.tx_hash">
              <td class="px-5 py-3 tabular-nums text-xs" style="color: var(--color-on-surface-variant)">
                {{ fmtTime(t.timestamp) }}
              </td>
              <td class="px-4 py-3 font-medium text-xs" :style="{ color: agentColor(t.agent_id) }">
                {{ t.agent_id }}
              </td>
              <td class="px-4 py-3">
                <span class="badge" :class="t.action_type?.includes('YES') ? 'badge-green' : 'badge-red'">
                  {{ t.action_type?.toUpperCase().replace('_',' ') }}
                </span>
              </td>
              <td class="px-4 py-3 tabular-nums">{{ t.amount_tokens?.toFixed(1) }}</td>
              <td class="px-4 py-3 tabular-nums text-xs">
                <span :style="{ color: '#8c909f' }">{{ pct(t.price_before) }}</span>
                <span style="color: var(--color-on-surface-variant)"> → </span>
                <span :style="{ color: t.action_type?.includes('YES') ? '#4ae176' : '#ff5451' }">
                  {{ pct(t.price_after) }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span class="badge badge-gray text-xs">{{ t.confidence }}</span>
              </td>
              <td class="px-4 py-3 text-xs font-mono" style="color: var(--color-on-surface-variant)">
                <a :href="`https://sepolia.basescan.org/tx/${t.tx_hash}`" target="_blank"
                   @click.stop class="hover:underline">
                  {{ t.tx_hash?.slice(0,10) }}...
                </a>
              </td>
            </tr>
            <!-- Expanded reasoning -->
            <tr v-if="expand === t.tx_hash">
              <td colspan="7" class="px-5 py-4" style="background: rgba(255,255,255,0.02)">
                <div class="micro-label mb-2">Agent Reasoning</div>
                <p class="text-sm leading-relaxed" style="color: var(--color-on-surface-variant)">
                  {{ t.reasoning || 'No reasoning recorded.' }}
                </p>
                <div class="mt-2 text-xs font-mono" style="color: var(--color-outline)">
                  P(YES): {{ t.probability_estimate?.toFixed(3) }}
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div v-if="!filteredTrades.length" class="py-16 text-center"
           style="color: var(--color-on-surface-variant)">
        No trades recorded yet
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getTrades } from '../api/client.js'

const trades  = ref([])
const active  = ref('All')
const expand  = ref(null)
let timer

const filters = ['All', 'Agent-A', 'Agent-B', 'Agent-C']

const filteredTrades = computed(() =>
  trades.value.filter(t =>
    (active.value === 'All' || t.agent_id === active.value) &&
    t.action_type && !t.action_type.includes('hold')
  )
)

function agentColor(id) {
  return { 'Agent-A': '#adc6ff', 'Agent-B': '#4ae176', 'Agent-C': '#ffb3ad' }[id] ?? '#8c909f'
}
function pct(v) { return v != null ? (v * 100).toFixed(1) + '%' : '—' }
function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function refresh() { trades.value = (await getTrades(100)).data }
onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
