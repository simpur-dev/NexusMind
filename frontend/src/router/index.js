import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/Process.vue'
import SimGraphPage from '../views/SimGraphPage.vue'
import EvaluationView from '../views/EvaluationView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/sim-graph/:simulationId',
    name: 'SimGraph',
    component: SimGraphPage,
    props: true
  },
  {
    path: '/evaluation/:simulationId',
    name: 'Evaluation',
    component: EvaluationView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
