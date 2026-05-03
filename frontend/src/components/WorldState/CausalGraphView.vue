<template>
  <div class="causal-view">
    <div class="section-head">
      <h3 class="section-title">事件因果链</h3>
      <div class="section-meta">
        <span class="count-badge" v-if="edges.length">
          已发现 {{ edges.length }} 条因果关系
        </span>
      </div>
    </div>

    <!-- Filter bar -->
    <div v-if="edges.length" class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">类型</span>
        <button
          v-for="opt in relationOptions"
          :key="opt.id"
          class="filter-chip"
          :class="[opt.id, { active: activeRelation === opt.id }]"
          type="button"
          @click="activeRelation = opt.id"
        >
          <span class="chip-dot"></span>
          {{ opt.label }}
          <span class="filter-count">{{ relationCounts[opt.id] }}</span>
        </button>
      </div>
      <div class="filter-group">
        <span class="filter-label">强度</span>
        <button
          v-for="opt in strengthOptions"
          :key="opt.id"
          class="filter-chip strength"
          :class="[opt.id, { active: activeStrength === opt.id }]"
          type="button"
          @click="activeStrength = opt.id"
        >
          <span class="chip-dot"></span>
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- Grid of causal edges -->
    <div v-if="visibleEdges.length" class="edges-grid">
      <div
        v-for="edge in visibleEdges"
        :key="edge.edge_id || `${edge.source_event_id}-${edge.target_event_id}`"
        class="edge-card"
        :class="edge.relation_type"
        :title="rawEvidenceTooltip(edge)"
      >
        <div class="edge-row">
          <div class="node src">
            <span class="node-round">R{{ getRound(edge.source_event_id) }}</span>
            <span class="node-type">{{ formatEventType(getType(edge.source_event_id)) }}</span>
          </div>
          <div class="edge-rel">
            <span class="rel-verb">{{ relationLabel(edge.relation_type) }}</span>
            <span
              v-if="strengthLabel(edge.strength)"
              class="rel-strength"
              :class="strengthClass(edge.strength)"
            >{{ strengthLabel(edge.strength) }}</span>
            <span class="rel-arrow">{{ relationSymbol(edge.relation_type) }}</span>
          </div>
          <div class="node tgt">
            <span class="node-round">R{{ getRound(edge.target_event_id) }}</span>
            <span class="node-type">{{ formatEventType(getType(edge.target_event_id)) }}</span>
          </div>
        </div>
        <div class="edge-meta">
          <span>{{ timingLabel(edge) }}</span>
          <span class="meta-dot">·</span>
          <span>强度 {{ (Number(edge.strength) || 0).toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="edges.length && filteredEdges.length === 0" class="no-edges">
      当前筛选下没有因果关系。试着放宽类型或强度。
    </div>
    <div v-else-if="events.length" class="no-edges">
      已有事件，正在推断因果关系…
    </div>
    <div v-else class="no-edges empty">
      尚未检测到因果关系。在几轮事件发生后系统会开始推断。
    </div>

    <!-- Show more / less -->
    <div v-if="filteredEdges.length > pageSize" class="more-row">
      <button class="more-btn" type="button" @click="showAll = !showAll">
        {{ showAll
          ? `收起，仅看前 ${pageSize} 条`
          : `展开全部 ${filteredEdges.length} 条` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  causalGraph: { type: Object, default: () => ({}) },
  events: { type: Array, default: () => [] }
})

const edges = computed(() => props.causalGraph?.edges || [])

// ============== 筛选状态 ==============

const activeRelation = ref('all') // all | triggered | amplified | suppressed | correlated
const activeStrength = ref('mid_up') // all | mid_up | strong_only
const showAll = ref(false)
const pageSize = 30

const relationOptions = [
  { id: 'all', label: '全部' },
  { id: 'triggered', label: '引发' },
  { id: 'amplified', label: '助推' },
  { id: 'suppressed', label: '平息' },
  { id: 'correlated', label: '同步' }
]

const strengthOptions = [
  { id: 'mid_up', label: '强 + 中' },
  { id: 'strong_only', label: '仅看强' },
  { id: 'all', label: '全部' }
]

const relationCounts = computed(() => {
  const counts = { all: edges.value.length, triggered: 0, amplified: 0, suppressed: 0, correlated: 0 }
  for (const e of edges.value) {
    if (counts[e.relation_type] !== undefined) counts[e.relation_type] += 1
  }
  return counts
})

const strengthPasses = (s) => {
  const v = Number(s) || 0
  if (activeStrength.value === 'strong_only') return v >= 0.7
  if (activeStrength.value === 'mid_up') return v >= 0.4
  return true
}

const filteredEdges = computed(() => {
  return edges.value.filter((e) => {
    if (activeRelation.value !== 'all' && e.relation_type !== activeRelation.value) return false
    if (!strengthPasses(e.strength)) return false
    return true
  })
})

const visibleEdges = computed(() =>
  showAll.value ? filteredEdges.value : filteredEdges.value.slice(0, pageSize)
)

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
  triggered: '引发',
  amplified: '助推',
  suppressed: '平息',
  correlated: '同步'
}[t] || '相关')

const relationSymbol = (t) => ({
  triggered: '→',
  amplified: '⇒',
  suppressed: '⊘',
  correlated: '↔'
}[t] || '→')

// 强度标签：评委一眼看到“强/中/弱”，比 0.42 直观
const strengthLabel = (s) => {
  const v = Number(s) || 0
  if (v >= 0.7) return '强'
  if (v >= 0.4) return '中'
  if (v > 0) return '弱'
  return ''
}

const strengthClass = (s) => {
  const v = Number(s) || 0
  if (v >= 0.7) return 'strong'
  if (v >= 0.4) return 'medium'
  if (v > 0) return 'weak'
  return ''
}

// 轮次差：只输出“同轮 / 紧接一轮 / N 轮内”这种紧凑描述
const timingLabel = (edge) => {
  const sN = Number(getRound(edge.source_event_id))
  const tN = Number(getRound(edge.target_event_id))
  if (!Number.isFinite(sN) || !Number.isFinite(tN)) return '跳轮传导'
  const gap = Math.abs(tN - sN)
  if (gap === 0) return '同轮发生'
  if (gap === 1) return '下一轮传导'
  return `${gap} 轮内传导`
}

// hover 时把原始 strength + 后端 evidence 暴露给想深看的评委
const rawEvidenceTooltip = (edge) => {
  const parts = []
  const s = Number(edge.strength) || 0
  if (s > 0) parts.push(`关系强度 ${s.toFixed(2)}`)
  if (edge.evidence) parts.push(String(edge.evidence).trim())
  return parts.join('  ·  ')
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
  margin-bottom: 10px;
}
.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.section-meta { display: flex; align-items: center; gap: 8px; }
.count-badge {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

/* ====== Filter Bar ====== */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 14px 24px;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 8px;
}
.filter-group { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.filter-label {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  margin-right: 4px;
  letter-spacing: 0.04em;
}
.filter-chip {
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(51, 65, 85, 0.45);
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  font-family: inherit;
}
.filter-chip:hover { background: rgba(71, 85, 105, 0.6); color: #f1f5f9; }

/* 色点：未激活时也给评委语义提示 */
.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  box-shadow: 0 0 0 2px rgba(148, 163, 184, 0.18);
  flex-shrink: 0;
}
.filter-chip.triggered  .chip-dot { background: #60a5fa; box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.25); }
.filter-chip.amplified  .chip-dot { background: #fb923c; box-shadow: 0 0 0 2px rgba(251, 146, 60, 0.25); }
.filter-chip.suppressed .chip-dot { background: #34d399; box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.25); }
.filter-chip.correlated .chip-dot { background: #c084fc; box-shadow: 0 0 0 2px rgba(192, 132, 252, 0.25); }

/* 未激活下的微弱边框关系色，让类型之间从静态就能区分 */
.filter-chip.triggered  { border-color: rgba(96, 165, 250, 0.35); }
.filter-chip.amplified  { border-color: rgba(251, 146, 60, 0.35); }
.filter-chip.suppressed { border-color: rgba(52, 211, 153, 0.35); }
.filter-chip.correlated { border-color: rgba(192, 132, 252, 0.35); }

.filter-chip.active {
  background: rgba(59, 130, 246, 0.22);
  border-color: rgba(59, 130, 246, 0.55);
  color: #dbeafe;
}
.filter-chip.triggered.active  { background: rgba(96, 165, 250, 0.22); border-color: #60a5fa; color: #dbeafe; }
.filter-chip.amplified.active  { background: rgba(251, 146, 60, 0.22);  border-color: #fb923c; color: #fed7aa; }
.filter-chip.suppressed.active { background: rgba(52, 211, 153, 0.22); border-color: #34d399; color: #d1fae5; }
.filter-chip.correlated.active { background: rgba(192, 132, 252, 0.22); border-color: #c084fc; color: #e9d5ff; }

/* 强度 chip 的色点：不走关系色，用“强/中/无”中性递进 */
.filter-chip.strength.strong_only .chip-dot {
  background: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.25);
}
.filter-chip.strength.mid_up .chip-dot {
  background: linear-gradient(90deg, #ef4444 0%, #ef4444 50%, rgba(239, 68, 68, 0.35) 50%, rgba(239, 68, 68, 0.35) 100%);
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.18);
}
.filter-chip.strength.all .chip-dot {
  background: transparent;
  border: 1.5px solid #94a3b8;
  width: 8px; height: 8px;
  box-shadow: none;
}
.filter-chip.strength.strong_only.active {
  background: rgba(239, 68, 68, 0.18);
  border-color: rgba(239, 68, 68, 0.55);
  color: #fecaca;
}
.filter-chip.strength.mid_up.active {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.4);
  color: #fecaca;
}
.filter-chip.strength.all.active {
  background: rgba(148, 163, 184, 0.2);
  border-color: rgba(148, 163, 184, 0.5);
  color: #f1f5f9;
}
.filter-count {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 700;
  padding: 0 5px;
  background: rgba(15, 23, 42, 0.55);
  border-radius: 999px;
}
.filter-chip.active .filter-count { color: #f8fafc; background: rgba(15, 23, 42, 0.4); }

/* ====== Cards Grid ====== */
.edges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 8px;
}

.edge-card {
  background: rgba(30, 41, 59, 0.55);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-left: 3px solid #3b82f6;
  border-radius: 8px;
  padding: 8px 10px;
  transition: background 0.15s;
}
.edge-card:hover { background: rgba(51, 65, 85, 0.65); }
.edge-card.triggered  { border-left-color: #60a5fa; }
.edge-card.amplified  { border-left-color: #fb923c; }
.edge-card.suppressed { border-left-color: #34d399; }
.edge-card.correlated { border-left-color: #c084fc; }

.edge-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}
.node {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(51, 65, 85, 0.5);
  padding: 4px 8px;
  border-radius: 6px;
  color: #e5e7eb;
  overflow: hidden;
  min-width: 0;
}
.node-round {
  font-size: 10px;
  color: #cbd5e1;
  font-weight: 800;
  letter-spacing: 0.04em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: rgba(148, 163, 184, 0.18);
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}
.node-type {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Compact relation chip in middle column */
.edge-rel {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.2);
  white-space: nowrap;
}
.edge-card.triggered  .edge-rel { background: rgba(96, 165, 250, 0.14);  border-color: rgba(96, 165, 250, 0.45); }
.edge-card.amplified  .edge-rel { background: rgba(251, 146, 60, 0.14);  border-color: rgba(251, 146, 60, 0.45); }
.edge-card.suppressed .edge-rel { background: rgba(52, 211, 153, 0.14);  border-color: rgba(52, 211, 153, 0.45); }
.edge-card.correlated .edge-rel { background: rgba(192, 132, 252, 0.14); border-color: rgba(192, 132, 252, 0.45); }

.rel-verb {
  font-size: 11px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.04em;
}
.edge-card.triggered  .rel-verb { color: #dbeafe; }
.edge-card.amplified  .rel-verb { color: #fed7aa; }
.edge-card.suppressed .rel-verb { color: #d1fae5; }
.edge-card.correlated .rel-verb { color: #e9d5ff; }

/* strength 标签跟随关系色，避免双色系冲突；
   “强” 实色背景，“中” 半透明，“弱” 中性灰 */
.rel-strength {
  font-size: 9px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 4px;
  letter-spacing: 0.04em;
  line-height: 1.4;
}
.rel-strength.weak {
  background: rgba(148, 163, 184, 0.22);
  color: #cbd5e1;
}
/* triggered (蓝) */
.edge-card.triggered  .rel-strength.strong { background: #2563eb; color: #ffffff; }
.edge-card.triggered  .rel-strength.medium { background: rgba(96, 165, 250, 0.28);  color: #bfdbfe; }
/* amplified (橙) */
.edge-card.amplified  .rel-strength.strong { background: #ea580c; color: #ffffff; }
.edge-card.amplified  .rel-strength.medium { background: rgba(251, 146, 60, 0.28);  color: #fed7aa; }
/* suppressed (翻绿) */
.edge-card.suppressed .rel-strength.strong { background: #059669; color: #ffffff; }
.edge-card.suppressed .rel-strength.medium { background: rgba(52, 211, 153, 0.28);  color: #a7f3d0; }
/* correlated (紫) */
.edge-card.correlated .rel-strength.strong { background: #9333ea; color: #ffffff; }
.edge-card.correlated .rel-strength.medium { background: rgba(192, 132, 252, 0.28); color: #e9d5ff; }

.rel-arrow {
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
  color: #cbd5e1;
}
.edge-card.triggered  .rel-arrow { color: #60a5fa; }
.edge-card.amplified  .rel-arrow { color: #fb923c; }
.edge-card.suppressed .rel-arrow { color: #34d399; }
.edge-card.correlated .rel-arrow { color: #c084fc; }

/* Compact meta line below */
.edge-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding-left: 2px;
  font-size: 11px;
  color: #94a3b8;
}
.meta-dot { color: #475569; }

.no-edges {
  font-size: 13px;
  color: #94a3b8;
  padding: 20px 0;
  text-align: center;
}
.no-edges.empty { color: #64748b; font-style: italic; }

.more-row {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.more-btn {
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #bfdbfe;
  padding: 6px 18px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.more-btn:hover {
  background: rgba(59, 130, 246, 0.25);
  border-color: rgba(59, 130, 246, 0.5);
}
</style>
