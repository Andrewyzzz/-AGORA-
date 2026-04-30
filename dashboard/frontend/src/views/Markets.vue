<template>
  <div class="p-8">
    <!-- K-line chart -->
    <div class="mb-8">
      <h2 class="text-lg font-semibold mb-4" style="font-family: var(--font-headline)">Price Chart</h2>
      <PriceChart :markets="markets" />
    </div>
    <h1 class="text-2xl font-bold mb-2" style="font-family: var(--font-headline)">Markets</h1>
    <p class="text-sm mb-8" style="color: var(--color-on-surface-variant)">All prediction markets created by AI agents</p>

    <div class="space-y-4">
      <div v-for="m in markets" :key="m.address"
           class="glass-panel p-6 cursor-pointer"
           :class="{ 'glow-secondary': selected?.address === m.address }"
           @click="select(m)">
        <!-- Top row -->
        <div class="flex items-start justify-between gap-4 mb-4">
          <div class="flex-1">
            <p class="font-semibold mb-1">{{ m.question }}</p>
            <p class="text-xs" style="color: var(--color-on-surface-variant)">
              Resolves {{ new Date(m.resolution_timestamp * 1000).toLocaleDateString() }}
              · {{ m.collateral_balance.toFixed(0) }} AGORA liquidity
            </p>
          </div>
          <div class="badge" :class="m.state === 'ACTIVE' ? 'badge-green' : 'badge-gray'">{{ m.state }}</div>
        </div>

        <!-- Price bar -->
        <div class="flex items-center gap-4">
          <div class="flex-1">
            <div class="flex justify-between text-xs mb-1">
              <span style="color: #4ae176" class="tabular-nums font-semibold">
                YES {{ (m.yes_price*100).toFixed(1) }}%
              </span>
              <span style="color: #ff5451" class="tabular-nums font-semibold">
                NO {{ (m.no_price*100).toFixed(1) }}%
              </span>
            </div>
            <div class="h-2 rounded-full overflow-hidden" style="background: rgba(255,84,81,0.25)">
              <div class="h-full rounded-full transition-all duration-700"
                   :style="{ width: (m.yes_price*100)+'%', background: 'linear-gradient(90deg,#22c55e,#4ade80)' }">
              </div>
            </div>
          </div>
          <div class="text-right text-xs" style="color: var(--color-on-surface-variant)">
            <div class="tabular-nums">{{ m.q_yes.toFixed(1) }} YES</div>
            <div class="tabular-nums">{{ m.q_no.toFixed(1) }} NO</div>
          </div>
        </div>

        <!-- Expanded detail -->
        <div v-if="selected?.address === m.address" class="mt-5 pt-5 border-t space-y-3"
             style="border-color: var(--color-outline-variant)">
          <div>
            <div class="micro-label mb-1">Resolution Criteria</div>
            <p class="text-sm" style="color: var(--color-on-surface-variant)">{{ m.resolution_criteria }}</p>
          </div>
          <div class="grid grid-cols-3 gap-4 text-center">
            <div class="glass-card p-3">
              <div class="text-lg font-bold tabular-nums" style="color: #adc6ff">{{ m.b }}</div>
              <div class="micro-label">Liquidity (b)</div>
            </div>
            <div class="glass-card p-3">
              <div class="text-lg font-bold tabular-nums" style="color: #4ae176">{{ m.q_yes.toFixed(1) }}</div>
              <div class="micro-label">YES Shares</div>
            </div>
            <div class="glass-card p-3">
              <div class="text-lg font-bold tabular-nums" style="color: #ff5451">{{ m.q_no.toFixed(1) }}</div>
              <div class="micro-label">NO Shares</div>
            </div>
          </div>
          <div class="text-xs font-mono px-3 py-2 rounded"
               style="background: var(--color-surface-container); color: var(--color-on-surface-variant)">
            {{ m.address }}
          </div>
        </div>
      </div>

      <div v-if="!markets.length" class="glass-panel p-16 text-center" style="color: var(--color-on-surface-variant)">
        Loading markets...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getMarkets } from '../api/client.js'
import PriceChart from '../components/PriceChart.vue'

const markets  = ref([])
const selected = ref(null)
let timer

function select(m) { selected.value = selected.value?.address === m.address ? null : m }

async function refresh() {
  const r = await getMarkets()
  markets.value = r.data
}

onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
