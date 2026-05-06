import { createRouter, createWebHistory } from 'vue-router'

const loadView = (name) => () => import(`../views/${name}.vue`)

const defineRoute = (path, name, viewName, props = false) => ({
  path,
  name,
  component: loadView(viewName),
  props
})

const routes = [
  defineRoute('/', 'Home', 'Home'),
  defineRoute('/process/:projectId', 'Process', 'Process', true),
  defineRoute('/sim-graph/:simulationId', 'SimGraph', 'SimGraphPage', true),
  defineRoute('/incident/:projectId', 'IncidentWorkspace', 'IncidentWorkspaceView', true)
]

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})
