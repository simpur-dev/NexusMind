<template>
  <div class="incident-workspace">
    <!-- ========== 顶栏 ========== -->
    <header class="ws-header">
      <div class="ws-header-left">
        <button class="ws-back-btn" @click="goHome" title="返回首页">
          <span class="back-icon">&larr;</span>
        </button>
        <div class="ws-brand">
          <span class="ws-brand-name">NexusMind</span>
          <span class="ws-mode-badge">事件工作台</span>
        </div>
      </div>
      <div class="ws-header-center">
        <h1 class="ws-project-title">{{ projectName || '加载中...' }}</h1>
        <span class="ws-baseline-tag" v-if="currentBaselineId">基线 {{ currentBaselineId.slice(-6) }}</span>
      </div>
      <div class="ws-header-right">
        <button class="ws-action-btn ws-secondary" @click="showExportReport = true">导出报告</button>
        <button class="ws-action-btn ws-primary" @click="onAppendMaterial">追加材料</button>
      </div>
    </header>

    <!-- ========== 三栏主体 ========== -->
    <main class="ws-body">
      <!-- 左栏：材料 & 基线 -->
      <section class="ws-panel ws-panel-left">
        <div class="panel-section">
          <h2 class="panel-title">材料时间线</h2>
          <div v-if="isBootstrapping" class="panel-empty">正在导入项目数据并分析...</div>
          <div v-else-if="materials.length === 0" class="panel-empty">尚未追加材料</div>
          <ul class="material-list" v-else>
            <li v-for="m in materials" :key="m.material_id" class="material-item"
                :class="{ active: selectedMaterialId === m.material_id }"
                @click="selectedMaterialId = m.material_id">
              <span class="material-type-badge">{{ m.source_type }}</span>
              <span class="material-name">{{ m.title || m.saved_filename || m.material_id.slice(-8) }}</span>
              <span class="material-time">{{ formatTime(m.ingested_at) }}</span>
            </li>
          </ul>
        </div>

        <div class="panel-section">
          <h2 class="panel-title">
            基线版本
            <button class="panel-title-action" @click="onRebuildBaseline" :disabled="materials.length === 0 || graphRebuilding">{{ graphRebuilding ? '图谱构建中...' : '重建' }}</button>
          </h2>
          <div v-if="baselines.length === 0" class="panel-empty">暂无基线</div>
          <ul class="baseline-list" v-else>
            <li v-for="(b, idx) in baselines" :key="b.baseline_id" class="baseline-item"
                :class="{ current: b.baseline_id === currentBaselineId }"
                @click="onSwitchBaseline(b)">
              <span class="baseline-version">v{{ idx + 1 }}</span>
              <span class="baseline-stage">{{ b.current_stage || '—' }}</span>
              <span class="baseline-time">{{ formatTime(b.created_at) }}</span>
              <button class="baseline-del-btn" @click.stop="onDeleteBaseline(b.baseline_id)" title="删除">×</button>
            </li>
          </ul>
          <div class="graph-rebuild-bar" v-if="graphRebuilding">
            <div class="graph-rebuild-msg">{{ graphRebuildMsg }}</div>
            <div class="graph-rebuild-track"><div class="graph-rebuild-fill" :style="{ width: graphRebuildProgress + '%' }"></div></div>
          </div>
          <div class="baseline-detail" v-if="activeBaseline">
            <div class="bd-section" v-if="activeBaseline.confirmed_facts?.length">
              <div class="bd-label">已确认事实</div>
              <ul class="bd-list"><li v-for="(f, i) in activeBaseline.confirmed_facts.slice(0, 5)" :key="i">{{ f }}</li></ul>
            </div>
            <div class="bd-section" v-if="activeBaseline.key_actors?.length">
              <div class="bd-label">关键主体</div>
              <div class="bd-tags"><span v-for="a in activeBaseline.key_actors.slice(0, 8)" :key="a" class="bd-tag">{{ a }}</span></div>
            </div>
            <div class="bd-section" v-if="activeBaseline.current_risks?.length">
              <div class="bd-label">当前风险</div>
              <ul class="bd-list bd-risk"><li v-for="(r, i) in activeBaseline.current_risks.slice(0, 3)" :key="i">{{ r }}</li></ul>
            </div>
          </div>
        </div>
      </section>

      <!-- 中栏：态势 & 预测分支 -->
      <section class="ws-panel ws-panel-center">
        <div class="panel-section">
          <h2 class="panel-title">当前态势</h2>
          <div class="state-grid" v-if="worldState">
            <div class="state-card" v-for="(val, key) in worldState" :key="key">
              <div class="state-label">{{ stateVarCN[key] || key }}</div>
              <div class="state-bar-track">
                <div class="state-bar-fill" :style="{ width: (val * 100) + '%', background: stateColor(key, val) }"></div>
              </div>
              <div class="state-value">{{ (val * 100).toFixed(0) }}%</div>
            </div>
          </div>
          <div v-else class="panel-empty">启动预测分支后可查看</div>
        </div>

        <div class="panel-section">
          <h2 class="panel-title">
            预测分支
            <button class="panel-title-action" @click="onCreateRun" :disabled="!currentBaselineId">新建分支</button>
          </h2>
          <div v-if="forecastRuns.length === 0" class="panel-empty">暂无预测分支</div>
          <ul class="run-list" v-else>
            <li v-for="r in forecastRuns" :key="r.run_id" class="run-item"
                :class="{ active: activeRunId === r.run_id }"
                @click="onSelectRun(r.run_id)">
              <span class="run-type-badge" :class="r.branch_type">{{ r.branch_type }}</span>
              <span class="run-label">{{ r.branch_label || r.run_id.slice(-8) }}</span>
              <span class="run-status" :class="r.status">{{ statusCN[r.status] || r.status }}</span>
              <span class="run-actions" v-if="activeRunId === r.run_id" @click.stop>
                <button v-if="r.status === 'created'" class="run-action-btn"
                  @click="onPrepareRun(r.run_id)" :disabled="runActionLoading">
                  {{ runActionLoading ? '准备中...' : '准备' }}
                </button>
                <button v-else-if="r.status === 'preparing'" class="run-action-btn run-view-btn"
                  @click="goToProcess(r, 2)">查看准备进度</button>
                <span v-else-if="['prepared','ready'].includes(r.status)" class="run-start-group">
                  <input type="number" v-model.number="startRounds" min="1" max="100" class="rounds-input" placeholder="轮" />
                  <button class="run-action-btn" @click="onStartRun(r.run_id)" :disabled="runActionLoading">
                    {{ runActionLoading ? '启动中...' : '启动' }}
                  </button>
                </span>
                <button v-if="r.status === 'running'" class="run-action-btn run-view-btn"
                  @click="goToProcess(r, 3)">查看推演</button>
                <button v-if="r.status === 'completed'" class="run-action-btn run-view-btn"
                  @click="goToProcess(r, 3)">查看结果</button>
              </span>
            </li>
          </ul>
        </div>

        <div class="panel-section" v-if="forecastPaths.length">
          <h2 class="panel-title">预测路径</h2>
          <div class="paths-grid">
            <div class="path-card" v-for="p in forecastPaths" :key="p.path_id"
                 :class="{ 'risk-high': p.risk_level === '高', 'risk-mid': p.risk_level === '中', 'risk-low': p.risk_level === '低' }">
              <div class="path-header">
                <span class="path-label">{{ p.label }}</span>
                <span class="path-risk-badge" :class="{ high: p.risk_level === '高', mid: p.risk_level === '中', low: p.risk_level === '低' }">风险{{ p.risk_level }}</span>
              </div>
              <div class="path-desc">{{ p.description }}</div>
              <div class="path-changes" v-if="p.key_changes?.length">
                <span class="path-change-tag" v-for="(c, ci) in p.key_changes" :key="ci">{{ c }}</span>
              </div>
              <div class="path-outcome">{{ p.outcome }}</div>
              <div class="path-prob" v-if="p.probability">可能性：{{ p.probability }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右栏：动作 & 决策 -->
      <section class="ws-panel ws-panel-right">
        <div class="panel-section">
          <h2 class="panel-title">推荐动作</h2>
          <div v-if="recommendedActions.length === 0" class="panel-empty">获取决策简报后显示</div>
          <ul class="action-list" v-else>
            <li v-for="a in recommendedActions" :key="a.action_id" class="action-item">
              <div class="action-rank">#{{ a.recommendation_rank }}</div>
              <div class="action-body">
                <div class="action-title">{{ a.title }}</div>
                <div class="action-why">{{ a.why_now }}</div>
                <div class="action-meta">
                  <span>置信度 {{ (a.confidence * 100).toFixed(0) }}%</span>
                  <span>见效 ~{{ a.estimated_delay_hours }}h</span>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <div class="panel-section" v-if="noActionRisk">
          <h2 class="panel-title">不作为风险</h2>
          <div class="no-action-card" :class="noActionRisk.severity">
            <div class="no-action-score">{{ (noActionRisk.risk_score * 100).toFixed(0) }}%</div>
            <div class="no-action-label">{{ noActionRisk.recommendation }}</div>
            <ul class="no-action-reasons">
              <li v-for="(reason, i) in noActionRisk.reasons" :key="i">{{ reason }}</li>
            </ul>
          </div>
        </div>

        <div class="panel-section" v-if="monitoringSignals.length">
          <h2 class="panel-title">监测信号</h2>
          <ul class="signal-list">
            <li v-for="(s, i) in monitoringSignals" :key="i" class="signal-item" :class="s.priority">
              <span class="signal-priority">{{ s.priority }}</span>
              <span class="signal-text">{{ s.signal }}</span>
            </li>
          </ul>
        </div>

        <div class="panel-section panel-actions-bar">
          <button class="ws-action-btn ws-primary ws-full" @click="onGetDecisionBrief" :disabled="!activeRunId">
            获取决策简报
          </button>
          <button class="ws-action-btn ws-secondary ws-full" @click="onRecalibrate" :disabled="!activeRunId">
            校准 & 重新预测
          </button>
        </div>
      </section>
    </main>

    <!-- ========== 导出报告对话框（简单占位） ========== -->
    <div class="modal-overlay" v-if="showExportReport" @click.self="showExportReport = false">
      <div class="modal-box">
        <h3>导出完整报告</h3>
        <p>此功能将调用 ReportAgent 生成完整分析报告，适用于对外汇报/比赛展示。</p>
        <p class="modal-hint">提示：日常工作请优先使用右栏的「决策简报」。</p>
        <div class="modal-actions">
          <button class="ws-action-btn ws-secondary" @click="showExportReport = false">取消</button>
          <button class="ws-action-btn ws-primary" @click="goToReport">前往报告生成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { listMaterials, listBaselines, rebuildBaseline, appendMaterialFiles, deleteBaseline } from '../api/incident'
import { createForecastRun, getForecastRunStatus, getDecisionBrief, prepareForecastRun, startForecastRun } from '../api/forecast'

const router = useRouter()
const route = useRoute()
const projectId = computed(() => route.params.projectId)

// ── 状态 ──
const projectName = ref('')
const materials = ref([])
const baselines = ref([])
const currentBaselineId = ref('')
const forecastRuns = ref([])
const activeRunId = ref('')
const selectedMaterialId = ref('')
const worldState = ref(null)
const recommendedActions = ref([])
const noActionRisk = ref(null)
const monitoringSignals = ref([])
const forecastPaths = ref([])
const showExportReport = ref(false)
const projectHasText = ref(false)
const isBootstrapping = ref(false)
const runActionLoading = ref(false)
const activeBaseline = ref(null)

const stateVarCN = {
  attention_level: '关注度',
  panic_level: '恐慌度',
  trust_level: '信任度',
  polarization_level: '极化度',
  risk_level: '风险等级',
  stability_level: '稳定性',
}

const statusCN = {
  created: '已创建',
  preparing: '准备中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  superseded: '已替代',
}

// ── 初始化 ──
onMounted(async () => {
  await loadProjectInfo()
  await Promise.all([loadMaterials(), loadBaselines(), loadForecastRuns()])
  // 自动引导：若项目已有文本但工作台无材料，自动导入
  if (materials.value.length === 0 && projectHasText.value) {
    await autoImportProjectText()
  }
})

async function loadProjectInfo() {
  try {
    const { getProjectOverview } = await import('../api/incident')
    const res = await getProjectOverview(projectId.value)
    if (res?.success) {
      const d = res.data
      projectName.value = (d.project?.name && d.project.name !== 'Unnamed Project' ? d.project.name : null)
        || d.project?.simulation_requirement?.slice(0, 40) || projectId.value
      currentBaselineId.value = d.current_baseline?.baseline_id || ''
      activeRunId.value = d.active_run_id || ''
      projectHasText.value = (d.project?.total_text_length || 0) > 0
    }
  } catch (e) {
    console.warn('loadProjectInfo', e)
    projectName.value = projectId.value
  }
}

async function loadMaterials() {
  try {
    const res = await listMaterials(projectId.value)
    if (res?.success) materials.value = res.data?.materials || []
  } catch (e) { console.warn('loadMaterials', e) }
}

async function loadBaselines() {
  try {
    const res = await listBaselines(projectId.value)
    if (res?.success) {
      baselines.value = res.data?.baselines || []
      // 设置当前活跃基线详情
      if (baselines.value.length > 0) {
        const target = baselines.value.find(b => b.baseline_id === currentBaselineId.value)
        activeBaseline.value = target || baselines.value[baselines.value.length - 1]
        if (!currentBaselineId.value && activeBaseline.value) {
          currentBaselineId.value = activeBaseline.value.baseline_id
        }
      }
    }
  } catch (e) { console.warn('loadBaselines', e) }
}

async function loadForecastRuns() {
  try {
    const { listForecastRuns } = await import('../api/incident')
    const res = await listForecastRuns(projectId.value)
    if (res?.success) forecastRuns.value = res.data?.runs || []
  } catch (e) { console.warn('loadForecastRuns', e) }
}

// ── 自动引导 ──
async function autoImportProjectText() {
  isBootstrapping.value = true
  try {
    const { autoBootstrapMaterials } = await import('../api/incident')
    const res = await autoBootstrapMaterials(projectId.value)
    if (res?.success) {
      await loadMaterials()
      // 自动重建基线
      await onRebuildBaseline()
    }
  } catch (e) {
    console.warn('autoImportProjectText', e)
  } finally {
    isBootstrapping.value = false
  }
}

// ── 操作 ──
function onAppendMaterial() {
  // 触发文件选择（简易实现）
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.pdf,.md,.txt'
  input.onchange = async (e) => {
    const files = e.target.files
    if (!files.length) return
    const formData = new FormData()
    for (const f of files) formData.append('files', f)
    try {
      await appendMaterialFiles(projectId.value, formData)
      await loadMaterials()
    } catch (err) { console.error('appendMaterials', err) }
  }
  input.click()
}

const graphRebuilding = ref(false)
const graphRebuildProgress = ref(0)
const graphRebuildMsg = ref('')

async function onRebuildBaseline() {
  try {
    const materialIds = materials.value.map(m => m.material_id)
    const res = await rebuildBaseline(projectId.value, { material_ids: materialIds })
    if (res?.success && res.data?.baseline_id) {
      currentBaselineId.value = res.data.baseline_id
    }
    await loadBaselines()
    await loadProjectInfo()

    // 如果后端返回了图谱重建任务 ID，开始轮询进度
    const taskId = res?.data?.graph_task_id
    if (taskId) {
      graphRebuilding.value = true
      graphRebuildProgress.value = 0
      graphRebuildMsg.value = '正在重建图谱...'
      const { getTaskStatus } = await import('../api/graph')
      const poll = setInterval(async () => {
        try {
          const tr = await getTaskStatus(taskId)
          if (tr?.success) {
            graphRebuildProgress.value = tr.data?.progress || 0
            graphRebuildMsg.value = tr.data?.message || '构建中...'
            if (tr.data?.status === 'completed' || tr.data?.status === 'failed') {
              clearInterval(poll)
              graphRebuilding.value = false
              await loadProjectInfo()
            }
          }
        } catch { /* ignore */ }
      }, 3000)
    }
  } catch (e) { console.error('rebuildBaseline', e) }
}

async function onDeleteBaseline(baselineId) {
  if (!confirm('确定删除此基线版本？')) return
  try {
    const res = await deleteBaseline(projectId.value, baselineId)
    if (res?.success) {
      await loadBaselines()
      await loadProjectInfo()
    }
  } catch (e) { console.error('deleteBaseline', e) }
}

async function onCreateRun() {
  try {
    const res = await createForecastRun({
      project_id: projectId.value,
      baseline_id: currentBaselineId.value,
      branch_type: 'base',
      branch_label: `预测 v${forecastRuns.value.length + 1}`,
    })
    if (res?.success) {
      activeRunId.value = res.data?.run?.run_id || activeRunId.value
      await loadForecastRuns()
    }
  } catch (e) { console.error('createRun', e) }
}

function onSelectRun(runId) {
  activeRunId.value = runId
}

async function onPrepareRun(runId) {
  runActionLoading.value = true
  try {
    const res = await prepareForecastRun(runId)
    if (res?.success) {
      await loadForecastRuns() // 立刻刷新，让 UI 显示"准备中..."
      // 轮询状态直到准备完成
      await pollRunStatus(runId, ['preparing'], 300)
    }
    await loadForecastRuns()
  } catch (e) { console.error('prepareRun', e) }
  finally { runActionLoading.value = false }
}

const startRounds = ref(10)

async function onStartRun(runId) {
  runActionLoading.value = true
  try {
    const rounds = startRounds.value || 10
    const res = await startForecastRun(runId, { max_rounds: rounds, enable_graph_memory_update: false })
    if (res?.success) {
      await loadForecastRuns()
      pollRunStatus(runId, ['running'], 1800)
        .then(() => loadForecastRuns())
        .catch(() => {})
    }
  } catch (e) { console.error('startRun', e) }
  finally { runActionLoading.value = false }
}

async function pollRunStatus(runId, waitStatuses, maxSec = 120) {
  const start = Date.now()
  while ((Date.now() - start) / 1000 < maxSec) {
    await new Promise(r => setTimeout(r, 3000))
    try {
      const res = await getForecastRunStatus(runId)
      const status = res?.data?.run?.status
      if (!waitStatuses.includes(status)) return status
    } catch { break }
  }
}

function onSwitchBaseline(b) {
  currentBaselineId.value = b.baseline_id
  activeBaseline.value = b
  // 如果已有决策简报，切换基线后自动刷新
  if (recommendedActions.value.length > 0 && activeRunId.value) {
    onGetDecisionBrief()
  }
}

async function onGetDecisionBrief() {
  if (!activeRunId.value) return
  const activeRun = forecastRuns.value.find(r => r.run_id === activeRunId.value)
  if (activeRun && !['running', 'completed'].includes(activeRun.status)) {
    alert(`当前分支状态为"${statusCN[activeRun.status] || activeRun.status}"，需先完成"准备→启动"流程后才能获取决策简报。`)
    return
  }
  try {
    const params = {}
    if (currentBaselineId.value) params.baseline_id = currentBaselineId.value
    const res = await getDecisionBrief(activeRunId.value, params)
    if (res?.success) {
      const d = res.data
      recommendedActions.value = d.recommended_actions || []
      noActionRisk.value = d.no_action_risk || null
      monitoringSignals.value = d.monitoring_signals || []
      forecastPaths.value = d.forecast_paths || []
      // 从 diagnosis 中提取世界状态
      if (d.current_diagnosis?.current_state) {
        worldState.value = d.current_diagnosis.current_state
      }
    }
  } catch (e) { console.error('getDecisionBrief', e) }
}

async function onRecalibrate() {
  // 简易实现：用最新基线校准
  if (!activeRunId.value || !currentBaselineId.value) return
  try {
    const { recalibrateForecastRun } = await import('../api/forecast')
    const res = await recalibrateForecastRun(activeRunId.value, {
      new_baseline_id: currentBaselineId.value,
    })
    if (res?.success) {
      activeRunId.value = res.data?.new_run?.run_id || activeRunId.value
      await loadForecastRuns()
    }
  } catch (e) { console.error('recalibrate', e) }
}

function goToProcess(run, step) {
  // 跳转到主链路可视化页面，带上 step 和 simulation_id
  router.push({
    path: `/process/${projectId.value}`,
    query: { step: String(step), sim: run.simulation_id || '' }
  })
}
function goHome() { router.push('/') }
function goToReport() {
  showExportReport.value = false
  // 找到当前 active run 的 simulation_id，跳转到 Step 4（报告生成）
  const run = forecastRuns.value.find(r => r.run_id === activeRunId.value)
  const simId = run?.simulation_id
  const blId = currentBaselineId.value
  let url = `/process/${projectId.value}?step=4`
  if (simId) url += `&sim=${simId}`
  if (blId) url += `&baseline_id=${blId}`
  router.push(url)
}

// ── 工具 ──
function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

function stateColor(key, val) {
  // 红色系变量（越高越危险）
  if (['panic_level', 'polarization_level', 'risk_level', 'attention_level'].includes(key)) {
    return val > 0.6 ? '#ef4444' : val > 0.4 ? '#f59e0b' : '#22c55e'
  }
  // 绿色系变量（越高越好）
  return val > 0.6 ? '#22c55e' : val > 0.4 ? '#f59e0b' : '#ef4444'
}
</script>

<style scoped>
/* ========== 布局 ========== */
.incident-workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1729;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
}

/* Header */
.ws-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: rgba(15, 23, 42, 0.95);
  border-bottom: 1px solid rgba(99, 179, 237, 0.15);
  flex-shrink: 0;
}
.ws-header-left { display: flex; align-items: center; gap: 12px; }
.ws-header-center { display: flex; align-items: center; gap: 12px; }
.ws-header-right { display: flex; align-items: center; gap: 8px; }
.ws-back-btn {
  background: none; border: none; color: #94a3b8; font-size: 18px; cursor: pointer;
  padding: 4px 8px; border-radius: 6px;
}
.ws-back-btn:hover { background: rgba(99, 179, 237, 0.1); color: #e2e8f0; }
.ws-brand-name { font-weight: 700; font-size: 15px; color: #63b3ed; }
.ws-mode-badge {
  background: rgba(99, 179, 237, 0.15); color: #63b3ed; font-size: 11px;
  padding: 2px 8px; border-radius: 4px; margin-left: 6px;
}
.ws-project-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
.ws-baseline-tag {
  font-size: 11px; color: #94a3b8; background: rgba(148, 163, 184, 0.12);
  padding: 2px 8px; border-radius: 4px;
}

/* Action buttons */
.ws-action-btn {
  padding: 6px 16px; border-radius: 6px; font-size: 12px; font-weight: 600;
  border: none; cursor: pointer; transition: all 0.15s;
}
.ws-primary { background: #3b82f6; color: #fff; }
.ws-primary:hover { background: #2563eb; }
.ws-primary:disabled { background: #334155; color: #64748b; cursor: not-allowed; }
.ws-secondary { background: rgba(99, 179, 237, 0.12); color: #63b3ed; }
.ws-secondary:hover { background: rgba(99, 179, 237, 0.2); }
.ws-full { width: 100%; margin-bottom: 8px; }

/* Body */
.ws-body {
  display: flex; flex: 1; overflow: hidden;
  gap: 1px; background: rgba(99, 179, 237, 0.08);
}
.ws-panel {
  overflow-y: auto; padding: 16px; background: #0f1729;
}
.ws-panel-left { width: 280px; flex-shrink: 0; }
.ws-panel-center { flex: 1; }
.ws-panel-right { width: 320px; flex-shrink: 0; }

/* Panel sections */
.panel-section { margin-bottom: 20px; }
.panel-title {
  font-size: 12px; font-weight: 700; color: #94a3b8; text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
}
.panel-title-action {
  font-size: 11px; background: rgba(59, 130, 246, 0.15); color: #60a5fa;
  border: none; padding: 2px 10px; border-radius: 4px; cursor: pointer;
}
.panel-title-action:disabled { opacity: 0.4; cursor: not-allowed; }
.panel-empty { color: #475569; font-size: 12px; padding: 12px 0; }

/* Materials list */
.material-list { list-style: none; padding: 0; }
.material-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  border-radius: 6px; cursor: pointer; font-size: 12px; margin-bottom: 2px;
  transition: background 0.12s;
}
.material-item:hover { background: rgba(99, 179, 237, 0.08); }
.material-item.active { background: rgba(59, 130, 246, 0.15); }
.material-type-badge {
  font-size: 10px; background: rgba(99, 179, 237, 0.12); color: #63b3ed;
  padding: 1px 6px; border-radius: 3px; flex-shrink: 0;
}
.material-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #cbd5e1; }
.material-time { font-size: 10px; color: #475569; flex-shrink: 0; }

/* Baseline list */
.baseline-list { list-style: none; padding: 0; }
.baseline-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  font-size: 12px; border-radius: 6px; margin-bottom: 2px; cursor: pointer;
}
.baseline-item:hover { background: rgba(255, 255, 255, 0.03); }
.baseline-item.current { background: rgba(34, 197, 94, 0.1); }
.baseline-version { font-weight: 700; color: #22c55e; min-width: 32px; }
.baseline-stage { color: #94a3b8; flex: 1; }
.baseline-time { font-size: 10px; color: #475569; }
.baseline-del-btn {
  background: none; border: none; color: #64748b; font-size: 14px; cursor: pointer;
  padding: 0 4px; line-height: 1; opacity: 0; transition: opacity 0.15s;
}
.baseline-item:hover .baseline-del-btn { opacity: 1; }
.baseline-del-btn:hover { color: #ef4444; }

/* Graph rebuild progress */
.graph-rebuild-bar { margin: 8px 0; padding: 6px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.08); }
.graph-rebuild-msg { font-size: 10px; color: #60a5fa; margin-bottom: 4px; }
.graph-rebuild-track { height: 3px; border-radius: 2px; background: rgba(59, 130, 246, 0.15); overflow: hidden; }
.graph-rebuild-fill { height: 100%; border-radius: 2px; background: #60a5fa; transition: width 0.5s ease; }

/* Baseline detail */
.baseline-detail { margin-top: 8px; padding: 8px; border-radius: 6px; background: rgba(99, 179, 237, 0.04); }
.bd-section { margin-bottom: 8px; }
.bd-section:last-child { margin-bottom: 0; }
.bd-label { font-size: 10px; font-weight: 700; color: #64748b; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.bd-list { list-style: none; padding: 0; margin: 0; }
.bd-list li { font-size: 11px; color: #94a3b8; padding: 2px 0; line-height: 1.4; border-bottom: 1px solid rgba(99, 179, 237, 0.05); }
.bd-list.bd-risk li { color: #f59e0b; }
.bd-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.bd-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 3px;
  background: rgba(99, 179, 237, 0.1); color: #63b3ed;
}

/* State grid */
.state-grid { display: flex; flex-direction: column; gap: 8px; }
.state-card { display: flex; align-items: center; gap: 10px; }
.state-label { width: 64px; font-size: 11px; color: #94a3b8; text-align: right; }
.state-bar-track {
  flex: 1; height: 8px; background: rgba(99, 179, 237, 0.08); border-radius: 4px; overflow: hidden;
}
.state-bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s, background 0.4s; }
.state-value { width: 36px; font-size: 11px; color: #cbd5e1; text-align: right; }

/* Run list */
.run-list { list-style: none; padding: 0; }
.run-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px;
  border-radius: 6px; cursor: pointer; font-size: 12px; margin-bottom: 2px;
  transition: background 0.12s;
}
.run-item:hover { background: rgba(99, 179, 237, 0.08); }
.run-item.active { background: rgba(59, 130, 246, 0.15); }
.run-type-badge {
  font-size: 10px; padding: 1px 6px; border-radius: 3px; flex-shrink: 0;
  background: rgba(99, 179, 237, 0.12); color: #63b3ed;
}
.run-type-badge.intervention_a { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.run-type-badge.recalibrated { background: rgba(139, 92, 246, 0.15); color: #a78bfa; }
.run-label { flex: 1; color: #cbd5e1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.run-actions { flex-shrink: 0; }
.run-action-btn {
  font-size: 10px; padding: 1px 8px; border-radius: 3px; border: none; cursor: pointer;
  background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-weight: 600;
}
.run-action-btn:hover:not(:disabled) { background: rgba(59, 130, 246, 0.35); }
.run-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.run-view-btn { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.run-view-btn:hover { background: rgba(34, 197, 94, 0.35); }
.run-start-group { display: inline-flex; align-items: center; gap: 4px; }
.rounds-input {
  width: 42px; height: 20px; padding: 0 4px; font-size: 10px; text-align: center;
  border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 3px;
  background: rgba(59, 130, 246, 0.08); color: #60a5fa; outline: none;
}
.rounds-input:focus { border-color: rgba(59, 130, 246, 0.6); }
.rounds-input::-webkit-inner-spin-button { -webkit-appearance: none; }
.run-status { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.run-status.running { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.run-status.completed { background: rgba(99, 179, 237, 0.12); color: #63b3ed; }
.run-status.failed { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.run-status.superseded { background: rgba(148, 163, 184, 0.1); color: #64748b; }

/* Paths grid */
.paths-grid { display: flex; gap: 8px; }
.path-card {
  flex: 1; padding: 10px; border-radius: 8px; font-size: 11px;
  background: rgba(99, 179, 237, 0.06); border: 1px solid rgba(99, 179, 237, 0.1);
  display: flex; flex-direction: column; gap: 5px;
}
.path-card.risk-high { border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.04); }
.path-card.risk-mid { border-color: rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.04); }
.path-card.risk-low { border-color: rgba(34, 197, 94, 0.3); background: rgba(34, 197, 94, 0.04); }
.path-header { display: flex; justify-content: space-between; align-items: center; }
.path-label { font-weight: 700; color: #e2e8f0; }
.path-risk-badge { font-size: 9px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.path-risk-badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.path-risk-badge.mid { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.path-risk-badge.low { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.path-desc { color: #94a3b8; line-height: 1.4; }
.path-changes { display: flex; flex-wrap: wrap; gap: 3px; }
.path-change-tag { font-size: 9px; padding: 1px 5px; border-radius: 3px; background: rgba(99, 179, 237, 0.1); color: #63b3ed; }
.path-outcome { color: #cbd5e1; font-size: 10px; line-height: 1.4; border-top: 1px solid rgba(99, 179, 237, 0.08); padding-top: 4px; }
.path-prob { font-size: 9px; color: #64748b; }

/* Action list */
.action-list { list-style: none; padding: 0; }
.action-item {
  display: flex; gap: 10px; padding: 10px; border-radius: 8px; margin-bottom: 6px;
  background: rgba(99, 179, 237, 0.04); border: 1px solid rgba(99, 179, 237, 0.08);
}
.action-rank {
  font-size: 18px; font-weight: 800; color: #3b82f6; min-width: 28px; text-align: center;
}
.action-body { flex: 1; }
.action-title { font-size: 13px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.action-why { font-size: 11px; color: #94a3b8; line-height: 1.5; margin-bottom: 6px; }
.action-meta { display: flex; gap: 12px; font-size: 10px; color: #64748b; }

/* No-action risk */
.no-action-card {
  padding: 12px; border-radius: 8px; border: 1px solid rgba(148, 163, 184, 0.15);
  background: rgba(99, 179, 237, 0.04);
}
.no-action-card.high { border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.06); }
.no-action-card.medium { border-color: rgba(245, 158, 11, 0.3); background: rgba(245, 158, 11, 0.06); }
.no-action-score { font-size: 24px; font-weight: 800; color: #f1f5f9; }
.no-action-label { font-size: 12px; color: #94a3b8; margin-bottom: 8px; }
.no-action-reasons { list-style: disc; padding-left: 16px; font-size: 11px; color: #94a3b8; }
.no-action-reasons li { margin-bottom: 4px; }

/* Signal list */
.signal-list { list-style: none; padding: 0; }
.signal-item {
  display: flex; gap: 8px; align-items: center; padding: 6px 0; font-size: 11px;
  border-bottom: 1px solid rgba(99, 179, 237, 0.06);
}
.signal-priority {
  font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 1px 6px;
  border-radius: 3px;
}
.signal-priority { background: rgba(148, 163, 184, 0.12); color: #94a3b8; }
.signal-item.high .signal-priority { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.signal-text { color: #cbd5e1; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: #1e293b; border-radius: 12px; padding: 24px; max-width: 420px; width: 90%;
  border: 1px solid rgba(99, 179, 237, 0.15);
}
.modal-box h3 { font-size: 16px; color: #f1f5f9; margin-bottom: 12px; }
.modal-box p { font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 8px; }
.modal-hint { font-size: 11px; color: #64748b; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
</style>
