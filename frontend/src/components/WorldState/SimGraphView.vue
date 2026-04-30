<template>
  <div class="sim-graph-section">
    <div class="section-header" @click="expanded = !expanded">
      <h3 class="section-title">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/>
          <circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/>
          <line x1="6" y1="7" x2="10" y2="11"/><line x1="14" y1="11" x2="18" y2="7"/>
          <line x1="6" y1="17" x2="10" y2="13"/><line x1="14" y1="13" x2="18" y2="17"/>
        </svg>
        模拟知识图谱
      </h3>
      <div class="header-right">
        <div v-if="stats" class="stats-pills">
          <span class="pill agent">{{ stats.total_agents }} 智能体</span>
          <span class="pill action">{{ stats.total_actions }} 行为</span>
          <span class="pill round">{{ stats.max_round }} 轮</span>
        </div>
        <button v-if="!loaded && !loading" class="load-btn" @click.stop="fetchGraph">
          加载图谱
        </button>
        <svg class="chevron" :class="{ open: expanded }" viewBox="0 0 24 24" width="16" height="16"
             fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>
    </div>

    <Transition name="slide">
      <div v-if="expanded" class="graph-body">
        <div v-if="loading" class="graph-loading">
          <div class="spinner"></div>
          <span>正在加载模拟知识图谱...</span>
        </div>
        <div v-else-if="error" class="graph-error">
          <span>{{ error }}</span>
          <button class="retry-btn" @click="fetchGraph">重试</button>
        </div>
        <div v-else-if="!loaded" class="graph-empty">
          <p>推演完成后可查看知识图谱可视化</p>
          <button class="load-btn" @click="fetchGraph">加载图谱</button>
        </div>
        <template v-else>
          <!-- Filter bar -->
          <div class="filter-bar">
            <button :class="['filter-btn', { active: filterPlatform === '' }]" @click="filterPlatform = ''">全部</button>
            <button :class="['filter-btn', { active: filterPlatform === 'twitter' }]" @click="filterPlatform = 'twitter'">信息广场</button>
            <button :class="['filter-btn', { active: filterPlatform === 'reddit' }]" @click="filterPlatform = 'reddit'">话题社区</button>
            <div class="filter-legend">
              <span class="legend-dot agent"></span><span>智能体</span>
              <span class="legend-dot action"></span><span>行为</span>
              <span class="legend-dot entity"></span><span>知识实体</span>
            </div>
          </div>
          <!-- SVG canvas -->
          <div class="graph-canvas-wrap" ref="canvasWrap">
            <svg ref="svgEl" class="graph-svg"></svg>
          </div>
          <!-- Tooltip -->
          <div v-if="tooltip.show" class="graph-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
            <div class="tt-label">{{ tooltip.label }}</div>
            <div class="tt-type">{{ tooltip.type }}</div>
            <div v-if="tooltip.extra" class="tt-extra">{{ tooltip.extra }}</div>
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import * as d3 from 'd3'
import { getSimGraph } from '../../api/simulation'

const props = defineProps({
  simulationId: String,
  graphId: String,
  simulationCompleted: Boolean
})

const expanded = ref(false)
const loading = ref(false)
const loaded = ref(false)
const error = ref(null)
const stats = ref(null)
const filterPlatform = ref('')
const svgEl = ref(null)
const canvasWrap = ref(null)

const tooltip = ref({ show: false, x: 0, y: 0, label: '', type: '', extra: '' })

let graphData = null
let simulation = null

const NODE_COLORS = {
  agent: '#6366f1',
  action: '#f59e0b',
  entity: '#10b981',
}
const EDGE_COLORS = {
  PERFORMED: '#6366f180',
  CORRESPONDS_TO: '#10b98180',
}

async function fetchGraph() {
  if (!props.simulationId) return
  loading.value = true
  error.value = null
  try {
    const res = await getSimGraph(props.simulationId, { limit: 500, graph_id: props.graphId })
    if (res.data?.success && res.data.data) {
      graphData = res.data.data
      stats.value = graphData.stats
      loaded.value = true
      await nextTick()
      renderGraph()
    } else {
      error.value = res.data?.error || '无数据'
    }
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!svgEl.value || !graphData) return
  const wrap = canvasWrap.value
  const width = wrap.clientWidth || 800
  const height = 500

  // Filter nodes/edges by platform
  let nodes = graphData.nodes
  let edges = graphData.edges
  if (filterPlatform.value) {
    const visibleNodeIds = new Set()
    nodes = graphData.nodes.filter(n => {
      if (n.type === 'entity') return true
      if (n.platform === filterPlatform.value || !n.platform) return true
      return false
    })
    nodes.forEach(n => visibleNodeIds.add(n.id))
    edges = graphData.edges.filter(e => visibleNodeIds.has(e.source?.id || e.source) && visibleNodeIds.has(e.target?.id || e.target))
  }

  // Limit displayed action nodes to avoid clutter (show top agents + their actions)
  const agentNodes = nodes.filter(n => n.type === 'agent').sort((a, b) => (b.action_count || 0) - (a.action_count || 0))
  const topAgentIds = new Set(agentNodes.slice(0, 30).map(n => n.id))
  const entityNodes = nodes.filter(n => n.type === 'entity')
  const actionNodes = nodes.filter(n => n.type === 'action')
  // For each top agent, keep up to 5 action nodes
  const agentActionCount = {}
  const keptActionIds = new Set()
  for (const edge of edges) {
    const sid = edge.source?.id || edge.source
    const tid = edge.target?.id || edge.target
    if (topAgentIds.has(sid) && actionNodes.some(n => n.id === tid)) {
      agentActionCount[sid] = (agentActionCount[sid] || 0) + 1
      if (agentActionCount[sid] <= 5) keptActionIds.add(tid)
    }
  }

  const displayNodes = [
    ...agentNodes.slice(0, 30),
    ...actionNodes.filter(n => keptActionIds.has(n.id)),
    ...entityNodes,
  ]
  const displayNodeIds = new Set(displayNodes.map(n => n.id))
  const displayEdges = edges.filter(e => {
    const sid = e.source?.id || e.source
    const tid = e.target?.id || e.target
    return displayNodeIds.has(sid) && displayNodeIds.has(tid)
  })

  // D3 setup
  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', width).attr('height', height)

  const g = svg.append('g')

  // Zoom
  const zoom = d3.zoom().scaleExtent([0.2, 4]).on('zoom', (event) => {
    g.attr('transform', event.transform)
  })
  svg.call(zoom)

  // Clone for simulation (d3 mutates)
  const simNodes = displayNodes.map(d => ({ ...d }))
  const simEdges = displayEdges.map(d => ({
    ...d,
    source: d.source?.id || d.source,
    target: d.target?.id || d.target,
  }))

  if (simulation) simulation.stop()

  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(60))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius(d => nodeRadius(d) + 4))

  // Edges
  const link = g.append('g').selectAll('line')
    .data(simEdges).join('line')
    .attr('stroke', d => EDGE_COLORS[d.type] || '#444')
    .attr('stroke-width', d => d.type === 'SAME_AS' ? 2 : 1)

  // Nodes
  const node = g.append('g').selectAll('circle')
    .data(simNodes).join('circle')
    .attr('r', d => nodeRadius(d))
    .attr('fill', d => NODE_COLORS[d.type] || '#888')
    .attr('stroke', '#1a1a2e')
    .attr('stroke-width', 1.5)
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
      .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
    )

  // Labels (agents only)
  const label = g.append('g').selectAll('text')
    .data(simNodes.filter(n => n.type === 'agent')).join('text')
    .text(d => truncate(d.label, 6))
    .attr('font-size', 10)
    .attr('fill', '#ccc')
    .attr('text-anchor', 'middle')
    .attr('dy', d => nodeRadius(d) + 12)
    .attr('pointer-events', 'none')

  // Hover
  node.on('mouseover', (event, d) => {
    const rect = canvasWrap.value.getBoundingClientRect()
    tooltip.value = {
      show: true,
      x: event.clientX - rect.left + 10,
      y: event.clientY - rect.top - 10,
      label: d.label,
      type: d.type === 'agent' ? `智能体 · ${d.platform || ''}` : d.type === 'action' ? `行为 · R${d.round_num}` : '知识实体',
      extra: d.content_preview || (d.action_count ? `${d.action_count} 条行为` : ''),
    }
  }).on('mouseout', () => { tooltip.value.show = false })

  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    node.attr('cx', d => d.x).attr('cy', d => d.y)
    label.attr('x', d => d.x).attr('y', d => d.y)
  })
}

function nodeRadius(d) {
  if (d.type === 'agent') return 8 + Math.min((d.action_count || 0), 20)
  if (d.type === 'entity') return 10
  return 4
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}

watch(filterPlatform, () => { if (loaded.value) renderGraph() })

watch(() => props.simulationCompleted, (val) => {
  if (val && !loaded.value) {
    expanded.value = true
    fetchGraph()
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
})

defineExpose({ expanded, loaded, fetchGraph })
</script>

<style scoped>
.sim-graph-section {
  margin-top: 24px;
  background: rgba(255,255,255,0.02);
  border: 1px solid #22222a;
  border-radius: 12px;
  overflow: hidden;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
  transition: background .15s;
}
.section-header:hover { background: rgba(255,255,255,0.03); }
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #e0e0e0;
  margin: 0;
}
.section-title svg { opacity: .7; }
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.stats-pills {
  display: flex;
  gap: 6px;
}
.pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.pill.agent { background: #6366f130; color: #a5b4fc; }
.pill.action { background: #f59e0b20; color: #fbbf24; }
.pill.round { background: #10b98120; color: #6ee7b7; }
.chevron {
  transition: transform .2s;
  opacity: .5;
}
.chevron.open { transform: rotate(180deg); }
.load-btn, .retry-btn {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  border: 1px solid #6366f1;
  background: transparent;
  color: #a5b4fc;
  cursor: pointer;
  transition: all .15s;
}
.load-btn:hover, .retry-btn:hover {
  background: #6366f1;
  color: #fff;
}

/* Body */
.graph-body {
  border-top: 1px solid #22222a;
  padding: 14px 18px;
}
.graph-loading, .graph-error, .graph-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 30px 0;
  color: #888;
  font-size: 13px;
}
.graph-error { color: #f87171; }
.spinner {
  width: 18px; height: 18px;
  border: 2px solid #333;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Filter bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.filter-btn {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: transparent;
  color: #999;
  cursor: pointer;
  transition: all .15s;
}
.filter-btn.active {
  border-color: #6366f1;
  color: #a5b4fc;
  background: #6366f118;
}
.filter-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  font-size: 11px;
  color: #777;
}
.legend-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-left: 8px;
}
.legend-dot.agent { background: #6366f1; }
.legend-dot.action { background: #f59e0b; }
.legend-dot.entity { background: #10b981; }

/* Canvas */
.graph-canvas-wrap {
  position: relative;
  width: 100%;
  height: 500px;
  background: #0d0d1a;
  border-radius: 8px;
  overflow: hidden;
}
.graph-svg {
  width: 100%;
  height: 100%;
}

/* Tooltip */
.graph-tooltip {
  position: absolute;
  padding: 8px 12px;
  background: #1e1e2e;
  border: 1px solid #333;
  border-radius: 8px;
  font-size: 12px;
  color: #ddd;
  pointer-events: none;
  z-index: 10;
  max-width: 240px;
}
.tt-label { font-weight: 600; margin-bottom: 2px; }
.tt-type { font-size: 11px; color: #999; }
.tt-extra { font-size: 11px; color: #bbb; margin-top: 4px; }

/* Transition */
.slide-enter-active, .slide-leave-active {
  transition: all .25s ease;
  max-height: 600px;
  overflow: hidden;
}
.slide-enter-from, .slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
