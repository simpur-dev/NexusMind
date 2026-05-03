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
        <div
          v-for="item in indicatorItems"
          :key="item.key"
          class="radial-indicator"
          @mouseenter="hoveredKey = item.key"
          @mouseleave="hoveredKey = null"
        >
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
          <div class="ind-label">
            {{ item.label }}
            <span class="info-mark" :style="{ borderColor: item.color, color: item.color }">i</span>
          </div>

          <!-- Hover 卡片：说明该指标的含义、信号源、计算规则、当前值解读 -->
          <div v-if="hoveredKey === item.key" class="info-card" :style="{ borderColor: item.color }">
            <div class="info-head">
              <span class="info-dot" :style="{ background: item.color }"></span>
              <span class="info-name">{{ item.label }}</span>
              <span class="info-value" :style="{ color: item.color }">
                {{ (clamp(item.value) * 100).toFixed(0) }} / 100
              </span>
            </div>
            <div class="info-row">
              <span class="info-tag">含义</span>
              <span class="info-text">{{ item.meta.definition }}</span>
            </div>
            <div class="info-row">
              <span class="info-tag">信号源</span>
              <span class="info-text">{{ item.meta.signal }}</span>
            </div>
            <div class="info-row">
              <span class="info-tag">计算</span>
              <span class="info-text mono">{{ item.meta.formula }}</span>
            </div>
            <div class="info-row reading">
              <span class="info-tag">当前</span>
              <span class="info-text">
                <strong :style="{ color: item.color }">{{ levelText(item.value) }}</strong>
                {{ item.meta.reading(item.value) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

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

const hoveredKey = ref(null)

// 与后端 get_state_summary_text() 中的档位保持一致
const levelText = (v) => {
  const x = clamp(v)
  if (x < 0.2) return '很低'
  if (x < 0.4) return '较低'
  if (x < 0.6) return '中等'
  if (x < 0.8) return '较高'
  return '很高'
}

const topKeywords = computed(() => {
  const kws = props.currentState?.top_keywords
  return Array.isArray(kws) ? kws.slice(0, 8) : []
})

// 指标元信息：定义 / 信号源 / 规则 / 当前读法
// 公式仅取后端 _compute_state_by_rules() 的核心项，便于评委一眼看懂
const META = {
  attention: {
    definition: '本轮舆论活跃度。不是互联网 PV，是 Agent 集体的发言热度。',
    signal: '本轮 Agent 发帖数 + 评论数 + 转发数，除以近几轮的滑动平均基线',
    formula: 'attention ≈ (发帖+评论+转发) / 基线 × 0.4',
    reading: (v) => clamp(v) >= 0.6 ? '，舆论正在快速发酵。' : (clamp(v) >= 0.3 ? '，舆论有较多讨论。' : '，舆论热度偏平静。')
  },
  panic: {
    definition: '负面情绪与恐慌在群体中的蔓延程度。',
    signal: '评论/帖文中负面关键词占比 + 负面内容被高频转发的加速信号',
    formula: 'panic ≈ 负面占比 × 0.8 + 转发加速项  低信任会进一步放大它',
    reading: (v) => clamp(v) >= 0.6 ? '，负面情绪明显占主导。' : (clamp(v) >= 0.3 ? '，部分人群出现不满/担忧。' : '，恐慌面处于可控状态。')
  },
  trust: {
    definition: '公众对官方/权威信息源的信任程度。初始偏高（0.6）。',
    signal: '正面情感占比 + “官方/公告/官宣”类权威关键词出现次数，减去负面侵蚀',
    formula: 'trust ≈ 0.2 + 正面×0.4 + 权威加分 − 负面×0.3',
    reading: (v) => clamp(v) >= 0.5 ? '，公众仍愿意听官方说话。' : (clamp(v) >= 0.3 ? '，信任动摇，需及时干预。' : '，信任几乎崩塌，官方表达难有效果。')
  },
  polarization: {
    definition: '群体内部对立意见的并存程度。一边倒不叫极化，双方都强才叫极化。',
    signal: '本轮正面声量与负面声量的较弱一方：min(pos, neg)。两者同时接近 0.5 时最高。',
    formula: 'polarization ≈ min(正面占比, 负面占比) × 2 × 0.8，高关注会加速扩散',
    reading: (v) => clamp(v) >= 0.5 ? '，两派对峙已明显。' : (clamp(v) >= 0.3 ? '，出现双方讨论但不极端。' : '，舆论偏向较一致。')
  },
  risk: {
    definition: '综合风险指数，代表本轮舆情外溢/升级成危机的概率。',
    signal: '由关注度、恐慌、低信任、极化联合加权。基线风险数量也有下限贡献。',
    formula: 'risk ≈ attention×0.25 + panic×0.35 + (1−trust)×0.25 + polar×0.15',
    reading: (v) => clamp(v) >= 0.6 ? '，需要高优先级干预。' : (clamp(v) >= 0.4 ? '，需谨慎监控。' : '，可保持观察状态。')
  },
  stability: {
    definition: '上一轮到本轮的全局变化是否温和。变化剧烈→不稳定。',
    signal: '只统计“恶化方向”的逐轮变化平均值，恐慌下降/信任上升等正向变化不拉低它',
    formula: 'stability ≈ 1 − 恶化变化×3 + 改善变化×1.5',
    reading: (v) => clamp(v) >= 0.6 ? '，状态平稳。' : (clamp(v) >= 0.4 ? '，变化较快，需关注。' : '，正在发生剧烈动荡。')
  }
}

const indicatorItems = computed(() => {
  if (!props.currentState) return []
  const s = props.currentState
  return [
    { key: 'attention',    label: '关注度',   value: s.attention_level,    color: '#3b82f6', meta: META.attention },
    { key: 'panic',        label: '恐慌',     value: s.panic_level,        color: '#ef4444', meta: META.panic },
    { key: 'trust',        label: '信任',     value: s.trust_level,        color: '#10b981', meta: META.trust },
    { key: 'polarization', label: '极化',     value: s.polarization_level, color: '#f59e0b', meta: META.polarization },
    { key: 'risk',         label: '风险',     value: s.risk_level,         color: '#f97316', meta: META.risk },
    { key: 'stability',    label: '稳定性',   value: s.stability_level,    color: '#8b5cf6', meta: META.stability }
  ]
})
</script>

<style scoped>
.ws-hero {
  background: linear-gradient(180deg, rgba(59,130,246,0.12) 0%, rgba(30,41,59,0.85) 100%),
              linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #1e293b 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
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
  position: relative; /* anchor for hover info-card */
  cursor: help;
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
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.info-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid currentColor;
  font-size: 9px;
  font-weight: 800;
  font-family: ui-serif, Georgia, serif;
  font-style: italic;
  line-height: 1;
  opacity: 0.65;
  transition: opacity 0.15s;
}
.radial-indicator:hover .info-mark { opacity: 1; }

/* ====== Hover info card ====== */
.info-card {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  max-width: 88vw;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-left-width: 3px;
  border-radius: 8px;
  padding: 10px 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
  z-index: 50;
  font-size: 12px;
  line-height: 1.5;
  color: #e2e8f0;
  text-align: left;
  pointer-events: none; /* never block underlying interactions */
  text-transform: none;
  letter-spacing: normal;
}
.info-card::before {
  content: '';
  position: absolute;
  top: -5px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 9px;
  height: 9px;
  background: rgba(15, 23, 42, 0.98);
  border-left: 1px solid rgba(148, 163, 184, 0.3);
  border-top: 1px solid rgba(148, 163, 184, 0.3);
}
.info-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.18);
}
.info-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.info-name {
  font-size: 13px;
  font-weight: 700;
  color: #f1f5f9;
  flex: 1;
}
.info-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-weight: 800;
}
.info-row {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 8px;
  align-items: baseline;
  margin-top: 4px;
}
.info-tag {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: none;
  letter-spacing: 0.04em;
  padding-top: 1px;
}
.info-text {
  color: #cbd5e1;
  font-size: 11.5px;
  line-height: 1.5;
}
.info-text.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  color: #e2e8f0;
  background: rgba(148, 163, 184, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}
.info-row.reading { margin-top: 6px; }

@media (max-width: 900px) {
  .indicators-row { grid-template-columns: repeat(3, 1fr); }
}
</style>
