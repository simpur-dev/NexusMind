<template>
  <div 
    class="history-database"
    :class="{ 'no-projects': projects.length === 0 && !loading }"
    ref="historyContainer"
  >
    <!-- 背景装饰：技术网格线（只在有项目时显示） -->
    <div v-if="projects.length > 0 || loading" class="tech-grid-bg">
      <div class="grid-pattern"></div>
      <div class="gradient-overlay"></div>
    </div>

    <!-- 标题区域 -->
    <div class="section-header">
      <div class="section-line"></div>
      <span class="section-title">推演记录</span>
      <div class="section-line"></div>
    </div>

    <!-- 卡片容器（只在有项目时显示） -->
    <div v-if="projects.length > 0" class="cards-container" :class="{ expanded: isExpanded }" :style="containerStyle">
      <div 
        v-for="(project, index) in projects" 
        :key="project.simulation_id"
        class="project-card"
        :class="{ expanded: isExpanded, hovering: hoveringCard === index }"
        :style="getCardStyle(index)"
        @mouseenter="hoveringCard = index"
        @mouseleave="hoveringCard = null"
        @click="navigateToProject(project)"
      >
        <!-- 卡片头部：simulation_id 和 功能可用状态 -->
        <div class="card-header">
          <span class="card-id">{{ formatSimulationId(project.simulation_id) }}</span>
          <div class="card-status-icons">
            <span 
              class="status-icon" 
              :class="{ available: project.project_id, unavailable: !project.project_id }"
              title="事件图谱生成"
            >◇</span>
            <span 
              class="status-icon available" 
              title="群体环境建模"
            >◈</span>
            <span 
              class="status-icon" 
              :class="{ available: project.report_id, unavailable: !project.report_id }"
              title="决策简报与智能研判"
            >◆</span>
            <span
              class="card-delete-btn"
              title="删除此推演记录"
              @click.stop="confirmDelete(project)"
            >×</span>
          </div>
        </div>

        <!-- 文件列表区域 -->
        <div class="card-files-wrapper">
          <!-- 角落装饰 - 取景框风格 -->
          <div class="corner-mark top-left-only"></div>
          
          <!-- 文件列表 -->
          <div class="files-list" v-if="project.files && project.files.length > 0">
            <div 
              v-for="(file, fileIndex) in project.files.slice(0, 3)" 
              :key="fileIndex"
              class="file-item"
            >
              <span class="file-tag" :class="getFileType(file.filename)">{{ getFileTypeLabel(file.filename) }}</span>
              <span class="file-name">{{ truncateFilename(file.filename, 20) }}</span>
            </div>
            <!-- 如果有更多文件，显示提示 -->
            <div v-if="project.files.length > 3" class="files-more">
              +{{ project.files.length - 3 }} 个文件
            </div>
          </div>
          <!-- 无文件时的占位 -->
          <div class="files-empty" v-else>
            <span class="empty-file-icon">◇</span>
            <span class="empty-file-text">暂无文件</span>
          </div>
        </div>

        <!-- 卡片标题（使用模拟需求的前20字作为标题） -->
        <h3 class="card-title">{{ getSimulationTitle(project.simulation_requirement) }}</h3>

        <!-- 卡片描述（模拟需求完整展示） -->
        <p class="card-desc">{{ truncateText(project.simulation_requirement, 55) }}</p>

        <!-- 卡片底部 -->
        <div class="card-footer">
          <div class="card-datetime">
            <span class="card-date">{{ formatDate(project.created_at) }}</span>
            <span class="card-time">{{ formatTime(project.created_at) }}</span>
          </div>
          <span class="card-progress" :class="getProgressClass(project)">
            <span class="status-dot">●</span> {{ formatRounds(project) }}
          </span>
        </div>

        <!-- 快捷入口：事件工作台 -->
        <div v-if="project.project_id" class="card-workspace-link" @click.stop="quickGoWorkspace(project)">
          <span class="workspace-icon">⌁</span> 事件工作台
        </div>
        
        <!-- 底部装饰线 (hover时展开) -->
        <div class="card-bottom-line"></div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <span class="loading-spinner"></span>
      <span class="loading-text">加载中...</span>
    </div>

    <!-- 历史回放详情弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedProject" class="modal-overlay" @click.self="closeModal">
          <div class="modal-content">
            <!-- 弹窗头部 -->
            <div class="modal-header">
              <div class="modal-title-section">
                <span class="modal-id">{{ formatSimulationId(selectedProject.simulation_id) }}</span>
                <span class="modal-progress" :class="getProgressClass(selectedProject)">
                  <span class="status-dot">●</span> {{ formatRounds(selectedProject) }}
                </span>
                <span class="modal-create-time">{{ formatDate(selectedProject.created_at) }} {{ formatTime(selectedProject.created_at) }}</span>
              </div>
              <button class="modal-close" @click="closeModal">×</button>
            </div>

            <!-- 弹窗内容 -->
            <div class="modal-body">
              <!-- 模拟需求 -->
              <div class="modal-section">
                <div class="modal-label">模拟需求</div>
                <div class="modal-requirement">{{ selectedProject.simulation_requirement || '无' }}</div>
              </div>

              <!-- 文件列表 -->
              <div class="modal-section">
                <div class="modal-label">关联文件</div>
                <div class="modal-files" v-if="selectedProject.files && selectedProject.files.length > 0">
                  <div v-for="(file, index) in selectedProject.files" :key="index" class="modal-file-item">
                    <span class="file-tag" :class="getFileType(file.filename)">{{ getFileTypeLabel(file.filename) }}</span>
                    <span class="modal-file-name">{{ file.filename }}</span>
                  </div>
                </div>
                <div class="modal-empty" v-else>暂无关联文件</div>
              </div>
            </div>

            <!-- 推演回放分割线 -->
            <div class="modal-divider">
              <span class="divider-line"></span>
              <span class="divider-text">推演回放</span>
              <span class="divider-line"></span>
            </div>

            <!-- 导航按钮 -->
            <div class="modal-actions">
              <button 
                class="modal-btn btn-project" 
                @click="goToProject"
                :disabled="!selectedProject.project_id"
              >
                <span class="btn-step">Step1</span>
                <span class="btn-icon">◇</span>
                <span class="btn-text">事件图谱生成</span>
              </button>
              <button 
                class="modal-btn btn-simulation" 
                @click="goToSimulation"
              >
                <span class="btn-step">Step2</span>
                <span class="btn-icon">◈</span>
                <span class="btn-text">群体环境建模</span>
              </button>
              <button 
                class="modal-btn btn-step3" 
                @click="goToStep3"
              >
                <span class="btn-step">Step3</span>
                <span class="btn-icon">▶</span>
                <span class="btn-text">舆情态势推演</span>
              </button>
              <button 
                class="modal-btn btn-report" 
                @click="goToReport"
                :disabled="!selectedProject.report_id"
              >
                <span class="btn-step">Step4</span>
                <span class="btn-icon">◆</span>
                <span class="btn-text">决策简报与智能研判</span>
              </button>
              <button 
                class="modal-btn btn-incident" 
                @click="goToIncidentWorkspace"
                :disabled="!selectedProject.project_id"
              >
                <span class="btn-step">OPS</span>
                <span class="btn-icon">⌁</span>
                <span class="btn-text">事件工作台</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onActivated, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getSimulationHistory, deleteSimulation } from '../api/simulation'

const router = useRouter()
const route = useRoute()

const projects = ref([])
const loading = ref(true)
const isExpanded = ref(false)
const hoveringCard = ref(null)
const historyContainer = ref(null)
const selectedProject = ref(null)

const CARD_LAYOUT = Object.freeze({
  perRow: 4,
  width: 280,
  height: 280,
  gap: 24,
  foldedHeight: 420,
  emptyHeight: 280,
  topOffset: 20,
  foldedTop: 25,
  foldedStepX: 35,
  foldedStepY: 8,
  foldedRotate: 3,
  foldedScale: 0.05,
  animationMs: 750,
  expandDelay: 50,
  collapseDelay: 200
})

const CARD_TRANSITION = 'transform 700ms cubic-bezier(0.23, 1, 0.32, 1), opacity 700ms cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.3s ease, border-color 0.3s ease'
const FILE_TYPE_CLASS = Object.freeze({
  pdf: 'pdf',
  doc: 'doc',
  docx: 'doc',
  xls: 'xls',
  xlsx: 'xls',
  csv: 'xls',
  ppt: 'ppt',
  pptx: 'ppt',
  txt: 'txt',
  md: 'txt',
  json: 'code',
  jpg: 'img',
  jpeg: 'img',
  png: 'img',
  gif: 'img',
  zip: 'zip',
  rar: 'zip',
  '7z': 'zip'
})

let observer = null
let isAnimating = false
let expandDebounceTimer = null
let expandReleaseTimer = null
let pendingState = null

const containerStyle = computed(() => {
  if (!isExpanded.value) return { minHeight: `${CARD_LAYOUT.foldedHeight}px` }
  const total = projects.value.length
  if (!total) return { minHeight: `${CARD_LAYOUT.emptyHeight}px` }
  const rows = Math.ceil(total / CARD_LAYOUT.perRow)
  const height = rows * CARD_LAYOUT.height + (rows - 1) * CARD_LAYOUT.gap + 10
  return { minHeight: `${height}px` }
})

const positionedCard = (x, y, rotate, scale, zIndex) => ({
  transform: `translate(${x}px, ${y}px) rotate(${rotate}deg) scale(${scale})`,
  zIndex,
  opacity: 1,
  transition: CARD_TRANSITION
})

const expandedCardStyle = (index, total) => {
  const row = Math.floor(index / CARD_LAYOUT.perRow)
  const rowStart = row * CARD_LAYOUT.perRow
  const rowCards = Math.min(CARD_LAYOUT.perRow, total - rowStart)
  const rowWidth = rowCards * CARD_LAYOUT.width + (rowCards - 1) * CARD_LAYOUT.gap
  const col = index % CARD_LAYOUT.perRow
  const x = -(rowWidth / 2) + (CARD_LAYOUT.width / 2) + col * (CARD_LAYOUT.width + CARD_LAYOUT.gap)
  const y = CARD_LAYOUT.topOffset + row * (CARD_LAYOUT.height + CARD_LAYOUT.gap)
  return positionedCard(x, y, 0, 1, 100 + index)
}

const foldedCardStyle = (index, total) => {
  const offset = index - (total - 1) / 2
  const x = offset * CARD_LAYOUT.foldedStepX
  const y = CARD_LAYOUT.foldedTop + Math.abs(offset) * CARD_LAYOUT.foldedStepY
  const rotate = offset * CARD_LAYOUT.foldedRotate
  const scale = 0.95 - Math.abs(offset) * CARD_LAYOUT.foldedScale
  return positionedCard(x, y, rotate, scale, 10 + index)
}

const getCardStyle = (index) => {
  const total = projects.value.length
  return isExpanded.value ? expandedCardStyle(index, total) : foldedCardStyle(index, total)
}

const getProgressClass = (simulation) => {
  const current = simulation.current_round || 0
  const total = simulation.total_rounds || 0
  if (!total || !current) return 'not-started'
  return current >= total ? 'completed' : 'in-progress'
}

const asDate = (dateStr) => {
  if (!dateStr) return null
  const date = new Date(dateStr)
  return Number.isNaN(date.getTime()) ? null : date
}

const formatDate = (dateStr) => {
  const date = asDate(dateStr)
  return date ? date.toISOString().slice(0, 10) : (dateStr?.slice(0, 10) || '')
}

const formatTime = (dateStr) => {
  const date = asDate(dateStr)
  if (!date) return ''
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const getSimulationTitle = (requirement) => requirement ? truncateText(requirement, 20) : '\u672a\u547d\u540d\u6a21\u62df'

const formatSimulationId = (simulationId) => {
  if (!simulationId) return 'SIM_UNKNOWN'
  return `SIM_${simulationId.replace('sim_', '').slice(0, 6).toUpperCase()}`
}

const formatRounds = (simulation) => {
  const total = simulation.total_rounds || 0
  if (!total) return '\u672a\u5f00\u59cb'
  return `${simulation.current_round || 0}/${total} \u8f6e`
}

const fileExtension = (filename) => filename?.split('.').pop()?.toLowerCase() || ''

const getFileType = (filename) => FILE_TYPE_CLASS[fileExtension(filename)] || 'other'

const getFileTypeLabel = (filename) => fileExtension(filename).toUpperCase() || 'FILE'

const truncateFilename = (filename, maxLength) => {
  if (!filename) return '\u672a\u77e5\u6587\u4ef6'
  if (filename.length <= maxLength) return filename
  const dotIndex = filename.lastIndexOf('.')
  const ext = dotIndex > -1 ? filename.slice(dotIndex) : ''
  const base = dotIndex > -1 ? filename.slice(0, dotIndex) : filename
  return `${base.slice(0, maxLength - ext.length - 3)}...${ext}`
}

const navigateToProject = (simulation) => {
  selectedProject.value = simulation
}

const closeModal = () => {
  selectedProject.value = null
}

const pushRoute = (routeConfig, shouldClose = true) => {
  router.push(routeConfig)
  if (shouldClose) closeModal()
}

const pushProcessStep = (step) => {
  const projectId = selectedProject.value?.project_id
  if (!projectId) return
  pushRoute({ name: 'Process', params: { projectId }, query: { step } })
}

const goToProject = () => pushProcessStep(1)
const goToSimulation = () => pushProcessStep(2)
const goToStep3 = () => pushProcessStep(3)
const goToReport = () => pushProcessStep(4)

const goToIncidentWorkspace = () => {
  const projectId = selectedProject.value?.project_id
  if (!projectId) return
  pushRoute({ name: 'IncidentWorkspace', params: { projectId } })
}

const quickGoWorkspace = (project) => {
  if (!project.project_id) return
  pushRoute({ name: 'IncidentWorkspace', params: { projectId: project.project_id } }, false)
}

const confirmDelete = async (project) => {
  if (!project?.simulation_id) return
  const simLabel = formatSimulationId(project.simulation_id)
  const confirmed = window.confirm(`\u786e\u5b9a\u8981\u5220\u9664\u63a8\u6f14\u8bb0\u5f55 ${simLabel} \u5417\uff1f\n\u6b64\u64cd\u4f5c\u4f1a\u505c\u6b62\u8fd0\u884c\u4e2d\u7684\u8fdb\u7a0b\u5e76\u5220\u9664\u76f8\u5173\u6570\u636e\uff0c\u4e0d\u53ef\u64a4\u9500\u3002`)
  if (!confirmed) return

  try {
    const res = await deleteSimulation(project.simulation_id)
    if (!res.success) {
      alert('\u5220\u9664\u5931\u8d25\uff1a' + (res.error || '\u672a\u77e5\u9519\u8bef'))
      return
    }
    projects.value = projects.value.filter(item => item.simulation_id !== project.simulation_id)
    if (selectedProject.value?.simulation_id === project.simulation_id) closeModal()
  } catch (err) {
    console.error('delete simulation history failed:', err)
    alert('\u5220\u9664\u5931\u8d25\uff1a' + (err.message || '\u7f51\u7edc\u9519\u8bef'))
  }
}

const withTimeout = (promise, ms) => Promise.race([
  promise,
  new Promise((_, reject) => setTimeout(() => reject(new Error('\u52a0\u8f7d\u8d85\u65f6')), ms))
])

const loadHistory = async () => {
  loading.value = true
  try {
    const response = await withTimeout(getSimulationHistory(20), 10000)
    projects.value = response.success ? (response.data || []) : []
  } catch (error) {
    console.error('load simulation history failed:', error)
    projects.value = []
  } finally {
    loading.value = false
  }
}

const clearExpandTimers = () => {
  if (expandDebounceTimer) clearTimeout(expandDebounceTimer)
  if (expandReleaseTimer) clearTimeout(expandReleaseTimer)
  expandDebounceTimer = null
  expandReleaseTimer = null
}

const releaseAnimation = () => {
  isAnimating = false
  if (pendingState !== null && pendingState !== isExpanded.value) {
    expandDebounceTimer = setTimeout(applyPendingState, 100)
  }
}

const applyPendingState = () => {
  if (isAnimating || pendingState === null || pendingState === isExpanded.value) return
  isAnimating = true
  isExpanded.value = pendingState
  pendingState = null
  expandReleaseTimer = setTimeout(releaseAnimation, CARD_LAYOUT.animationMs)
}

const scheduleExpandedState = (nextState) => {
  pendingState = nextState
  if (expandDebounceTimer) clearTimeout(expandDebounceTimer)
  if (nextState === isExpanded.value) {
    pendingState = null
    return
  }
  if (isAnimating) return
  const delay = nextState ? CARD_LAYOUT.expandDelay : CARD_LAYOUT.collapseDelay
  expandDebounceTimer = setTimeout(applyPendingState, delay)
}

const initObserver = () => {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    entries => entries.forEach(entry => scheduleExpandedState(entry.isIntersecting)),
    { threshold: [0.4, 0.6, 0.8], rootMargin: '0px 0px -150px 0px' }
  )
  if (historyContainer.value) observer.observe(historyContainer.value)
}

watch(() => route.path, (newPath) => {
  if (newPath === '/') loadHistory()
})

onMounted(async () => {
  await nextTick()
  await loadHistory()
  setTimeout(initObserver, 100)
})

onActivated(() => {
  loadHistory()
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
  clearExpandTimers()
})
</script>

<style scoped>
/* 容器 */
.history-database {
  position: relative;
  width: 100%;
  min-height: 280px;
  margin-top: 40px;
  padding: 35px 0 40px;
  overflow: visible;
}

/* 无项目时简化显示 */
.history-database.no-projects {
  min-height: auto;
  padding: 40px 0 20px;
}

/* 技术网格背景 */
.tech-grid-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
  pointer-events: none;
}

/* 使用CSS背景图案创建固定间距的正方形网格 */
.grid-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(0, 0, 0, 0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0, 0, 0, 0.05) 1px, transparent 1px);
  background-size: 50px 50px;
  /* 从左上角开始定位，高度变化时只在底部扩展，不影响已有网格位置 */
  background-position: top left;
}

.gradient-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    linear-gradient(to right, rgba(255, 255, 255, 0.9) 0%, transparent 15%, transparent 85%, rgba(255, 255, 255, 0.9) 100%),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.8) 0%, transparent 20%, transparent 80%, rgba(255, 255, 255, 0.8) 100%);
  pointer-events: none;
}

/* 标题区域 */
.section-header {
  position: relative;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-bottom: 24px;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  padding: 0 40px;
}

.section-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #E5E7EB, transparent);
  max-width: 300px;
}

.section-title {
  font-size: 0.8rem;
  font-weight: 500;
  color: #9CA3AF;
  letter-spacing: 3px;
  text-transform: uppercase;
}

/* 卡片容器 */
.cards-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 0 40px;
  transition: min-height 700ms cubic-bezier(0.23, 1, 0.32, 1);
  /* min-height 由 JS 动态计算，根据卡片数量自适应 */
}

/* 项目卡片 */
.project-card {
  position: absolute;
  width: 280px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 0;
  padding: 14px;
  cursor: pointer;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.3s ease, border-color 0.3s ease, transform 700ms cubic-bezier(0.23, 1, 0.32, 1), opacity 700ms cubic-bezier(0.23, 1, 0.32, 1);
}

.project-card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.4);
  z-index: 1000 !important;
}

.project-card.hovering {
  z-index: 1000 !important;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F3F4F6;
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
  font-size: 0.7rem;
}

.card-id {
  color: #6B7280;
  letter-spacing: 0.5px;
  font-weight: 500;
}

/* 功能状态图标组 */
.card-status-icons {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  font-size: 0.75rem;
  transition: all 0.2s ease;
  cursor: default;
}

.status-icon.available {
  opacity: 1;
}

/* 不同功能的颜色 */
.status-icon:nth-child(1).available { color: #3B82F6; } /* 事件图谱生成 - 蓝色 */
.status-icon:nth-child(2).available { color: #F59E0B; } /* 群体环境建模 - 橙色 */
.status-icon:nth-child(3).available { color: #10B981; } /* 决策简报 - 绿色 */

.status-icon.unavailable {
  color: #D1D5DB;
  opacity: 0.5;
}

/* 删除按钮 */
.card-delete-btn {
  font-size: 1rem;
  font-weight: 600;
  color: #D1D5DB;
  cursor: pointer;
  margin-left: 4px;
  padding: 0 4px;
  border-radius: 3px;
  transition: all 0.2s ease;
  line-height: 1;
  user-select: none;
}

.card-delete-btn:hover {
  color: #EF4444;
  background: rgba(239, 68, 68, 0.1);
  transform: scale(1.2);
}

/* 轮数进度显示 */
.card-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.5px;
  font-weight: 600;
  font-size: 0.65rem;
}

.status-dot {
  font-size: 0.5rem;
}

/* 进度状态颜色 */
.card-progress.completed { color: #10B981; }    /* 已完成 - 绿色 */
.card-progress.in-progress { color: #F59E0B; }  /* 进行中 - 橙色 */
.card-progress.not-started { color: #9CA3AF; }  /* 未开始 - 灰色 */
.card-status.pending { color: #9CA3AF; }

/* 文件列表区域 */
.card-files-wrapper {
  position: relative;
  width: 100%;
  min-height: 48px;
  max-height: 110px;
  margin-bottom: 12px;
  padding: 8px 10px;
  background: linear-gradient(135deg, #f8f9fa 0%, #f1f3f4 100%);
  border-radius: 4px;
  border: 1px solid #e8eaed;
  overflow: hidden;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 更多文件提示 */
.files-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3px 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  color: #6B7280;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 3px;
  letter-spacing: 0.3px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 3px;
  transition: all 0.2s ease;
}

.file-item:hover {
  background: rgba(255, 255, 255, 1);
  transform: translateX(2px);
  border-color: #e5e7eb;
}

/* 简约文件标签样式 */
.file-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 16px;
  padding: 0 4px;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.55rem;
  font-weight: 600;
  line-height: 1;
  text-transform: uppercase;
  letter-spacing: 0.2px;
  flex-shrink: 0;
  min-width: 28px;
}

/* 低饱和度配色方案 - Morandi色系 */
.file-tag.pdf { background: #f2e6e6; color: #a65a5a; }
.file-tag.doc { background: #e6eff5; color: #5a7ea6; }
.file-tag.xls { background: #e6f2e8; color: #5aa668; }
.file-tag.ppt { background: #f5efe6; color: #a6815a; }
.file-tag.txt { background: #f0f0f0; color: #757575; }
.file-tag.code { background: #eae6f2; color: #815aa6; }
.file-tag.img { background: #e6f2f2; color: #5aa6a6; }
.file-tag.zip { background: #f2f0e6; color: #a69b5a; }
.file-tag.other { background: #f3f4f6; color: #6b7280; }

.file-name {
  font-family: 'Inter', sans-serif;
  font-size: 0.7rem;
  color: #4b5563;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.1px;
}

/* 无文件时的占位 */
.files-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  color: #9CA3AF;
}

.empty-file-icon {
  font-size: 1rem;
  opacity: 0.5;
}

.empty-file-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.5px;
}

/* 悬停时文件区域效果 */
.project-card:hover .card-files-wrapper {
  border-color: #d1d5db;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}

/* 角落装饰 */
.corner-mark.top-left-only {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 8px;
  height: 8px;
  border-top: 1.5px solid rgba(0, 0, 0, 0.4);
  border-left: 1.5px solid rgba(0, 0, 0, 0.4);
  pointer-events: none;
  z-index: 10;
}

/* 卡片标题 */
.card-title {
  font-family: 'Inter', -apple-system, sans-serif;
  font-size: 0.9rem;
  font-weight: 700;
  color: #111827;
  margin: 0 0 6px 0;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.3s ease;
}

.project-card:hover .card-title {
  color: #2563EB;
}

/* 卡片描述 */
.card-desc {
  font-family: 'Inter', sans-serif;
  font-size: 0.75rem;
  color: #6B7280;
  margin: 0 0 16px 0;
  line-height: 1.5;
  height: 34px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 卡片底部 */
.card-footer {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #F3F4F6;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  color: #9CA3AF;
  font-weight: 500;
}

/* 日期时间组合 */
.card-datetime {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 底部轮数进度显示 */
.card-footer .card-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.5px;
  font-weight: 600;
  font-size: 0.65rem;
}

.card-footer .status-dot {
  font-size: 0.5rem;
}

/* 进度状态颜色 - 底部 */
.card-footer .card-progress.completed { color: #10B981; }
.card-footer .card-progress.in-progress { color: #F59E0B; }
.card-footer .card-progress.not-started { color: #9CA3AF; }

/* 底部装饰线 */
.card-bottom-line {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  width: 0;
  background-color: #000;
  transition: width 0.5s cubic-bezier(0.23, 1, 0.32, 1);
  z-index: 20;
}

.project-card:hover .card-bottom-line {
  width: 100%;
}

/* 空状态 */
.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 48px;
  color: #9CA3AF;
}

.empty-icon {
  font-size: 2rem;
  opacity: 0.5;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #E5E7EB;
  border-top-color: #6B7280;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 1200px) {
  .project-card {
    width: 240px;
  }
}

@media (max-width: 768px) {
  .cards-container {
    padding: 0 20px;
  }
  .project-card {
    width: 200px;
  }
}

/* ===== 历史回放详情弹窗样式 ===== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #FFFFFF;
  width: 560px;
  max-width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* 动画过渡 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-content {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-leave-active .modal-content {
  transition: all 0.2s ease-in;
}

.modal-enter-from .modal-content {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

.modal-leave-to .modal-content {
  transform: scale(0.95) translateY(10px);
  opacity: 0;
}

/* 弹窗头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 32px;
  border-bottom: 1px solid #F3F4F6;
  background: #FFFFFF;
}

.modal-title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.modal-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  letter-spacing: 0.5px;
}

.modal-progress {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  background: #F9FAFB;
}

.modal-progress.completed { color: #10B981; background: rgba(16, 185, 129, 0.1); }
.modal-progress.in-progress { color: #F59E0B; background: rgba(245, 158, 11, 0.1); }
.modal-progress.not-started { color: #9CA3AF; background: #F3F4F6; }

.modal-create-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #9CA3AF;
  letter-spacing: 0.3px;
}

.modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 1.5rem;
  color: #9CA3AF;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border-radius: 6px;
}

.modal-close:hover {
  background: #F3F4F6;
  color: #111827;
}

/* 弹窗内容 */
.modal-body {
  padding: 24px 32px;
}

.modal-section {
  margin-bottom: 24px;
}

.modal-section:last-child {
  margin-bottom: 0;
}

.modal-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 10px;
  font-weight: 500;
}

.modal-requirement {
  font-size: 0.95rem;
  color: #374151;
  line-height: 1.6;
  padding: 16px;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  border-radius: 8px;
}

.modal-files {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

/* 自定义滚动条样式 */
.modal-files::-webkit-scrollbar {
  width: 4px;
}

.modal-files::-webkit-scrollbar-track {
  background: #F3F4F6;
  border-radius: 2px;
}

.modal-files::-webkit-scrollbar-thumb {
  background: #D1D5DB;
  border-radius: 2px;
}

.modal-files::-webkit-scrollbar-thumb:hover {
  background: #9CA3AF;
}

.modal-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.modal-file-item:hover {
  border-color: #D1D5DB;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.modal-file-name {
  font-size: 0.85rem;
  color: #4B5563;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-empty {
  font-size: 0.85rem;
  color: #9CA3AF;
  padding: 16px;
  background: #F9FAFB;
  border: 1px dashed #E5E7EB;
  border-radius: 6px;
  text-align: center;
}

/* 推演回放分割线 */
.modal-divider {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 32px 0;
  background: #FFFFFF;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #E5E7EB, transparent);
}

.divider-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: #9CA3AF;
  letter-spacing: 2px;
  text-transform: uppercase;
  white-space: nowrap;
}

/* 导航按钮 */
.modal-actions {
  display: flex;
  gap: 16px;
  padding: 20px 32px;
  background: #FFFFFF;
}

.modal-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #FFFFFF;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.modal-btn:hover:not(:disabled) {
  border-color: #000000;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.modal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #F9FAFB;
}

.btn-step {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 500;
  color: #9CA3AF;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.btn-icon {
  font-size: 1.4rem;
  line-height: 1;
  transition: color 0.2s ease;
}

.btn-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #4B5563;
}

.modal-btn.btn-project .btn-icon { color: #3B82F6; }
.modal-btn.btn-simulation .btn-icon { color: #F59E0B; }
.modal-btn.btn-step3 .btn-icon { color: #8B5CF6; }
.modal-btn.btn-report .btn-icon { color: #10B981; }
/* 卡片快捷工作台入口 */
.card-workspace-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 5px 0;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #63b3ed;
  background: rgba(99, 179, 237, 0.06);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  opacity: 0;
}
.project-card:hover .card-workspace-link { opacity: 1; }
.card-workspace-link:hover {
  background: rgba(99, 179, 237, 0.15);
  color: #90cdf4;
}
.workspace-icon { font-size: 13px; }

.modal-btn.btn-incident { border-color: rgba(99, 179, 237, 0.3); }
.modal-btn.btn-incident .btn-icon { color: #63b3ed; }
.modal-btn.btn-incident .btn-step { color: #63b3ed; }

.modal-btn:hover:not(:disabled) .btn-text {
  color: #111827;
}
</style>
