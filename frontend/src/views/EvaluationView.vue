<template>
  <div class="eval-page">
    <!-- Background -->
    <div class="page-bg">
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
    </div>

    <!-- Top bar -->
    <nav class="top-bar">
      <button class="back-btn" @click="$router.back()">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        返回
      </button>
      <h1 class="page-title">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
          <line x1="6" y1="20" x2="6" y2="14"/>
        </svg>
        量化评估报告
      </h1>
      <div class="sim-id">{{ simulationId }}</div>
    </nav>

    <!-- Loading / Error -->
    <div v-if="loading" class="center-state">
      <div class="spinner"></div>
      <span>正在生成评估报告...</span>
    </div>
    <div v-else-if="error" class="center-state error-state">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchReport">重试</button>
    </div>

    <!-- Main content -->
    <div v-else-if="report" class="eval-content">

      <!-- KPI Cards -->
      <section class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-value">{{ report.total_rounds }}</div>
          <div class="kpi-label">模拟轮次</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ report.total_actions }}</div>
          <div class="kpi-label">总动作数</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">{{ report.total_agents }}</div>
          <div class="kpi-label">Agent 数</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-value">{{ (report.behavior_diversity.agent_activity_gini || 0).toFixed(2) }}</div>
          <div class="kpi-label">基尼系数</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-value">{{ ((report.behavior_diversity.unique_active_ratio || 0) * 100).toFixed(1) }}%</div>
          <div class="kpi-label">Agent 活跃率</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-value">{{ report.state_evolution.total_events || 0 }}</div>
          <div class="kpi-label">关键事件</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-value">{{ ((report.influence_analysis.information_concentration || 0) * 100).toFixed(1) }}%</div>
          <div class="kpi-label">信息集中度</div>
        </div>
      </section>

      <!-- Charts Grid -->
      <div class="charts-grid">

        <!-- Sentiment Chart -->
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            情感演化趋势
          </h2>
          <div ref="sentimentChart" class="chart-area"></div>
          <div class="chart-legend">
            <span class="legend-item"><span class="dot" style="background:#4ade80"></span>正面</span>
            <span class="legend-item"><span class="dot" style="background:#f87171"></span>负面</span>
            <span class="legend-item"><span class="dot" style="background:#94a3b8"></span>中性</span>
          </div>
        </section>

        <!-- Radar Chart -->
        <section class="chart-card">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5"/>
            </svg>
            最终世界状态
          </h2>
          <div ref="radarChart" class="chart-area"></div>
        </section>

        <!-- Pie Chart -->
        <section class="chart-card">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>
            </svg>
            动作类型分布
          </h2>
          <div ref="pieChart" class="chart-area"></div>
        </section>

        <!-- Influence Bar Chart -->
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            影响力排行 Top 10
          </h2>
          <div ref="barChart" class="chart-area tall"></div>
        </section>

        <!-- Turning Points -->
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            关键转折点
          </h2>
          <div class="events-list">
            <div v-for="(tp, i) in (report.state_evolution.turning_points || []).slice(0, 8)" :key="i" class="event-item">
              <div class="event-round">R{{ tp.round }}</div>
              <div class="event-bar" :style="{ width: (tp.severity * 100) + '%' }"></div>
              <div class="event-type">{{ eventTypeLabel(tp.event_type) }}</div>
              <div class="event-severity">{{ (tp.severity * 100).toFixed(0) }}%</div>
            </div>
          </div>
        </section>

      </div>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3'
import { getEvaluationReport } from '../api/evaluation'

export default {
  name: 'EvaluationView',
  props: {
    simulationId: { type: String, required: true }
  },
  data() {
    return {
      report: null,
      loading: true,
      error: null
    }
  },
  mounted() {
    this.fetchReport()
  },
  methods: {
    async fetchReport() {
      this.loading = true
      this.error = null
      try {
        const res = await getEvaluationReport(this.simulationId)
        this.report = res.data
        // 先关闭 loading，让 v-else-if="report" 的 DOM 渲染出来
        this.loading = false
        // 然后等 DOM 更新 + 浏览器布局完成后再绘图
        this.$nextTick(() => {
          requestAnimationFrame(() => {
            this.drawAllCharts()
          })
        })
      } catch (e) {
        this.error = e.message || '加载评估报告失败'
        this.loading = false
      }
    },

    drawAllCharts(retry = 0) {
      const el = this.$refs.sentimentChart
      // 如果容器还没有宽度，延迟重试（最多 5 次）
      if (el && el.clientWidth === 0 && retry < 5) {
        setTimeout(() => this.drawAllCharts(retry + 1), 80)
        return
      }
      this.drawSentimentChart()
      this.drawRadarChart()
      this.drawPieChart()
      this.drawBarChart()
    },

    // ==================== Sentiment Line Chart ====================
    drawSentimentChart() {
      const el = this.$refs.sentimentChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const timeline = this.report.sentiment_timeline || []
      if (!timeline.length) return

      const margin = { top: 20, right: 20, bottom: 35, left: 45 }
      const width = el.clientWidth - margin.left - margin.right
      const height = 220 - margin.top - margin.bottom

      const svg = d3.select(el).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g').attr('transform', `translate(${margin.left},${margin.top})`)

      const x = d3.scaleLinear()
        .domain(d3.extent(timeline, d => d.round_num))
        .range([0, width])

      const y = d3.scaleLinear().domain([0, 1]).range([height, 0])

      // Grid
      svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(''))
        .selectAll('line').attr('stroke', '#ffffff08')

      // Axes
      svg.append('g').attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(8).tickFormat(d => `R${d}`))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')

      svg.append('g')
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('.0%')))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')

      const series = [
        { key: 'positive', color: '#4ade80' },
        { key: 'negative', color: '#f87171' },
        { key: 'neutral', color: '#94a3b8' }
      ]

      series.forEach(s => {
        const line = d3.line()
          .x(d => x(d.round_num))
          .y(d => y(d[s.key]))
          .curve(d3.curveMonotoneX)

        // Area
        const area = d3.area()
          .x(d => x(d.round_num))
          .y0(height)
          .y1(d => y(d[s.key]))
          .curve(d3.curveMonotoneX)

        svg.append('path')
          .datum(timeline)
          .attr('d', area)
          .attr('fill', s.color)
          .attr('fill-opacity', 0.08)

        svg.append('path')
          .datum(timeline)
          .attr('fill', 'none')
          .attr('stroke', s.color)
          .attr('stroke-width', 2)
          .attr('d', line)
      })
    },

    // ==================== Radar Chart ====================
    drawRadarChart() {
      const el = this.$refs.radarChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const finalState = this.report.state_evolution?.final_state
      if (!finalState) return

      const dims = [
        { key: 'attention_level', label: '关注度' },
        { key: 'panic_level', label: '恐慌度' },
        { key: 'trust_level', label: '信任度' },
        { key: 'polarization_level', label: '极化度' },
        { key: 'risk_level', label: '风险' },
        { key: 'stability_level', label: '稳定性' }
      ]

      const size = Math.min(el.clientWidth, 260)
      const cx = size / 2, cy = size / 2, radius = size / 2 - 40

      const svg = d3.select(el).append('svg')
        .attr('width', size).attr('height', size)
        .append('g').attr('transform', `translate(${cx},${cy})`)

      const angleSlice = (2 * Math.PI) / dims.length

      // Grid circles
      const levels = 5
      for (let i = 1; i <= levels; i++) {
        const r = (radius / levels) * i
        svg.append('circle')
          .attr('r', r).attr('fill', 'none')
          .attr('stroke', '#ffffff10').attr('stroke-width', 1)
      }

      // Axes
      dims.forEach((d, i) => {
        const angle = angleSlice * i - Math.PI / 2
        const lx = Math.cos(angle) * radius
        const ly = Math.sin(angle) * radius

        svg.append('line')
          .attr('x1', 0).attr('y1', 0)
          .attr('x2', lx).attr('y2', ly)
          .attr('stroke', '#ffffff15')

        svg.append('text')
          .attr('x', Math.cos(angle) * (radius + 18))
          .attr('y', Math.sin(angle) * (radius + 18))
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('fill', '#999')
          .attr('font-size', '11px')
          .text(d.label)
      })

      // Data polygon
      const points = dims.map((d, i) => {
        const val = finalState[d.key] || 0
        const angle = angleSlice * i - Math.PI / 2
        return [Math.cos(angle) * radius * val, Math.sin(angle) * radius * val]
      })

      svg.append('polygon')
        .attr('points', points.map(p => p.join(',')).join(' '))
        .attr('fill', '#818cf8')
        .attr('fill-opacity', 0.25)
        .attr('stroke', '#818cf8')
        .attr('stroke-width', 2)

      // Data points
      points.forEach(p => {
        svg.append('circle')
          .attr('cx', p[0]).attr('cy', p[1]).attr('r', 3)
          .attr('fill', '#a5b4fc')
      })

      // Value labels
      dims.forEach((d, i) => {
        const val = finalState[d.key] || 0
        const angle = angleSlice * i - Math.PI / 2
        const lx = Math.cos(angle) * radius * val
        const ly = Math.sin(angle) * radius * val
        svg.append('text')
          .attr('x', lx).attr('y', ly - 10)
          .attr('text-anchor', 'middle')
          .attr('fill', '#c7d2fe')
          .attr('font-size', '10px')
          .text(val.toFixed(2))
      })
    },

    // ==================== Pie Chart ====================
    drawPieChart() {
      const el = this.$refs.pieChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const dist = this.report.behavior_diversity?.action_type_distribution
      if (!dist || !Object.keys(dist).length) return

      const data = Object.entries(dist).map(([k, v]) => ({ label: this.actionLabel(k), value: v }))
      const size = Math.min(el.clientWidth, 260)
      const radius = size / 2 - 30

      const svg = d3.select(el).append('svg')
        .attr('width', size).attr('height', size)
        .append('g').attr('transform', `translate(${size / 2},${size / 2})`)

      const colors = d3.scaleOrdinal()
        .domain(data.map(d => d.label))
        .range(['#818cf8', '#34d399', '#fbbf24', '#f87171', '#38bdf8', '#f472b6', '#a78bfa'])

      const pie = d3.pie().value(d => d.value).sort(null)
      const arc = d3.arc().innerRadius(radius * 0.5).outerRadius(radius)

      const arcs = svg.selectAll('.arc').data(pie(data)).enter().append('g')

      arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => colors(d.data.label))
        .attr('stroke', '#1a1a2e')
        .attr('stroke-width', 2)

      // Labels
      const labelArc = d3.arc().innerRadius(radius * 0.8).outerRadius(radius * 0.8)
      arcs.filter(d => d.data.value > 0.05).append('text')
        .attr('transform', d => `translate(${labelArc.centroid(d)})`)
        .attr('text-anchor', 'middle')
        .attr('fill', '#eee')
        .attr('font-size', '10px')
        .text(d => `${d.data.label} ${(d.data.value * 100).toFixed(0)}%`)
    },

    // ==================== Bar Chart ====================
    drawBarChart() {
      const el = this.$refs.barChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const agents = (this.report.influence_analysis?.top_agents || []).slice(0, 10)
      if (!agents.length) return

      const margin = { top: 10, right: 20, bottom: 5, left: 120 }
      const width = el.clientWidth - margin.left - margin.right
      const barH = 28
      const height = agents.length * barH

      const svg = d3.select(el).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g').attr('transform', `translate(${margin.left},${margin.top})`)

      const x = d3.scaleLinear()
        .domain([0, d3.max(agents, d => d.influence_score)])
        .range([0, width])

      const y = d3.scaleBand()
        .domain(agents.map(d => d.agent_name))
        .range([0, height])
        .padding(0.25)

      // Bars
      svg.selectAll('.bar').data(agents).enter()
        .append('rect')
        .attr('x', 0).attr('y', d => y(d.agent_name))
        .attr('width', d => x(d.influence_score))
        .attr('height', y.bandwidth())
        .attr('fill', '#818cf8')
        .attr('rx', 4)

      // Score labels
      svg.selectAll('.score').data(agents).enter()
        .append('text')
        .attr('x', d => x(d.influence_score) + 6)
        .attr('y', d => y(d.agent_name) + y.bandwidth() / 2)
        .attr('dominant-baseline', 'central')
        .attr('fill', '#a5b4fc')
        .attr('font-size', '11px')
        .text(d => d.influence_score)

      // Name labels
      svg.selectAll('.name').data(agents).enter()
        .append('text')
        .attr('x', -6)
        .attr('y', d => y(d.agent_name) + y.bandwidth() / 2)
        .attr('dominant-baseline', 'central')
        .attr('text-anchor', 'end')
        .attr('fill', '#ccc')
        .attr('font-size', '11px')
        .text(d => d.agent_name.length > 12 ? d.agent_name.slice(0, 12) + '...' : d.agent_name)
    },

    // ==================== Helpers ====================
    actionLabel(type) {
      const map = {
        'CREATE_POST': '发帖',
        'CREATE_COMMENT': '评论',
        'LIKE_POST': '点赞',
        'DISLIKE_POST': '踩',
        'REPOST': '转发',
        'DO_NOTHING': '无操作',
        'UPVOTE': '赞同',
        'DOWNVOTE': '反对',
        'FOLLOW_USER': '关注',
        'MUTE_USER': '屏蔽'
      }
      return map[type] || type
    },
    eventTypeLabel(type) {
      const map = {
        'heat_spike': '热度飙升',
        'sentiment_shift': '情绪转变',
        'trust_drop': '信任下降',
        'official_response': '官方回应',
        'polarization_surge': '极化加剧',
        'stabilization': '趋于稳定',
        'topic_outbreak': '话题爆发',
        'calm_restored': '恢复平静'
      }
      return map[type] || type
    }
  }
}
</script>

<style scoped>
/* ==================== Page Layout ==================== */
.eval-page {
  min-height: 100vh; background: #0f0f1a; color: #e0e0f0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  position: relative; overflow-x: hidden;
}
.page-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.bg-orb {
  position: absolute; border-radius: 50%; filter: blur(100px); opacity: 0.12;
}
.bg-orb-1 {
  width: 500px; height: 500px; background: #6366f1; top: -100px; right: -100px;
}
.bg-orb-2 {
  width: 400px; height: 400px; background: #06b6d4; bottom: -50px; left: -80px;
}

/* ==================== Top Bar ==================== */
.top-bar {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center; gap: 16px;
  padding: 14px 24px;
  background: rgba(15, 15, 26, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #ffffff10;
}
.back-btn {
  display: flex; align-items: center; gap: 4px;
  background: none; border: 1px solid #333; border-radius: 8px;
  color: #aaa; padding: 6px 12px; cursor: pointer; font-size: 13px;
}
.back-btn:hover { color: #fff; border-color: #555; }
.page-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; font-weight: 600; color: #f0f0f8; margin: 0;
}
.sim-id {
  font-size: 12px; color: #666; margin-left: auto;
  font-family: 'Courier New', monospace;
}

/* ==================== Loading / Error ==================== */
.center-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 16px; padding: 120px 0;
  color: #888; font-size: 14px; position: relative; z-index: 1;
}
.spinner {
  width: 32px; height: 32px; border: 3px solid #333;
  border-top-color: #818cf8; border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-state { color: #f87171; }
.retry-btn {
  background: #818cf830; border: 1px solid #818cf850; border-radius: 8px;
  color: #a5b4fc; padding: 8px 20px; cursor: pointer; font-size: 13px;
}
.retry-btn:hover { background: #818cf850; }

/* ==================== Content ==================== */
.eval-content {
  position: relative; z-index: 1;
  padding: 24px; max-width: 1200px; margin: 0 auto;
}

/* ==================== KPI Cards ==================== */
.kpi-row {
  display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;
}
.kpi-card {
  flex: 1; min-width: 110px;
  background: rgba(255,255,255,0.04);
  border: 1px solid #ffffff0a;
  border-radius: 12px; padding: 16px; text-align: center;
}
.kpi-card.accent {
  background: rgba(129, 140, 248, 0.06);
  border-color: rgba(129, 140, 248, 0.15);
}
.kpi-value {
  font-size: 24px; font-weight: 700; color: #f0f0f8;
  font-variant-numeric: tabular-nums;
}
.kpi-card.accent .kpi-value { color: #a5b4fc; }
.kpi-label {
  font-size: 11px; color: #666; margin-top: 4px; text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ==================== Charts Grid ==================== */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.chart-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid #ffffff08;
  border-radius: 14px; padding: 20px;
  overflow: hidden;
}
.chart-card.wide {
  grid-column: 1 / -1;
}
.chart-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: #ccc; margin: 0 0 16px;
}
.chart-area {
  width: 100%; min-height: 220px;
  display: flex; align-items: center; justify-content: center;
}
.chart-area.tall { min-height: 300px; }
.chart-legend {
  display: flex; gap: 16px; justify-content: center; margin-top: 8px;
}
.legend-item {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: #888;
}
.dot {
  width: 8px; height: 8px; border-radius: 50%;
}

/* ==================== Events List ==================== */
.events-list {
  display: flex; flex-direction: column; gap: 8px;
}
.event-item {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 0;
}
.event-round {
  font-size: 12px; color: #818cf8; font-weight: 600; min-width: 36px;
  font-family: 'Courier New', monospace;
}
.event-bar {
  height: 6px; border-radius: 3px;
  background: linear-gradient(90deg, #818cf8, #f472b6);
  min-width: 4px; max-width: 60%;
  transition: width 0.6s ease;
}
.event-type {
  font-size: 12px; color: #aaa; min-width: 70px;
}
.event-severity {
  font-size: 12px; color: #f0f0f8; font-weight: 600; margin-left: auto;
}

/* ==================== Responsive ==================== */
@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
  .kpi-row { gap: 8px; }
  .kpi-card { min-width: 80px; padding: 12px; }
  .kpi-value { font-size: 18px; }
}
</style>
