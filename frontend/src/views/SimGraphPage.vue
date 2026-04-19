<template>
  <div class="sim-graph-page">
    <!-- Background -->
    <div class="page-bg">
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
    </div>

    <!-- Top bar -->
    <nav class="top-bar">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回推演
      </button>
      <h1 class="page-title">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/>
          <circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/>
          <line x1="6" y1="7" x2="10" y2="11"/><line x1="14" y1="11" x2="18" y2="7"/>
          <line x1="6" y1="17" x2="10" y2="13"/><line x1="14" y1="13" x2="18" y2="17"/>
        </svg>
        模拟知识图谱
      </h1>
      <div class="stats-bar" v-if="stats">
        <span class="stat"><strong>{{ stats.total_agents }}</strong> 智能体</span>
        <span class="stat"><strong>{{ stats.total_actions }}</strong> 行为</span>
        <span class="stat"><strong>{{ stats.total_events }}</strong> 事件</span>
        <span class="stat"><strong>{{ stats.total_variables }}</strong> 变量</span>
        <span class="stat"><strong>{{ stats.causal_edges }}</strong> 因果边</span>
        <span class="stat"><strong>{{ stats.max_round }}</strong> 轮</span>
      </div>
    </nav>

    <!-- Loading / Error -->
    <div v-if="loading" class="center-state">
      <div class="spinner"></div>
      <span>正在加载模拟知识图谱...</span>
    </div>
    <div v-else-if="error" class="center-state error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchGraph">重试</button>
    </div>

    <!-- Main content -->
    <template v-else-if="loaded">
      <!-- Toolbar -->
      <div class="toolbar">
        <div class="filter-group">
          <button :class="['filter-btn', { active: filterPlatform === '' }]" @click="filterPlatform = ''">全部</button>
          <button :class="['filter-btn twitter', { active: filterPlatform === 'twitter' }]" @click="filterPlatform = 'twitter'">信息广场</button>
          <button :class="['filter-btn reddit', { active: filterPlatform === 'reddit' }]" @click="filterPlatform = 'reddit'">话题社区</button>
        </div>
        <div class="legend">
          <span class="legend-item"><span class="dot agent"></span>智能体</span>
          <span class="legend-item"><span class="dot action"></span>行为</span>
          <span class="legend-item"><span class="dot event"></span>事件</span>
          <span class="legend-item"><span class="dot variable"></span>变量</span>
          <span class="legend-item"><span class="dot entity"></span>知识实体</span>
          <span class="legend-item"><span class="line performed"></span>执行</span>
          <span class="legend-item"><span class="line contributes"></span>汇聚为事件</span>
          <span class="legend-item"><span class="line causal"></span>因果链</span>
          <span class="legend-item"><span class="line affects"></span>影响变量</span>
          <span class="legend-item"><span class="line corresponds"></span>对应实体</span>
        </div>
        <div class="view-controls">
          <label class="ctrl-label">
            智能体上限
            <input type="range" min="5" max="50" v-model.number="topAgentCount" class="range-input" />
            {{ topAgentCount }} 个
          </label>
          <label class="ctrl-label">
            每事件行为上限
            <input type="range" min="1" max="15" v-model.number="actionsPerAgent" class="range-input" />
            {{ actionsPerAgent }} 条
          </label>
        </div>
      </div>

      <!-- Graph SVG -->
      <div class="graph-container" ref="containerEl">
        <svg ref="svgEl" class="graph-svg"></svg>
      </div>

      <!-- Detail panel -->
      <Transition name="slide-right">
        <div v-if="selectedNode" class="detail-panel">
          <div class="detail-header">
            <span class="detail-type-badge" :class="selectedNode.type">{{ typeLabel(selectedNode.type) }}</span>
            <button class="close-btn" @click="selectedNode = null">&times;</button>
          </div>
          <h3 class="detail-name">{{ selectedNode.label }}</h3>
          <div class="detail-fields">
            <div v-if="selectedNode.platform" class="field">
              <span class="field-key">平台</span>
              <span class="field-val">{{ selectedNode.platform === 'twitter' ? '信息广场' : selectedNode.platform === 'reddit' ? '话题社区' : selectedNode.platform }}</span>
            </div>
            <div v-if="selectedNode.round_num !== undefined" class="field">
              <span class="field-key">轮次</span>
              <span class="field-val">R{{ selectedNode.round_num }}</span>
            </div>
            <div v-if="selectedNode.severity !== undefined" class="field">
              <span class="field-key">严重度</span>
              <span class="field-val">{{ formatMetric(selectedNode.severity) }}</span>
            </div>
            <div v-if="selectedNode.value !== undefined" class="field">
              <span class="field-key">当前值</span>
              <span class="field-val">{{ formatMetric(selectedNode.value) }}</span>
            </div>
            <div v-if="selectedNode.delta !== undefined" class="field">
              <span class="field-key">变化量</span>
              <span class="field-val">{{ formatSignedMetric(selectedNode.delta) }}</span>
            </div>
            <div v-if="selectedNode.action_count" class="field">
              <span class="field-key">行为数</span>
              <span class="field-val">{{ selectedNode.action_count }}</span>
            </div>
            <div v-if="selectedNode.description" class="field full">
              <span class="field-key">事件描述</span>
              <p class="field-val content">{{ selectedNode.description }}</p>
            </div>
            <div v-if="selectedNode.content_preview" class="field full">
              <span class="field-key">内容预览</span>
              <p class="field-val content">{{ selectedNode.content_preview }}</p>
            </div>
            <div v-if="selectedNode.affected_variables && Object.keys(selectedNode.affected_variables).length > 0" class="field full">
              <span class="field-key">影响变量</span>
              <p class="field-val content">{{ formatAffectedVariables(selectedNode.affected_variables) }}</p>
            </div>
            <div v-if="selectedNode.entity_labels" class="field">
              <span class="field-key">实体类型</span>
              <span class="field-val">{{ selectedNode.entity_labels.join(', ') }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </template>

    <!-- Tooltip -->
    <div v-if="tooltip.show" class="graph-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      <div class="tt-label">{{ tooltip.label }}</div>
      <div class="tt-meta">{{ tooltip.meta }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as d3 from 'd3'
import { getSimGraph } from '../api/simulation'

const router = useRouter()
const route = useRoute()

const simulationId = route.params.simulationId
const graphId = route.query.graph_id
const projectId = route.query.project_id

function goBack() {
  if (projectId) {
    router.replace({
      name: 'Process',
      params: { projectId },
      query: { step: '3' }
    })
    return
  }
  router.back()
}

const loading = ref(true)
const loaded = ref(false)
const error = ref(null)
const stats = ref(null)
const filterPlatform = ref('')
const topAgentCount = ref(24)
const actionsPerAgent = ref(6)
const selectedNode = ref(null)
const tooltip = ref({ show: false, x: 0, y: 0, label: '', meta: '' })

const svgEl = ref(null)
const containerEl = ref(null)

let graphData = null
let sim = null

const NODE_COLORS = {
  agent: '#6366f1',
  action: '#f59e0b',
  entity: '#10b981',
  event: '#f43f5e',
  variable: '#38bdf8'
}
const NODE_COLORS_DIM = {
  agent: '#6366f140',
  action: '#f59e0b40',
  entity: '#10b98140',
  event: '#f43f5e40',
  variable: '#38bdf840'
}
const VARIABLE_LABELS = {
  attention_level: '关注度',
  panic_level: '恐慌度',
  trust_level: '信任度',
  polarization_level: '极化度',
  risk_level: '风险等级',
  stability_level: '稳定性'
}
const VARIABLE_ORDER = ['attention_level', 'panic_level', 'trust_level', 'polarization_level', 'risk_level', 'stability_level']
const EVENT_TYPE_LABELS = {
  heat_spike: '热度飙升',
  sentiment_shift: '情绪转折',
  trust_drop: '信任下滑',
  official_response: '官方回应',
  stabilization: '系统稳定',
  polarization_surge: '极化加剧',
  calm_restored: '恢复平稳',
  topic_outbreak: '议题爆发'
}

function typeLabel(type) {
  if (type === 'agent') return '智能体'
  if (type === 'action') return '行为'
  if (type === 'event') return '系统事件'
  if (type === 'variable') return '状态变量'
  return '知识实体'
}

function formatPlatform(platform) {
  if (!platform) return '全平台'
  return String(platform).split(',').filter(Boolean).map(item => {
    if (item === 'twitter') return '信息广场'
    if (item === 'reddit') return '话题社区'
    return item
  }).join(' / ')
}

function eventTypeLabel(eventType) {
  return EVENT_TYPE_LABELS[eventType] || String(eventType || '').replace(/_/g, ' ')
}

function formatMetric(value) {
  return Number(value || 0).toFixed(2)
}

function formatSignedMetric(value) {
  const num = Number(value || 0)
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}`
}

function formatAffectedVariables(affected) {
  return Object.entries(affected || {}).map(([key, value]) => {
    return `${VARIABLE_LABELS[key] || key} ${formatSignedMetric(value)}`
  }).join('，')
}

function edgeSourceId(edge) {
  return edge.source?.id || edge.source
}

function edgeTargetId(edge) {
  return edge.target?.id || edge.target
}

async function fetchGraph() {
  loading.value = true
  error.value = null
  try {
    const res = await getSimGraph(simulationId, {
      limit: 420,
      event_limit: 18,
      action_links_per_event: 15,
      graph_id: graphId
    })
    if (res.success && res.data) {
      graphData = res.data
      stats.value = res.data.stats
      loaded.value = true
      await nextTick()
      renderGraph()
    } else {
      error.value = res.error || '无数据'
    }
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

function normalizeGraph(nodes, edges) {
  const entityKeyToId = new Map()
  const mergedNodes = []
  const mergedIds = new Set()
  const nodeById = new Map(nodes.map(node => [node.id, node]))

  for (const node of nodes) {
    if (node.type === 'entity') {
      const entityKey = String(node.label || '').trim().toLowerCase()
      if (!entityKeyToId.has(entityKey)) {
        entityKeyToId.set(entityKey, node.id)
        mergedNodes.push(node)
        mergedIds.add(node.id)
      }
      continue
    }
    mergedNodes.push(node)
    mergedIds.add(node.id)
  }

  const mergedEdges = []
  const edgeKeys = new Set()
  for (const edge of edges) {
    let sourceId = edgeSourceId(edge)
    let targetId = edgeTargetId(edge)
    const sourceNode = nodeById.get(sourceId)
    const targetNode = nodeById.get(targetId)
    if (sourceNode?.type === 'entity') {
      sourceId = entityKeyToId.get(String(sourceNode.label || '').trim().toLowerCase())
    }
    if (targetNode?.type === 'entity') {
      targetId = entityKeyToId.get(String(targetNode.label || '').trim().toLowerCase())
    }
    if (!mergedIds.has(sourceId) || !mergedIds.has(targetId) || sourceId === targetId) continue
    const edgeKey = `${sourceId}|${targetId}|${edge.type}|${edge.relation_type || ''}`
    if (edgeKeys.has(edgeKey)) continue
    edgeKeys.add(edgeKey)
    mergedEdges.push({ ...edge, source: sourceId, target: targetId })
  }

  return {
    nodes: mergedNodes,
    edges: mergedEdges
  }
}

function renderGraph() {
  if (!svgEl.value || !graphData) return

  const width = containerEl.value?.clientWidth || window.innerWidth
  const height = containerEl.value?.clientHeight || 760

  let baseNodes = graphData.nodes || []
  let baseEdges = graphData.edges || []

  if (filterPlatform.value) {
    const visibleIds = new Set(baseNodes.filter(node => {
      if (node.type === 'event' || node.type === 'variable' || node.type === 'entity') return true
      if (!node.platform) return true
      return String(node.platform).split(',').includes(filterPlatform.value)
    }).map(node => node.id))
    baseNodes = baseNodes.filter(node => visibleIds.has(node.id))
    baseEdges = baseEdges.filter(edge => visibleIds.has(edgeSourceId(edge)) && visibleIds.has(edgeTargetId(edge)))
  }

  const normalized = normalizeGraph(baseNodes, baseEdges)
  const nodes = normalized.nodes
  const edges = normalized.edges

  const eventNodes = nodes.filter(node => node.type === 'event').sort((a, b) => (a.round_num || 0) - (b.round_num || 0))
  const variableNodes = nodes.filter(node => node.type === 'variable').sort((a, b) => VARIABLE_ORDER.indexOf(a.key) - VARIABLE_ORDER.indexOf(b.key))
  const eventIds = new Set(eventNodes.map(node => node.id))
  const variableIds = new Set(variableNodes.map(node => node.id))

  const contributionBuckets = new Map()
  for (const edge of edges) {
    if (edge.type === 'CONTRIBUTES_TO' && eventIds.has(edgeTargetId(edge))) {
      const targetId = edgeTargetId(edge)
      if (!contributionBuckets.has(targetId)) contributionBuckets.set(targetId, [])
      contributionBuckets.get(targetId).push(edgeSourceId(edge))
    }
  }

  const candidateActionIds = new Set()
  for (const eventNode of eventNodes) {
    const actionIds = contributionBuckets.get(eventNode.id) || []
    actionIds.slice(0, actionsPerAgent.value).forEach(actionId => candidateActionIds.add(actionId))
  }

  const actionToAgent = new Map()
  const candidateAgentIds = new Set()
  for (const edge of edges) {
    if (edge.type === 'PERFORMED' && candidateActionIds.has(edgeTargetId(edge))) {
      actionToAgent.set(edgeTargetId(edge), edgeSourceId(edge))
      candidateAgentIds.add(edgeSourceId(edge))
    }
  }

  const selectedAgentNodes = nodes
    .filter(node => node.type === 'agent' && candidateAgentIds.has(node.id))
    .sort((a, b) => (b.action_count || 0) - (a.action_count || 0))
    .slice(0, topAgentCount.value)
  const selectedAgentIds = new Set(selectedAgentNodes.map(node => node.id))
  const selectedActionIds = new Set([...candidateActionIds].filter(actionId => selectedAgentIds.has(actionToAgent.get(actionId))))

  const selectedEntityIds = new Set()
  for (const edge of edges) {
    if (edge.type === 'CORRESPONDS_TO' && selectedAgentIds.has(edgeSourceId(edge))) {
      selectedEntityIds.add(edgeTargetId(edge))
    }
  }

  const displayIds = new Set([
    ...selectedEntityIds,
    ...selectedAgentIds,
    ...selectedActionIds,
    ...eventIds,
    ...variableIds
  ])

  const displayNodes = nodes.filter(node => displayIds.has(node.id))
  const displayEdges = edges.filter(edge => {
    const sourceId = edgeSourceId(edge)
    const targetId = edgeTargetId(edge)
    if (!displayIds.has(sourceId) || !displayIds.has(targetId)) return false
    if (edge.type === 'PERFORMED') return selectedAgentIds.has(sourceId) && selectedActionIds.has(targetId)
    if (edge.type === 'CORRESPONDS_TO') return selectedAgentIds.has(sourceId) && selectedEntityIds.has(targetId)
    if (edge.type === 'CONTRIBUTES_TO') return selectedActionIds.has(sourceId) && eventIds.has(targetId)
    if (edge.type === 'CAUSAL') return eventIds.has(sourceId) && eventIds.has(targetId)
    if (edge.type === 'AFFECTS') return eventIds.has(sourceId) && variableIds.has(targetId)
    return true
  })

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', width).attr('height', height)

  const g = svg.append('g')
  svg.call(d3.zoom().scaleExtent([0.2, 5]).on('zoom', event => g.attr('transform', event.transform)))

  const eventYMap = new Map()
  const variableYMap = new Map()
  eventNodes.forEach((node, index) => {
    eventYMap.set(node.id, ((height - 120) / Math.max(eventNodes.length, 1)) * (index + 0.5) + 60)
  })
  variableNodes.forEach((node, index) => {
    variableYMap.set(node.id, ((height - 140) / Math.max(variableNodes.length, 1)) * (index + 0.5) + 70)
  })

  const actionYBuckets = new Map()
  const agentYBuckets = new Map()
  const entityYBuckets = new Map()
  for (const edge of displayEdges) {
    if (edge.type === 'CONTRIBUTES_TO' && eventYMap.has(edgeTargetId(edge))) {
      const actionId = edgeSourceId(edge)
      if (!actionYBuckets.has(actionId)) actionYBuckets.set(actionId, [])
      actionYBuckets.get(actionId).push(eventYMap.get(edgeTargetId(edge)))
    }
  }
  for (const edge of displayEdges) {
    if (edge.type === 'PERFORMED' && actionYBuckets.has(edgeTargetId(edge))) {
      const agentId = edgeSourceId(edge)
      if (!agentYBuckets.has(agentId)) agentYBuckets.set(agentId, [])
      agentYBuckets.get(agentId).push(...actionYBuckets.get(edgeTargetId(edge)))
    }
  }
  for (const edge of displayEdges) {
    if (edge.type === 'CORRESPONDS_TO' && agentYBuckets.has(edgeSourceId(edge))) {
      const entityId = edgeTargetId(edge)
      if (!entityYBuckets.has(entityId)) entityYBuckets.set(entityId, [])
      entityYBuckets.get(entityId).push(...agentYBuckets.get(edgeSourceId(edge)))
    }
  }

  const average = values => values && values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : height / 2
  const simNodes = displayNodes.map(node => ({
    ...node,
    x: layerX(node, width),
    y: layerY(node, height, eventYMap, variableYMap, actionYBuckets, agentYBuckets, entityYBuckets, average)
  }))
  const simEdges = displayEdges.map(edge => ({
    ...edge,
    source: edgeSourceId(edge),
    target: edgeTargetId(edge)
  }))

  if (sim) sim.stop()
  sim = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(node => node.id).distance(edgeDistance).strength(edgeStrength))
    .force('charge', d3.forceManyBody().strength(nodeCharge))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('x', d3.forceX(node => layerX(node, width)).strength(node => node.type === 'event' || node.type === 'variable' ? 0.35 : 0.18))
    .force('y', d3.forceY(node => layerY(node, height, eventYMap, variableYMap, actionYBuckets, agentYBuckets, entityYBuckets, average)).strength(node => node.type === 'event' || node.type === 'variable' ? 0.24 : 0.06))
    .force('collide', d3.forceCollide().radius(node => radius(node) + 10))
    .alphaDecay(0.08)

  const link = g.append('g').selectAll('line').data(simEdges).join('line')
    .attr('stroke', edgeColor)
    .attr('stroke-width', edgeWidth)
    .attr('stroke-dasharray', edgeDasharray)

  const node = g.append('g').selectAll('circle').data(simNodes).join('circle')
    .attr('r', radius)
    .attr('fill', item => NODE_COLORS[item.type])
    .attr('stroke', '#111')
    .attr('stroke-width', 1.5)
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, item) => {
        if (!event.active) sim.alphaTarget(0.3).restart()
        item.fx = item.x
        item.fy = item.y
      })
      .on('drag', (event, item) => {
        item.fx = event.x
        item.fy = event.y
      })
      .on('end', (event, item) => {
        if (!event.active) sim.alphaTarget(0)
        item.fx = null
        item.fy = null
      })
    )

  const label = g.append('g').selectAll('text').data(simNodes.filter(node => node.type !== 'action')).join('text')
    .text(nodeLabel)
    .attr('font-size', item => item.type === 'event' ? 11 : item.type === 'variable' ? 10 : 10)
    .attr('fill', item => {
      if (item.type === 'agent') return '#c7d2fe'
      if (item.type === 'entity') return '#6ee7b7'
      if (item.type === 'event') return '#fda4af'
      return '#7dd3fc'
    })
    .attr('text-anchor', 'middle')
    .attr('dy', item => radius(item) + 14)
    .attr('pointer-events', 'none')

  const actionLabel = g.append('g').selectAll('text').data(simNodes.filter(node => node.type === 'action')).join('text')
    .text(node => `${node.label} R${node.round_num}`)
    .attr('font-size', 9)
    .attr('fill', '#fbbf2480')
    .attr('text-anchor', 'middle')
    .attr('dy', node => radius(node) + 12)
    .attr('pointer-events', 'none')

  node.on('mouseover', (event, item) => {
    tooltip.value = {
      show: true,
      x: event.pageX + 12,
      y: event.pageY - 10,
      label: item.label,
      meta: nodeMeta(item)
    }
    const connected = new Set([item.id])
    simEdges.forEach(edge => {
      if (edge.source.id === item.id) connected.add(edge.target.id)
      if (edge.target.id === item.id) connected.add(edge.source.id)
    })
    node.attr('fill', nodeItem => connected.has(nodeItem.id) ? NODE_COLORS[nodeItem.type] : NODE_COLORS_DIM[nodeItem.type])
    link.attr('stroke-opacity', edge => edge.source.id === item.id || edge.target.id === item.id ? 1 : 0.1)
    label.attr('opacity', nodeItem => connected.has(nodeItem.id) ? 1 : 0.15)
    actionLabel.attr('opacity', nodeItem => connected.has(nodeItem.id) ? 1 : 0.15)
  })
  .on('mouseout', () => {
    tooltip.value.show = false
    node.attr('fill', item => NODE_COLORS[item.type])
    link.attr('stroke-opacity', 1)
    label.attr('opacity', 1)
    actionLabel.attr('opacity', 1)
  })
  .on('click', (_, item) => {
    selectedNode.value = { ...item }
  })

  sim.on('tick', () => {
    link
      .attr('x1', edge => edge.source.x)
      .attr('y1', edge => edge.source.y)
      .attr('x2', edge => edge.target.x)
      .attr('y2', edge => edge.target.y)
    node
      .attr('cx', item => item.x)
      .attr('cy', item => item.y)
    label
      .attr('x', item => item.x)
      .attr('y', item => item.y)
    actionLabel
      .attr('x', item => item.x)
      .attr('y', item => item.y)
  })
}

function radius(node) {
  if (node.type === 'variable') return 12
  if (node.type === 'event') return 10 + Math.min((node.severity || 0) * 10, 10)
  if (node.type === 'agent') return 10 + Math.min((node.action_count || 0) * 0.5, 20)
  if (node.type === 'entity') return 9
  return 5
}

function trunc(value, limit) {
  return !value ? '' : value.length > limit ? `${value.slice(0, limit)}…` : value
}

function layerX(node, width) {
  if (node.type === 'entity') return width * 0.08
  if (node.type === 'agent') return width * 0.24
  if (node.type === 'action') return width * 0.46
  if (node.type === 'event') return width * 0.70
  if (node.type === 'variable') return width * 0.88
  return width * 0.5
}

function layerY(node, height, eventYMap, variableYMap, actionYBuckets, agentYBuckets, entityYBuckets, average) {
  if (node.type === 'event') return eventYMap.get(node.id) || height / 2
  if (node.type === 'variable') return variableYMap.get(node.id) || height / 2
  if (node.type === 'action') return average(actionYBuckets.get(node.id))
  if (node.type === 'agent') return average(agentYBuckets.get(node.id))
  if (node.type === 'entity') return average(entityYBuckets.get(node.id))
  return height / 2
}

function edgeDistance(edge) {
  if (edge.type === 'CAUSAL') return 110
  if (edge.type === 'AFFECTS') return 90
  if (edge.type === 'CONTRIBUTES_TO') return 95
  if (edge.type === 'PERFORMED') return 72
  if (edge.type === 'CORRESPONDS_TO') return 84
  return 70
}

function edgeStrength(edge) {
  if (edge.type === 'CAUSAL') return 0.72
  if (edge.type === 'AFFECTS') return 0.88
  if (edge.type === 'CONTRIBUTES_TO') return 0.66
  if (edge.type === 'PERFORMED') return 0.48
  if (edge.type === 'CORRESPONDS_TO') return 0.34
  return 0.4
}

function edgeColor(edge) {
  if (edge.type === 'CAUSAL') return '#fb718580'
  if (edge.type === 'AFFECTS') return '#38bdf880'
  if (edge.type === 'CONTRIBUTES_TO') return '#f59e0b80'
  if (edge.type === 'CORRESPONDS_TO') return '#10b98160'
  return '#6366f150'
}

function edgeWidth(edge) {
  if (edge.type === 'CAUSAL') return 2.2
  if (edge.type === 'AFFECTS') return 2
  if (edge.type === 'CONTRIBUTES_TO') return 1.6
  if (edge.type === 'CORRESPONDS_TO') return 1.5
  return 1.2
}

function edgeDasharray(edge) {
  if (edge.type === 'CAUSAL') return '6 4'
  if (edge.type === 'AFFECTS') return '4 4'
  return null
}

function nodeCharge(node) {
  if (node.type === 'variable') return -420
  if (node.type === 'event') return -260
  if (node.type === 'entity') return -160
  return -120
}

function nodeMeta(node) {
  if (node.type === 'agent') return `${node.action_count || 0} 条行为 · ${formatPlatform(node.platform)}`
  if (node.type === 'action') return `${node.label} · R${node.round_num} · ${formatPlatform(node.platform)}`
  if (node.type === 'event') return `${eventTypeLabel(node.event_type || node.label)} · R${node.round_num} · 严重度 ${formatMetric(node.severity)}`
  if (node.type === 'variable') return `当前值 ${formatMetric(node.value)} · 变化 ${formatSignedMetric(node.delta)}`
  return '知识实体'
}

function nodeLabel(node) {
  if (node.type === 'agent') return `[智] ${trunc(node.label, 6)}`
  if (node.type === 'entity') return `${trunc(node.label, 8)} (实体)`
  if (node.type === 'event') return `${eventTypeLabel(node.event_type || node.label)} · R${node.round_num}`
  if (node.type === 'variable') return `${node.label} ${formatMetric(node.value)}`
  return trunc(node.label, 10)
}

watch([filterPlatform, topAgentCount, actionsPerAgent], () => {
  if (loaded.value) renderGraph()
})

onMounted(() => {
  fetchGraph()
})

onBeforeUnmount(() => {
  if (sim) sim.stop()
})
</script>

<style scoped>
.sim-graph-page {
  position: fixed;
  inset: 0;
  background: #0a0a14;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Inter', -apple-system, sans-serif;
  z-index: 100;
}

/* BG */
.page-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.bg-orb {
  position: absolute; border-radius: 50%; filter: blur(120px); opacity: .15;
}
.bg-orb-1 { width: 500px; height: 500px; background: #6366f1; top: -100px; left: -100px; }
.bg-orb-2 { width: 400px; height: 400px; background: #10b981; bottom: -80px; right: -80px; }

/* Top bar */
.top-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: rgba(10,10,20,0.85);
  border-bottom: 1px solid #1a1a2e;
  backdrop-filter: blur(10px);
  z-index: 2;
  flex-shrink: 0;
}
.back-btn {
  display: flex; align-items: center; gap: 4px;
  background: none; border: 1px solid #333; border-radius: 8px;
  color: #aaa; padding: 6px 12px; font-size: 13px; cursor: pointer;
  transition: all .15s;
}
.back-btn:hover { border-color: #6366f1; color: #c7d2fe; }
.page-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 17px; font-weight: 600; margin: 0; color: #e8e8f0;
}
.page-title svg { opacity: .7; }
.stats-bar {
  margin-left: auto;
  display: flex; gap: 16px; font-size: 13px; color: #888;
}
.stat strong { color: #c7d2fe; margin-right: 2px; }

/* Toolbar */
.toolbar {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 10px 20px;
  background: rgba(10,10,20,0.6);
  border-bottom: 1px solid #1a1a2e;
  flex-shrink: 0;
  z-index: 2;
  position: relative;
}
.filter-group { display: flex; gap: 4px; }
.filter-btn {
  font-size: 12px; padding: 4px 12px; border-radius: 6px;
  border: 1px solid #2a2a3a; background: transparent; color: #888; cursor: pointer;
  transition: all .15s;
}
.filter-btn.active { border-color: #6366f1; color: #a5b4fc; background: #6366f118; }
.filter-btn.twitter.active { border-color: #3b82f6; color: #93c5fd; background: #3b82f618; }
.filter-btn.reddit.active { border-color: #f97316; color: #fdba74; background: #f9731618; }
.legend {
  display: flex; align-items: center; gap: 12px; font-size: 11px; color: #777;
}
.legend-item { display: flex; align-items: center; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.agent { background: #6366f1; }
.dot.action { background: #f59e0b; }
.dot.event { background: #f43f5e; }
.dot.variable { background: #38bdf8; }
.dot.entity { background: #10b981; }
.line { width: 16px; height: 2px; border-radius: 1px; }
.line.performed { background: #6366f160; }
.line.contributes { background: #f59e0b80; }
.line.causal { background: #fb718580; }
.line.affects { background: #38bdf880; }
.line.corresponds { background: #10b98160; }
.view-controls {
  margin-left: auto;
  display: flex; gap: 16px; align-items: center;
}
.ctrl-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #888;
}
.range-input {
  width: 80px; accent-color: #6366f1;
}

/* Graph */
.graph-container {
  flex: 1; position: relative; overflow: hidden;
}
.graph-svg { width: 100%; height: 100%; }

/* Center state */
.center-state {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 10px; font-size: 14px; color: #888;
}
.center-state.error { color: #f87171; }
.spinner {
  width: 22px; height: 22px;
  border: 2px solid #333; border-top-color: #6366f1;
  border-radius: 50%; animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.retry-btn {
  padding: 6px 14px; border-radius: 6px;
  border: 1px solid #6366f1; background: transparent; color: #a5b4fc;
  cursor: pointer; font-size: 13px;
}
.retry-btn:hover { background: #6366f1; color: #fff; }

/* Detail panel */
.detail-panel {
  position: absolute; right: 0; top: 0; bottom: 0;
  width: 320px; background: rgba(14,14,28,0.95);
  border-left: 1px solid #1a1a2e; padding: 20px;
  overflow-y: auto; z-index: 5;
  backdrop-filter: blur(12px);
}
.detail-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.detail-type-badge {
  font-size: 11px; padding: 3px 10px; border-radius: 10px; font-weight: 600;
}
.detail-type-badge.agent { background: #6366f130; color: #a5b4fc; }
.detail-type-badge.action { background: #f59e0b20; color: #fbbf24; }
.detail-type-badge.event { background: #f43f5e20; color: #fda4af; }
.detail-type-badge.variable { background: #38bdf820; color: #7dd3fc; }
.detail-type-badge.entity { background: #10b98120; color: #6ee7b7; }
.close-btn {
  background: none; border: none; color: #666; font-size: 22px;
  cursor: pointer; line-height: 1;
}
.close-btn:hover { color: #eee; }
.detail-name {
  font-size: 16px; font-weight: 600; margin: 0 0 16px; color: #f0f0f8;
}
.detail-fields { display: flex; flex-direction: column; gap: 10px; }
.field {
  display: flex; gap: 8px; align-items: baseline;
}
.field.full { flex-direction: column; }
.field-key { font-size: 11px; color: #666; min-width: 50px; flex-shrink: 0; }
.field-val { font-size: 13px; color: #ccc; }
.field-val.content {
  margin: 4px 0 0; font-size: 12px; line-height: 1.5;
  color: #aaa; background: rgba(255,255,255,0.03);
  padding: 8px 10px; border-radius: 6px;
}

/* Tooltip */
.graph-tooltip {
  position: fixed; padding: 8px 14px;
  background: #1e1e2e; border: 1px solid #333; border-radius: 8px;
  font-size: 12px; color: #ddd; pointer-events: none; z-index: 20;
  max-width: 280px;
}
.tt-label { font-weight: 600; }
.tt-meta { font-size: 11px; color: #999; margin-top: 2px; }

/* Transitions */
.slide-right-enter-active, .slide-right-leave-active {
  transition: transform .25s ease, opacity .25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  transform: translateX(100%); opacity: 0;
}
</style>
