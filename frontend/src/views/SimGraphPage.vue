<template>
  <div class="causal-page timeline">
    <!-- Top bar -->
    <nav class="top-bar">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回推演
      </button>
      <h1 class="page-title">事件故事线</h1>

      <div class="stats-bar" v-if="stats">
        <span class="stat" v-if="seedEvents.length"><strong>{{ seedEvents.length }}</strong> 种子事件</span>
        <span class="stat"><strong>{{ stats.total_events }}</strong> 推演事件</span>
        <span class="stat"><strong>{{ stats.max_round }}</strong> 轮</span>
      </div>
    </nav>

    <!-- Loading / Error -->
    <div v-if="loading" class="center-state">
      <div class="spinner"></div>
      <span>正在加载故事线...</span>
    </div>
    <div v-else-if="error" class="center-state error">
      <span>{{ error }}</span>
      <button class="retry-btn" @click="fetchGraph">重试</button>
    </div>

    <template v-else-if="loaded">
      <!-- Empty state (no sim events AND no seed events) -->
      <div v-if="stats && stats.total_events === 0 && seedEvents.length === 0" class="center-state empty-hint">
        <span class="empty-icon">&#128302;</span>
        <span>模拟尚未产生事件，请等待更多轮次完成后刷新</span>
        <button class="retry-btn" @click="fetchGraph">刷新</button>
      </div>

      <!-- ============ TIMELINE / STORYLINE VIEW ============ -->
      <div v-if="stats && (stats.total_events > 0 || seedEvents.length > 0)" class="timeline-view">
        <!-- Compact legend -->
        <div class="tl-legend">
          <span v-for="(label, key) in EVENT_TYPE_LABELS" :key="key" class="tl-legend-item">
            <span class="tl-dot" :style="{ background: EVENT_COLORS[key] }"></span>{{ label }}
          </span>
          <span class="tl-legend-sep">|</span>
          <span v-for="(label, key) in RELATION_LABELS" :key="key" class="tl-legend-item">
            <span class="tl-edge-dot" :style="{ background: RELATION_COLORS[key] }"></span>{{ label }}
          </span>
        </div>

        <div class="tl-scroll">
          <!-- ====== 种子事件（来自基线材料提取） ====== -->
          <div v-if="seedEvents.length" class="tl-round tl-seed-round">
            <div class="tl-round-header">
              <div class="tl-round-marker seed-marker">
                <span class="tl-round-num">S</span>
              </div>
              <span class="tl-round-label">种子事件 <small style="color:#94a3b8;font-weight:400">（材料提取）</small></span>
              <span class="tl-round-count">{{ seedEvents.length }} 个事件</span>
            </div>
            <div class="tl-cards">
              <div
                v-for="evt in seedEvents" :key="evt.id"
                class="tl-card tl-seed-card"
                :class="{ selected: selectedEvent?.id === evt.id }"
                @click="selectEvent(evt)"
              >
                <div class="tl-card-head">
                  <span class="tl-type-badge" :style="{ background: SEED_TYPE_COLORS[evt.type] || '#64748b' }">
                    {{ SEED_TYPE_LABELS[evt.type] || evt.type || '事件' }}
                  </span>
                  <span v-if="evt.time" class="tl-seed-time">{{ evt.time }}</span>
                </div>
                <p class="tl-seed-title" v-if="evt.title">{{ evt.title }}</p>
                <p class="tl-card-desc">{{ evt.description || '无描述' }}</p>
                <div class="tl-seed-meta" v-if="evt.actor || evt.stage">
                  <span v-if="evt.actor" class="tl-seed-actor">{{ evt.actor }}</span>
                  <span v-if="evt.stage" class="tl-seed-stage">{{ evt.stage }}</span>
                </div>
                <!-- 因果关系箭头 -->
                <div class="tl-seed-links" v-if="getSeedEffects(evt.id).length">
                  <span class="tl-causal-icon">→</span>
                  <span v-for="e in getSeedEffects(evt.id)" :key="e.id" class="tl-seed-link-tag" @click.stop="selectEvent(e)">
                    {{ e.title || e.description?.slice(0,20) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- ====== 推演事件（按轮次） ====== -->
          <div v-for="group in roundGroups" :key="group.round" class="tl-round">
            <!-- Round header -->
            <div class="tl-round-header">
              <div class="tl-round-marker">
                <span class="tl-round-num">R{{ group.round }}</span>
              </div>
              <span class="tl-round-label">第 {{ group.round }} 轮</span>
              <span class="tl-round-count">{{ group.events.length }} 个事件</span>
            </div>

            <!-- Event cards -->
            <div class="tl-cards">
              <div
                v-for="evt in group.events" :key="evt.id"
                class="tl-card"
                :class="{
                  selected: selectedEvent?.id === evt.id,
                  highlighted: highlightedIds.has(evt.id),
                  dimmed: selectedEvent && !highlightedIds.has(evt.id)
                }"
                @click="selectEvent(evt)"
              >
                <!-- Card header -->
                <div class="tl-card-head">
                  <span class="tl-type-badge" :style="{ background: EVENT_COLORS[evt.event_type] }">
                    {{ eventTypeLabel(evt.event_type) }}
                  </span>
                  <span class="tl-severity" :class="severityClass(evt.severity)">
                    {{ (evt.severity || 0).toFixed(1) }}
                  </span>
                </div>

                <!-- Description -->
                <p class="tl-card-desc">{{ evt.description || '无描述' }}</p>

                <!-- Affected variables -->
                <div v-if="evt.affected_variables && Object.keys(evt.affected_variables).length" class="tl-vars">
                  <span v-for="(val, key) in evt.affected_variables" :key="key" class="tl-var-tag" :class="Number(val) >= 0 ? 'up' : 'down'">
                    {{ VARIABLE_LABELS[key] || key }} {{ Number(val) >= 0 ? '↑' : '↓' }}{{ Math.abs(Number(val)).toFixed(1) }}
                  </span>
                </div>

                <!-- Causal links -->
                <div class="tl-causal" v-if="getCauses(evt.id).length || getEffects(evt.id).length">
                  <div v-if="getCauses(evt.id).length" class="tl-causal-row">
                    <span class="tl-causal-icon">←</span>
                    <span
                      v-for="c in getCauses(evt.id)" :key="c.id"
                      class="tl-causal-tag cause"
                      :style="{ '--tag-color': EVENT_COLORS[c.event_type] }"
                      @click.stop="selectEvent(c)"
                    >{{ eventTypeLabel(c.event_type) }} R{{ c.round_num }}</span>
                  </div>
                  <div v-if="getEffects(evt.id).length" class="tl-causal-row">
                    <span class="tl-causal-icon">→</span>
                    <span
                      v-for="e in getEffects(evt.id)" :key="e.id"
                      class="tl-causal-tag effect"
                      :style="{ '--tag-color': EVENT_COLORS[e.event_type] }"
                      @click.stop="selectEvent(e)"
                    >{{ eventTypeLabel(e.event_type) }} R{{ e.round_num }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail panel -->
      <Transition name="slide-right">
        <div v-if="selectedEvent" class="detail-panel">
          <div class="detail-header">
            <span class="detail-type-badge" :style="{
              background: (selectedEvent.type ? SEED_TYPE_COLORS[selectedEvent.type] : EVENT_COLORS[selectedEvent.event_type] || '#64748b') + '20',
              color: selectedEvent.type ? SEED_TYPE_COLORS[selectedEvent.type] : EVENT_COLORS[selectedEvent.event_type]
            }">
              {{ selectedEvent.type ? (SEED_TYPE_LABELS[selectedEvent.type] || selectedEvent.type) : eventTypeLabel(selectedEvent.event_type) }}
            </span>
            <button class="close-btn" @click="selectedEvent = null">&times;</button>
          </div>
          <!-- Seed event detail -->
          <template v-if="selectedEvent.type">
            <h3 class="detail-name">{{ selectedEvent.title || '种子事件' }}</h3>
            <div class="detail-fields">
              <div v-if="selectedEvent.time" class="field">
                <span class="field-key">时间</span>
                <span class="field-val">{{ selectedEvent.time }}</span>
              </div>
              <div v-if="selectedEvent.actor" class="field full">
                <span class="field-key">主要角色</span>
                <span class="field-val">{{ selectedEvent.actor }}</span>
              </div>
              <div v-if="selectedEvent.stage" class="field">
                <span class="field-key">阶段</span>
                <span class="field-val">{{ selectedEvent.stage }}</span>
              </div>
              <div v-if="selectedEvent.description" class="field full">
                <span class="field-key">事件描述</span>
                <p class="field-val content">{{ selectedEvent.description }}</p>
              </div>
              <div v-if="getSeedEffects(selectedEvent.id).length" class="field full">
                <span class="field-key">导致事件</span>
                <div class="related-edges">
                  <div v-for="eff in getSeedEffects(selectedEvent.id)" :key="eff.id"
                       class="re-card" style="border-left-color: #f59e0b; cursor: pointer;"
                       @click="selectEvent(eff)">
                    <div class="re-head">
                      <span class="re-rel">{{ SEED_TYPE_LABELS[eff.type] || eff.type }}</span>
                    </div>
                    <div class="re-pair">{{ eff.title || eff.description?.slice(0, 60) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <!-- Simulation event detail -->
          <template v-else>
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
          </template>
        </div>
      </Transition>
    </template>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getSimGraph } from '../api/simulation'

const router = useRouter()
const route = useRoute()

const simulationId = route.params.simulationId
const graphId = route.query.graph_id
const projectId = route.query.project_id

function goBack() {
  // If opened in a new tab (no history), close the tab
  if (window.history.length <= 1) {
    window.close()
    return
  }
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

// 种子事件类型映射
const SEED_TYPE_LABELS = {
  trigger: '触发事件', escalation: '升级', response: '回应', consequence: '后果',
  turning_point: '转折点', resolution: '平息', follow_up: '后续',
  media_coverage: '媒体报道', public_reaction: '公众反应', official_action: '官方行动',
}
const SEED_TYPE_COLORS = {
  trigger: '#ef4444', escalation: '#f97316', response: '#3b82f6', consequence: '#8b5cf6',
  turning_point: '#ec4899', resolution: '#10b981', follow_up: '#06b6d4',
  media_coverage: '#f59e0b', public_reaction: '#a855f7', official_action: '#0ea5e9',
}
const SEED_RELATION_LABELS = {
  triggered: '触发', amplified: '放大', suppressed: '抑制', correlated: '关联',
  caused: '导致', led_to: '引向', followed_by: '紧随',
}

function eventTypeLabel(t) { return EVENT_TYPE_LABELS[t] || SEED_TYPE_LABELS[t] || String(t || '').replace(/_/g, ' ') }

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
const seedEvents = ref([])
let rawSeedEdges = []

let rawEvents = []
let rawCausalEdges = []

// 按轮次分组
const roundGroups = computed(() => {
  const groups = new Map()
  rawEvents.forEach(e => {
    if (!groups.has(e.round_num)) groups.set(e.round_num, [])
    groups.get(e.round_num).push(e)
  })
  return [...groups.entries()]
    .sort(([a], [b]) => a - b)
    .map(([round, events]) => ({ round, events }))
})

// 事件索引
const eventMap = computed(() => new Map(rawEvents.map(e => [e.id, e])))

// 因果关系查询
function getCauses(eventId) {
  return rawCausalEdges
    .filter(e => (e.target?.id || e.target) === eventId)
    .map(e => eventMap.value.get(e.source?.id || e.source))
    .filter(Boolean)
}
function getEffects(eventId) {
  return rawCausalEdges
    .filter(e => (e.source?.id || e.source) === eventId)
    .map(e => eventMap.value.get(e.target?.id || e.target))
    .filter(Boolean)
}

// 选中事件时高亮因果链
const highlightedIds = computed(() => {
  if (!selectedEvent.value) return new Set()
  const ids = new Set([selectedEvent.value.id])
  getCauses(selectedEvent.value.id).forEach(e => ids.add(e.id))
  getEffects(selectedEvent.value.id).forEach(e => ids.add(e.id))
  return ids
})

function severityClass(s) {
  const v = Number(s || 0)
  if (v >= 0.7) return 'high'
  if (v >= 0.4) return 'mid'
  return 'low'
}

function selectEvent(evt) {
  selectedEvent.value = selectedEvent.value?.id === evt.id ? null : { ...evt }
}

// 种子事件因果关系查询
function getSeedEffects(seedId) {
  return rawSeedEdges
    .filter(e => e.source === seedId)
    .map(e => seedEvents.value.find(s => s.id === e.target))
    .filter(Boolean)
}

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
async function fetchSeedEvents() {
  if (!projectId) return
  try {
    const { getCurrentBaseline } = await import('../api/incident')
    const res = await getCurrentBaseline(projectId)
    const cg = res?.data?.event_causal_graph
    if (cg?.events?.length) {
      seedEvents.value = cg.events
      rawSeedEdges = cg.edges || []
    }
  } catch (e) {
    console.warn('加载种子事件失败:', e)
  }
}

async function fetchGraph() {
  loading.value = true
  error.value = null
  try {
    // 并行加载推演事件和种子事件
    const [res] = await Promise.all([
      getSimGraph(simulationId, {
        limit: 10,
        event_limit: 60,
        action_links_per_event: 0,
        graph_id: graphId
      }),
      fetchSeedEvents()
    ])
    if (res.success && res.data) {
      rawEvents = (res.data.nodes || []).filter(n => n.type === 'event')
      rawCausalEdges = (res.data.edges || []).filter(e => e.type === 'CAUSAL')
      stats.value = {
        total_events: rawEvents.length,
        causal_edges: rawCausalEdges.length,
        max_round: res.data.stats?.max_round || 0
      }
      loaded.value = true
      loading.value = false
    } else {
      error.value = res.error || '无数据'
      loading.value = false
    }
  } catch (e) {
    error.value = e.message || '请求失败'
    loading.value = false
  }
}

function truncate(s, n) { return !s ? '' : s.length > n ? s.slice(0, n) + '…' : s }

onMounted(() => { fetchGraph() })
</script>

<style scoped>
/* ============ BASE ============ */
.causal-page {
  position: fixed; inset: 0;
  display: flex; flex-direction: column;
  overflow: hidden;
  font-family: 'Inter', -apple-system, sans-serif;
  z-index: 100;
  background: #f8fafc; color: #1e293b;
}

/* ============ TOP BAR ============ */
.top-bar {
  position: relative;
  display: flex; align-items: center; gap: 16px;
  padding: 10px 20px;
  backdrop-filter: blur(10px);
  z-index: 2; flex-shrink: 0;
  background: #fff; border-bottom: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.back-btn {
  display: flex; align-items: center; gap: 5px;
  background: none; border: 1px solid #d1d5db; border-radius: 8px;
  padding: 6px 14px; font-size: 13px; cursor: pointer; transition: all .15s;
  color: #64748b;
}
.back-btn:hover { border-color: #6366f1; color: #4f46e5; }

.page-title { font-size: 17px; font-weight: 700; margin: 0; color: #1e293b; }

.stats-bar { margin-left: auto; display: flex; gap: 16px; font-size: 13px; color: #94a3b8; }
.stat strong { color: #4f46e5; }

/* ============ CENTER STATES ============ */
.center-state {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 10px; font-size: 14px; color: #888;
}
.center-state.error { color: #f87171; }
.spinner {
  width: 22px; height: 22px;
  border: 2px solid #ddd; border-top-color: #6366f1;
  border-radius: 50%; animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.retry-btn {
  padding: 6px 14px; border-radius: 6px;
  border: 1px solid #6366f1; background: transparent; color: #6366f1;
  cursor: pointer; font-size: 13px;
}
.retry-btn:hover { background: #6366f1; color: #fff; }

/* ============ TIMELINE VIEW ============ */
.timeline-view {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; position: relative;
}

/* Compact legend */
.tl-legend {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 8px 24px;
  background: #fff; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.tl-legend-item { display: flex; align-items: center; gap: 4px; font-size: 11px; color: #64748b; }
.tl-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tl-edge-dot { width: 16px; height: 3px; border-radius: 2px; flex-shrink: 0; }
.tl-legend-sep { color: #cbd5e1; font-size: 13px; }

/* Scroll area */
.tl-scroll {
  flex: 1; overflow-y: auto; padding: 20px 24px 40px;
  scrollbar-width: thin; scrollbar-color: #c7d2fe #f1f5f9;
}
.tl-scroll::-webkit-scrollbar { width: 6px; }
.tl-scroll::-webkit-scrollbar-track { background: #f1f5f9; }
.tl-scroll::-webkit-scrollbar-thumb { background: #c7d2fe; border-radius: 3px; }

/* Round section */
.tl-round { margin-bottom: 24px; }
.tl-round:last-child { margin-bottom: 0; }

.tl-round-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px; padding-bottom: 8px;
  border-bottom: 2px solid #e2e8f0;
}
.tl-round-marker {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.tl-round-num { font-size: 11px; font-weight: 800; color: #fff; letter-spacing: 0.02em; }
.tl-round-label { font-size: 15px; font-weight: 700; color: #334155; }
.tl-round-count { font-size: 12px; color: #94a3b8; }

/* Cards grid */
.tl-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

/* Event card */
.tl-card {
  background: #fff; border: 1px solid #e2e8f0;
  border-radius: 12px; padding: 14px 16px;
  cursor: pointer; transition: all .2s;
  position: relative;
}
.tl-card:hover { border-color: #a5b4fc; box-shadow: 0 4px 16px rgba(99,102,241,0.08); }
.tl-card.selected { border-color: #6366f1; box-shadow: 0 4px 20px rgba(99,102,241,0.15); background: #fafaff; }
.tl-card.highlighted { border-color: #a5b4fc; background: #f5f3ff; }
.tl-card.dimmed { opacity: 0.35; }

.tl-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.tl-type-badge {
  font-size: 11px; font-weight: 700; color: #fff;
  padding: 2px 10px; border-radius: 10px;
  letter-spacing: 0.02em;
}
.tl-severity {
  font-size: 11px; font-weight: 700; padding: 2px 8px;
  border-radius: 6px;
}
.tl-severity.high { background: #fef2f2; color: #dc2626; }
.tl-severity.mid { background: #fffbeb; color: #d97706; }
.tl-severity.low { background: #f0fdf4; color: #16a34a; }

.tl-card-desc {
  font-size: 13px; line-height: 1.6; color: #475569;
  margin: 0 0 8px; display: -webkit-box;
  -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Variable tags */
.tl-vars { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.tl-var-tag {
  font-size: 10px; font-weight: 600; padding: 1px 6px;
  border-radius: 4px; white-space: nowrap;
}
.tl-var-tag.up { background: #fef2f2; color: #dc2626; }
.tl-var-tag.down { background: #f0fdf4; color: #16a34a; }

/* Causal links */
.tl-causal { border-top: 1px solid #f1f5f9; padding-top: 8px; }
.tl-causal-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
.tl-causal-row:last-child { margin-bottom: 0; }
.tl-causal-icon { font-size: 12px; color: #94a3b8; font-weight: 700; width: 16px; text-align: center; flex-shrink: 0; }
.tl-causal-tag {
  font-size: 10px; font-weight: 600; padding: 2px 8px;
  border-radius: 6px; cursor: pointer; transition: all .15s;
  border: 1px solid; white-space: nowrap;
}
.tl-causal-tag.cause {
  background: color-mix(in srgb, var(--tag-color) 8%, white);
  border-color: color-mix(in srgb, var(--tag-color) 25%, white);
  color: var(--tag-color);
}
.tl-causal-tag.effect {
  background: color-mix(in srgb, var(--tag-color) 8%, white);
  border-color: color-mix(in srgb, var(--tag-color) 25%, white);
  color: var(--tag-color);
}
.tl-causal-tag:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.08); }

/* ============ SEED EVENTS ============ */
.tl-seed-round { border-left: 3px solid #f59e0b; padding-left: 12px; }
.seed-marker {
  background: linear-gradient(135deg, #f59e0b, #f97316) !important;
}
.tl-seed-card {
  background: linear-gradient(135deg, #fffbeb 0%, #fff 100%);
  border-color: #fde68a;
}
.tl-seed-card:hover { border-color: #f59e0b; box-shadow: 0 4px 16px rgba(245,158,11,0.12); }
.tl-seed-card.selected { border-color: #f59e0b; background: #fffbeb; }
.tl-seed-title {
  font-size: 14px; font-weight: 700; color: #1e293b;
  margin: 0 0 4px; line-height: 1.4;
}
.tl-seed-time {
  font-size: 11px; font-weight: 600; color: #92400e;
  background: #fef3c7; padding: 1px 8px; border-radius: 6px;
}
.tl-seed-meta {
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;
}
.tl-seed-actor {
  font-size: 11px; font-weight: 600; color: #4f46e5;
  background: #eef2ff; padding: 2px 8px; border-radius: 6px;
}
.tl-seed-stage {
  font-size: 11px; font-weight: 600; color: #0f766e;
  background: #ccfbf1; padding: 2px 8px; border-radius: 6px;
}
.tl-seed-links {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin-top: 8px; padding-top: 8px; border-top: 1px solid #fde68a;
}
.tl-seed-link-tag {
  font-size: 10px; font-weight: 600; color: #92400e;
  background: #fef3c7; padding: 2px 8px; border-radius: 6px;
  cursor: pointer; transition: all .15s;
  max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.tl-seed-link-tag:hover { background: #fde68a; transform: translateY(-1px); }

/* ============ DETAIL PANEL ============ */
.detail-panel {
  position: absolute; right: 0; top: 0; bottom: 0;
  width: 360px; padding: 20px;
  overflow-y: auto; z-index: 5;
  backdrop-filter: blur(12px);
  background: #fff; border-left: 1px solid #e2e8f0; box-shadow: -4px 0 20px rgba(0,0,0,0.06);
}

.detail-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.detail-type-badge { font-size: 11px; padding: 3px 10px; border-radius: 10px; font-weight: 600; }
.close-btn {
  background: none; border: none; font-size: 22px;
  cursor: pointer; line-height: 1; color: #94a3b8;
}
.close-btn:hover { color: #1e293b; }

.detail-name { font-size: 16px; font-weight: 600; margin: 0 0 16px; color: #1e293b; }

.detail-fields { display: flex; flex-direction: column; gap: 10px; }
.field { display: flex; gap: 8px; align-items: baseline; }
.field.full { flex-direction: column; }
.field-key { font-size: 11px; min-width: 50px; flex-shrink: 0; color: #94a3b8; }
.field-val { font-size: 13px; color: #334155; }
.field-val.content {
  margin: 4px 0 0; font-size: 12px; line-height: 1.5;
  padding: 8px 10px; border-radius: 6px;
  color: #475569; background: #f8fafc; border: 1px solid #e2e8f0;
}

/* Related edges */
.related-edges { display: flex; flex-direction: column; gap: 8px; margin-top: 6px; }
.re-card { background: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid; border-radius: 6px; padding: 8px 10px; }
.re-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.re-rel { font-size: 12px; font-weight: 700; }
.re-strength { font-size: 11px; color: #888; }
.re-pair { font-size: 12px; color: #64748b; }
.re-evidence { font-size: 11px; color: #888; margin-top: 4px; line-height: 1.4; }

/* Transitions */
.slide-right-enter-active, .slide-right-leave-active {
  transition: transform .25s ease, opacity .25s ease;
}
.slide-right-enter-from, .slide-right-leave-to {
  transform: translateX(100%); opacity: 0;
}
</style>
