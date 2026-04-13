<template>
  <div class="world-state-panel">
    <div class="panel-header">
      <h3>🌍 Global World State</h3>
      <span class="round-badge" v-if="currentState">Round {{ currentState.round_num }}</span>
    </div>

    <!-- No Data State -->
    <div v-if="!currentState" class="empty-state">
      <div class="spinner"></div>
      <p>Waiting for World Model data...</p>
    </div>

    <!-- Data Content -->
    <div v-else class="panel-content">
      
      <!-- 1. 核心指标刻度 (Macro Indicators) -->
      <div class="indicators-section section-box">
        <h4 class="section-title">Macro Indicators</h4>
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
        <h4 class="section-title">Current Summary</h4>
        <p class="summary-text">{{ stateSummary || 'System is currently stable.' }}</p>
        
        <div class="keywords-wrap" v-if="currentState.top_keywords && currentState.top_keywords.length > 0">
          <span v-for="(kw, idx) in currentState.top_keywords" :key="idx" class="keyword-tag">
            {{ kw }}
          </span>
        </div>
      </div>

      <!-- 3. 事件与因果链 (Event & Causal Graph) -->
      <div class="causal-section section-box">
        <h4 class="section-title">Event Causality Chain</h4>
        <div v-if="causalGraph && causalGraph.edges && causalGraph.edges.length > 0" class="causal-chain">
          <div v-for="edge in causalGraph.edges" :key="edge.edge_id" class="causal-edge">
            <div class="edge-nodes">
              <span class="node src">{{ formatEventNode(edge.source_event_id) }}</span>
              <span class="relation-arrow" :class="edge.relation_type" :title="`Strength: ${edge.strength}`">
                {{ getRelationSymbol(edge.relation_type) }}
              </span>
              <span class="node tgt">{{ formatEventNode(edge.target_event_id) }}</span>
            </div>
            <div class="edge-evidence">{{ edge.evidence }}</div>
          </div>
        </div>
        <div v-else-if="events && events.length > 0" class="event-list">
          <div v-for="evt in events" :key="evt.event_id" class="event-item" :class="evt.severity > 0.6 ? 'high-sev' : ''">
            <span class="evt-round">R{{ evt.round_num }}</span>
            <span class="evt-type">{{ formatEventType(evt.event_type) }}</span>
            <span class="evt-desc">{{ evt.description }}</span>
          </div>
        </div>
        <div v-else class="empty-state mini">
          No significant events detected yet.
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentState: Object,
  stateHistory: Array,
  stateSummary: String,
  events: Array,
  causalGraph: Object
})

// --- Indicators ---
const indicatorItems = computed(() => {
  if (!props.currentState) return []
  const s = props.currentState
  return [
    { key: 'attention', label: 'Public Attention', value: s.attention_level, color: '#3b82f6' },
    { key: 'panic', label: 'Panic Level', value: s.panic_level, color: '#ef4444' },
    { key: 'trust', label: 'Public Trust', value: s.trust_level, color: '#10b981' },
    { key: 'polarization', label: 'Polarization', value: s.polarization_level, color: '#f59e0b' },
    { key: 'risk', label: 'System Risk', value: s.risk_level, color: '#f97316' },
    { key: 'stability', label: 'Stability', value: s.stability_level, color: '#8b5cf6' }
  ]
})

// --- Formatters ---
const formatEventNode = (eventId) => {
  if (!props.events) return eventId.substring(0, 8)
  const evt = props.events.find(e => e.event_id === eventId)
  if (evt) {
    return `[R${evt.round_num}] ${formatEventType(evt.event_type)}`
  }
  return eventId.substring(0, 8)
}

const formatEventType = (type) => {
  const map = {
    'sentiment_shift': 'Sentiment Shift',
    'polarization_surge': 'Polarization Surge',
    'trust_drop': 'Trust Drop',
    'heat_spike': 'Heat Spike',
    'official_response': 'Official Response',
    'stabilization': 'Stabilization'
  }
  return map[type] || type
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
  text-transform: uppercase;
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
</style>