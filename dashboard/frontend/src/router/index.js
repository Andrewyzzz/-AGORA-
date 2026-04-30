import { createRouter, createWebHistory } from 'vue-router'
import Overview   from '../views/Overview.vue'
import Markets    from '../views/Markets.vue'
import Agents     from '../views/Agents.vue'
import Governance from '../views/Governance.vue'
import Trades     from '../views/Trades.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',           component: Overview   },
    { path: '/markets',    component: Markets    },
    { path: '/agents',     component: Agents     },
    { path: '/governance', component: Governance },
    { path: '/trades',     component: Trades     },
  ]
})
