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
    <div class="grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))">
      <div v-for="m in filteredMarkets" :key="m.address"
           class="glass-panel p-5 cursor-pointer transition-all duration-200"
           style="border: 1px solid transparent"
           @mouseenter="e => e.currentTarget.style.borderColor='rgba(77,142,255,0.3)'"
           @mouseleave="e => e.currentTarget.style.borderColor='transparent'"
           @click="$router.push(`/markets/${m.address}`)">

        <!-- State + date -->
        <div class="flex items-center justify-between mb-3">
          <span class="badge text-xs" :class="m.state === 'ACTIVE' ? 'badge-green' : 'badge-gray'">
            {{ m.state }}
          </span>
          <span class="text-xs tabular-nums" style="color: var(--color-on-surface-variant)">
            {{ new Date(m.resolution_timestamp * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'}) }}
          </span>
        </div>

        <!-- Question -->
        <p class="font-semibold leading-snug mb-4" style="font-size:0.9rem; min-height:3em; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden">
          {{ m.question }}
        </p>

        <!-- YES/NO bar -->
        <div class="mb-3">
          <div class="flex justify-between text-xs mb-1">
            <span class="tabular-nums font-bold" style="color:#4ae176">YES {{ (m.yes_price*100).toFixed(1) }}%</span>
            <span class="tabular-nums font-bold" style="color:#ff5451">NO {{ (m.no_price*100).toFixed(1) }}%</span>
          </div>
          <div class="h-2 rounded-full overflow-hidden" style="background:rgba(255,84,81,0.2)">
            <div class="h-full rounded-full transition-all duration-700"
                 :style="{width:(m.yes_price*100)+'%', background:'linear-gradient(90deg,#22c55e,#4ade80)'}"/>
          </div>
        </div>

        <!-- Footer stats -->
        <div class="flex gap-3 text-xs" style="color:var(--color-on-surface-variant)">
          <span>💧 {{ m.collateral_balance.toFixed(0) }} liq</span>
          <span>b={{ m.b }}</span>
          <span class="ml-auto" style="color:rgba(77,142,255,0.7)">View details →</span>
        </div>
      </div>

      <div v-if="filteredMarkets.length === 0" class="glass-panel p-16 text-center col-span-full"
           style="color:var(--color-on-surface-variant)">
        {{ markets.length ? 'No markets in this filter' : 'Loading markets…' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getMarkets } from '../api/client.js'

const markets = ref([])
const filter  = ref('active')
let timer

const inactiveStyle = { background:'rgba(255,255,255,0.04)', color:'var(--color-on-surface-variant)' }
const filters = [
  { value:'active',   label: m => `Active (${m.filter(x=>x.state==='ACTIVE').length})`,    activeStyle:{background:'rgba(74,225,118,0.2)', color:'#4ae176', border:'1px solid #4ae176'} },
  { value:'resolved', label: m => `Resolved (${m.filter(x=>x.state==='RESOLVED').length})`,activeStyle:{background:'rgba(140,144,159,0.2)',color:'#8c909f', border:'1px solid #8c909f'} },
  { value:'all',      label: m => `All (${m.length})`,                                      activeStyle:{background:'rgba(77,142,255,0.2)', color:'#adc6ff', border:'1px solid #4d8eff'} },
]

const filteredMarkets = computed(() => {
  if (filter.value === 'active')   return markets.value.filter(m => m.state === 'ACTIVE')
  if (filter.value === 'resolved') return markets.value.filter(m => m.state === 'RESOLVED')
  return markets.value
})

async function refresh() { markets.value = (await getMarkets()).data }
onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
