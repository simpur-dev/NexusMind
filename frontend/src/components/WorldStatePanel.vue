<template>
  <div class="world-state-panel">
    <div class="panel-header">
      <h3>🌍 全局世界状态</h3>
      <span class="round-badge" v-if="currentState">第 {{ currentState.round_num }} 轮</span>
    </div>

    <!-- No Data State -->
    <div v-if="!currentState" class="empty-state">
      <div class="spinner"></div>
      <p>正在等待世界模型数据...</p>
    </div>

    <!-- Data Content -->
    <div v-else class="panel-content">
      
      <!-- 1. 核心指标刻度 (Macro Indicators) -->
      <div class="indicators-section section-box">
        <h4 class="section-title">宏观指标</h4>
        <div class="indicator-grid">
          <div v-for="item in indicatorItems" :key="item.key" class="indicator-item">
            <div class="ind-header">
              <span class="ind-label">{{ item.label }}</span>
              <span class="ind-val" :style="{ color: item.color }">{{ (item.value * 100).toFixed(1) }}%</span>
            </div>
            <div class="progress-bg">
              <div class="progress-bar" :style="{ width: `${item.value * 100}%`, backgroundColor: item.color }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. 状态总结 & 热词 (Summary & Keywords) -->
      <div class="summary-section section-box">
        <h4 class="section-title">当前状态摘要</h4>
        <p class="summary-text">{{ stateSummary || '系统当前运行稳定。' }}</p>
        
        <div class="keywords-wrap" v-if="currentState.top_keywords && currentState.top_keywords.length > 0">
          <span v-for="(kw, idx) in currentState.top_keywords" :key="idx" class="keyword-tag">
            {{ kw }}
          </span>
        </div>
      </div>

      <!-- 3. 事件注入面板 (God Mode) -->
      <div class="inject-section section-box" v-if="simulationId">
        <h4 class="section-title inject-title" @click="showInjectPanel = !showInjectPanel">
          <span>事件注入</span>
          <span class="toggle-icon">{{ showInjectPanel ? '▾' : '▸' }}</span>
        </h4>
        <div v-if="showInjectPanel" class="inject-form">
          <div class="form-row">
            <label class="form-label">事件类型</label>
            <select v-model="injectForm.event_type" class="form-select">
              <option value="breaking_news">突发新闻</option>
              <option value="official_statement">官方声明</option>
              <option value="policy_change">政策变化</option>
              <option value="rumor_spread">谣言传播</option>
              <option value="public_protest">公众抗议</option>
              <option value="expert_opinion">专家意见</option>
              <option value="custom">自定义</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label">描述</label>
            <textarea v-model="injectForm.description" class="form-textarea" rows="3" placeholder="描述事件..."></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">严重性: <span class="severity-val">{{ injectForm.severity.toFixed(1) }}</span></label>
            <input type="range" v-model.number="injectForm.severity" min="0" max="1" step="0.1" class="form-range" />
          </div>
          <button class="inject-btn" :disabled="injectLoading || !injectForm.description" @click="handleInjectEvent">
            <span v-if="injectLoading" class="spinner-small"></span>
            {{ injectLoading ? '注入中...' : '注入事件' }}
          </button>
          <div v-if="injectResult" class="inject-result" :class="injectResult.success ? 'success' : 'error'">
            {{ injectResult.message }}
          </div>
        </div>
      </div>

      <!-- 4. 事件与因果链 (Event & Causal Graph) -->
      <div class="causal-section section-box">
        <h4 class="section-title">事件因果链</h4>
        <div v-if="causalGraph && causalGraph.edges && causalGraph.edges.length > 0" class="causal-chain">
          <div v-for="edge in causalGraph.edges" :key="edge.edge_id" class="causal-edge">
            <div class="edge-nodes">
              <span class="node src">{{ formatEventNode(edge.source_event_id) }}</span>
              <span class="relation-arrow" :class="edge.relation_type" :title="`强度: ${edge.strength}`">
                {{ getRelationSymbol(edge.relation_type) }}
              </span>
              <span class="node tgt">{{ formatEventNode(edge.target_event_id) }}</span>
            </div>
            <div class="edge-evidence">{{ cleanEvidence(edge.evidence) }}</div>
          </div>
        </div>
        <div v-else-if="events && events.length > 0" class="event-list">
          <div v-for="evt in events" :key="evt.event_id" class="event-item" :class="evt.severity > 0.6 ? 'high-sev' : ''">
            <span class="evt-round">第{{ evt.round_num }}轮</span>
            <span class="evt-type">{{ formatEventType(evt.event_type) }}</span>
            <span class="evt-desc">{{ evt.description }}</span>
          </div>
        </div>
        <div v-else class="empty-state mini">
          尚未检测到显著事件。
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed, ref, reactive } from 'vue'
import { injectEvent } from '../api/simulation'

const props = defineProps({
  currentState: Object,
  stateHistory: Array,
  stateSummary: String,
  events: Array,
  causalGraph: Object,
  simulationId: String
})

// --- Event Injection State ---
const showInjectPanel = ref(false)
const injectLoading = ref(false)
const injectResult = ref(null)
const injectForm = reactive({
  event_type: 'breaking_news',
  description: '',
  severity: 0.7
})

const handleInjectEvent = async () => {
  if (!props.simulationId || !injectForm.description) return
  injectLoading.value = true
  injectResult.value = null
  try {
    const res = await injectEvent({
      simulation_id: props.simulationId,
      event_type: injectForm.event_type,
      description: injectForm.description,
      severity: injectForm.severity
    })
    if (res.success) {
      injectResult.value = { success: true, message: `事件注入成功 (队列: ${res.data?.result?.queue_size || '?'})` }
      injectForm.description = ''
    } else {
      injectResult.value = { success: false, message: res.error || '注入失败' }
    }
  } catch (err) {
    injectResult.value = { success: false, message: err.message || '网络错误' }
  } finally {
    injectLoading.value = false
    setTimeout(() => { injectResult.value = null }, 4000)
  }
}

// --- Indicators ---
const indicatorItems = computed(() => {
  if (!props.currentState) return []
  const s = props.currentState
  return [
    { key: 'attention', label: '公众关注度', value: s.attention_level, color: '#3b82f6' },
    { key: 'panic', label: '恐慌水平', value: s.panic_level, color: '#ef4444' },
    { key: 'trust', label: '公众信任度', value: s.trust_level, color: '#10b981' },
    { key: 'polarization', label: '极化水平', value: s.polarization_level, color: '#f59e0b' },
    { key: 'risk', label: '系统风险', value: s.risk_level, color: '#f97316' },
    { key: 'stability', label: '系统稳定性', value: s.stability_level, color: '#8b5cf6' }
  ]
})

// --- Formatters ---
const formatEventNode = (eventId) => {
  if (eventId === null || eventId === undefined) return '-'
  const idStr = String(eventId)
  if (props.events) {
    const evt = props.events.find(e => e.event_id === eventId)
    if (evt) {
      return `[第${evt.round_num}轮] ${formatEventType(evt.event_type)}`
    }
  }
  return idStr.length > 8 ? idStr.substring(0, 8) : idStr
}

const formatEventType = (type) => {
  const map = {
    'sentiment_shift': '情绪转变',
    'polarization_surge': '极化加剧',
    'trust_drop': '信任下滑',
    'heat_spike': '热度飙升',
    'official_response': '官方回应',
    'stabilization': '系统稳定',
    'calm_restored': '舆情平息',
    'topic_outbreak': '议题爆发'
  }
  return map[type] || type
}

const cleanEvidence = (txt) => {
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

const getRelationSymbol = (type) => {
  const map = {
    'triggered': '──▶',
    'amplified': '══▶',
    'suppressed': '──✕',
    'correlated': '···▶'
  }
  return map[type] || '──▶'
}
</script>

<style scoped>
.world-state-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--panel-bg, #1e1e24);
  border-left: 1px solid var(--border-color, #333);
  color: var(--text-primary, #e2e8f0);
  font-family: system-ui, -apple-system, sans-serif;
  overflow-y: auto;
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, #333);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(0, 0, 0, 0.2);
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.round-badge {
  background: var(--primary-color, #3b82f6);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-secondary, #94a3b8);
  flex: 1;
}

.empty-state.mini {
  padding: 20px;
  font-size: 13px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color, #333);
  border-top-color: var(--primary-color, #3b82f6);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.panel-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color, #333);
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary, #94a3b8);
  letter-spacing: 0.05em;
}

/* Indicators */
.indicator-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.indicator-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ind-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.ind-label {
  color: var(--text-primary, #e2e8f0);
}

.ind-val {
  font-weight: 600;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.progress-bg {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease-out, background-color 0.5s ease;
}

/* Summary & Keywords */
.summary-text {
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary, #e2e8f0);
}

.keywords-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

/* Causal Chain */
.causal-chain {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.causal-edge {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  padding: 10px;
  font-size: 13px;
}

.edge-nodes {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.node {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: #e2e8f0;
}

.node.src {
  border-left: 2px solid #ef4444;
}

.node.tgt {
  border-left: 2px solid #10b981;
}

.relation-arrow {
  font-weight: bold;
  color: #94a3b8;
}

.relation-arrow.triggered { color: #ef4444; }
.relation-arrow.amplified { color: #f59e0b; }
.relation-arrow.suppressed { color: #10b981; }

.edge-evidence {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.4;
  padding-left: 8px;
  border-left: 2px solid rgba(255,255,255,0.1);
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  padding: 8px;
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  border-left: 2px solid #3b82f6;
}

.event-item.high-sev {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.evt-round {
  color: #94a3b8;
  font-family: monospace;
  font-weight: bold;
}

.evt-type {
  font-weight: 600;
  color: #e2e8f0;
}

.evt-desc {
  color: #cbd5e1;
  flex: 1;
}
/* Event Injection Panel */
.inject-section {
  border-color: rgba(168, 85, 247, 0.3);
}

.inject-title {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  margin-bottom: 0 !important;
}

.inject-title:hover {
  color: #c084fc;
}

.toggle-icon {
  font-size: 12px;
  color: #94a3b8;
}

.inject-form {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 12px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.severity-val {
  font-family: monospace;
  color: #c084fc;
}

.form-select,
.form-textarea {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color, #333);
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-primary, #e2e8f0);
  font-family: inherit;
  resize: vertical;
}

.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #a855f7;
}

.form-range {
  width: 100%;
  accent-color: #a855f7;
}

.inject-btn {
  background: linear-gradient(135deg, #7c3aed, #a855f7);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: opacity 0.2s;
}

.inject-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.inject-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.inject-result {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 4px;
  text-align: center;
}

.inject-result.success {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.inject-result.error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
</style>