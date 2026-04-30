<template>
  <div class="flex min-h-screen" style="background: var(--color-background)">
    <!-- Sidebar -->
    <aside class="w-56 flex-shrink-0 flex flex-col py-6 px-3 border-r"
           style="border-color: var(--color-outline-variant); background: var(--color-surface-low)">
      <!-- Logo -->
      <div class="flex items-center gap-3 px-3 mb-8">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center"
             style="background: linear-gradient(135deg, #4d8eff, #00b954)">
          <span class="text-white font-bold text-sm">A</span>
        </div>
        <div>
          <div class="font-bold text-sm" style="font-family: var(--font-headline); color: var(--color-on-surface)">AGORA</div>
          <div class="micro-label">AI Economy</div>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex flex-col gap-1 flex-1">
        <router-link v-for="item in navItems" :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ active: $route.path === item.path }">
          <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </nav>

      <!-- Live indicator -->
      <div class="flex items-center gap-2 px-3 py-2">
        <div class="live-dot"></div>
        <span class="micro-label">Live · Base Sepolia</span>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
const navItems = [
  { path: '/',           label: 'Overview',   icon: 'dashboard'    },
  { path: '/markets',    label: 'Markets',    icon: 'trending_up'  },
  { path: '/agents',     label: 'Agents',     icon: 'smart_toy'    },
  { path: '/governance', label: 'Governance', icon: 'how_to_vote'  },
  { path: '/trades',     label: 'Trades',     icon: 'swap_horiz'   },
]
</script>
