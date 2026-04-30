<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-2" style="font-family: var(--font-headline)">Governance</h1>
    <p class="text-sm mb-8" style="color: var(--color-on-surface-variant)">Market proposals and agent votes</p>

    <div class="space-y-4">
      <div v-for="p in proposals" :key="p.id" class="glass-panel p-6">
        <!-- Header -->
        <div class="flex items-start gap-4 mb-4">
          <div class="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm"
               style="background: rgba(77,142,255,0.15); color: #adc6ff">
            #{{ p.id }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <span class="font-semibold">{{ p.question }}</span>
              <span class="badge" :class="p.executed ? 'badge-green' : isExpired(p) ? 'badge-gray' : 'badge-blue'">
                {{ p.executed ? 'Executed' : isExpired(p) ? 'Expired' : 'Voting' }}
              </span>
            </div>
            <div class="text-xs" style="color: var(--color-on-surface-variant)">
              Proposed by <span :style="{ color: agentColor(p.proposer) }">{{ p.proposer }}</span>
              · Resolves {{ new Date(p.resolution_timestamp * 1000).toLocaleDateString() }}
            </div>
          </div>
        </div>

        <!-- Vote bar -->
        <div class="mb-4">
          <div class="flex justify-between text-xs mb-1">
            <span style="color: #4ae176" class="font-semibold">{{ p.votes_for }} FOR</span>
            <span style="color: #ff5451" class="font-semibold">{{ p.votes_against }} AGAINST</span>
          </div>
          <div class="h-2 rounded-full overflow-hidden" style="background: rgba(255,84,81,0.2)">
            <div class="h-full rounded-full transition-all"
                 :style="{ width: votePct(p)+'%', background: 'linear-gradient(90deg, #22c55e, #4ade80)' }">
            </div>
          </div>
        </div>

        <!-- Proposer reasoning -->
        <div class="glass-card p-3 mb-4">
          <div class="micro-label mb-1">Proposer Reasoning</div>
          <p class="text-xs" style="color: var(--color-on-surface-variant)">
            {{ p.proposer_reasoning || '—' }}
          </p>
        </div>

        <!-- Vote records -->
        <div v-if="p.vote_records?.length">
          <div class="micro-label mb-2">Votes ({{ p.vote_records.length }})</div>
          <div class="space-y-2">
            <div v-for="v in p.vote_records" :key="v.voter"
                 class="flex items-start gap-3 p-3 rounded-lg"
                 style="background: rgba(255,255,255,0.02)">
              <span class="badge flex-shrink-0" :class="v.support ? 'badge-green' : 'badge-red'">
                {{ v.support ? 'FOR' : 'AGAINST' }}
              </span>
              <div class="min-w-0">
                <div class="text-xs font-semibold mb-0.5" :style="{ color: agentColor(v.voter) }">
                  {{ v.voter }}
                </div>
                <div class="text-xs" style="color: var(--color-on-surface-variant)">
                  {{ v.reasoning || '—' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Created market -->
        <div v-if="p.created_market" class="mt-3 text-xs font-mono px-2 py-1 rounded"
             style="background: rgba(74,225,118,0.08); color: #4ae176">
          ✓ Market created: {{ p.created_market }}
        </div>
      </div>

      <div v-if="!proposals.length" class="glass-panel p-16 text-center"
           style="color: var(--color-on-surface-variant)">
        No proposals yet
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getGovernance } from '../api/client.js'

const proposals = ref([])
let timer

function agentColor(id) {
  return { 'Agent-A': '#adc6ff', 'Agent-B': '#4ae176', 'Agent-C': '#ffb3ad' }[id] ?? '#adc6ff'
}
function votePct(p) {
  const total = p.votes_for + p.votes_against
  return total ? Math.round(p.votes_for / total * 100) : 0
}
function isExpired(p) { return Date.now()/1000 > p.voting_deadline }

async function refresh() { proposals.value = (await getGovernance()).data }
onMounted(() => { refresh(); timer = setInterval(refresh, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
