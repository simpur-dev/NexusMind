<template>
  <div class="events-block">
    <div class="block-head">
      <h3 class="section-title">事件时间线</h3>
      <button
        class="inject-toggle"
        :class="{ active: showInject }"
        v-if="simulationId"
        @click="showInject = !showInject"
      >
        {{ showInject ? '× 关闭注入' : '+ 注入事件' }}
      </button>
    </div>

    <!-- Inject Panel (collapsible) -->
    <div v-if="showInject && simulationId" class="inject-panel">
      <div class="form-grid">
        <div class="form-row">
          <label>类型</label>
          <select v-model="form.event_type">
            <option value="breaking_news">突发新闻</option>
            <option value="official_statement">官方声明</option>
            <option value="policy_change">政策变动</option>
            <option value="rumor_spread">谣言传播</option>
            <option value="public_protest">公众抗议</option>
            <option value="expert_opinion">专家观点</option>
            <option value="custom">自定义</option>
          </select>
        </div>
        <div class="form-row severity">
          <label>严重度 <span class="sev-val">{{ form.severity.toFixed(1) }}</span></label>
          <input type="range" v-model.number="form.severity" min="0" max="1" step="0.1" />
        </div>
      </div>
      <textarea
        v-model="form.description"
        class="desc-input"
        rows="2"
        placeholder="描述你想注入的事件…"
      />
      <div class="inject-actions">
        <button class="btn-inject" :disabled="injecting || !form.description" @click="handleInject">
          <span v-if="injecting" class="spinner-small"></span>
          {{ injecting ? '注入中…' : '注入到模拟' }}
        </button>
        <span
          v-if="injectResult"
          class="inject-msg"
          :class="injectResult.success ? 'ok' : 'err'"
        >{{ injectResult.message }}</span>
      </div>
    </div>

    <!-- Horizontal event timeline (latest on right) -->
    <div v-if="events.length" class="timeline-track">
      <div
        v-for="evt in sortedEvents"
        :key="evt.event_id"
        class="evt-chip"
        :class="[evt.event_type, severityClass(evt.severity)]"
        :title="evt.description"
      >
        <div class="evt-round">R{{ evt.round_num }}</div>
        <div class="evt-type">{{ formatEventType(evt.event_type) }}</div>
        <div class="evt-desc">{{ truncate(evt.description, 70) }}</div>
      </div>
    </div>
    <div v-else class="empty-hint">
      尚未触发事件。当宏观指标出现显著变化时，系统会自动识别出事件。
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { injectEvent } from '../../api/simulation'

const props = defineProps({
  events: { type: Array, default: () => [] },
  simulationId: String
})

const showInject = ref(false)
const injecting = ref(false)
const injectResult = ref(null)
const form = reactive({
  event_type: 'breaking_news',
  description: '',
  severity: 0.7
})

const sortedEvents = computed(() => {
  return [...(props.events || [])].sort((a, b) => a.round_num - b.round_num)
})

const severityClass = (sev) => {
  const s = Number(sev) || 0
  if (s >= 0.7) return 'sev-high'
  if (s >= 0.4) return 'sev-mid'
  return 'sev-low'
}

const formatEventType = (t) => ({
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
}[t] || t || '—')

const truncate = (s, n) => {
  if (!s) return ''
  const str = String(s)
  return str.length > n ? str.slice(0, n) + '…' : str
}

const handleInject = async () => {
  if (!props.simulationId || !form.description) return
  injecting.value = true
  injectResult.value = null
  try {
    const res = await injectEvent({
      simulation_id: props.simulationId,
      event_type: form.event_type,
      description: form.description,
      severity: form.severity
    })
    if (res.success) {
      injectResult.value = { success: true, message: `已入队（队长：${res.data?.result?.queue_size ?? '?'}）` }
      form.description = ''
    } else {
      injectResult.value = { success: false, message: res.error || '注入失败' }
    }
  } catch (err) {
    injectResult.value = { success: false, message: err.message || '网络错误' }
  } finally {
    injecting.value = false
    setTimeout(() => { injectResult.value = null }, 4500)
  }
}
</script>

<style scoped>
.events-block {
  background: #0f0f14;
  border: 1px solid #2a2a33;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.inject-toggle {
  background: transparent;
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.inject-toggle:hover { background: rgba(59, 130, 246, 0.1); }
.inject-toggle.active { background: rgba(59, 130, 246, 0.18); color: #bfdbfe; }

.inject-panel {
  background: rgba(59, 130, 246, 0.05);
  border: 1px dashed rgba(59, 130, 246, 0.25);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-row label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.form-row.severity label { display: flex; justify-content: space-between; align-items: center; }
.sev-val { color: #3b82f6; font-family: ui-monospace, Menlo, monospace; font-size: 12px; }
.form-row select,
.desc-input {
  background: #18181f;
  color: #e5e7eb;
  border: 1px solid #2a2a33;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
  font-family: inherit;
}
.desc-input { resize: vertical; }
.form-row input[type=range] { accent-color: #3b82f6; }

.inject-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.btn-inject {
  background: #3b82f6;
  color: #fff;
  border: 0;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-inject:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-inject:hover:not(:disabled) { background: #2563eb; }
.spinner-small {
  display: inline-block;
  width: 11px;
  height: 11px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
  margin-right: 6px;
}
@keyframes spin { to { transform: rotate(360deg); } }

.inject-msg {
  font-size: 12px;
}
.inject-msg.ok { color: #10b981; }
.inject-msg.err { color: #ef4444; }

.timeline-track {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 2px 8px;
}
.evt-chip {
  flex: 0 0 180px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid #2a2a33;
  border-left: 3px solid #64748b;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.evt-chip.heat_spike { border-left-color: #ef4444; }
.evt-chip.sentiment_shift { border-left-color: #f59e0b; }
.evt-chip.trust_drop { border-left-color: #f97316; }
.evt-chip.polarization_surge { border-left-color: #a855f7; }
.evt-chip.official_response { border-left-color: #10b981; }
.evt-chip.stabilization { border-left-color: #22c55e; }
.evt-chip.sev-high { box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.3); }

.evt-round {
  font-size: 10px;
  color: #94a3b8;
  font-weight: 700;
  letter-spacing: 0.05em;
}
.evt-type {
  font-size: 13px;
  font-weight: 600;
  color: #e5e7eb;
}
.evt-desc {
  font-size: 11px;
  color: #cbd5e1;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-hint {
  color: #64748b;
  font-size: 13px;
  font-style: italic;
  padding: 16px 0;
  text-align: center;
}
</style>
