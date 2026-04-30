<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-2" style="font-family: var(--font-headline)">Agents</h1>
    <p class="text-sm mb-8" style="color: var(--color-on-surface-variant)">AI agent balances, positions, and trading stats</p>

    <div class="grid grid-cols-3 gap-6">
      <div v-for="agent in agents" :key="agent.id">
        <!-- Agent card -->
        <div class="glass-panel p-6 mb-4 border-t-4"
             :style="{ borderTopColor: color(agent.id) }">
          <div class="flex items-start justify-between mb-5">
            <div>
              <div class="text-lg font-bold" style="font-family: var(--font-headline)">{{ agent.id }}</div>
              <div class="text-sm" :style="{ color: color(agent.id) }">{{ agent.model }}</div>
              <div class="micro-label mt-1">{{ agent.persona }}</div>
            </div>
            <div class="w-10 h-10 rounded-xl flex items-center justify-center text-lg font-bold"
                 :style="{ background: `${color(agent.id)}22`, color: color(agent.id) }">
              {{ agent.id.slice(-1) }}
            </div>
          </div>

          <!-- Balances -->
          <div class="grid grid-cols-2 gap-3 mb-5">
            <div class="glass-card p-3 text-center">
              <div class="text-xl font-bold tabular-nums" :style="{ color: color(agent.id) }">
                {{ agent.eth_balance.toFixed(4) }}
              </div>
              <div class="micro-label">ETH Balance</div>
            </div>
            <div class="glass-card p-3 text-center">
              <div class="text-xl font-bold tabular-nums" style="color: #adc6ff">
                {{ agent.agora_balance.toFixed(0) }}
              </div>
              <div class="micro-label">AGORA Balance</div>
            </div>
          </div>

          <!-- Trade stats -->
          <div class="grid grid-cols-3 gap-2 mb-5">
            <div class="text-center p-2 rounded-lg" style="background: rgba(255,255,255,0.03)">
              <div class="text-2xl font-bold tabular-nums" :style="{ color: color(agent.id) }">
                {{ agent.total_trades }}
              </div>
              <div class="micro-label">Total</div>
            </div>
            <div class="text-center p-2 rounded-lg" style="background: rgba(74,225,118,0.06)">
              <div class="text-2xl font-bold tabular-nums" style="color: #4ae176">
                {{ agent.yes_trades }}
              </div>
              <div class="micro-label">BUY YES</div>
            </div>
            <div class="text-center p-2 rounded-lg" style="background: rgba(255,84,81,0.06)">
              <div class="text-2xl font-bold tabular-nums" style="color: #ff5451">
                {{ agent.no_trades }}
              </div>
              <div class="micro-label">BUY NO</div>
            </div>
          </div>

          <!-- Bull/Bear bar -->
          <div v-if="agent.total_trades > 0" class="mb-4">
            <div class="micro-label mb-2">Trading Direction</div>
            <div class="h-2 rounded-full overflow-hidden" style="background: rgba(255,84,81,0.25)">
              <div class="h-full rounded-full"
                   :style="{ width: yesPct(agent)+'%', background: 'linear-gradient(90deg,#22c55e,#4ade80)' }">
              </div>
            </div>
            <div class="flex justify-between text-xs mt-1">
              <span style="color: #4ae176">{{ yesPct(agent).toFixed(0) }}% YES</span>
              <span style="color: #ff5451">{{ (100-yesPct(agent)).toFixed(0) }}% NO</span>
            </div>
          </div>

          <!-- Wallet address -->
          <div class="text-xs font-mono px-2 py-1 rounded truncate"
               style="background: var(--color-surface-container); color: var(--color-on-surface-variant)">
            {{ agent.address }}
          </div>
        </div>

        <!-- Positions -->
        <div v-if="agent.positions?.length" class="glass-panel p-4">
          <div class="micro-label mb-3">Positions ({{ agent.positions.length }})</div>
          <div class="space-y-2">
            <div v-for="pos in agent.positions" :key="pos.market_address"
                 class="glass-card p-3">
              <div class="text-xs truncate mb-2" style="color: var(--color-on-surface-variant)">
                {{ pos.question }}
              </div>
              <div class="flex gap-2">
                <span v-if="pos.yes_tokens > 0" class="badge badge-green">
                  {{ pos.yes_tokens.toFixed(1) }} YES
                </span>
                <span v-if="pos.no_tokens > 0" class="badge badge-red">
                  {{ pos.no_tokens.toFixed(1) }} NO
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="glass-panel p-4 text-center text-sm"
             style="color: var(--color-on-surface-variant)">
          No open positions
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getAgents } from '../api/client.js'

const agents = ref([])
let timer

function color(id) {
  return { 'Agent-A': '#adc6ff', 'Agent-B': '#4ae176', 'Agent-C': '#ffb3ad' }[id] ?? '#8c909f'
}
function yesPct(a) {
  return a.total_trades ? (a.yes_trades / a.total_trades * 100) : 50
}

async function refresh() { agents.value = (await getAgents()).data }
onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
