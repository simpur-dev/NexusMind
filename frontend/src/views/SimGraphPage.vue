<template>
  <div class="causal-page">
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
          <path d="M4 4h6v6H4z"/><path d="M14 4h6v6h-6z"/><path d="M9 14h6v6H9z"/>
          <path d="M7 10v2l2 2"/><path d="M17 10v2l-2 2"/>
        </svg>
        事件因果图谱
      </h1>
      <div class="stats-bar" v-if="stats">
        <span class="stat"><strong>{{ stats.total_events }}</strong> 事件</span>
        <span class="stat"><strong>{{ stats.causal_edges }}</strong> 因果边</span>
        <span class="stat"><strong>{{ stats.max_round }}</strong> 轮</span>
      </div>
    </nav>

    <!-- Loading / Error -->
    <div v-if="loading" class="center-state">
      <div class="spinner"></div>
      <span>正在加载因果图谱...</span>
    </div>
    <div v-else-if="error" class="center-state error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchGraph">重试</button>
    </div>

    <!-- Main content -->
    <template v-else-if="loaded">
      <!-- Legend bar -->
      <div class="toolbar">
        <div class="legend-section">
          <span class="legend-title">事件类型</span>
          <span class="legend-item" v-for="(label, key) in EVENT_TYPE_LABELS" :key="key">
            <span class="dot" :style="{ background: EVENT_COLORS[key] || '#f43f5e' }"></span>{{ label }}
          </span>
        </div>
        <div class="legend-section">
          <span class="legend-title">因果关系</span>
          <span class="legend-item" v-for="(label, key) in RELATION_LABELS" :key="key">
            <span class="edge-sample" :style="{ background: RELATION_COLORS[key] }"></span>{{ label }}
          </span>
        </div>
      </div>

      <!-- Graph SVG -->
      <div class="graph-container" ref="containerEl">
        <svg ref="svgEl" class="graph-svg"></svg>
      </div>

      <!-- Detail panel -->
      <Transition name="slide-right">
        <div v-if="selectedEvent" class="detail-panel">
          <div class="detail-header">
            <span class="detail-type-badge" :style="{ background: EVENT_COLORS[selectedEvent.event_type] + '30', color: EVENT_COLORS[selectedEvent.event_type] }">
              {{ eventTypeLabel(selectedEvent.event_type) }}
            </span>
            <button class="close-btn" @click="selectedEvent = null">&times;</button>
          </div>
          <h3 class="detail-name">{{ eventTypeLabel(selectedEvent.event_type) }} · 第{{ selectedEvent.round_num }}轮</h3>
          <div class="detail-fields">
            <div class="field">
              <span class="field-key">轮次</span>
              <span class="field-val">第 {{ selectedEvent.round_num }} 轮</span>
            </div>
            <div class="field">
              <span class="field-key">严重度</span>
              <span class="field-val">{{ (selectedEvent.severity || 0).toFixed(2) }}</span>
            </div>
            <div v-if="selectedEvent.description" class="field full">
              <span class="field-key">事件描述</span>
              <p class="field-val content">{{ selectedEvent.description }}</p>
            </div>
            <div v-if="selectedEvent.affected_variables && Object.keys(selectedEvent.affected_variables).length" class="field full">
              <span class="field-key">影响变量</span>
              <p class="field-val content">{{ formatAffectedVars(selectedEvent.affected_variables) }}</p>
            </div>
            <!-- 相关因果边 -->
            <div v-if="relatedEdges.length" class="field full">
              <span class="field-key">相关因果 ({{ relatedEdges.length }})</span>
              <div class="related-edges">
                <div v-for="re in relatedEdges" :key="re.id" class="re-card" :style="{ borderLeftColor: RELATION_COLORS[re.relation_type] }">
                  <div class="re-head">
                    <span class="re-rel">{{ RELATION_LABELS[re.relation_type] || re.relation_type }}</span>
                    <span class="re-strength">{{ (re.strength || 0).toFixed(2) }}</span>
                  </div>
                  <div class="re-pair">
                    {{ eventTypeLabel(re.source_type) }} 第{{ re.source_round }}轮
                    → {{ eventTypeLabel(re.target_type) }} 第{{ re.target_round }}轮
                  </div>
                  <div v-if="cleanEvidence(re.evidence)" class="re-evidence">{{ cleanEvidence(re.evidence) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </template>

    <!-- Tooltip -->
    <div v-if="tooltip.show" class="graph-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      <div class="tt-label">{{ tooltip.label }}</div>
      <div class="tt-meta">{{ tooltip.meta }}</div>
      <div v-if="tooltip.desc" class="tt-desc">{{ tooltip.desc }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
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
    router.replace({ name: 'Process', params: { projectId }, query: { step: '3' } })
    return
  }
  router.back()
}

// ============== 常量 ==============
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
const EVENT_COLORS = {
  heat_spike: '#f97316',
  sentiment_shift: '#a855f7',
  trust_drop: '#ef4444',
  official_response: '#3b82f6',
  stabilization: '#10b981',
  polarization_surge: '#ec4899',
  calm_restored: '#06b6d4',
  topic_outbreak: '#f59e0b'
}
const RELATION_COLORS = {
  triggered: '#60a5fa',
  amplified: '#f87171',
  suppressed: '#34d399',
  correlated: '#fbbf24'
}
const RELATION_LABELS = {
  triggered: '触发',
  amplified: '放大',
  suppressed: '抑制',
  correlated: '关联'
}
const VARIABLE_LABELS = {
  attention_level: '关注度', panic_level: '恐慌度', trust_level: '信任度',
  polarization_level: '极化度', risk_level: '风险等级', stability_level: '稳定性'
}

function eventTypeLabel(t) { return EVENT_TYPE_LABELS[t] || String(t || '').replace(/_/g, ' ') }

function cleanEvidence(txt) {
  if (!txt) return ''
  return String(txt)
    .replace(/[\(（][^\)）]*(?:evt_|ce_)[a-f0-9]+[^\)）]*[\)）]/g, '')
    .replace(/\b(?:evt_|ce_)[a-f0-9]{6,}\b/g, '')
    .replace(/\b(?:Round|round)\s*\d*/gi, '')
    .replace(/\b(?:severity|strength|stabilization|heat_spike|sentiment_shift|trust_drop|official_response|polarization_surge|calm_restored|topic_outbreak)\b/gi, '')
    .replace(/\s*[,，]\s*[,，]/g, '，')
    .replace(/\s{2,}/g, ' ')
    .trim()
}
function formatAffectedVars(affected) {
  return Object.entries(affected || {}).map(([k, v]) => {
    const num = Number(v || 0)
    return `${VARIABLE_LABELS[k] || k} ${num >= 0 ? '+' : ''}${num.toFixed(2)}`
  }).join('，')
}

// ============== 状态 ==============
const loading = ref(true)
const loaded = ref(false)
const error = ref(null)
const stats = ref(null)
const selectedEvent = ref(null)
const tooltip = ref({ show: false, x: 0, y: 0, label: '', meta: '', desc: '' })
const svgEl = ref(null)
const containerEl = ref(null)

let rawEvents = []
let rawCausalEdges = []
let sim = null

// 选中事件的相关因果边
const relatedEdges = computed(() => {
  if (!selectedEvent.value) return []
  const id = selectedEvent.value.id
  const eventMap = new Map(rawEvents.map(e => [e.id, e]))
  return rawCausalEdges
    .filter(e => e.source === id || e.target === id)
    .map(e => {
      const src = eventMap.get(typeof e.source === 'object' ? e.source.id : e.source) || {}
      const tgt = eventMap.get(typeof e.target === 'object' ? e.target.id : e.target) || {}
      return {
        id: `${e.source}-${e.target}`,
        relation_type: e.relation_type,
        strength: e.strength,
        evidence: e.evidence,
        source_type: src.event_type,
        source_round: src.round_num,
        target_type: tgt.event_type,
        target_round: tgt.round_num
      }
    })
})

// ============== 数据加载 ==============
async function fetchGraph() {
  loading.value = true
  error.value = null
  try {
    const res = await getSimGraph(simulationId, {
      limit: 10,
      event_limit: 60,
      action_links_per_event: 0,
      graph_id: graphId
    })
    if (res.success && res.data) {
      // 只提取事件节点和因果边
      rawEvents = (res.data.nodes || []).filter(n => n.type === 'event')
      rawCausalEdges = (res.data.edges || []).filter(e => e.type === 'CAUSAL')
      stats.value = {
        total_events: rawEvents.length,
        causal_edges: rawCausalEdges.length,
        max_round: res.data.stats?.max_round || 0
      }
      loaded.value = true
      loading.value = false
      await nextTick()
      renderGraph()
    } else {
      error.value = res.error || '无数据'
      loading.value = false
    }
  } catch (e) {
    error.value = e.message || '请求失败'
    loading.value = false
  }
}

// ============== 渲染 ==============
function truncate(s, n) { return !s ? '' : s.length > n ? s.slice(0, n) + '…' : s }

function renderGraph() {
  if (!svgEl.value || !rawEvents.length) return

  const cRect = containerEl.value?.getBoundingClientRect()
  const W = cRect?.width || window.innerWidth
  const H = cRect?.height || 700
  const pad = { top: 90, bottom: 60, left: 120, right: 120 }

  // 按轮次分组
  const rounds = [...new Set(rawEvents.map(e => e.round_num))].sort((a, b) => a - b)
  const roundIndex = new Map(rounds.map((r, i) => [r, i]))
  const eventsByRound = new Map()
  rawEvents.forEach(e => {
    if (!eventsByRound.has(e.round_num)) eventsByRound.set(e.round_num, [])
    eventsByRound.get(e.round_num).push(e)
  })

  // 布局：扩展画布让节点不挤
  const canvasW = Math.max(W, rounds.length * 220)
  const canvasH = Math.max(H, (Math.max(...[...eventsByRound.values()].map(b => b.length)) + 1) * 140)
  const maxRI = Math.max(rounds.length - 1, 1)
  const xScale = d3.scaleLinear().domain([0, maxRI]).range([pad.left, canvasW - pad.right])

  const nodeIds = new Set(rawEvents.map(e => e.id))
  const nodes = rawEvents.map(e => {
    const ri = roundIndex.get(e.round_num)
    const bucket = eventsByRound.get(e.round_num)
    const idx = bucket.indexOf(e)
    const ySpan = canvasH - pad.top - pad.bottom
    const yStep = ySpan / (bucket.length + 1)
    return { ...e, x: xScale(ri), y: pad.top + yStep * (idx + 1), fx: xScale(ri) }
  })

  const edges = rawCausalEdges
    .map(e => ({ ...e, source: e.source?.id || e.source, target: e.target?.id || e.target }))
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()
  svg.attr('width', W).attr('height', H)

  // 箭头标记（加大尺寸）
  const defs = svg.append('defs')
  for (const [rel, color] of Object.entries(RELATION_COLORS)) {
    defs.append('marker')
      .attr('id', `arrow-${rel}`)
      .attr('viewBox', '0 -6 12 12')
      .attr('refX', 24).attr('refY', 0)
      .attr('markerWidth', 10).attr('markerHeight', 10)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-5L12,0L0,5Z').attr('fill', color)
  }
  // 节点发光
  const glow = defs.append('filter').attr('id', 'glow').attr('x', '-40%').attr('y', '-40%').attr('width', '180%').attr('height', '180%')
  glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur')
  glow.append('feMerge').selectAll('feMergeNode').data(['blur', 'SourceGraphic']).join('feMergeNode').attr('in', d => d)
  // 连线发光
  const edgeGlow = defs.append('filter').attr('id', 'edge-glow').attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%')
  edgeGlow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
  edgeGlow.append('feMerge').selectAll('feMergeNode').data(['blur', 'SourceGraphic']).join('feMergeNode').attr('in', d => d)

  const g = svg.append('g')
  const zoom = d3.zoom().scaleExtent([0.15, 4]).on('zoom', ev => g.attr('transform', ev.transform))
  svg.call(zoom)
  // zoom-to-fit：缩放到能看到全部内容，但保证最小 0.5 倍不会太小
  const rawScale = Math.min(W / canvasW, H / canvasH)
  const fitScale = Math.max(rawScale * 0.88, 0.45)
  const fitTx = (W - canvasW * fitScale) / 2
  const fitTy = (H - canvasH * fitScale) / 2
  svg.call(zoom.transform, d3.zoomIdentity.translate(fitTx, fitTy).scale(fitScale))

  // ── 轮次列标记 ──
  rounds.forEach((r, i) => {
    const x = xScale(i)
    // 竖线
    g.append('line')
      .attr('x1', x).attr('y1', pad.top - 10).attr('x2', x).attr('y2', canvasH - pad.bottom)
      .attr('stroke', '#ffffff08').attr('stroke-dasharray', '6 4')
    // 轮次标签（顶部 pill 样式）
    const labelG = g.append('g').attr('transform', `translate(${x}, ${pad.top - 35})`)
    labelG.append('rect').attr('x', -30).attr('y', -12).attr('width', 60).attr('height', 24)
      .attr('rx', 12).attr('fill', '#1a1a2e').attr('stroke', '#2a2a3e').attr('stroke-width', 1)
    labelG.append('text').attr('text-anchor', 'middle').attr('dy', 4)
      .attr('fill', '#8888aa').attr('font-size', 12).attr('font-weight', 600).text(`第 ${r} 轮`)
  })

  // ── 计算平行边偏移索引 ──
  const edgePairCount = {}
  const edgePairIdx = []
  edges.forEach(e => {
    const sId = typeof e.source === 'object' ? e.source.id : e.source
    const tId = typeof e.target === 'object' ? e.target.id : e.target
    const pairKey = [sId, tId].sort().join('|')
    if (!edgePairCount[pairKey]) edgePairCount[pairKey] = 0
    edgePairIdx.push({ key: pairKey, idx: edgePairCount[pairKey]++ })
  })
  edges.forEach((e, i) => {
    e._pairIdx = edgePairIdx[i].idx
    e._pairTotal = edgePairCount[edgePairIdx[i].key]
  })

  // ── 力模拟（加大间距）──
  if (sim) sim.stop()
  sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(n => n.id).distance(160).strength(0.1))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('y', d3.forceY(canvasH / 2).strength(0.03))
    .force('collide', d3.forceCollide().radius(55).strength(0.85))
    .alphaDecay(0.04)

  // ── 因果边（底层发光 + 上层实线）──
  const edgeG = g.append('g')
  // 发光底层
  const causalGlow = edgeG.selectAll('path.glow').data(edges).join('path')
    .attr('class', 'glow')
    .attr('fill', 'none')
    .attr('stroke', e => RELATION_COLORS[e.relation_type] || '#555')
    .attr('stroke-width', e => 3 + (e.strength || 0.5) * 4)
    .attr('stroke-opacity', 0.15)
    .attr('filter', 'url(#edge-glow)')
  // 主线
  const causalPath = edgeG.selectAll('path.main').data(edges).join('path')
    .attr('class', 'main')
    .attr('fill', 'none')
    .attr('stroke', e => RELATION_COLORS[e.relation_type] || '#555')
    .attr('stroke-width', e => 2 + (e.strength || 0.5) * 2.5)
    .attr('stroke-opacity', 0.85)
    .attr('stroke-linecap', 'round')
    .attr('marker-end', e => `url(#arrow-${e.relation_type || 'correlated'})`)

  // 边标签（带背景 pill）
  const edgeLabelG = g.append('g')
  const edgeLabelItems = edgeLabelG.selectAll('g').data(edges).join('g')
    .attr('pointer-events', 'none')
  edgeLabelItems.append('rect')
    .attr('rx', 7).attr('fill', '#0e0e1c').attr('stroke', e => RELATION_COLORS[e.relation_type] || '#555')
    .attr('stroke-width', 1).attr('stroke-opacity', 0.7)
  edgeLabelItems.append('text')
    .text(e => RELATION_LABELS[e.relation_type] || '')
    .attr('font-size', 11).attr('font-weight', 700)
    .attr('fill', e => RELATION_COLORS[e.relation_type] || '#888')
    .attr('text-anchor', 'middle').attr('dy', 4)

  // ── 事件节点 ──
  const nodeG = g.append('g')
  const R = 18 // 统一半径，severity 用不同效果体现
  const nodeItems = nodeG.selectAll('g').data(nodes).join('g')
    .attr('transform', n => `translate(${n.x},${n.y})`)
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(0.3).restart(); d.fy = d.y })
      .on('drag', (ev, d) => { d.fy = ev.y })
      .on('end', (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fy = null })
    )
  // 外圈光晕
  nodeItems.append('circle')
    .attr('r', R + 4)
    .attr('fill', n => EVENT_COLORS[n.event_type] || '#f43f5e')
    .attr('opacity', 0.15)
    .attr('filter', 'url(#glow)')
  // 主圆
  nodeItems.append('circle')
    .attr('r', R)
    .attr('fill', n => EVENT_COLORS[n.event_type] || '#f43f5e')
    .attr('stroke', '#0a0a14').attr('stroke-width', 2.5)
  // 严重度小标记（右上角小圆）
  nodeItems.filter(n => (n.severity || 0) > 0.5).append('circle')
    .attr('cx', 10).attr('cy', -10).attr('r', 4)
    .attr('fill', '#ff4444').attr('stroke', '#0a0a14').attr('stroke-width', 1.5)

  // ── 节点标签（类型 pill + 截断描述）──
  const labelOffset = R + 8
  // 类型标签 pill
  const labelItems = nodeG.selectAll('g.label-g').data(nodes).join('g')
    .attr('class', 'label-g').attr('pointer-events', 'none')
  // 背景 rect
  labelItems.append('rect')
    .attr('rx', 8).attr('fill', n => EVENT_COLORS[n.event_type] + '20')
    .attr('stroke', n => EVENT_COLORS[n.event_type] + '40').attr('stroke-width', 1)
  // 类型文字
  labelItems.append('text')
    .attr('class', 'node-type-text')
    .text(n => eventTypeLabel(n.event_type))
    .attr('font-size', 12).attr('font-weight', 700)
    .attr('fill', n => EVENT_COLORS[n.event_type] || '#fda4af')
    .attr('text-anchor', 'middle').attr('dy', 4)
  // 描述文字（第二行）
  labelItems.append('text')
    .attr('class', 'node-desc-text')
    .text(n => truncate(n.description, 14))
    .attr('font-size', 10).attr('fill', '#999')
    .attr('text-anchor', 'middle').attr('dy', 18)

  // 调整标签背景大小
  labelItems.each(function() {
    const grp = d3.select(this)
    const typeText = grp.select('.node-type-text').node()
    if (!typeText) return
    const bbox = typeText.getBBox()
    grp.select('rect')
      .attr('x', bbox.x - 6).attr('y', bbox.y - 4)
      .attr('width', bbox.width + 12).attr('height', bbox.height + 8)
  })

  // ── Hover ──
  nodeItems.on('mouseover', (event, d) => {
    tooltip.value = {
      show: true,
      x: event.pageX + 14, y: event.pageY - 14,
      label: `${eventTypeLabel(d.event_type)} · 第${d.round_num}轮`,
      meta: `严重度 ${(d.severity || 0).toFixed(2)}`,
      desc: d.description || ''
    }
    const connected = new Set([d.id])
    edges.forEach(e => {
      const sid = e.source?.id || e.source, tid = e.target?.id || e.target
      if (sid === d.id) connected.add(tid)
      if (tid === d.id) connected.add(sid)
    })
    nodeItems.attr('opacity', n => connected.has(n.id) ? 1 : 0.15)
    labelItems.attr('opacity', n => connected.has(n.id) ? 1 : 0.1)
    causalPath.attr('stroke-opacity', e => {
      const sid = e.source?.id || e.source, tid = e.target?.id || e.target
      return sid === d.id || tid === d.id ? 1 : 0.06
    })
    causalGlow.attr('stroke-opacity', e => {
      const sid = e.source?.id || e.source, tid = e.target?.id || e.target
      return sid === d.id || tid === d.id ? 0.3 : 0
    })
    edgeLabelItems.attr('opacity', e => {
      const sid = e.source?.id || e.source, tid = e.target?.id || e.target
      return sid === d.id || tid === d.id ? 1 : 0.05
    })
  })
  .on('mouseout', () => {
    tooltip.value.show = false
    nodeItems.attr('opacity', 1)
    labelItems.attr('opacity', 1)
    causalPath.attr('stroke-opacity', 0.85)
    causalGlow.attr('stroke-opacity', 0.15)
    edgeLabelItems.attr('opacity', 1)
  })
  .on('click', (_, d) => { selectedEvent.value = { ...d } })

  // ── 贝塞尔曲线生成（支持平行边偏移）──
  function edgePath(e) {
    const sx = e.source.x, sy = e.source.y, tx = e.target.x, ty = e.target.y
    if (isNaN(sx) || isNaN(sy) || isNaN(tx) || isNaN(ty)) return ''
    const dx = tx - sx, dy = ty - sy
    const dist = Math.sqrt(dx * dx + dy * dy) || 1
    // 法线方向
    const nx = -dy / dist, ny = dx / dist
    // 平行边偏移：多条边之间拉开
    const total = e._pairTotal || 1
    const idx = e._pairIdx || 0
    const spread = 30
    const baseOff = (idx - (total - 1) / 2) * spread
    // 曲线弯曲程度
    const sameCol = Math.abs((e.source.fx ?? sx) - (e.target.fx ?? tx)) < 10
    const curvature = sameCol ? 0.5 : 0.25
    const bendOff = dist * curvature + baseOff
    // 控制点
    const mx = (sx + tx) / 2 + nx * bendOff
    const my = (sy + ty) / 2 + ny * bendOff
    return `M${sx},${sy} Q${mx},${my} ${tx},${ty}`
  }

  // ── Tick ──
  sim.on('tick', () => {
    // 边曲线（发光层 + 主线层）
    causalGlow.attr('d', edgePath)
    causalPath.attr('d', edgePath)
    // 边标签
    edgeLabelItems.each(function(e) {
      const sx = e.source.x, sy = e.source.y, tx = e.target.x, ty = e.target.y
      const dx = tx - sx, dy = ty - sy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const nx = -dy / dist, ny = dx / dist
      const total = e._pairTotal || 1
      const idx = e._pairIdx || 0
      const spread = 30
      const baseOff = (idx - (total - 1) / 2) * spread
      const sameCol = Math.abs((e.source.fx ?? sx) - (e.target.fx ?? tx)) < 10
      const curvature = sameCol ? 0.5 : 0.25
      const bendOff = dist * curvature + baseOff
      // 标签放在曲线 t=0.5 的位置（即控制点与中点之间）
      const t = 0.5
      const lx = (1-t)*(1-t)*sx + 2*(1-t)*t*((sx+tx)/2 + nx*bendOff) + t*t*tx
      const ly = (1-t)*(1-t)*sy + 2*(1-t)*t*((sy+ty)/2 + ny*bendOff) + t*t*ty
      const grp = d3.select(this)
      grp.select('text').attr('x', lx).attr('y', ly)
      const bbox = grp.select('text').node().getBBox()
      grp.select('rect')
        .attr('x', bbox.x - 6).attr('y', bbox.y - 3)
        .attr('width', bbox.width + 12).attr('height', bbox.height + 6)
    })
    // 节点
    nodeItems.attr('transform', n => `translate(${n.x},${n.y})`)
    // 节点标签
    labelItems.each(function(n) {
      d3.select(this).attr('transform', `translate(${n.x},${n.y + labelOffset})`)
    })
  })
}

onMounted(() => { fetchGraph() })
onBeforeUnmount(() => { if (sim) sim.stop() })
</script>

<style scoped>
.causal-page {
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
.bg-orb { position: absolute; border-radius: 50%; filter: blur(140px); opacity: .12; }
.bg-orb-1 { width: 500px; height: 500px; background: #6366f1; top: -120px; left: -120px; }
.bg-orb-2 { width: 400px; height: 400px; background: #10b981; bottom: -100px; right: -100px; }

/* Top bar */
.top-bar {
  position: relative;
  display: flex; align-items: center; gap: 16px;
  padding: 12px 20px;
  background: rgba(10,10,20,0.85);
  border-bottom: 1px solid #1a1a2e;
  backdrop-filter: blur(10px);
  z-index: 2; flex-shrink: 0;
}
.back-btn {
  display: flex; align-items: center; gap: 6px;
  background: none; border: 1px solid #333; border-radius: 8px;
  color: #aaa; padding: 8px 16px; font-size: 15px; cursor: pointer;
  transition: all .15s;
}
.back-btn:hover { border-color: #6366f1; color: #c7d2fe; }
.page-title {
  display: flex; align-items: center; gap: 10px;
  font-size: 20px; font-weight: 700; margin: 0; color: #e8e8f0;
}
.page-title svg { opacity: .7; }
.stats-bar { margin-left: auto; display: flex; gap: 20px; font-size: 16px; color: #888; }
.stat strong { color: #c7d2fe; margin-right: 2px; }

/* Toolbar / Legend */
.toolbar {
  display: flex; align-items: center; gap: 28px; flex-wrap: wrap;
  padding: 10px 24px;
  background: rgba(10,10,20,0.5);
  border-bottom: 1px solid #1a1a2e;
  flex-shrink: 0; z-index: 2; position: relative;
}
.legend-section { display: flex; align-items: center; gap: 10px; }
.legend-title { font-size: 13px; color: #666; font-weight: 700; margin-right: 6px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 13px; color: #999; }
.dot { width: 12px; height: 12px; border-radius: 50%; }
.edge-sample { width: 28px; height: 4px; border-radius: 2px; box-shadow: 0 0 6px currentColor; }

/* Graph */
.graph-container { flex: 1; position: relative; overflow: hidden; }
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
  width: 340px; background: rgba(14,14,28,0.96);
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
.close-btn {
  background: none; border: none; color: #666; font-size: 22px;
  cursor: pointer; line-height: 1;
}
.close-btn:hover { color: #eee; }
.detail-name {
  font-size: 16px; font-weight: 600; margin: 0 0 16px; color: #f0f0f8;
}
.detail-fields { display: flex; flex-direction: column; gap: 10px; }
.field { display: flex; gap: 8px; align-items: baseline; }
.field.full { flex-direction: column; }
.field-key { font-size: 11px; color: #666; min-width: 50px; flex-shrink: 0; }
.field-val { font-size: 13px; color: #ccc; }
.field-val.content {
  margin: 4px 0 0; font-size: 12px; line-height: 1.5;
  color: #aaa; background: rgba(255,255,255,0.03);
  padding: 8px 10px; border-radius: 6px;
}

/* Related edges in detail panel */
.related-edges { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
.re-card {
  background: rgba(255,255,255,0.03);
  border-left: 3px solid #555;
  border-radius: 6px; padding: 8px 10px;
}
.re-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.re-rel { font-size: 12px; font-weight: 700; }
.re-strength { font-size: 11px; color: #888; }
.re-pair { font-size: 12px; color: #bbb; }
.re-evidence { font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }

/* Tooltip */
.graph-tooltip {
  position: fixed; padding: 10px 16px;
  background: #1a1a2e; border: 1px solid #333; border-radius: 10px;
  font-size: 12px; color: #ddd; pointer-events: none; z-index: 20;
  max-width: 320px;
}
.tt-label { font-weight: 600; font-size: 13px; }
.tt-meta { font-size: 11px; color: #999; margin-top: 2px; }
.tt-desc { font-size: 11px; color: #777; margin-top: 4px; line-height: 1.4; }

/* Transitions */
.slide-right-enter-active, .slide-right-leave-active {
  transition: transform .25s ease, opacity .25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  transform: translateX(100%); opacity: 0;
}
</style>
