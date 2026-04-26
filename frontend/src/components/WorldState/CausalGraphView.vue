<template>
  <div class="causal-view">
    <div class="section-head">
      <h3 class="section-title">事件因果链</h3>
      <span class="count-badge" v-if="edges.length">
        {{ edges.length }} 条因果
      </span>
    </div>

    <!-- Grid of causal edges -->
    <div v-if="edges.length" class="edges-grid">
      <div v-for="edge in edges" :key="edge.edge_id || `${edge.source_event_id}-${edge.target_event_id}`"
           class="edge-card" :class="edge.relation_type">
        <div class="edge-row">
          <div class="node src">
            <div class="node-round">第{{ getRound(edge.source_event_id) }}轮</div>
            <div class="node-type">{{ formatEventType(getType(edge.source_event_id)) }}</div>
          </div>
          <div class="edge-arrow" :title="`强度: ${(edge.strength || 0).toFixed(2)}`">
            <span class="arrow-label">{{ relationLabel(edge.relation_type) }}</span>
            <span class="arrow-line">{{ relationSymbol(edge.relation_type) }}</span>
          </div>
          <div class="node tgt">
            <div class="node-round">第{{ getRound(edge.target_event_id) }}轮</div>
            <div class="node-type">{{ formatEventType(getType(edge.target_event_id)) }}</div>
          </div>
        </div>
        <div class="edge-evidence" v-if="cleanEvidence(edge.evidence)" :title="cleanEvidence(edge.evidence)">{{ truncate(cleanEvidence(edge.evidence), 140) }}</div>
      </div>
    </div>

    <div v-else-if="events.length" class="no-edges">
      已有事件，正在推断因果关系…
    </div>
    <div v-else class="no-edges empty">
      尚未检测到因果关系。在几轮事件发生后系统会开始推断。
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  causalGraph: { type: Object, default: () => ({}) },
  events: { type: Array, default: () => [] }
})

const edges = computed(() => props.causalGraph?.edges || [])

const eventMap = computed(() => {
  const m = new Map()
  for (const e of (props.events || [])) {
    if (e && e.event_id) m.set(e.event_id, e)
  }
  return m
})

const getRound = (eventId) => {
  const e = eventMap.value.get(eventId)
  return e ? e.round_num : '?'
}

const getType = (eventId) => {
  const e = eventMap.value.get(eventId)
  return e ? e.event_type : (eventId ? String(eventId).slice(0, 8) : 'unknown')
}

const formatEventType = (type) => {
  const map = {
    sentiment_shift: '情绪转变',
    polarization_surge: '极化加剧',
    trust_drop: '信任下滑',
    heat_spike: '热度骤升',
    official_response: '官方回应',
    stabilization: '气氛回稳',
    breaking_news: '突发新闻',
    official_statement: '官方声明',
    policy_change: '政策变动',
    rumor_spread: '谣言传播',
    public_protest: '公众抗议',
    expert_opinion: '专家观点'
  }
  return map[type] || type || '—'
}

const relationLabel = (t) => ({
  triggered: '触发',
  amplified: '放大',
  suppressed: '抑制',
  correlated: '关联'
}[t] || t || '相关')

const relationSymbol = (t) => ({
  triggered: '──▶',
  amplified: '══▶',
  suppressed: '──✕',
  correlated: '···▶'
}[t] || '──▶')

// 清洗 evidence：去掉裸露的 evt_xxx / ce_xxx 标识符，保留可读性
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

const truncate = (s, n) => {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '…' : s
}
</script>

<style scoped>
.causal-view {
  background: linear-gradient(180deg, rgba(59,130,246,0.12) 0%, rgba(30,41,59,0.85) 100%),
              linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #1e293b 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 16px 20px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.count-badge {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.edges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 10px;
}

.edge-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-left: 3px solid #3b82f6;
  border-radius: 8px;
  padding: 10px 12px;
}
.edge-card.triggered { border-left-color: #3b82f6; }
.edge-card.amplified { border-left-color: #ef4444; }
.edge-card.suppressed { border-left-color: #10b981; }
.edge-card.correlated { border-left-color: #f59e0b; }

.edge-row {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.node {
  background: rgba(51, 65, 85, 0.5);
  padding: 6px 8px;
  border-radius: 6px;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}
.node-round {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.node-type {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edge-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  color: #94a3b8;
  font-size: 10px;
}
.arrow-label {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.arrow-line {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
}

.edge-evidence {
  font-size: 12px;
  line-height: 1.4;
  color: #cbd5e1;
  padding: 4px 0 0 0;
}

.no-edges {
  font-size: 13px;
  color: #94a3b8;
  padding: 20px 0;
  text-align: center;
}
.no-edges.empty { color: #64748b; font-style: italic; }
</style>
