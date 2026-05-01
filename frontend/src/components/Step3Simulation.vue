<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <!-- 综合进度面板 -->
        <div class="progress-panel" :class="{ active: phase === 1, completed: phase === 2 }">
          <!-- 双平台进度条 -->
          <div class="dual-progress">
            <div class="progress-row">
              <span class="progress-label">
                <svg class="platform-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                </svg>
                信息广场
              </span>
              <div class="progress-track">
                <div class="progress-fill twitter" :style="{ width: twitterProgress + '%' }"></div>
              </div>
              <span class="progress-text mono">{{ runStatus.twitter_current_round || 0 }}<span class="progress-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
              <span v-if="runStatus.twitter_completed" class="check-icon">✓</span>
            </div>
            <div class="progress-row">
              <span class="progress-label">
                <svg class="platform-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                </svg>
                话题社区
              </span>
              <div class="progress-track">
                <div class="progress-fill reddit" :style="{ width: redditProgress + '%' }"></div>
              </div>
              <span class="progress-text mono">{{ runStatus.reddit_current_round || 0 }}<span class="progress-total">/{{ runStatus.total_rounds || maxRounds || '-' }}</span></span>
              <span v-if="runStatus.reddit_completed" class="check-icon">✓</span>
            </div>
          </div>
          <!-- ETA -->
          <div class="eta-badge" v-if="phase === 1 && etaText">
            <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {{ etaText }}
          </div>
          <div class="eta-badge done" v-else-if="phase === 2">
            <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            推演完成
          </div>
        </div>

        <!-- 世界状态迷你指标 -->
        <div class="ws-mini" v-if="worldState">
          <div class="ws-indicator" title="关注度">
            <span class="ws-dot" :style="{ background: wsColor(worldState.attention) }"></span>
            <span class="ws-name">关注</span>
            <span class="ws-val mono">{{ wsFormat(worldState.attention) }}</span>
          </div>
          <div class="ws-indicator" title="恐慌度">
            <span class="ws-dot" :style="{ background: wsColor(worldState.panic) }"></span>
            <span class="ws-name">恐慌</span>
            <span class="ws-val mono">{{ wsFormat(worldState.panic) }}</span>
          </div>
          <div class="ws-indicator" title="信任度">
            <span class="ws-dot" :style="{ background: wsColorInverse(worldState.trust) }"></span>
            <span class="ws-name">信任</span>
            <span class="ws-val mono">{{ wsFormat(worldState.trust) }}</span>
          </div>
          <div class="ws-indicator" title="极化度">
            <span class="ws-dot" :style="{ background: wsColor(worldState.polarization) }"></span>
            <span class="ws-name">极化</span>
            <span class="ws-val mono">{{ wsFormat(worldState.polarization) }}</span>
          </div>
        </div>
      </div>

      <div class="action-controls">
        <!-- 返回群体环境建模：任意 phase 都允许返回 Step 2 -->
        <button
          class="action-btn secondary"
          :disabled="phase === 1 && isStopping"
          @click="$emit('go-back')"
          title="返回群体环境建模（Step 2）"
        >
          ← 返回群体环境建模
        </button>
        <!-- 启动 / 重新启动：仅在 phase=0 且非 starting 时可见 -->
        <button
          v-if="phase === 0"
          class="action-btn secondary"
          :disabled="isStarting || !props.simulationId"
          @click="doStartSimulation"
        >
          <span v-if="isStarting" class="loading-spinner-small"></span>
          {{ isStarting ? '启动中…' : (runStatus.runner_status ? '重新启动' : '启动模拟') }}
        </button>
        <!-- 停止：仅在运行中可见 -->
        <button
          v-if="phase === 1"
          class="action-btn secondary"
          :disabled="isStopping"
          @click="handleStopSimulation"
        >
          <span v-if="isStopping" class="loading-spinner-small"></span>
          {{ isStopping ? '停止中…' : '停止模拟' }}
        </button>
        <!-- 重新模拟：在运行中或已完成时可见 -->
        <button
          v-if="phase === 1 || phase === 2"
          class="action-btn secondary"
          :disabled="isStarting || isStopping"
          @click="doRestartSimulation"
        >
          <span v-if="isStarting" class="loading-spinner-small"></span>
          {{ isStarting ? '重启中…' : '重新模拟' }}
        </button>
        <button
          v-if="phase === 2"
          class="action-btn secondary"
          @click="scrollToSimGraph"
        >
          查看事件故事线
        </button>
        <button
          class="action-btn primary"
          :disabled="phase !== 2 || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="loading-spinner-small"></span>
          {{ isGeneratingReport ? '启动中...' : '开始生成结果报告' }} 
          <span v-if="!isGeneratingReport" class="arrow-icon">→</span>
        </button>
      </div>
    </div>

    <!-- 进入 Step3 时的选择对话框：旧数据 vs 新设定 -->
    <div v-if="showRunChoice" class="run-choice-overlay">
      <div class="run-choice-card">
        <div class="run-choice-header">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>检测到已有模拟数据</span>
        </div>
        <div class="run-choice-body">
          <p class="run-choice-info">
            已有数据：<strong>{{ oldRunRounds }} 轮</strong>，
            本次设定：<strong>{{ props.maxRounds }} 轮</strong>
          </p>
          <!-- 旧轮次 >= 新设定：已有数据足够，是否重新跑 -->
          <template v-if="oldRunRounds >= props.maxRounds">
            <p class="run-choice-hint">已有数据已达到或超过本次设定轮数。</p>
            <div class="run-choice-actions">
              <button class="choice-btn primary" @click="handleChoiceRestart">重新运行 ({{ props.maxRounds }} 轮)</button>
              <button class="choice-btn secondary" @click="handleChoiceKeepOld">查看已有数据 ({{ oldRunRounds }} 轮)</button>
            </div>
          </template>
          <!-- 旧轮次 < 新设定：数据不足，可以续跑 -->
          <template v-else>
            <p class="run-choice-hint">已有数据少于本次设定轮数。</p>
            <div class="run-choice-actions">
              <button class="choice-btn primary" @click="handleChoiceResume">续跑到 {{ props.maxRounds }} 轮</button>
              <button class="choice-btn secondary" @click="handleChoiceRestart">重新运行 ({{ props.maxRounds }} 轮)</button>
              <button class="choice-btn secondary" @click="handleChoiceKeepOld">查看已有数据 ({{ oldRunRounds }} 轮)</button>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Narrative main content (World Model 为叙事主角) -->
    <div class="narrative-content" ref="scrollContainer">

      <!-- Section 1 — Hero: Summary + 6 Radial Indicators -->
      <WorldStateHero
        :current-state="worldState"
        :state-summary="worldStateSummary"
      />

      <!-- Section 2 — Causal Chain -->
      <CausalGraphView
        :causal-graph="causalGraph"
        :events="worldEvents"
      />

      <!-- Section 3 — Event Timeline + Inject -->
      <EventTimeline
        :events="worldEvents"
        :simulation-id="simulationId"
      />

      <!-- Section 4 — Dual Platform Simulation Display -->
      <div class="actions-section">
        <div class="actions-head">
          <h3 class="section-title">🌐 双平台模拟推演</h3>
          <div class="actions-head-right">
            <label class="idle-toggle">
              <input type="checkbox" v-model="hideIdleActions" />
              <span>隐藏静默</span>
            </label>
            <div class="actions-stat" v-if="allActions.length > 0">
              共计 <span class="mono">{{ allActions.length }}</span> 条<span v-if="hideIdleActions && (twitterIdleHidden + redditIdleHidden) > 0" class="idle-hint">（隐藏 {{ twitterIdleHidden + redditIdleHidden }} 条静默）</span>
            </div>
          </div>
        </div>

        <div class="dual-columns">
          <!-- Twitter / Info Plaza -->
          <div class="col-panel twitter-col">
            <div class="col-head twitter-head">
              <div class="col-brand">
                <div class="brand-icon twitter-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                </div>
                <div class="brand-text">
                  <span class="col-name">Twitter</span>
                  <span class="col-subtitle">微博型平台 · 信息广场</span>
                </div>
              </div>
              <div class="col-stats">
                <span class="col-stat-num mono">{{ twitterActionsCount }}</span>
                <span class="col-stat-label">条动态</span>
              </div>
            </div>
            <div class="col-body twitter-feed">
              <TransitionGroup name="timeline-item">
                <template v-for="item in twitterFeedItems" :key="item._key || item._uniqueId || item.id || `${item.timestamp}-${item.agent_id}`">
                  <div v-if="item._isSeparator" class="round-sep">
                    <span class="round-sep-line"></span>
                    <span class="round-sep-label">Round {{ item.round_num }}</span>
                    <span class="round-sep-line"></span>
                  </div>
                  <AgentActionCard v-else :action="item" />
                </template>
              </TransitionGroup>
              <div v-if="twitterActions.length === 0" class="col-empty">
                <div class="empty-icon">📡</div>
                <span>等待 Twitter 平台智能体活动…</span>
              </div>
            </div>
          </div>

          <!-- Reddit / Topic Community -->
          <div class="col-panel reddit-col">
            <div class="col-head reddit-head">
              <div class="col-brand">
                <div class="brand-icon reddit-icon">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 01-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 01.042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 014.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 01.14-.197.35.35 0 01.238-.042l2.906.617a1.214 1.214 0 011.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 00-.231.094.33.33 0 000 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 000-.463.327.327 0 00-.462 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 00-.205-.094z"/></svg>
                </div>
                <div class="brand-text">
                  <span class="col-name">Reddit</span>
                  <span class="col-subtitle">论坛型平台 · 话题社区</span>
                </div>
              </div>
              <div class="col-stats">
                <span class="col-stat-num mono">{{ redditActionsCount }}</span>
                <span class="col-stat-label">条动态</span>
              </div>
            </div>
            <div class="col-body reddit-feed">
              <TransitionGroup name="timeline-item">
                <template v-for="item in redditFeedItems" :key="item._key || item._uniqueId || item.id || `${item.timestamp}-${item.agent_id}`">
                  <div v-if="item._isSeparator" class="round-sep reddit-sep">
                    <span class="round-sep-line"></span>
                    <span class="round-sep-label">Round {{ item.round_num }}</span>
                    <span class="round-sep-line"></span>
                  </div>
                  <!-- 折叠的轻量操作组 -->
                  <div v-else-if="item._isGroup" class="action-group">
                    <div class="ag-header" @click="toggleGroup(item._key)">
                      <span class="ag-count">{{ item.count }} 条互动</span>
                      <span class="ag-pills">{{ formatGroupSummary(item.typeCounts) }}</span>
                      <span class="ag-toggle">{{ expandedGroups.has(item._key) ? '▴ 收起' : '▾ 展开' }}</span>
                    </div>
                    <div v-if="expandedGroups.has(item._key)" class="ag-body">
                      <AgentActionCard
                        v-for="a in item.items"
                        :key="a._uniqueId || a.id || `${a.timestamp}-${a.agent_id}`"
                        :action="a"
                      />
                    </div>
                  </div>
                  <AgentActionCard v-else :action="item" />
                </template>
              </TransitionGroup>
              <div v-if="redditActions.length === 0" class="col-empty">
                <div class="empty-icon">💬</div>
                <span>等待 Reddit 平台智能体活动…</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="allActions.length === 0" class="waiting-state">
          <div class="pulse-ring"></div>
          <span>等待智能体行为…</span>
        </div>
      </div>
    </div><!-- /.narrative-content -->

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">模拟监视器</span>
        <span class="log-id">{{ simulationId || '无模拟' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { 
  startSimulation, 
  stopSimulation,
  getRunStatus, 
  getRunStatusDetail,
  getWorldState,
  getWorldEvents,
  getCausalGraph
} from '../api/simulation'
import { generateReport } from '../api/report'
import WorldStateHero from './WorldState/WorldStateHero.vue'
import CausalGraphView from './WorldState/CausalGraphView.vue'
import EventTimeline from './WorldState/EventTimeline.vue'
import AgentActionCard from './WorldState/AgentActionCard.vue'

const props = defineProps({
  simulationId: String,
  maxRounds: Number, // 从Step2传入的最大轮数
  freshStart: Boolean, // Step2 点"开始推演"时为 true，跳过旧数据恢复直接启动新模拟
  minutesPerRound: {
    type: Number,
    default: 60 // 默认每轮60分钟（与后端 simulation_config_generator 一致）
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status', 'fresh-start-consumed'])
const vueRouter = useRouter()

// State
const isGeneratingReport = ref(false)
const phase = ref(0) // 0: 未开始, 1: 运行中, 2: 已完成
const isStarting = ref(false)
const isStopping = ref(false)
const startError = ref(null)
const showRunChoice = ref(false) // 显示“重新运行 / 查看已有数据”选择对话框
const oldRunRounds = ref(0)       // 旧模拟已跑轮次
const runStatus = ref({})
const allActions = ref([]) // 所有动作（增量累积）
const actionIds = ref(new Set()) // 用于去重的动作ID集合
const scrollContainer = ref(null)
// World State Data
const worldState = ref(null)
const worldStateHistory = ref([])
const worldStateSummary = ref('')
const worldEvents = ref([])
const causalGraph = ref({})

// Computed
// 按时间顺序显示动作（最新的在最后面，即底部）
const chronologicalActions = computed(() => {
  return allActions.value
})

// 各平台动作列表（供叙事流双栏使用）
// 默认隐藏静默动作（DO_NOTHING）——LLM 偶断时 OASIS 常量回补，视觉上太吵
const hideIdleActions = ref(true)

const _isIdle = (a) => a.action_type === 'DO_NOTHING'

const twitterActionsAll = computed(() =>
  allActions.value.filter(a => a.platform === 'twitter')
)
const redditActionsAll = computed(() =>
  allActions.value.filter(a => a.platform === 'reddit')
)
const twitterActions = computed(() =>
  hideIdleActions.value ? twitterActionsAll.value.filter(a => !_isIdle(a)) : twitterActionsAll.value
)
const redditActions = computed(() =>
  hideIdleActions.value ? redditActionsAll.value.filter(a => !_isIdle(a)) : redditActionsAll.value
)

// 轻量操作类型集合（可折叠分组）
const _LIGHTWEIGHT = new Set([
  'LIKE_POST', 'LIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
  'FOLLOW', 'UPVOTE_POST', 'DOWNVOTE_POST', 'DISLIKE_POST',
  'TREND', 'DO_NOTHING'
])

// Twitter: 简单插入轮次分隔符
function _interleaveSimple(actions) {
  const result = []
  let lastRound = null
  for (const a of actions) {
    const rn = a.round_num
    if (rn !== lastRound) {
      result.push({ _isSeparator: true, _key: `sep-${rn}`, round_num: rn })
      lastRound = rn
    }
    result.push(a)
  }
  return result
}

// Reddit: 连续 3+ 轻量操作折叠成组
const _GROUP_ICONS = {
  LIKE_POST: '♥', LIKE_COMMENT: '♥',
  UPVOTE_POST: '▲', DOWNVOTE_POST: '▼', DISLIKE_POST: '👎',
  SEARCH_POSTS: '🔍', SEARCH_USER: '🔍',
  FOLLOW: '➕', TREND: '📈', DO_NOTHING: '💤'
}
const _GROUP_LABELS = {
  LIKE_POST: '赞', LIKE_COMMENT: '赞',
  UPVOTE_POST: '赞同', DOWNVOTE_POST: '反对', DISLIKE_POST: '踩',
  SEARCH_POSTS: '搜索', SEARCH_USER: '查人',
  FOLLOW: '关注', TREND: '热搜', DO_NOTHING: '静默'
}

function _interleaveWithGroups(actions) {
  const result = []
  let lastRound = null
  let i = 0
  while (i < actions.length) {
    const a = actions[i]
    const rn = a.round_num
    if (rn !== lastRound) {
      result.push({ _isSeparator: true, _key: `sep-${rn}`, round_num: rn })
      lastRound = rn
    }
    if (_LIGHTWEIGHT.has(a.action_type)) {
      let j = i + 1
      while (j < actions.length && actions[j].round_num === rn && _LIGHTWEIGHT.has(actions[j].action_type)) j++
      const count = j - i
      if (count >= 3) {
        const items = actions.slice(i, j)
        const typeCounts = {}
        items.forEach(it => { typeCounts[it.action_type] = (typeCounts[it.action_type] || 0) + 1 })
        result.push({ _isGroup: true, _key: `grp-${rn}-${i}`, round_num: rn, items, count, typeCounts })
        i = j
        continue
      }
    }
    result.push(a)
    i++
  }
  return result
}

const expandedGroups = ref(new Set())
const toggleGroup = (key) => {
  const s = new Set(expandedGroups.value)
  s.has(key) ? s.delete(key) : s.add(key)
  expandedGroups.value = s
}
const formatGroupSummary = (typeCounts) => {
  return Object.entries(typeCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([t, n]) => `${_GROUP_ICONS[t] || '•'}${n}`)
    .join('  ')
}

const twitterFeedItems = computed(() => _interleaveSimple(twitterActions.value))
const redditFeedItems = computed(() => _interleaveWithGroups(redditActions.value))

// 各平台动作计数（显示后的）
const twitterActionsCount = computed(() => twitterActions.value.length)
const redditActionsCount = computed(() => redditActions.value.length)
// 隐藏的静默数量
const twitterIdleHidden = computed(() => twitterActionsAll.value.length - twitterActions.value.length)
const redditIdleHidden = computed(() => redditActionsAll.value.length - redditActions.value.length)

// 进度百分比
const totalRounds = computed(() => runStatus.value.total_rounds || props.maxRounds || 1)
const twitterProgress = computed(() => {
  const r = runStatus.value.twitter_current_round || 0
  return Math.min(100, Math.round(r / totalRounds.value * 100))
})
const redditProgress = computed(() => {
  const r = runStatus.value.reddit_current_round || 0
  return Math.min(100, Math.round(r / totalRounds.value * 100))
})

// ETA 计算（基于实际墙钟时间）
const simulationStartTime = ref(null)
const etaText = computed(() => {
  if (!simulationStartTime.value) return ''
  const maxR = Math.max(runStatus.value.twitter_current_round || 0, runStatus.value.reddit_current_round || 0)
  if (maxR <= 0) return '计算中...'
  const elapsed = (Date.now() - simulationStartTime.value) / 1000
  const perRound = elapsed / maxR
  const remaining = Math.max(0, (totalRounds.value - maxR) * perRound)
  if (remaining < 60) return `预计 ${Math.ceil(remaining)}秒`
  if (remaining < 3600) return `预计 ${Math.ceil(remaining / 60)}分钟`
  return `预计 ${(remaining / 3600).toFixed(1)}小时`
})

// 世界状态迷你指标格式化
const wsFormat = (v) => v != null ? v.toFixed(2) : '--'
const wsColor = (v) => {
  if (v == null) return '#94a3b8'
  if (v < 0.3) return '#22c55e'
  if (v < 0.6) return '#f59e0b'
  return '#ef4444'
}
const wsColorInverse = (v) => {
  if (v == null) return '#94a3b8'
  if (v > 0.6) return '#22c55e'
  if (v > 0.3) return '#f59e0b'
  return '#ef4444'
}

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

// 重置所有状态（用于重新启动模拟）
const resetAllState = () => {
  phase.value = 0
  runStatus.value = {}
  allActions.value = []
  actionIds.value = new Set()
  prevTwitterRound.value = 0
  prevRedditRound.value = 0
  startError.value = null
  isStarting.value = false
  isStopping.value = false
  worldState.value = null
  worldStateHistory.value = []
  worldStateSummary.value = ''
  worldEvents.value = []
  causalGraph.value = {}
  _lastCausalFetchAt.value = 0
  stopPolling()  // 停止之前可能存在的轮询
}

// 启动模拟
const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog('错误：缺少 simulationId')
    return
  }
  
  // 先重置所有状态，确保不会受到上一次模拟的影响
  resetAllState()
  
  isStarting.value = true
  startError.value = null
  addLog('正在启动双平台并行模拟...')
  emit('update-status', 'processing')
  
  try {
    const params = {
      simulation_id: props.simulationId,
      platform: 'parallel',
      force: true,  // 强制重新开始
      enable_graph_memory_update: false,  // 模拟期间关闭实时更新（节省内存）
      post_sim_graph_import: true           // 模拟结束后批量导入图谱
    }
    
    if (props.maxRounds) {
      params.max_rounds = props.maxRounds
      addLog(`设置最大模拟轮数: ${props.maxRounds}`)
    }
    
    addLog('图谱更新将在模拟结束后批量执行')
    
    const res = await startSimulation(params)
    
    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog('✓ 已清理旧的模拟日志，重新启动推演')
      }
      addLog('✓ 模拟引擎启动成功')
      addLog(`  ├─ PID: ${res.data.process_pid || '-'}`)
      
      phase.value = 1
      simulationStartTime.value = Date.now()
      runStatus.value = res.data
      
      startStatusPolling()
      startDetailPolling()
    } else {
      startError.value = res.error || '启动失败'
      addLog(`✗ 启动失败: ${res.error || '未知错误'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    startError.value = err.message
    addLog(`✗ 启动异常: ${err.message}`)
    emit('update-status', 'error')
  } finally {
    isStarting.value = false
  }
}

// 续跑模拟：从已有轮次继续跑到目标轮数
const doResumeSimulation = async () => {
  if (!props.simulationId) {
    addLog('错误：缺少 simulationId')
    return
  }
  
  isStarting.value = true
  startError.value = null
  addLog(`正在续跑模拟（从第 ${oldRunRounds.value + 1} 轮开始）...`)
  emit('update-status', 'processing')
  
  try {
    const params = {
      simulation_id: props.simulationId,
      platform: 'parallel',
      force: true,   // 需要 force 绕过状态检查
      resume: true,  // 续跑模式：不清理日志，从断点继续
      enable_graph_memory_update: false,   // 模拟期间关闭实时更新
      post_sim_graph_import: true            // 模拟结束后批量导入
    }
    
    if (props.maxRounds) {
      params.max_rounds = props.maxRounds
      addLog(`目标轮数: ${props.maxRounds}`)
    }
    
    const res = await startSimulation(params)
    
    if (res.success && res.data) {
      addLog('✓ 续跑模式启动成功')
      addLog(`  ├─ PID: ${res.data.process_pid || '-'}`)
      
      phase.value = 1
      simulationStartTime.value = Date.now()
      runStatus.value = res.data
      
      startStatusPolling()
      startDetailPolling()
    } else {
      startError.value = res.error || '续跑失败'
      addLog(`✗ 续跑失败: ${res.error || '未知错误'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    startError.value = err.message
    addLog(`✗ 续跑异常: ${err.message}`)
    emit('update-status', 'error')
  } finally {
    isStarting.value = false
  }
}

// 打开模拟图谱独立页面
const scrollToSimGraph = () => {
  const resolved = vueRouter.resolve({
    name: 'SimGraph',
    params: { simulationId: props.simulationId },
    query: {
      graph_id: props.projectData?.graph_id,
      project_id: props.projectData?.project_id
    }
  })
  window.open(resolved.href, '_blank')
}


// 重新模拟：先停止当前（如在运行），再强制启动
const doRestartSimulation = async () => {
  if (!props.simulationId) return
  const confirmed = window.confirm('确定要重新启动推演吗？当前数据将被覆盖。')
  if (!confirmed) return

  // 如果正在运行，先停止
  if (phase.value === 1) {
    addLog('正在停止当前模拟…')
    try {
      await stopSimulation({ simulation_id: props.simulationId })
      stopPolling()
    } catch (e) { /* 忽略停止错误，强制重启 */ }
  }
  // 然后启动新模拟
  await doStartSimulation()
}

// 停止模拟
const handleStopSimulation = async () => {
  if (!props.simulationId) return
  
  isStopping.value = true
  addLog('正在停止模拟...')
  
  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })
    
    if (res.success) {
      addLog('✓ 模拟已停止')
      phase.value = 2
      stopPolling()
      emit('update-status', 'completed')
    } else {
      addLog(`停止失败: ${res.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`停止异常: ${err.message}`)
  } finally {
    isStopping.value = false
  }
}

// 轮询状态
let statusTimer = null
let detailTimer = null

const startStatusPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 5000)
}

const startDetailPolling = () => {
  detailTimer = setInterval(fetchRunStatusDetail, 8000)
}

const stopPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (detailTimer) {
    clearInterval(detailTimer)
    detailTimer = null
  }
}

// 追踪各平台的上一次轮次，用于检测变化并输出日志
const prevTwitterRound = ref(0)
const prevRedditRound = ref(0)

const looksLikeMojibake = (text) => {
  if (!text || typeof text !== 'string') return false
  return /[�]/.test(text) || /[鍒妯鏈绔]/.test(text)
}

const getRunStatusErrorMessage = (data) => {
  const rawError = typeof data?.error === 'string' ? data.error.trim() : ''

  if (rawError && !looksLikeMojibake(rawError)) {
    return rawError
  }

  if (data?.runner_status === 'failed') {
    return '模拟运行失败，请检查后端日志'
  }

  if (data?.runner_status === 'stopped') {
    return '模拟已中断，通常是开发服务被关闭、重启，或手动停止了进程'
  }

  return '模拟状态异常'
}

const fetchRunStatus = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatus(props.simulationId)
    
    if (res.success && res.data) {
      const data = res.data
      
      runStatus.value = data
      
      // 分别检测各平台的轮次变化并输出日志
      if (data.twitter_current_round > prevTwitterRound.value) {
        addLog(`[Plaza] R${data.twitter_current_round}/${data.total_rounds} | T:${data.twitter_simulated_hours || 0}h | A:${data.twitter_actions_count}`)
        prevTwitterRound.value = data.twitter_current_round
      }
      
      if (data.reddit_current_round > prevRedditRound.value) {
        addLog(`[Community] R${data.reddit_current_round}/${data.total_rounds} | T:${data.reddit_simulated_hours || 0}h | A:${data.reddit_actions_count}`)
        prevRedditRound.value = data.reddit_current_round
      }
      
      // 检测模拟是否已完成（通过 runner_status 或平台完成状态判断）
      const platformsCompleted = checkPlatformsCompleted(data)
      const isFailed = data.runner_status === 'failed'
      const isStoppedUnexpectedly = data.runner_status === 'stopped' && !platformsCompleted

      if (isFailed || isStoppedUnexpectedly) {
        stopPolling()
        const hasRoundData = (data.current_round || 0) > 0
        if (hasRoundData) {
          // 已有轮次数据 → 按"已完成"对待，保留数据并允许生成报告
          phase.value = 2
          addLog(`⚠ 模拟在 R${data.current_round} ${isFailed ? '异常退出' : '中断'}，已有数据可生成报告`)
          fetchWorldModelData({ initial: true })
          emit('update-status', 'completed')
        } else {
          phase.value = 0
          const errorMessage = getRunStatusErrorMessage(data)
          startError.value = errorMessage
          addLog(`✗ ${errorMessage}`)
          emit('update-status', 'error')
        }
        return
      }

      const isCompleted = data.runner_status === 'completed'
      
      // 额外检查：如果后端还没来得及更新 runner_status，但平台已经决策简报已生成
      
      if (isCompleted || platformsCompleted) {
        if (platformsCompleted && !isCompleted) {
          addLog('✓ 检测到所有平台模拟已结束')
        }
        addLog('✓ 推演已完成')
        phase.value = 2
        stopPolling()
        // 推演完成时拉取一次完整的世界模型数据
        fetchWorldModelData({ initial: true })
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('获取运行状态失败:', err)
  }
}

// 检查所有启用的平台是否已完成
const checkPlatformsCompleted = (data) => {
  // 如果没有任何平台数据，返回 false
  if (!data) return false
  
  // 检查各平台的完成状态
  const twitterCompleted = data.twitter_completed === true
  const redditCompleted = data.reddit_completed === true
  
  // 如果至少有一个平台完成了，检查是否所有启用的平台都完成了
  // 通过 actions_count 判断平台是否被启用（如果 count > 0 或 running 曾为 true）
  const twitterEnabled = (data.twitter_actions_count > 0) || data.twitter_running || twitterCompleted
  const redditEnabled = (data.reddit_actions_count > 0) || data.reddit_running || redditCompleted
  
  // 如果没有任何平台被启用，返回 false
  if (!twitterEnabled && !redditEnabled) return false
  
  // 检查所有启用的平台是否都已完成
  if (twitterEnabled && !twitterCompleted) return false
  if (redditEnabled && !redditCompleted) return false
  
  return true
}

const fetchRunStatusDetail = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getRunStatusDetail(props.simulationId)
    
    if (res.success && res.data) {
      // 使用 all_actions 获取完整的动作列表
      const serverActions = res.data.all_actions || []
      
      // 更新世界状态
      if (res.data.world_state) {
        // Only fetch full graph if world state round changed or initialized
        const oldRound = worldState.value?.round_num || -1
        const newRound = res.data.world_state.round_num
        
        if (newRound > oldRound) {
          worldState.value = res.data.world_state
          fetchWorldModelData()
        }
      }
      
      // 增量添加新动作（去重）
      let newActionsAdded = 0
      serverActions.forEach(action => {
        // 生成唯一ID
        const actionId = action.id || `${action.timestamp}-${action.platform}-${action.agent_id}-${action.action_type}`
        
        if (!actionIds.value.has(actionId)) {
          actionIds.value.add(actionId)
          allActions.value.push({
            ...action,
            _uniqueId: actionId
          })
          newActionsAdded++
        }
      })
      
      // 不自动滚动，让用户自由查看时间轴
      // 新动作会在底部追加
    }
  } catch (err) {
    console.warn('获取详细状态失败:', err)
  }
}

// 获取世界模型数据
// - initial=true：全量加载（挂载、恢复、完成时使用）
// - initial=false：增量加载，仅拉取比当前已有更新的 state / events / graph
//   （解决原实现每轮 3 个全量查询导致的性能问题，对应 #3）
const _lastCausalFetchAt = ref(0)
const CAUSAL_MIN_INTERVAL_MS = 10000  // 因果图谱节流：至少 10s 才重算一次
let _fetchingWorldModel = false
const fetchWorldModelData = async ({ initial = false } = {}) => {
  if (!props.simulationId) return
  if (_fetchingWorldModel) return  // 防重入：避免并行重复请求
  _fetchingWorldModel = true
  try {
    // --- 状态历史（增量） ---
    if (initial || worldStateHistory.value.length === 0) {
      const wsRes = await getWorldState(props.simulationId)
      if (wsRes.success && wsRes.data) {
        worldStateHistory.value = wsRes.data.state_history || []
        worldStateSummary.value = wsRes.data.state_summary || ''
      }
    } else {
      // 仅拉最后 5 条，按 round_num 合并去重，避免每轮重读整个 jsonl
      const wsRes = await getWorldState(props.simulationId, { last_n: 5 })
      if (wsRes.success && wsRes.data) {
        const existing = new Set(worldStateHistory.value.map(s => s.round_num))
        const incoming = wsRes.data.state_history || []
        for (const snap of incoming) {
          if (!existing.has(snap.round_num)) {
            worldStateHistory.value.push(snap)
          }
        }
        if (wsRes.data.state_summary) {
          worldStateSummary.value = wsRes.data.state_summary
        }
      }
    }

    // --- 事件（增量：from_round = 已有最大 round + 1） ---
    const maxRound = worldEvents.value.reduce(
      (m, e) => (e.round_num > m ? e.round_num : m),
      -1
    )
    const evtParams = initial ? {} : { from_round: Math.max(0, maxRound) }
    const evtRes = await getWorldEvents(props.simulationId, evtParams)
    if (evtRes.success && evtRes.data) {
      if (initial) {
        worldEvents.value = evtRes.data.events || []
      } else {
        const knownIds = new Set(worldEvents.value.map(e => e.event_id))
        for (const evt of (evtRes.data.events || [])) {
          if (!knownIds.has(evt.event_id)) worldEvents.value.push(evt)
        }
      }
    }

    // --- 因果图（节流：间隔 < 10s 跳过） ---
    const now = Date.now()
    if (initial || now - _lastCausalFetchAt.value >= CAUSAL_MIN_INTERVAL_MS) {
      const cgRes = await getCausalGraph(props.simulationId)
      if (cgRes.success && cgRes.data) {
        causalGraph.value = cgRes.data
      }
      _lastCausalFetchAt.value = now
    }
  } catch (err) {
    console.warn('获取世界模型数据失败:', err)
  } finally {
    _fetchingWorldModel = false
  }
}

// Helpers
const getActionTypeLabel = (type) => {
  const labels = {
    'CREATE_POST': 'POST',
    'REPOST': 'REPOST',
    'LIKE_POST': 'LIKE',
    'CREATE_COMMENT': 'COMMENT',
    'LIKE_COMMENT': 'LIKE',
    'DO_NOTHING': 'IDLE',
    'FOLLOW': 'FOLLOW',
    'SEARCH_POSTS': 'SEARCH',
    'QUOTE_POST': 'QUOTE',
    'UPVOTE_POST': 'UPVOTE',
    'DOWNVOTE_POST': 'DOWNVOTE'
  }
  return labels[type] || type || 'UNKNOWN'
}

const getActionTypeClass = (type) => {
  const classes = {
    'CREATE_POST': 'badge-post',
    'REPOST': 'badge-action',
    'LIKE_POST': 'badge-action',
    'CREATE_COMMENT': 'badge-comment',
    'LIKE_COMMENT': 'badge-action',
    'QUOTE_POST': 'badge-post',
    'FOLLOW': 'badge-meta',
    'SEARCH_POSTS': 'badge-meta',
    'UPVOTE_POST': 'badge-action',
    'DOWNVOTE_POST': 'badge-action',
    'DO_NOTHING': 'badge-idle'
  }
  return classes[type] || 'badge-default'
}

const truncateContent = (content, maxLength = 100) => {
  if (!content) return ''
  if (content.length > maxLength) return content.substring(0, maxLength) + '...'
  return content
}

const formatActionTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog('错误：缺少 simulationId')
    return
  }
  
  if (isGeneratingReport.value) {
    addLog('决策简报生成请求已发送，请稍候...')
    return
  }
  
  isGeneratingReport.value = true
  addLog('正在启动决策简报生成...')
  
  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true
    })
    
    if (res.success && res.data) {
      const reportId = res.data.report_id
      addLog(`✓ 决策简报生成任务已启动: ${reportId}`)

      // 通知父组件跳转决策简报生成步骤
      emit('next-step', { reportId })
    } else {
      addLog(`✗ 启动决策简报生成失败: ${res.error || '未知错误'}`)
      isGeneratingReport.value = false
    }
  } catch (err) {
    addLog(`✗ 启动决策简报生成异常: ${err.message}`)
    isGeneratingReport.value = false
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

// 用户选择：续跑
const handleChoiceResume = () => {
  showRunChoice.value = false
  addLog(`→ 用户选择续跑：从第 ${oldRunRounds.value + 1} 轮继续到 ${props.maxRounds} 轮`)
  doResumeSimulation()
}

// 用户选择：重新运行
const handleChoiceRestart = () => {
  showRunChoice.value = false
  addLog(`→ 用户选择重新运行 (${props.maxRounds} 轮)`)
  doStartSimulation()
}

// 用户选择：查看已有数据
const handleChoiceKeepOld = async () => {
  showRunChoice.value = false
  addLog(`→ 用户选择查看已有数据 (${oldRunRounds.value} 轮)`)
  phase.value = 2
  await fetchRunStatusDetail()
  await fetchWorldModelData({ initial: true })
  emit('update-status', 'completed')
}

// 检测当前 simulation_id 的后端状态，再决定是启动 / 恢复 / 只读查看
// 替换原先的"无条件 force 重启"，避免刷新页面即销毁进行中或已完成的模拟
const bootstrap = async () => {
  if (!props.simulationId) return
  addLog('Step3 模拟运行初始化')

  // 从 Step2 点"开始推演"进入时，检查是否有旧数据，有则让用户选择
  if (props.freshStart) {
    emit('fresh-start-consumed')
    try {
      const oldRes = await getRunStatus(props.simulationId)
      const oldData = oldRes?.data || {}
      const oldRound = oldData.current_round || 0
      if (oldRound > 0) {
        // 有旧数据，弹出选择
        oldRunRounds.value = oldRound
        runStatus.value = oldData
        showRunChoice.value = true
        addLog(`检测到已有 ${oldRound} 轮数据，本次设定 ${props.maxRounds} 轮，请选择操作`)
        return
      }
    } catch (_) { /* 无旧数据，继续 */ }
    addLog('→ 启动新模拟')
    doStartSimulation()
    return
  }

  try {
    const res = await getRunStatus(props.simulationId)
    const data = res?.data || {}
    const status = data.runner_status

    if (status === 'running') {
      addLog(`✓ 检测到模拟进行中 (R${data.current_round || 0}/${data.total_rounds || '-'})，恢复监听`)
      runStatus.value = data
      phase.value = 1
      simulationStartTime.value = simulationStartTime.value || Date.now()
      startStatusPolling()
      startDetailPolling()
      emit('update-status', 'processing')
      fetchRunStatusDetail()
      fetchWorldModelData({ initial: true })
    } else if (status === 'completed') {
      addLog('✓ 检测到推演已完成，加载历史数据')
      runStatus.value = data
      phase.value = 2
      emit('update-status', 'completed')
      fetchRunStatusDetail()
      fetchWorldModelData({ initial: true })
    } else if (status === 'failed' || status === 'stopped') {
      runStatus.value = data
      // 如果已跑过轮次（stopped 且 current_round > 0），按"已完成"对待：
      // 保留数据、允许生成报告；只有真·失败或 0 轮才回到未开始状态
      const hasRoundData = (data.current_round || 0) > 0
      if (status === 'stopped' && hasRoundData) {
        addLog(`✓ 模拟已在 R${data.current_round} 停止，已累计数据可直接生成报告`)
        phase.value = 2
        emit('update-status', 'completed')
      } else {
        addLog(`⚠ 上次模拟为 ${status} 状态，加载已有数据（可点击"重新启动"重跑）`)
        phase.value = 0
        startError.value = getRunStatusErrorMessage(data)
      }
      fetchRunStatusDetail()
      fetchWorldModelData({ initial: true })
    } else {
      // idle / null：检查是否有已持久化的历史数据
      const hasHistoricData = (data.current_round || 0) > 0
      if (hasHistoricData) {
        addLog(`✓ 检测到历史模拟数据 (R${data.current_round})，加载中`)
        runStatus.value = data
        phase.value = 2
        emit('update-status', 'completed')
        fetchRunStatusDetail()
        fetchWorldModelData({ initial: true })
      } else {
        // 真正的首次进入，启动
        doStartSimulation()
      }
    }
  } catch (err) {
    addLog(`读取当前模拟状态失败: ${err.message}，尝试启动`)
    doStartSimulation()
  }
}

onMounted(() => {
  bootstrap()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* ==================== 新配色方案 ==================== */
/* 基础色 */
:root {
  --color-white: #FFFFFF;
  --color-snow: #FAFAFC;
  --color-slate: #F2F4F8;
  --color-border: #E6E8EF;
  --color-black: #0A0A0C;
  /* 渐变色 */
  --gradient-orange: #FFB96B;
  --gradient-yellow: #FDE8A4;
  --gradient-cyan: #A7F9FF;
  --gradient-purple: #887DFF;
  --gradient-pink: #FF68D6;
  /* 保留的青色 */
  --color-cyan: #A7F9FF;
  --color-cyan-dark: #7DD8E8;
  --color-cyan-accent: #5BC4D8;
}

/* ==================== 选择对话框 ==================== */
.run-choice-overlay {
  position: absolute;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(8px);
}
.run-choice-card {
  background: #FFFFFF;
  border: 1px solid #c7d2fe;
  border-radius: 16px;
  padding: 28px 32px;
  max-width: 440px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255,255,255,0.8);
}
.run-choice-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #4338ca;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 18px;
}
.run-choice-body {
  color: #1e293b;
}
.run-choice-info {
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 8px;
}
.run-choice-info strong {
  color: #0f172a;
  font-weight: 600;
}
.run-choice-hint {
  font-size: 13px;
  color: #475569;
  margin-bottom: 20px;
}
.run-choice-actions {
  display: flex;
  gap: 12px;
}
.choice-btn {
  flex: 1;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.choice-btn.primary {
  background: linear-gradient(135deg, var(--gradient-cyan), var(--gradient-purple));
  color: var(--color-white);
}
.choice-btn.primary:hover {
  background: linear-gradient(135deg, var(--gradient-purple), var(--gradient-pink));
}
.choice-btn.secondary {
  background: var(--color-slate);
  color: var(--color-black);
  border: 1px solid var(--color-border);
}
.choice-btn.secondary:hover {
  background: var(--color-snow);
  color: var(--color-black);
}

.simulation-panel {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-snow);
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  overflow: hidden;
}

/* --- Control Bar --- */
.control-bar {
  background: var(--color-white);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
  height: 80px;
  box-shadow: 0 2px 8px rgba(136, 125, 255, 0.08);
}

.status-group {
  display: flex;
  gap: 14px;
  align-items: center;
}

/* Progress Panel */
.progress-panel {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 18px;
  border-radius: 10px;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  opacity: 0.7;
  transition: all 0.3s;
  min-width: 200px;
  position: relative;
  cursor: pointer;
}

.progress-panel.active {
  opacity: 1;
  border-color: var(--gradient-cyan);
  background: linear-gradient(135deg, var(--color-white), rgba(167, 249, 255, 0.08));
  box-shadow: 0 2px 12px rgba(167, 249, 255, 0.15);
}

.progress-panel.completed {
  opacity: 1;
  border-color: var(--gradient-purple);
  background: linear-gradient(135deg, var(--color-white), rgba(136, 125, 255, 0.06));
  box-shadow: 0 2px 12px rgba(136, 125, 255, 0.12);
}

/* Dual Progress Bars */
.dual-progress {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 220px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  min-width: 74px;
  white-space: nowrap;
  letter-spacing: 0.03em;
}

.progress-label .platform-icon { width: 13px; height: 13px; }

.progress-track {
  flex: 1;
  height: 7px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  min-width: 110px;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.progress-fill.twitter {
  background: linear-gradient(90deg, var(--gradient-cyan), #38bdf8);
}

.progress-fill.reddit {
  background: linear-gradient(90deg, var(--gradient-purple), #a78bfa);
}

.progress-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-black);
  min-width: 38px;
  text-align: right;
}

.progress-total {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 400;
}

.check-icon {
  font-size: 13px;
  color: var(--gradient-purple);
  font-weight: 700;
}

/* ETA Badge */
.eta-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  padding: 5px 12px;
  border-radius: 6px;
  white-space: nowrap;
}

.eta-badge.done {
  color: var(--gradient-purple);
  background: rgba(136, 125, 255, 0.1);
}

/* World State Mini Indicators */
.ws-mini {
  display: flex;
  gap: 14px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--color-white);
  border: 1px solid var(--color-border);
}

.ws-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.ws-name {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ws-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-black);
}

/* Action Button */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-btn.primary {
  background: linear-gradient(135deg, var(--gradient-cyan), var(--gradient-purple));
  color: var(--color-white);
  box-shadow: 0 2px 12px rgba(136, 125, 255, 0.25);
}

.action-btn.primary:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--gradient-purple), var(--gradient-pink));
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(136, 125, 255, 0.35);
}

.action-btn.secondary {
  background: var(--color-white);
  color: var(--color-black);
  border: 1px solid var(--color-border);
}

.action-btn.secondary:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(167, 249, 255, 0.15), rgba(136, 125, 255, 0.1));
  border-color: var(--gradient-cyan);
  color: var(--gradient-purple);
}

.action-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* --- Narrative Main Content (World Model as protagonist) --- */
.narrative-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 24px;
  background: #FAFAFC;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Section 4: Dual Platform Simulation */
.actions-section {
  background: var(--color-white);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 4px 20px rgba(136, 125, 255, 0.08);
}

.actions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.actions-head .section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-black);
}

.actions-head-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.idle-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  user-select: none;
}
.idle-toggle input {
  accent-color: var(--gradient-purple);
  width: 14px;
  height: 14px;
}
.idle-toggle:hover { color: var(--gradient-purple); }

.actions-stat {
  font-size: 13px;
  color: #64748b;
}
.actions-stat .mono {
  color: var(--color-black);
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.idle-hint {
  margin-left: 6px;
  color: #94a3b8;
  font-size: 11px;
}

.dual-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-height: 0;
}
@media (max-width: 900px) {
  .dual-columns { grid-template-columns: 1fr; }
}

.col-panel {
  background: var(--color-snow);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  min-height: 500px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(136, 125, 255, 0.06);
}
.twitter-col { border-top: 3px solid var(--gradient-cyan); }
.reddit-col { border-top: 3px solid var(--gradient-purple); }

.col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}
.twitter-head { background: linear-gradient(135deg, rgba(167, 249, 255, 0.15), transparent); }
.reddit-head { background: linear-gradient(135deg, rgba(136, 125, 255, 0.1), transparent); }

.col-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-icon {
  width: 34px; height: 34px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
}
.twitter-icon { background: linear-gradient(135deg, rgba(167, 249, 255, 0.25), rgba(167, 249, 255, 0.1)); color: var(--gradient-cyan); }
.reddit-icon { background: linear-gradient(135deg, rgba(136, 125, 255, 0.2), rgba(136, 125, 255, 0.08)); color: var(--gradient-purple); }
.brand-text { display: flex; flex-direction: column; }
.col-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-black);
}
.col-subtitle {
  font-size: 11px;
  color: #64748b;
  margin-top: 1px;
}

.col-stats {
  display: flex; align-items: baseline; gap: 4px;
}
.col-stat-num {
  font-size: 22px;
  font-weight: 800;
  color: var(--gradient-purple);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.col-stat-label {
  font-size: 12px;
  color: #64748b;
}

.col-body {
  padding: 0;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.col-body::-webkit-scrollbar { width: 6px; }
.col-body::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--gradient-cyan), var(--gradient-purple)); border-radius: 3px; }
.col-body::-webkit-scrollbar-track { background: var(--color-slate); }
.twitter-feed { gap: 0; }
.reddit-feed { gap: 0; padding: 4px 0; }

/* ---- 轮次分隔线 ---- */
.round-sep {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px;
}
.round-sep-line {
  flex: 1; height: 1px;
  background: linear-gradient(90deg, transparent, var(--gradient-cyan), transparent);
}
.round-sep-label {
  font-size: 10px; font-weight: 700; letter-spacing: .8px;
  color: var(--gradient-purple); text-transform: uppercase;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.reddit-sep .round-sep-line {
  background: linear-gradient(90deg, transparent, var(--gradient-purple), transparent);
}
.reddit-sep .round-sep-label { color: var(--gradient-purple); }

/* ---- 轻量操作折叠组 ---- */
.action-group {
  margin: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-white);
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(136, 125, 255, 0.06);
}
.ag-header {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  user-select: none;
  transition: background .15s;
}
.ag-header:hover { background: var(--color-snow); }
.ag-count {
  font-size: 11px; font-weight: 700; color: var(--gradient-purple);
  white-space: nowrap;
}
.ag-pills {
  flex: 1; font-size: 11px; color: #64748b;
  letter-spacing: 1px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ag-toggle {
  font-size: 10px; color: #94a3b8;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.ag-body {
  border-top: 1px solid var(--color-border);
  padding: 2px 0;
  background: var(--color-snow);
}

.col-empty {
  color: #64748b;
  font-size: 13px;
  padding: 40px 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.empty-icon { font-size: 28px; opacity: 0.5; }

/* TransitionGroup animations for action cards */
.timeline-item-enter-active,
.timeline-item-leave-active {
  transition: all 0.35s cubic-bezier(0.165, 0.84, 0.44, 1);
}
.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.timeline-item-leave-to {
  opacity: 0;
}

/* Logs */
.system-logs {
  background: var(--color-white);
  color: var(--color-black);
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #64748b;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 6px; }
.log-content::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--gradient-cyan), var(--gradient-purple)); border-radius: 3px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time { color: #94a3b8; min-width: 75px; }
.log-msg { color: var(--color-black); word-break: break-all; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Loading spinner for button */
.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-top-color: var(--color-white);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

</style>
