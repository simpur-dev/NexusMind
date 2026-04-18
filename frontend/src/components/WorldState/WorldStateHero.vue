<template>
  <div class="ws-hero" :class="{ 'is-empty': !currentState }">
    <div v-if="!currentState" class="empty-state">
      <div class="spinner"></div>
      <span>等待世界模型数据…</span>
    </div>
    <template v-else>
      <!-- Header -->
      <div class="hero-header">
        <h2 class="hero-title">
          <span class="hero-icon">🌍</span>
          <span>全局世界状态</span>
        </h2>
        <span class="round-pill">第 {{ currentState.round_num }} 轮</span>
      </div>

      <!-- Narrative summary (hero) -->
      <p class="hero-summary">
        {{ stateSummary || '系统当前保持稳定。' }}
      </p>

      <!-- Keywords -->
      <div v-if="topKeywords.length" class="hero-keywords">
        <span v-for="(kw, idx) in topKeywords" :key="idx" class="keyword-chip">{{ kw }}</span>
      </div>

      <!-- 6 radial indicators -->
      <div class="indicators-row">
        <div v-for="item in indicatorItems" :key="item.key" class="radial-indicator">
          <svg :viewBox="`0 0 ${ringSize} ${ringSize}`" class="ring-svg">
            <circle
              :cx="ringCenter" :cy="ringCenter" :r="ringRadius"
              fill="none" stroke="rgba(255,255,255,0.08)" :stroke-width="ringWidth"
            />
            <circle
              :cx="ringCenter" :cy="ringCenter" :r="ringRadius"
              fill="none" :stroke="item.color" :stroke-width="ringWidth"
              :stroke-dasharray="ringCircumference"
              :stroke-dashoffset="ringCircumference * (1 - clamp(item.value))"
              stroke-linecap="round"
              :transform="`rotate(-90 ${ringCenter} ${ringCenter})`"
              class="ring-progress"
            />
            <text
              :x="ringCenter" :y="ringCenter + 4"
              text-anchor="middle"
              class="ring-label"
              :fill="item.color"
            >
              {{ (clamp(item.value) * 100).toFixed(0) }}
            </text>
          </svg>
          <div class="ind-label">{{ item.label }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentState: Object,
  stateSummary: String
})

const ringSize = 64
const ringCenter = ringSize / 2
const ringWidth = 6
const ringRadius = ringCenter - ringWidth
const ringCircumference = 2 * Math.PI * ringRadius

const clamp = (v) => Math.max(0, Math.min(1, Number(v) || 0))

const topKeywords = computed(() => {
  const kws = props.currentState?.top_keywords
  return Array.isArray(kws) ? kws.slice(0, 8) : []
})

const indicatorItems = computed(() => {
  if (!props.currentState) return []
  const s = props.currentState
  return [
    { key: 'attention',    label: '关注度',   value: s.attention_level,    color: '#3b82f6' },
    { key: 'panic',        label: '恐慌',     value: s.panic_level,        color: '#ef4444' },
    { key: 'trust',        label: '信任',     value: s.trust_level,        color: '#10b981' },
    { key: 'polarization', label: '极化',     value: s.polarization_level, color: '#f59e0b' },
    { key: 'risk',         label: '风险',     value: s.risk_level,         color: '#f97316' },
    { key: 'stability',    label: '稳定性',   value: s.stability_level,    color: '#8b5cf6' }
  ]
})
</script>

<style scoped>
.ws-hero {
  background: linear-gradient(180deg, rgba(59,130,246,0.08), rgba(0,0,0,0) 60%), #0f0f14;
  border: 1px solid #2a2a33;
  border-radius: 12px;
  padding: 20px 24px;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ws-hero.is-empty {
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 13px;
}

.spinner {
  width: 22px;
  height: 22px;
  border: 2px solid #2a2a33;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.hero-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hero-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.02em;
}
.hero-icon { font-size: 18px; }
.round-pill {
  background: #3b82f6;
  color: #fff;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.hero-summary {
  margin: 0;
  font-size: 15px;
  line-height: 1.55;
  color: #f1f5f9;
  font-weight: 500;
}

.hero-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.keyword-chip {
  background: rgba(59, 130, 246, 0.12);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.indicators-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-top: 6px;
}

.radial-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.ring-svg {
  width: 64px;
  height: 64px;
}
.ring-progress {
  transition: stroke-dashoffset 0.6s ease-out;
}
.ring-label {
  font-size: 16px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.ind-label {
  font-size: 11px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

@media (max-width: 900px) {
  .indicators-row { grid-template-columns: repeat(3, 1fr); }
}
</style>
