<template>
  <div class="eval-page">
    <!-- Background -->
    <div class="page-bg">
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
      <div class="bg-orb bg-orb-3"></div>
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
        模拟量化评估报告
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

      <!-- ========== Section 1: KPI Overview ========== -->
      <div class="section-header">
        <div class="section-num">01</div>
        <div class="section-text">
          <h2>模拟全局概览</h2>
          <p>Simulation Overview — 核心指标一览</p>
        </div>
      </div>
      <section class="kpi-row">
        <div class="kpi-card">
          <div class="kpi-icon">🔄</div>
          <div class="kpi-value">{{ report.total_rounds }}</div>
          <div class="kpi-label">模拟轮次</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon">⚡</div>
          <div class="kpi-value">{{ report.total_actions }}</div>
          <div class="kpi-label">总动作数</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-icon">👤</div>
          <div class="kpi-value">{{ report.total_agents }}</div>
          <div class="kpi-label">Agent 数</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-icon">📊</div>
          <div class="kpi-value">{{ (report.behavior_diversity.agent_activity_gini || 0).toFixed(2) }}</div>
          <div class="kpi-label">基尼系数</div>
          <div class="kpi-hint">{{ giniDescription }}</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-icon">🔥</div>
          <div class="kpi-value">{{ ((report.behavior_diversity.unique_active_ratio || 0) * 100).toFixed(1) }}%</div>
          <div class="kpi-label">Agent 活跃率</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-icon">📌</div>
          <div class="kpi-value">{{ report.state_evolution.total_events || 0 }}</div>
          <div class="kpi-label">关键事件</div>
        </div>
        <div class="kpi-card accent">
          <div class="kpi-icon">🎯</div>
          <div class="kpi-value">{{ ((report.influence_analysis.information_concentration || 0) * 100).toFixed(1) }}%</div>
          <div class="kpi-label">信息集中度</div>
          <div class="kpi-hint">{{ report.influence_analysis.concentration_description || '' }}</div>
        </div>
      </section>

      <!-- Sentiment Summary Mini-Cards -->
      <div v-if="report.sentiment_summary" class="sentiment-summary-row">
        <div class="ss-card positive">
          <span class="ss-dot"></span>
          <span class="ss-label">正面情感均值</span>
          <span class="ss-value">{{ ((report.sentiment_summary.average?.positive || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div class="ss-card negative">
          <span class="ss-dot"></span>
          <span class="ss-label">负面情感均值</span>
          <span class="ss-value">{{ ((report.sentiment_summary.average?.negative || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div class="ss-card neutral">
          <span class="ss-dot"></span>
          <span class="ss-label">中性情感均值</span>
          <span class="ss-value">{{ ((report.sentiment_summary.average?.neutral || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div class="ss-card peak">
          <span class="ss-label">负面峰值</span>
          <span class="ss-value">R{{ report.sentiment_summary.negative_peak?.round }} · {{ ((report.sentiment_summary.negative_peak?.value || 0) * 100).toFixed(1) }}%</span>
        </div>
        <div class="ss-card peak">
          <span class="ss-label">负面主导轮次占比</span>
          <span class="ss-value">{{ ((report.sentiment_summary.negative_dominant_ratio || 0) * 100).toFixed(0) }}%</span>
        </div>
      </div>

      <!-- ========== Section 2: World State Evolution ========== -->
      <div class="section-header">
        <div class="section-num">02</div>
        <div class="section-text">
          <h2>世界模型状态演化</h2>
          <p>World State Evolution — 六维状态动态追踪</p>
        </div>
      </div>

      <div class="charts-grid">
        <!-- World State 6-Dim Line Chart (NEW) -->
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            六维世界状态演化曲线
            <span class="chart-subtitle">注意力 · 恐慌 · 信任 · 极化 · 风险 · 稳定性</span>
          </h2>
          <div ref="worldStateChart" class="chart-area wide-chart"></div>
          <div class="chart-legend">
            <span class="legend-item"><span class="dot" style="background:#f59e0b"></span>关注度</span>
            <span class="legend-item"><span class="dot" style="background:#ef4444"></span>恐慌度</span>
            <span class="legend-item"><span class="dot" style="background:#3b82f6"></span>信任度</span>
            <span class="legend-item"><span class="dot" style="background:#a855f7"></span>极化度</span>
            <span class="legend-item"><span class="dot" style="background:#f97316"></span>风险</span>
            <span class="legend-item"><span class="dot" style="background:#22c55e"></span>稳定性</span>
          </div>
        </section>

        <!-- Radar: Initial vs Final (ENHANCED) -->
        <section class="chart-card">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5"/>
            </svg>
            世界状态对比
            <span class="chart-subtitle">初始 → 最终</span>
          </h2>
          <div ref="radarChart" class="chart-area"></div>
          <div class="chart-legend">
            <span class="legend-item"><span class="dot" style="background:#818cf8"></span>最终状态</span>
            <span class="legend-item"><span class="dot" style="background:#4ade80"></span>初始状态</span>
          </div>
        </section>

        <!-- Volatility Indicators -->
        <section class="chart-card">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            状态波动率
            <span class="chart-subtitle">标准差衡量变化剧烈程度</span>
          </h2>
          <div class="volatility-grid">
            <div v-for="(v, key) in (report.state_evolution.volatilities || {})" :key="key" class="vol-item">
              <div class="vol-bar-bg">
                <div class="vol-bar-fill" :style="{ width: Math.min(v * 500, 100) + '%', background: volColor(v) }"></div>
              </div>
              <div class="vol-label">{{ dimLabel(key) }}</div>
              <div class="vol-value" :style="{ color: volColor(v) }">{{ v.toFixed(4) }}</div>
            </div>
            <div class="vol-avg">
              平均波动率：<strong>{{ (report.state_evolution.avg_volatility || 0).toFixed(4) }}</strong>
            </div>
          </div>
        </section>
      </div>

      <!-- ========== Section 3: Feedback Loop ========== -->
      <div v-if="feedbackStats" class="section-header">
        <div class="section-num">03</div>
        <div class="section-text">
          <h2>世界模型反馈环</h2>
          <p>Feedback Loop — 状态偏移检测与干预统计</p>
        </div>
      </div>

      <div v-if="feedbackStats" class="charts-grid">
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            轮间状态偏移量
            <span class="chart-subtitle">每轮六维均差 — 超过阈值触发反馈注入</span>
          </h2>
          <div ref="feedbackChart" class="chart-area"></div>
          <div class="feedback-kpis">
            <div class="fbk"><span class="fbk-val">{{ feedbackStats.injection_rounds }}</span><span class="fbk-lbl">活跃偏移轮</span></div>
            <div class="fbk"><span class="fbk-val">{{ feedbackStats.avg_deviation?.toFixed(4) || '0' }}</span><span class="fbk-lbl">平均偏移量</span></div>
            <div class="fbk"><span class="fbk-val">R{{ feedbackStats.max_deviation_round }}</span><span class="fbk-lbl">最大偏移轮</span></div>
            <div class="fbk"><span class="fbk-val">{{ feedbackStats.max_deviation?.toFixed(4) || '0' }}</span><span class="fbk-lbl">最大偏移量</span></div>
          </div>
        </section>
      </div>

      <!-- ========== Section 4: Sentiment & Behavior ========== -->
      <div class="section-header">
        <div class="section-num">{{ feedbackStats ? '04' : '03' }}</div>
        <div class="section-text">
          <h2>情感演化与行为分析</h2>
          <p>Sentiment & Behavior — 群体情绪与动作模式</p>
        </div>
      </div>

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

        <!-- Platform Comparison (NEW) -->
        <section class="chart-card">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
            </svg>
            双平台行为对比
          </h2>
          <div v-if="platformBreakdown" class="platform-compare">
            <div v-for="(stats, pname) in platformBreakdown" :key="pname" class="pc-col">
              <div class="pc-name" :class="pname">{{ pname === 'twitter' ? 'Twitter' : 'Reddit' }}</div>
              <div class="pc-total">{{ stats.total }} 动作</div>
              <div class="pc-bars">
                <div class="pc-bar-row">
                  <span class="pc-bar-label">发帖</span>
                  <div class="pc-bar"><div class="pc-bar-fill post" :style="{ width: pctOf(stats.posts, stats.total) }"></div></div>
                  <span class="pc-bar-num">{{ stats.posts }}</span>
                </div>
                <div class="pc-bar-row">
                  <span class="pc-bar-label">评论</span>
                  <div class="pc-bar"><div class="pc-bar-fill comment" :style="{ width: pctOf(stats.comments, stats.total) }"></div></div>
                  <span class="pc-bar-num">{{ stats.comments }}</span>
                </div>
                <div class="pc-bar-row">
                  <span class="pc-bar-label">转发</span>
                  <div class="pc-bar"><div class="pc-bar-fill repost" :style="{ width: pctOf(stats.reposts, stats.total) }"></div></div>
                  <span class="pc-bar-num">{{ stats.reposts }}</span>
                </div>
                <div class="pc-bar-row">
                  <span class="pc-bar-label">互动</span>
                  <div class="pc-bar"><div class="pc-bar-fill like" :style="{ width: pctOf(stats.likes, stats.total) }"></div></div>
                  <span class="pc-bar-num">{{ stats.likes }}</span>
                </div>
                <div class="pc-bar-row">
                  <span class="pc-bar-label">搜索</span>
                  <div class="pc-bar"><div class="pc-bar-fill search" :style="{ width: pctOf(stats.searches, stats.total) }"></div></div>
                  <span class="pc-bar-num">{{ stats.searches }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="chart-empty">暂无平台数据</div>
        </section>
      </div>

      <!-- ========== Section 5: Influence & Causal ========== -->
      <div class="section-header">
        <div class="section-num">{{ feedbackStats ? '05' : '04' }}</div>
        <div class="section-text">
          <h2>影响力与因果分析</h2>
          <p>Influence & Causality — Agent 影响力排行与因果传播链</p>
        </div>
      </div>

      <div class="charts-grid">
        <!-- Influence Bar Chart (ENHANCED) -->
        <section class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            影响力排行 Top 10
            <span class="chart-subtitle">得分 = 发帖×3 + 转发×2 + 评论×1.5 + 互动×0.5</span>
          </h2>
          <div ref="barChart" class="chart-area tall"></div>
        </section>

        <!-- Causal Graph Stats (NEW) -->
        <section v-if="causalStats && causalStats.total_edges > 0" class="chart-card wide">
          <h2 class="chart-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
            </svg>
            因果图谱统计
            <span class="chart-subtitle">{{ causalStats.total_edges }} 条因果边</span>
          </h2>
          <div class="causal-grid">
            <div class="causal-col">
              <h3>因果关系类型</h3>
              <div v-for="(cnt, rel) in causalStats.edge_types" :key="rel" class="causal-row">
                <span class="cr-name">{{ rel }}</span>
                <span class="cr-count">{{ cnt }}</span>
              </div>
            </div>
            <div class="causal-col">
              <h3>主要驱动因素 (Top Causes)</h3>
              <div v-for="c in causalStats.top_causes" :key="c.name" class="causal-row">
                <span class="cr-name">{{ c.name }}</span>
                <span class="cr-count">{{ c.count }}</span>
              </div>
            </div>
            <div class="causal-col">
              <h3>主要受影响项 (Top Effects)</h3>
              <div v-for="e in causalStats.top_effects" :key="e.name" class="causal-row">
                <span class="cr-name">{{ e.name }}</span>
                <span class="cr-count">{{ e.count }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- ========== Section 6: Turning Points ========== -->
      <div class="section-header">
        <div class="section-num">{{ feedbackStats ? '06' : '05' }}</div>
        <div class="section-text">
          <h2>关键转折点</h2>
          <p>Turning Points — 由世界模型事件引擎检测的重大状态转变</p>
        </div>
      </div>

      <section class="chart-card wide" style="margin-bottom: 32px;">
        <div class="events-list">
          <div v-for="(tp, i) in (report.state_evolution.turning_points || []).slice(0, 10)" :key="i" class="event-item">
            <div class="event-rank">#{{ i + 1 }}</div>
            <div class="event-round">R{{ tp.round }}</div>
            <div class="event-bar-wrap">
              <div class="event-bar" :style="{ width: (tp.severity * 100) + '%' }"></div>
            </div>
            <div class="event-type">{{ eventTypeLabel(tp.event_type) }}</div>
            <div class="event-severity">{{ (tp.severity * 100).toFixed(0) }}%</div>
            <div v-if="tp.description" class="event-desc">{{ tp.description }}</div>
          </div>
        </div>
      </section>

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
  computed: {
    giniDescription() {
      const g = this.report?.behavior_diversity?.agent_activity_gini || 0
      if (g < 0.2) return '高度均匀'
      if (g < 0.4) return '较为均匀'
      if (g < 0.6) return '适度分化'
      return '高度分化'
    },
    feedbackStats() {
      return this.report?.state_evolution?.feedback_loop_stats || null
    },
    platformBreakdown() {
      return this.report?.state_evolution?.platform_breakdown || null
    },
    causalStats() {
      return this.report?.state_evolution?.causal_graph_stats || null
    }
  },
  mounted() {
    this.fetchReport()
  },
  methods: {
    pctOf(val, total) {
      if (!total) return '0%'
      return Math.round((val / total) * 100) + '%'
    },
    dimLabel(key) {
      const m = {
        attention_level: '关注度', panic_level: '恐慌度', trust_level: '信任度',
        polarization_level: '极化度', risk_level: '风险', stability_level: '稳定性'
      }
      return m[key] || key
    },
    volColor(v) {
      if (v < 0.02) return '#4ade80'
      if (v < 0.05) return '#fbbf24'
      return '#f87171'
    },

    async fetchReport() {
      this.loading = true
      this.error = null
      try {
        const res = await getEvaluationReport(this.simulationId)
        this.report = res.data
        this.loading = false
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
      if (el && el.clientWidth === 0 && retry < 5) {
        setTimeout(() => this.drawAllCharts(retry + 1), 80)
        return
      }
      this.drawWorldStateChart()
      this.drawSentimentChart()
      this.drawRadarChart()
      this.drawPieChart()
      this.drawBarChart()
      this.drawFeedbackChart()
    },

    // ==================== World State 6-Dim Line Chart ====================
    drawWorldStateChart() {
      const el = this.$refs.worldStateChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const timeline = this.report.state_evolution?.world_state_timeline || []
      if (!timeline.length) return

      const margin = { top: 20, right: 20, bottom: 35, left: 50 }
      const width = el.clientWidth - margin.left - margin.right
      const height = 260 - margin.top - margin.bottom

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

      svg.append('g').attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(Math.min(timeline.length, 12)).tickFormat(d => `R${d}`))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')

      svg.append('g')
        .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('.1f')))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')

      const dims = [
        { key: 'attention_level', color: '#f59e0b' },
        { key: 'panic_level', color: '#ef4444' },
        { key: 'trust_level', color: '#3b82f6' },
        { key: 'polarization_level', color: '#a855f7' },
        { key: 'risk_level', color: '#f97316' },
        { key: 'stability_level', color: '#22c55e' }
      ]

      dims.forEach(s => {
        const line = d3.line()
          .x(d => x(d.round_num))
          .y(d => y(d[s.key] || 0))
          .curve(d3.curveMonotoneX)

        svg.append('path')
          .datum(timeline)
          .attr('fill', 'none')
          .attr('stroke', s.color)
          .attr('stroke-width', 2)
          .attr('stroke-opacity', 0.85)
          .attr('d', line)

        // End dot
        const last = timeline[timeline.length - 1]
        svg.append('circle')
          .attr('cx', x(last.round_num))
          .attr('cy', y(last[s.key] || 0))
          .attr('r', 3.5)
          .attr('fill', s.color)
      })
    },

    // ==================== Feedback Loop Chart ====================
    drawFeedbackChart() {
      const el = this.$refs.feedbackChart
      if (!el || !this.feedbackStats) return
      el.innerHTML = ''

      const deltas = this.feedbackStats.round_deltas || []
      if (!deltas.length) return

      const margin = { top: 15, right: 20, bottom: 35, left: 50 }
      const width = el.clientWidth - margin.left - margin.right
      const height = 180 - margin.top - margin.bottom

      const svg = d3.select(el).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g').attr('transform', `translate(${margin.left},${margin.top})`)

      const x = d3.scaleBand()
        .domain(deltas.map(d => d.round_num))
        .range([0, width]).padding(0.2)

      const maxD = d3.max(deltas, d => d.delta) || 0.1
      const y = d3.scaleLinear().domain([0, maxD * 1.2]).range([height, 0])

      svg.append('g').attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).tickFormat(d => `R${d}`))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')
        .selectAll('text').attr('font-size', '9px')

      svg.append('g')
        .call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('.3f')))
        .selectAll('text,line,path').attr('stroke', '#555').attr('fill', '#555')

      // Threshold line at 0.03
      svg.append('line')
        .attr('x1', 0).attr('x2', width)
        .attr('y1', y(0.03)).attr('y2', y(0.03))
        .attr('stroke', '#f87171').attr('stroke-dasharray', '4,3')
        .attr('stroke-opacity', 0.6)

      svg.append('text')
        .attr('x', width - 4).attr('y', y(0.03) - 4)
        .attr('text-anchor', 'end').attr('fill', '#f87171').attr('font-size', '9px')
        .text('阈值 0.03')

      // Bars
      svg.selectAll('.bar').data(deltas).enter()
        .append('rect')
        .attr('x', d => x(d.round_num))
        .attr('y', d => y(d.delta))
        .attr('width', x.bandwidth())
        .attr('height', d => height - y(d.delta))
        .attr('fill', d => d.delta > 0.03 ? '#f87171' : '#818cf8')
        .attr('rx', 2)
        .attr('opacity', 0.8)
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

      svg.append('g').attr('class', 'grid')
        .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(''))
        .selectAll('line').attr('stroke', '#ffffff08')

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

    // ==================== Radar Chart (Initial + Final) ====================
    drawRadarChart() {
      const el = this.$refs.radarChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const finalState = this.report.state_evolution?.final_state
      const initialState = this.report.state_evolution?.initial_state
      if (!finalState) return

      const dims = [
        { key: 'attention_level', label: '关注度' },
        { key: 'panic_level', label: '恐慌度' },
        { key: 'trust_level', label: '信任度' },
        { key: 'polarization_level', label: '极化度' },
        { key: 'risk_level', label: '风险' },
        { key: 'stability_level', label: '稳定性' }
      ]

      const size = Math.min(el.clientWidth, 280)
      const cx = size / 2, cy = size / 2, radius = size / 2 - 45

      const svg = d3.select(el).append('svg')
        .attr('width', size).attr('height', size)
        .append('g').attr('transform', `translate(${cx},${cy})`)

      const angleSlice = (2 * Math.PI) / dims.length
      const levels = 5

      for (let i = 1; i <= levels; i++) {
        const r = (radius / levels) * i
        svg.append('circle')
          .attr('r', r).attr('fill', 'none')
          .attr('stroke', '#ffffff10').attr('stroke-width', 1)
      }

      dims.forEach((d, i) => {
        const angle = angleSlice * i - Math.PI / 2
        const lx = Math.cos(angle) * radius
        const ly = Math.sin(angle) * radius

        svg.append('line')
          .attr('x1', 0).attr('y1', 0)
          .attr('x2', lx).attr('y2', ly)
          .attr('stroke', '#ffffff15')

        svg.append('text')
          .attr('x', Math.cos(angle) * (radius + 22))
          .attr('y', Math.sin(angle) * (radius + 22))
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('fill', '#999')
          .attr('font-size', '11px')
          .text(d.label)
      })

      // Helper: draw polygon
      const drawPoly = (state, color, opacity) => {
        if (!state) return
        const points = dims.map((d, i) => {
          const val = state[d.key] || 0
          const angle = angleSlice * i - Math.PI / 2
          return [Math.cos(angle) * radius * val, Math.sin(angle) * radius * val]
        })
        svg.append('polygon')
          .attr('points', points.map(p => p.join(',')).join(' '))
          .attr('fill', color)
          .attr('fill-opacity', opacity)
          .attr('stroke', color)
          .attr('stroke-width', 1.5)
        points.forEach(p => {
          svg.append('circle')
            .attr('cx', p[0]).attr('cy', p[1]).attr('r', 2.5)
            .attr('fill', color)
        })
      }

      // Draw initial (green, faint) first, then final (purple, bold) on top
      drawPoly(initialState, '#4ade80', 0.12)
      drawPoly(finalState, '#818cf8', 0.25)

      // Value labels for final state
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
        .range(['#818cf8', '#34d399', '#fbbf24', '#f87171', '#38bdf8', '#f472b6', '#a78bfa', '#fb923c'])

      const pie = d3.pie().value(d => d.value).sort(null)
      const arc = d3.arc().innerRadius(radius * 0.5).outerRadius(radius)

      const arcs = svg.selectAll('.arc').data(pie(data)).enter().append('g')

      arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => colors(d.data.label))
        .attr('stroke', '#1a1a2e')
        .attr('stroke-width', 2)

      const labelArc = d3.arc().innerRadius(radius * 0.8).outerRadius(radius * 0.8)
      arcs.filter(d => d.data.value > 0.05).append('text')
        .attr('transform', d => `translate(${labelArc.centroid(d)})`)
        .attr('text-anchor', 'middle')
        .attr('fill', '#eee')
        .attr('font-size', '10px')
        .text(d => `${d.data.label} ${(d.data.value * 100).toFixed(0)}%`)
    },

    // ==================== Bar Chart (Enhanced) ====================
    drawBarChart() {
      const el = this.$refs.barChart
      if (!el || !this.report) return
      el.innerHTML = ''

      const agents = (this.report.influence_analysis?.top_agents || []).slice(0, 10)
      if (!agents.length) return

      const margin = { top: 10, right: 50, bottom: 5, left: 140 }
      const width = el.clientWidth - margin.left - margin.right
      const barH = 30
      const height = agents.length * barH

      const svg = d3.select(el).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g').attr('transform', `translate(${margin.left},${margin.top})`)

      const maxScore = d3.max(agents, d => d.influence_score)
      const x = d3.scaleLinear()
        .domain([0, maxScore])
        .range([0, width])

      const y = d3.scaleBand()
        .domain(agents.map(d => d.agent_name))
        .range([0, height])
        .padding(0.22)

      // Bars with gradient
      agents.forEach((agent, i) => {
        const barWidth = x(agent.influence_score)
        const yPos = y(agent.agent_name)

        svg.append('rect')
          .attr('x', 0).attr('y', yPos)
          .attr('width', barWidth)
          .attr('height', y.bandwidth())
          .attr('fill', i < 3 ? '#818cf8' : '#6366f180')
          .attr('rx', 4)

        // Score
        svg.append('text')
          .attr('x', barWidth + 6)
          .attr('y', yPos + y.bandwidth() / 2)
          .attr('dominant-baseline', 'central')
          .attr('fill', '#a5b4fc')
          .attr('font-size', '11px')
          .attr('font-weight', i < 3 ? '700' : '400')
          .text(agent.influence_score)

        // Name
        const displayName = agent.agent_name.length > 16
          ? agent.agent_name.slice(0, 16) + '...'
          : agent.agent_name
        svg.append('text')
          .attr('x', -6)
          .attr('y', yPos + y.bandwidth() / 2)
          .attr('dominant-baseline', 'central')
          .attr('text-anchor', 'end')
          .attr('fill', i < 3 ? '#e0e7ff' : '#aaa')
          .attr('font-size', '11px')
          .attr('font-weight', i < 3 ? '600' : '400')
          .text(displayName)
      })
    },

    // ==================== Helpers ====================
    actionLabel(type) {
      const map = {
        'CREATE_POST': '发帖', 'CREATE_COMMENT': '评论', 'LIKE_POST': '点赞',
        'LIKE_COMMENT': '点赞评论', 'DISLIKE_POST': '踩', 'REPOST': '转发',
        'DO_NOTHING': '无操作', 'UPVOTE_POST': '赞同', 'DOWNVOTE_POST': '反对',
        'FOLLOW': '关注', 'SEARCH_POSTS': '搜索', 'SEARCH_USER': '查人',
        'QUOTE_POST': '引用', 'TREND': '热搜', 'FOLLOW_USER': '关注',
        'MUTE_USER': '屏蔽', 'UPVOTE': '赞同', 'DOWNVOTE': '反对'
      }
      return map[type] || type
    },
    eventTypeLabel(type) {
      const map = {
        'heat_spike': '热度飙升', 'sentiment_shift': '情绪转变',
        'trust_drop': '信任下降', 'official_response': '官方回应',
        'polarization_surge': '极化加剧', 'stabilization': '趋于稳定',
        'topic_outbreak': '话题爆发', 'calm_restored': '恢复平静'
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
.bg-orb-1 { width: 500px; height: 500px; background: #6366f1; top: -100px; right: -100px; }
.bg-orb-2 { width: 400px; height: 400px; background: #06b6d4; bottom: -50px; left: -80px; }
.bg-orb-3 { width: 350px; height: 350px; background: #a855f7; top: 40%; left: 50%; }

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

/* ==================== Section Headers ==================== */
.section-header {
  display: flex; align-items: flex-start; gap: 16px;
  margin: 36px 0 18px;
}
.section-header:first-child { margin-top: 0; }
.section-num {
  font-size: 28px; font-weight: 800; color: #818cf830;
  font-family: 'Courier New', monospace; line-height: 1;
  min-width: 44px;
}
.section-text h2 {
  font-size: 18px; font-weight: 700; color: #e0e0f0; margin: 0;
}
.section-text p {
  font-size: 12px; color: #666; margin: 2px 0 0; letter-spacing: 0.3px;
}

/* ==================== KPI Cards ==================== */
.kpi-row {
  display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
}
.kpi-card {
  flex: 1; min-width: 110px;
  background: rgba(255,255,255,0.04);
  border: 1px solid #ffffff0a;
  border-radius: 12px; padding: 14px 12px; text-align: center;
  position: relative;
}
.kpi-card.accent {
  background: rgba(129, 140, 248, 0.06);
  border-color: rgba(129, 140, 248, 0.15);
}
.kpi-icon { font-size: 16px; margin-bottom: 4px; }
.kpi-value {
  font-size: 22px; font-weight: 700; color: #f0f0f8;
  font-variant-numeric: tabular-nums;
}
.kpi-card.accent .kpi-value { color: #a5b4fc; }
.kpi-label {
  font-size: 10px; color: #666; margin-top: 2px; text-transform: uppercase;
  letter-spacing: 0.5px;
}
.kpi-hint {
  font-size: 9px; color: #555; margin-top: 4px;
  line-height: 1.3; max-width: 140px; margin-left: auto; margin-right: auto;
}

/* ==================== Sentiment Summary Row ==================== */
.sentiment-summary-row {
  display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;
}
.ss-card {
  flex: 1; min-width: 140px;
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.03);
  border: 1px solid #ffffff08;
  border-radius: 10px; padding: 10px 14px;
}
.ss-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.ss-card.positive .ss-dot { background: #4ade80; }
.ss-card.negative .ss-dot { background: #f87171; }
.ss-card.neutral .ss-dot { background: #94a3b8; }
.ss-label { font-size: 11px; color: #888; }
.ss-value { font-size: 13px; font-weight: 600; color: #e0e0f0; margin-left: auto; white-space: nowrap; }

/* ==================== Charts Grid ==================== */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 8px;
}
.chart-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid #ffffff08;
  border-radius: 14px; padding: 20px;
  overflow: hidden;
}
.chart-card.wide { grid-column: 1 / -1; }
.chart-title {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 14px; font-weight: 600; color: #ccc; margin: 0 0 16px;
}
.chart-subtitle {
  font-size: 11px; font-weight: 400; color: #666; margin-left: 4px;
}
.chart-area {
  width: 100%; min-height: 220px;
  display: flex; align-items: center; justify-content: center;
}
.chart-area.wide-chart { min-height: 280px; }
.chart-area.tall { min-height: 300px; }
.chart-empty { color: #555; font-size: 13px; text-align: center; padding: 40px 0; }
.chart-legend {
  display: flex; gap: 14px; justify-content: center; margin-top: 8px; flex-wrap: wrap;
}
.legend-item {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #888;
}
.dot { width: 8px; height: 8px; border-radius: 50%; }

/* ==================== Volatility Grid ==================== */
.volatility-grid {
  display: flex; flex-direction: column; gap: 12px; padding: 8px 0;
}
.vol-item {
  display: grid; grid-template-columns: 1fr 72px 56px; align-items: center; gap: 10px;
}
.vol-bar-bg {
  height: 8px; border-radius: 4px; background: #ffffff08; overflow: hidden;
}
.vol-bar-fill {
  height: 100%; border-radius: 4px; transition: width 0.6s ease;
}
.vol-label { font-size: 12px; color: #aaa; text-align: right; }
.vol-value { font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.vol-avg {
  font-size: 12px; color: #888; text-align: center; padding-top: 8px;
  border-top: 1px solid #ffffff08;
}
.vol-avg strong { color: #e0e0f0; }

/* ==================== Feedback Loop ==================== */
.feedback-kpis {
  display: flex; gap: 16px; justify-content: center; margin-top: 12px; flex-wrap: wrap;
}
.fbk {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  min-width: 80px;
}
.fbk-val { font-size: 18px; font-weight: 700; color: #a5b4fc; font-variant-numeric: tabular-nums; }
.fbk-lbl { font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.3px; }

/* ==================== Platform Comparison ==================== */
.platform-compare {
  display: flex; gap: 20px; padding: 4px 0;
}
.pc-col { flex: 1; }
.pc-name {
  font-size: 14px; font-weight: 700; margin-bottom: 4px;
}
.pc-name.twitter { color: #38bdf8; }
.pc-name.reddit { color: #f97316; }
.pc-total { font-size: 11px; color: #888; margin-bottom: 10px; }
.pc-bars { display: flex; flex-direction: column; gap: 6px; }
.pc-bar-row {
  display: flex; align-items: center; gap: 8px;
}
.pc-bar-label { font-size: 11px; color: #888; min-width: 32px; text-align: right; }
.pc-bar {
  flex: 1; height: 8px; border-radius: 4px; background: #ffffff08; overflow: hidden;
}
.pc-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.pc-bar-fill.post { background: #818cf8; }
.pc-bar-fill.comment { background: #34d399; }
.pc-bar-fill.repost { background: #fbbf24; }
.pc-bar-fill.like { background: #f472b6; }
.pc-bar-fill.search { background: #38bdf8; }
.pc-bar-num { font-size: 11px; color: #aaa; min-width: 28px; font-variant-numeric: tabular-nums; }

/* ==================== Causal Grid ==================== */
.causal-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
}
.causal-col h3 {
  font-size: 12px; font-weight: 600; color: #999; margin: 0 0 10px;
  text-transform: uppercase; letter-spacing: 0.3px;
}
.causal-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 0; border-bottom: 1px solid #ffffff06;
}
.cr-name { font-size: 12px; color: #ccc; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cr-count { font-size: 12px; font-weight: 600; color: #a5b4fc; font-variant-numeric: tabular-nums; }

/* ==================== Events List ==================== */
.events-list {
  display: flex; flex-direction: column; gap: 4px;
}
.event-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255,255,255,0.02);
  flex-wrap: wrap;
}
.event-item:hover { background: rgba(255,255,255,0.04); }
.event-rank {
  font-size: 11px; color: #555; font-weight: 700; min-width: 24px;
  font-family: 'Courier New', monospace;
}
.event-round {
  font-size: 13px; color: #818cf8; font-weight: 700; min-width: 36px;
  font-family: 'Courier New', monospace;
}
.event-bar-wrap {
  flex: 1; max-width: 200px; height: 6px; border-radius: 3px;
  background: #ffffff08; overflow: hidden;
}
.event-bar {
  height: 100%; border-radius: 3px;
  background: linear-gradient(90deg, #818cf8, #f472b6);
  transition: width 0.6s ease;
}
.event-type { font-size: 12px; color: #aaa; min-width: 70px; }
.event-severity { font-size: 13px; color: #f0f0f8; font-weight: 700; }
.event-desc {
  width: 100%; font-size: 11px; color: #666; margin-top: 2px;
  padding-left: 34px; line-height: 1.4;
}

/* ==================== Responsive ==================== */
@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
  .kpi-row { gap: 8px; }
  .kpi-card { min-width: 80px; padding: 12px; }
  .kpi-value { font-size: 18px; }
  .causal-grid { grid-template-columns: 1fr; }
  .platform-compare { flex-direction: column; }
  .sentiment-summary-row { flex-direction: column; }
  .section-num { font-size: 22px; }
}
</style>
