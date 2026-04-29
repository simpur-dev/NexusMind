<template>
  <div class="process-page">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand-group">
        <div class="nav-brand" @click="goHome">NexusMind</div>
        <button class="home-btn" @click="goHome" title="返回首页">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
        </button>
        <button class="home-btn incident-back-btn" @click="goBackToWorkspace" title="返回事件工作台">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          <span style="font-size:11px;margin-left:2px">事件工作台</span>
        </button>
      </div>
      
      <!-- 中间步骤指示器 -->
      <div class="nav-center">
        <div class="step-badge">STEP {{ String(currentStep).padStart(2, '0') }}</div>
        <div class="step-name">{{ stepNames[currentStep - 1] }}</div>
        <!-- 顶部同步 dot -->
        <div class="nav-step-dots">
          <div
            v-for="(n, idx) in stepNames"
            :key="idx"
            class="nav-dot"
            :class="{
              active: currentStep === idx + 1,
              completed: currentStep > idx + 1
            }"
          ></div>
        </div>
      </div>

      <div class="nav-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </nav>

    <!-- 分支上下文条（从事件工作台跳转时显示） -->
    <div class="branch-context-bar" v-if="branchContext">
      <span class="branch-ctx-icon">⑂</span>
      <span class="branch-ctx-type" :class="branchContext.type">{{ branchContext.typeLabel }}</span>
      <span class="branch-ctx-label">{{ branchContext.label }}</span>
      <span class="branch-ctx-sep">|</span>
      <span class="branch-ctx-baseline">基线 {{ branchContext.baselineId?.slice(-6) || '—' }}</span>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">

      <!-- 左侧图谱：仅 Step 1-2 显示 -->
      <Transition name="panel-slide">
        <div v-if="currentStep <= 2" class="left-panel" :class="{ 'full-screen': isFullScreen }">
        <div class="graph-left-atmosphere" aria-hidden="true">
          <div class="gl-glow gl-glow-a"></div>
          <div class="gl-glow gl-glow-b"></div>
          <div class="gl-glow gl-glow-c"></div>
          <div class="gl-ellipses"></div>
          <div class="gl-symbol-pattern"></div>
        </div>
        <div class="panel-header">
          <div class="header-left">
            <span class="header-deco">◆</span>
            <span class="header-title">实时知识图谱</span>
          </div>
          <div class="header-right">
            <template v-if="graphData">
              <span class="stat-item">{{ graphData.node_count || graphData.nodes?.length || 0 }} 节点</span>
              <span class="stat-divider">|</span>
              <span class="stat-item">{{ graphData.edge_count || graphData.edges?.length || 0 }} 关系</span>
              <span class="stat-divider">|</span>
            </template>
            <div class="action-buttons">
                <button class="action-btn" @click="refreshGraph" :disabled="graphLoading" title="刷新图谱">
                  <span class="icon-refresh" :class="{ 'spinning': graphLoading }">↻</span>
                </button>
                <button class="action-btn" @click="toggleFullScreen" :title="isFullScreen ? '退出全屏' : '全屏显示'">
                  <span class="icon-fullscreen">{{ isFullScreen ? '↙' : '↗' }}</span>
                </button>
            </div>
          </div>
        </div>
        
        <div class="graph-container" ref="graphContainer">
          <!-- 图谱可视化（只要有数据就显示） -->
          <div v-if="graphData" class="graph-view">
            <svg ref="graphSvg" class="graph-svg"></svg>
            <!-- 构建中提示 -->
            <div v-if="currentPhase === 1" class="graph-building-hint">
              <span class="building-dot"></span>
              实时更新中...
            </div>
            
            <!-- 节点/边详情面板 -->
            <div v-if="selectedItem" class="detail-panel">
              <div class="detail-panel-header">
                <span class="detail-title">{{ selectedItem.type === 'node' ? 'Node Details' : 'Relationship' }}</span>
                <span v-if="selectedItem.type === 'node'" class="detail-badge" :style="{ background: selectedItem.color }">
                  {{ selectedItem.entityType }}
                </span>
                <button class="detail-close" @click="closeDetailPanel">×</button>
              </div>
              
              <!-- 节点详情 -->
              <div v-if="selectedItem.type === 'node'" class="detail-content">
                <div class="detail-row">
                  <span class="detail-label">Name:</span>
                  <span class="detail-value highlight">{{ selectedItem.data.name }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">UUID:</span>
                  <span class="detail-value uuid">{{ selectedItem.data.uuid }}</span>
                </div>
                <div class="detail-row" v-if="selectedItem.data.created_at">
                  <span class="detail-label">Created:</span>
                  <span class="detail-value">{{ formatDate(selectedItem.data.created_at) }}</span>
                </div>
                
                <!-- Properties / Attributes -->
                <div class="detail-section" v-if="selectedItem.data.attributes && Object.keys(selectedItem.data.attributes).length > 0">
                  <span class="detail-label">Properties:</span>
                  <div class="properties-list">
                    <div v-for="(value, key) in selectedItem.data.attributes" :key="key" class="property-item">
                      <span class="property-key">{{ key }}:</span>
                      <span class="property-value">{{ value }}</span>
                    </div>
                  </div>
                </div>
                
                <!-- Summary -->
                <div class="detail-section" v-if="selectedItem.data.summary">
                  <span class="detail-label">Summary:</span>
                  <p class="detail-summary">{{ selectedItem.data.summary }}</p>
                </div>
                
                <!-- Labels -->
                <div class="detail-row" v-if="selectedItem.data.labels?.length">
                  <span class="detail-label">Labels:</span>
                  <div class="detail-labels">
                    <span v-for="label in selectedItem.data.labels" :key="label" class="label-tag">{{ label }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 边详情 -->
              <div v-else class="detail-content">
                <!-- 关系展示 -->
                <div class="edge-relation">
                  <span class="edge-source">{{ selectedItem.data.source_name || selectedItem.data.source_node_name }}</span>
                  <span class="edge-arrow">→</span>
                  <span class="edge-type">{{ selectedItem.data.name || selectedItem.data.fact_type || 'RELATED_TO' }}</span>
                  <span class="edge-arrow">→</span>
                  <span class="edge-target">{{ selectedItem.data.target_name || selectedItem.data.target_node_name }}</span>
                </div>
                
                <div class="detail-subtitle">Relationship</div>
                
                <div class="detail-row">
                  <span class="detail-label">UUID:</span>
                  <span class="detail-value uuid">{{ selectedItem.data.uuid }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">Label:</span>
                  <span class="detail-value">{{ selectedItem.data.name || selectedItem.data.fact_type || 'RELATED_TO' }}</span>
                </div>
                <div class="detail-row" v-if="selectedItem.data.fact_type">
                  <span class="detail-label">Type:</span>
                  <span class="detail-value">{{ selectedItem.data.fact_type }}</span>
                </div>
                
                <!-- Fact -->
                <div class="detail-section" v-if="selectedItem.data.fact">
                  <span class="detail-label">Fact:</span>
                  <p class="detail-summary">{{ selectedItem.data.fact }}</p>
                </div>
                
                <!-- Episodes -->
                <div class="detail-section" v-if="selectedItem.data.episodes?.length">
                  <span class="detail-label">Episodes:</span>
                  <div class="episodes-list">
                    <span v-for="ep in selectedItem.data.episodes" :key="ep" class="episode-tag">{{ ep }}</span>
                  </div>
                </div>
                
                <div class="detail-row" v-if="selectedItem.data.created_at">
                  <span class="detail-label">Created:</span>
                  <span class="detail-value">{{ formatDate(selectedItem.data.created_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedItem.data.valid_at">
                  <span class="detail-label">Valid From:</span>
                  <span class="detail-value">{{ formatDate(selectedItem.data.valid_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedItem.data.invalid_at">
                  <span class="detail-label">Invalid At:</span>
                  <span class="detail-value">{{ formatDate(selectedItem.data.invalid_at) }}</span>
                </div>
                <div class="detail-row" v-if="selectedItem.data.expired_at">
                  <span class="detail-label">Expired At:</span>
                  <span class="detail-value">{{ formatDate(selectedItem.data.expired_at) }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 加载状态 -->
          <div v-else-if="graphLoading" class="graph-loading">
            <div class="loading-animation">
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
            </div>
            <p class="loading-text">图谱数据加载中...</p>
          </div>
          
          <!-- 等待构建 -->
          <div v-else-if="currentPhase < 1" class="graph-waiting">
            <div class="waiting-icon">
              <!-- 科技风发光环形图标 -->
              <svg viewBox="0 0 120 120" class="tech-ring-icon">
                <defs>
                  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                    <feMerge>
                      <feMergeNode in="coloredBlur"/>
                      <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                  </filter>
                  <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:1" />
                    <stop offset="50%" style="stop-color:#06b6d4;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:1" />
                  </linearGradient>
                </defs>
                <!-- 外圈 -->
                <circle cx="60" cy="60" r="50" fill="none" stroke="url(#ringGradient)" stroke-width="2" 
                        stroke-dasharray="10 5" filter="url(#glow)" class="ring-outer">
                  <animateTransform attributeName="transform" type="rotate" from="0 60 60" to="360 60 60" dur="20s" repeatCount="indefinite"/>
                </circle>
                <!-- 中圈 -->
                <circle cx="60" cy="60" r="38" fill="none" stroke="url(#ringGradient)" stroke-width="1.5" 
                        stroke-dasharray="6 4" filter="url(#glow)" opacity="0.7" class="ring-middle">
                  <animateTransform attributeName="transform" type="rotate" from="360 60 60" to="0 60 60" dur="15s" repeatCount="indefinite"/>
                </circle>
                <!-- 内圈 -->
                <circle cx="60" cy="60" r="26" fill="none" stroke="url(#ringGradient)" stroke-width="1" 
                        stroke-dasharray="4 3" filter="url(#glow)" opacity="0.5" class="ring-inner">
                  <animateTransform attributeName="transform" type="rotate" from="0 60 60" to="360 60 60" dur="10s" repeatCount="indefinite"/>
                </circle>
                <!-- 中心光点 -->
                <circle cx="60" cy="60" r="8" fill="url(#ringGradient)" filter="url(#glow)" class="core-pulse">
                  <animate attributeName="r" values="8;10;8" dur="2s" repeatCount="indefinite"/>
                  <animate attributeName="opacity" values="1;0.6;1" dur="2s" repeatCount="indefinite"/>
                </circle>
                <!-- 十字星 -->
                <g stroke="url(#ringGradient)" stroke-width="1.5" filter="url(#glow)" opacity="0.6">
                  <line x1="60" y1="20" x2="60" y2="40">
                    <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite"/>
                  </line>
                  <line x1="60" y1="80" x2="60" y2="100">
                    <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite" begin="0.2s"/>
                  </line>
                  <line x1="20" y1="60" x2="40" y2="60">
                    <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite" begin="0.4s"/>
                  </line>
                  <line x1="80" y1="60" x2="100" y2="60">
                    <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite" begin="0.6s"/>
                  </line>
                </g>
              </svg>
            </div>
            <p class="waiting-text">等待本体生成</p>
            <p class="waiting-hint">生成完成后将自动开始构建图谱</p>
          </div>
          
          <!-- 构建中但还没有数据 -->
          <div v-else-if="currentPhase === 1 && !graphData" class="graph-waiting">
            <div class="loading-animation">
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
              <div class="loading-ring"></div>
            </div>
            <p class="waiting-text">图谱构建中</p>
            <p class="waiting-hint">数据即将显示...</p>
          </div>
          
          <!-- 错误状态 -->
          <div v-else-if="error" class="graph-error">
            <span class="error-icon">⚠</span>
            <p>{{ error }}</p>
          </div>
        </div>
        
        <!-- 图谱图例 -->
        <div v-if="graphData" class="graph-legend">
          <div class="legend-item" v-for="type in entityTypes" :key="type.name">
            <span class="legend-dot" :style="{ background: type.color }"></span>
            <span class="legend-label">{{ type.name }}</span>
            <span class="legend-count">{{ type.count }}</span>
          </div>
        </div>
      </div>
    </Transition>

      <!-- 可拖拽分隔条 -->
      <div
        v-if="currentStep <= 2 && !isFullScreen"
        class="resize-handle"
        :class="{ 'dragging': isDragging }"
        @mousedown="startResize"
        @dblclick="resetLayout"
        title="拖拽调整比例 / 双击重置为 7:3"
      >
        <div class="handle-indicator">
          <span class="handle-dot"></span>
          <span class="handle-dot"></span>
          <span class="handle-dot"></span>
        </div>
      </div>

      <!-- 右侧: Step 组件容器 -->
      <div
        class="right-panel"
        :class="{
          'hidden': isFullScreen && currentStep <= 2,
          'full-screen-step': currentStep >= 3
        }"
      >
        <!-- 顶部导航条（Step 1-2 仅在右侧显示） -->
        <div class="panel-header dark-header">
          <div class="header-left">
            <span class="header-icon">▣</span>
            <span class="header-title">构建流程</span>
          </div>
          <!-- Step dot 指示器 -->
          <div class="step-dots">
            <div
              v-for="(name, idx) in stepNames"
              :key="idx"
              class="step-dot-wrap"
              :title="name"
              @click="maxReachedStep >= idx + 1 && currentStep !== idx + 1 && (currentStep = idx + 1)"
              :style="{ cursor: maxReachedStep >= idx + 1 && currentStep !== idx + 1 ? 'pointer' : 'default' }"
            >
              <div
                class="step-dot"
                :class="{
                  active: currentStep === idx + 1,
                  completed: maxReachedStep > idx + 1 && currentStep !== idx + 1,
                  pending: maxReachedStep < idx + 1
                }"
              >
                <span v-if="maxReachedStep > idx + 1 && currentStep !== idx + 1" class="dot-check">✓</span>
                <span v-else class="dot-num">{{ idx + 1 }}</span>
              </div>
              <span class="step-dot-label">{{ name }}</span>
            </div>
          </div>
        </div>

        <!-- 本体/图谱进度条（仅 Step 1 时显示） -->
        <div class="progress-strip" v-if="currentStep === 1">
          <div class="strip-ontology" v-if="currentPhase === 0">
            <div class="strip-spinner"></div>
            <span class="strip-text">{{ ontologyProgress?.message || '本体生成中...' }}</span>
          </div>
          <div class="strip-graph" v-else-if="currentPhase >= 1 && currentPhase < 2">
            <div class="strip-label">
              <span>图谱构建</span>
              <span class="strip-pct">{{ buildProgress?.progress || 0 }}%</span>
            </div>
            <div class="strip-bar">
              <div class="strip-fill" :style="{ width: (buildProgress?.progress || 0) + '%' }"></div>
            </div>
          </div>
          <div class="strip-done" v-else-if="currentPhase >= 2">
            <span class="strip-done-icon">◆</span>
            <span class="strip-done-text">图谱构建完成 · {{ graphData?.node_count || graphData?.nodes?.length || 0 }} 节点 · {{ graphData?.edge_count || graphData?.edges?.length || 0 }} 关系</span>
          </div>
        </div>

        <div class="step-area">
          <Transition name="step-slide" mode="out-in">
            <div :key="currentStep" class="step-area-inner">
              <Step1GraphBuild
                v-if="currentStep === 1"
                :currentPhase="currentPhase"
                :projectData="projectData"
                :ontologyProgress="ontologyProgress"
                :buildProgress="buildProgress"
                :graphData="graphData"
                :systemLogs="systemLogs"
                :rebuildingGraph="rebuildingGraph"
                @next-step="handleNextStep"
                @simulation-created="handleSimulationCreated"
                @rebuild-graph="handleRebuildGraph"
              />
              <!-- Step 2 用和 Step 1 相同的外层包裹 -->
              <div v-else-if="currentStep === 2" class="workbench-wrapper">
                <div class="scroll-container">
                  <Step2EnvSetup
                    :simulationId="currentSimulationId"
                    :projectData="projectData"
                    :graphData="graphData"
                    :systemLogs="systemLogs"
                    @go-back="handleGoBack"
                    @next-step="handleNextStep"
                    @add-log="addLog"
                    @update-status="updateStatus"
                  />
                </div>
              </div>
              <Step3Simulation
                v-else-if="currentStep === 3"
                :simulationId="currentSimulationId"
                :maxRounds="maxRounds"
                :minutesPerRound="minutesPerRound"
                :freshStart="pendingFreshStart"
                :projectData="projectData"
                :graphData="graphData"
                :systemLogs="systemLogs"
                @go-back="handleGoBack"
                @next-step="handleNextStep"
                @add-log="addLog"
                @update-status="updateStatus"
                @fresh-start-consumed="pendingFreshStart = false"
              />
              <Step4Report
                v-else-if="currentStep === 4"
                :reportId="currentReportId"
                :simulationId="currentSimulationId"
                :baselineId="route.query.baseline_id || ''"
                :systemLogs="systemLogs"
                @next-step="handleNextStep"
                @add-log="addLog"
                @update-status="updateStatus"
              />
              <Step5Interaction
                v-else
                :reportId="currentReportId"
                :simulationId="currentSimulationId"
                @add-log="addLog"
                @update-status="updateStatus"
              />
            </div>
          </Transition>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { generateOntology, generateOntologyFromWeb, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import Step3Simulation from '../components/Step3Simulation.vue'
import Step4Report from '../components/Step4Report.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import * as d3 from 'd3'

const route = useRoute()
const router = useRouter()

// 当前项目ID（可能从'new'变为实际ID）
const currentProjectId = ref(route.params.projectId)

// 状态
const loading = ref(true)
const graphLoading = ref(false)
const error = ref('')
const projectData = ref(null)
const graphData = ref(null)
const buildProgress = ref(null)
const ontologyProgress = ref(null) // 本体生成进度
const currentPhase = ref(-1) // -1: 上传中, 0: 本体生成中, 1: 图谱构建, 2: 完成
const rebuildingGraph = ref(false) // 重新构建图谱中
const selectedItem = ref(null) // 选中的节点或边
const isFullScreen = ref(false)

// Step 导航状态
const currentStep = ref(1) // 1: 图谱构建, 2: 环境搭建, 3: 世界模型推演, 4: 报告生成, 5: 深度互动
const maxReachedStep = ref(1) // 已到达过的最高步骤，允许在已访问步骤间自由跳转
const stepNames = ['图谱构建', '环境搭建', '世界模型推演', '报告生成', '深度互动']
const currentSimulationId = ref(null)
const currentReportId = ref(null)
const maxRounds = ref(null) // 从 Step2 传入的模拟轮数配置
const minutesPerRound = ref(60) // 每轮分钟数，默认60（与后端 simulation_config_generator 一致）
const pendingFreshStart = ref(false) // Step2 点击"开始推演"时置 true，让 Step3 跳过 resume 直接启动
const stepStatus = ref('') // 子组件通过 emit('update-status') 上报的状态: processing / completed / error
const systemLogs = ref([])

// 响应式布局状态
const leftPanelWidth = ref(70) // 默认 70%
const isDragging = ref(false)
let resizeStartX = 0
let resizeStartWidth = 70

// 开始拖拽调整布局
const startResize = (e) => {
  if (isFullScreen.value || currentStep.value > 2) return
  isDragging.value = true
  resizeStartX = e.clientX
  resizeStartWidth = leftPanelWidth.value
  // 拖拽时禁用过渡效果以实现即时响应
  document.body.classList.add('is-resizing')
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

// 处理拖拽 - 使用 requestAnimationFrame 优化性能
let resizeRafId = null
const handleResize = (e) => {
  if (!isDragging.value) return
  
  if (resizeRafId) return
  resizeRafId = requestAnimationFrame(() => {
    resizeRafId = null
    
    const containerWidth = document.querySelector('.main-content')?.offsetWidth || window.innerWidth
    const deltaX = e.clientX - resizeStartX
    const deltaPercent = (deltaX / containerWidth) * 100
    
    // 限制范围在 20% - 80% 之间
    let newWidth = resizeStartWidth + deltaPercent
    newWidth = Math.max(20, Math.min(80, newWidth))
    
    // 同时更新 Vue 响应式状态和 CSS 变量实现即时同步
    leftPanelWidth.value = newWidth
    document.documentElement.style.setProperty('--left-panel-width', newWidth + '%')
  })
}

// 停止拖拽
const stopResize = () => {
  isDragging.value = false
  if (resizeRafId) {
    cancelAnimationFrame(resizeRafId)
    resizeRafId = null
  }
  document.body.classList.remove('is-resizing')
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// 重置布局为默认 7:3
const resetLayout = () => {
  leftPanelWidth.value = 70
  document.documentElement.style.setProperty('--left-panel-width', '70%')
}

// DOM引用
const graphContainer = ref(null)
const graphSvg = ref(null)

// 轮询定时器
let pollTimer = null

const statusText = computed(() => {
  if (rebuildingGraph.value || currentPhase.value === 1) {
    return '图谱构建中'
  }
  if (error.value) return '构建失败'
  if (stepStatus.value === 'error') return '出错'
  switch (currentStep.value) {
    case 1:
      if (currentPhase.value >= 2) return '构建完成'
      if (currentPhase.value === 0) return '本体生成中'
      return '初始化中'
    case 2:
      return stepStatus.value === 'completed' ? '环境搭建完成' : '环境搭建中'
    case 3:
      return stepStatus.value === 'completed' ? '模拟完成' : '模拟运行中'
    case 4:
      return stepStatus.value === 'completed' ? '报告完成' : '报告生成中'
    default:
      return ''
  }
})

const statusClass = computed(() => {
  if (rebuildingGraph.value || currentPhase.value === 1) return 'processing'
  if (error.value || stepStatus.value === 'error') return 'error'
  // Step 1: 图谱构建
  if (currentStep.value === 1) {
    if (currentPhase.value >= 2) return 'completed'
    return 'processing'
  }
  // Step 2-5: 使用子组件上报的 stepStatus
  if (stepStatus.value === 'completed') return 'completed'
  if (stepStatus.value === 'processing') return 'processing'
  // 默认：刚切到这个步骤，还没有状态上报
  return 'processing'
})

const entityTypes = computed(() => {
  if (!graphData.value?.nodes) return []
  
  const typeMap = {}
  const colors = ['#FF6B35', '#004E89', '#7B2D8E', '#1A936F', '#C5283D', '#E9724C']
  
  graphData.value.nodes.forEach(node => {
    const type = node.labels?.find(l => l !== 'Entity') || 'Entity'
    if (!typeMap[type]) {
      typeMap[type] = { name: type, count: 0, color: colors[Object.keys(typeMap).length % colors.length] }
    }
    typeMap[type].count++
  })
  
  return Object.values(typeMap)
})

// 是否从事件工作台跳转过来
const fromIncidentWorkspace = computed(() => !!route.query.sim)

const branchTypeCN = { base: '基准', recalibrated: '校准', intervention_a: '干预A', intervention_b: '干预B', intervention_c: '干预C' }
const branchContext = computed(() => {
  const bl = route.query.baseline_id
  const label = route.query.branch_label
  const type = route.query.branch_type
  if (!bl && !label) return null
  return {
    baselineId: bl || '',
    label: label || '—',
    type: type || 'base',
    typeLabel: branchTypeCN[type] || type || '基准',
  }
})

const goBackToWorkspace = () => {
  router.push(`/incident/${currentProjectId.value}`)
}

// 方法
const goHome = () => {
  router.push('/')
}

const addLog = (msg, status) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  const inferStatus = (m) => {
    const n = String(m).toLowerCase()
    if (/(error|failed|exception)/.test(n)) return 'error'
    if (/(success|completed|loaded|done|ready)/.test(n)) return 'success'
    return 'info'
  }
  systemLogs.value.push({ time, msg, status: status || inferStatus(msg) })
  if (systemLogs.value.length > 100) systemLogs.value.shift()
}

const updateStatus = (s) => {
  stepStatus.value = s || ''
}

let isSyncingFromRoute = false
let isInitialStepSync = true
const pushStepToRoute = (step) => {
  if (isSyncingFromRoute) return
  if (Number(route.query.step) === step) return
  const navigate = isInitialStepSync ? router.replace : router.push
  navigate.call(router, {
    name: 'Process',
    params: { projectId: route.params.projectId },
    query: { ...route.query, step: String(step) }
  })
  isInitialStepSync = false
}

const handleNextStep = (params = {}) => {
  // Step2 passes maxRounds —— 始终更新，防止上一次的旧值残留
  if (params.maxRounds) {
    maxRounds.value = params.maxRounds
    // 从 Step2 点"开始推演"进入 Step3 时，标记需要全新启动
    if (currentStep.value === 2) {
      pendingFreshStart.value = true
    }
    if (params.minutesPerRound) {
      minutesPerRound.value = params.minutesPerRound
    }
    addLog(`配置模拟轮数: ${params.maxRounds} 轮, 每轮 ${minutesPerRound.value} 分钟`)
  } else {
    maxRounds.value = null
  }
  if (params.reportId) {
    currentReportId.value = params.reportId
  }
  if (currentStep.value < 5) {
    currentStep.value++
    if (currentStep.value > maxReachedStep.value) {
      maxReachedStep.value = currentStep.value
    }
    addLog(`进入 ${stepNames[currentStep.value - 1]} (Step ${currentStep.value}/5)`)
  }
}

const handleGoBack = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    addLog(`返回 ${stepNames[currentStep.value - 1]} (Step ${currentStep.value}/5)`)
  }
}

const handleGoBackTo = (step) => {
  if (step < currentStep.value) {
    currentStep.value = step
    addLog(`返回 ${stepNames[step - 1]} (Step ${step}/5)`)
  }
}

const handleSimulationCreated = ({ simulationId }) => {
  currentSimulationId.value = simulationId
  currentStep.value = 2
  if (2 > maxReachedStep.value) maxReachedStep.value = 2
  addLog(`模拟实例已创建: ${simulationId}`)
  addLog(`进入 ${stepNames[1]} (Step 2/5)`)
}

// 兜底：任何 currentStep 变更（包括初始化/加载项目）都同步到 URL
// 首次会通过 router.replace 写入 ?step=N（不产生历史），后续是 push（产生历史）
watch(currentStep, (newStep) => {
  if (!newStep) return
  stepStatus.value = '' // 切换步骤时重置子组件状态
  pushStepToRoute(newStep)
})

// 监听 URL ?step=N 变化（浏览器后退/前进），同步 currentStep
watch(() => route.query.step, (newStep) => {
  if (!newStep) return
  const target = Number(newStep)
  if (!Number.isInteger(target) || target < 1 || target > 5) return
  // 只允许跳到已到达过的 step，防止通过 URL 非法越级
  if (target > maxReachedStep.value) return
  if (target === currentStep.value) return
  isSyncingFromRoute = true
  currentStep.value = target
  addLog(`浏览器导航：切换到 ${stepNames[target - 1]} (Step ${target}/5)`)
  nextTick(() => { isSyncingFromRoute = false })
})

const toggleFullScreen = () => {
  isFullScreen.value = !isFullScreen.value
  // Wait for transition to finish then re-render graph
  setTimeout(() => {
    renderGraph()
  }, 350) 
}

// 关闭详情面板
const closeDetailPanel = () => {
  selectedItem.value = null
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

// 选中节点
const selectNode = (nodeData, color) => {
  selectedItem.value = {
    type: 'node',
    data: nodeData,
    color: color,
    entityType: nodeData.labels?.find(l => l !== 'Entity' && l !== 'Node') || 'Entity'
  }
}

// 选中边
const selectEdge = (edgeData) => {
  selectedItem.value = {
    type: 'edge',
    data: edgeData
  }
}

const getPhaseStatusClass = (phase) => {
  if (currentPhase.value > phase) return 'completed'
  if (currentPhase.value === phase) return 'active'
  return 'pending'
}

const getPhaseStatusText = (phase) => {
  if (currentPhase.value > phase) return '已完成'
  if (currentPhase.value === phase) {
    if (phase === 1 && buildProgress.value) {
      return `${buildProgress.value.progress}%`
    }
    return '进行中'
  }
  return '等待中'
}

// 初始化 - 处理新建项目或加载已有项目
const initProject = async () => {
  const paramProjectId = route.params.projectId

  if (paramProjectId === 'new') {
    // 新建项目：从 store 获取待上传的数据
    currentStep.value = 1
    await handleNewProject()
  } else {
    // 加载已有项目（可能是从历史记录跳转回来）
    currentProjectId.value = paramProjectId
    await loadProject()
  }
}

// 处理新建项目 - 调用 ontology/generate 或 generate-from-web API
const handleNewProject = async () => {
  const pending = getPendingUpload()
  
  if (!pending.isPending) {
    error.value = '没有待处理的数据，请返回首页重新操作'
    loading.value = false
    return
  }
  
  // 根据模式验证输入
  if (pending.mode === 'file' && pending.files.length === 0) {
    error.value = '没有待上传的文件，请返回首页重新操作'
    loading.value = false
    return
  }
  if (pending.mode === 'web' && !pending.webQuery) {
    error.value = '没有搜索关键词，请返回首页重新操作'
    loading.value = false
    return
  }
  if (pending.mode === 'file+web' && (pending.files.length === 0 || !pending.webQuery)) {
    error.value = '混合模式需要同时提供文件和搜索关键词，请返回首页重新操作'
    loading.value = false
    return
  }
  
  try {
    loading.value = true
    currentPhase.value = 0 // 本体生成阶段
    
    let response
    
    if (pending.mode === 'web') {
      // 网络搜索模式
      ontologyProgress.value = { message: '正在搜索网络舆情信息...' }
      response = await generateOntologyFromWeb({
        query: pending.webQuery,
        simulation_requirement: pending.simulationRequirement,
      })
    } else {
      // 文件上传模式（含可选的网络抓取）
      const isHybrid = pending.mode === 'file+web' && pending.webQuery
      ontologyProgress.value = {
        message: isHybrid
          ? '正在上传文件并搜索网络舆情信息...'
          : '正在上传文件并分析文档...'
      }
      const formDataObj = new FormData()
      pending.files.forEach(file => {
        formDataObj.append('files', file)
      })
      formDataObj.append('simulation_requirement', pending.simulationRequirement)
      if (isHybrid) {
        formDataObj.append('web_query', pending.webQuery)
      }
      response = await generateOntology(formDataObj)
    }
    
    if (response.success) {
      // 清除待上传数据
      clearPendingUpload()
      
      // 更新项目ID和数据
      currentProjectId.value = response.data.project_id
      projectData.value = response.data
      
      // 更新URL（不刷新页面）
      router.replace({
        name: 'Process',
        params: { projectId: response.data.project_id }
      })
      
      ontologyProgress.value = null
      
      // 自动开始图谱构建
      await startBuildGraph()
    } else {
      error.value = response.error || '本体生成失败'
    }
  } catch (err) {
    console.error('Handle new project error:', err)
    error.value = '项目初始化失败: ' + (err.message || '未知错误')
  } finally {
    loading.value = false
  }
}

// 加载已有项目数据
const loadProject = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await getProject(currentProjectId.value)
    
    if (response.success) {
      projectData.value = response.data
      updatePhaseByStatus(response.data.status)

      // URL 中指定的目标步骤（从历史回放按钮传入）
      const requestedStep = Number(route.query.step) || 0
      // 事件工作台跳转时可通过 ?sim= 指定 simulation_id
      const querySim = route.query.sim

      // 辅助：从 baseline / simulation / project 中解析正确的 graph_id
      // 优先级：baseline_graph_id（路由参数）> simulation graph_id > project graph_id
      const queryBaselineGraphId = route.query.baseline_graph_id
      const resolveGraphId = async (simId) => {
        // 1. 事件工作台传入的基线 graph_id（最可靠）
        if (queryBaselineGraphId) return queryBaselineGraphId
        // 2. 从模拟分支获取
        if (simId) {
          try {
            const { getSimulation } = await import('../api/simulation')
            const simRes = await getSimulation(simId)
            const simGraphId = simRes?.data?.graph_id
            if (simGraphId && simGraphId !== response.data.graph_id) {
              const checkRes = await getGraphData(simGraphId)
              const nodeCount = checkRes?.data?.node_count || checkRes?.data?.nodes?.length || 0
              if (nodeCount > 0) return simGraphId
            }
          } catch (_) { /* fallback */ }
        }
        // 3. 回退到项目全局 graph_id
        return response.data.graph_id
      }

      // 从项目数据恢复 Step 导航状态
      if (response.data.report_id) {
        // 报告已生成，恢复关联数据
        currentSimulationId.value = querySim || response.data.simulation_id
        currentReportId.value = response.data.report_id
        maxReachedStep.value = 5
        const graphIdToLoad = await resolveGraphId(currentSimulationId.value)
        if (graphIdToLoad) {
          currentPhase.value = 2
          await loadGraph(graphIdToLoad)
        }
        // 从后端恢复模拟轮数配置
        try {
          const { getRunStatus } = await import('../api/simulation')
          const statusRes = await getRunStatus(currentSimulationId.value)
          if (statusRes?.data?.total_rounds) {
            maxRounds.value = statusRes.data.total_rounds
          }
        } catch (_) { /* 模拟状态不可用 */ }
        // 优先使用 URL 指定的步骤，否则默认 Step 4
        const targetStep = (requestedStep >= 1 && requestedStep <= maxReachedStep.value) ? requestedStep : 4
        currentStep.value = targetStep
        addLog(`从历史记录恢复项目，进入 Step ${targetStep} (${stepNames[targetStep - 1]})`)
      } else if (querySim || response.data.simulation_id) {
        // 模拟已创建，恢复关联数据（querySim 来自事件工作台跳转）
        currentSimulationId.value = querySim || response.data.simulation_id
        maxReachedStep.value = 5
        const graphIdToLoad = await resolveGraphId(currentSimulationId.value)
        if (graphIdToLoad) {
          currentPhase.value = 2
          await loadGraph(graphIdToLoad)
        }
        // 从后端恢复模拟轮数配置
        try {
          const { getRunStatus } = await import('../api/simulation')
          const statusRes = await getRunStatus(currentSimulationId.value)
          if (statusRes?.data?.total_rounds) {
            maxRounds.value = statusRes.data.total_rounds
          }
        } catch (_) { /* 模拟状态不可用，保持默认 */ }
        // 优先使用 URL 指定的步骤，否则默认 Step 2
        const targetStep = (requestedStep >= 1 && requestedStep <= maxReachedStep.value) ? requestedStep : 2
        currentStep.value = targetStep
        addLog(`从历史记录恢复项目，进入 Step ${targetStep} (${stepNames[targetStep - 1]})，模拟ID: ${currentSimulationId.value}`)
      } else if (response.data.status === 'graph_completed' && response.data.graph_id) {
        // 图谱构建完成，默认在 Step 1
        currentPhase.value = 2
        currentStep.value = 1
        await loadGraph(response.data.graph_id)
      } else if (response.data.status === 'graph_building' && response.data.graph_build_task_id) {
        currentPhase.value = 1
        currentStep.value = 1
        startPollingTask(response.data.graph_build_task_id)
      } else {
        currentStep.value = 1
      }

      // 继续轮询构建中的任务（仅当图谱尚未完成时）
      if (response.data.status === 'ontology_generated' && !response.data.graph_id) {
        await startBuildGraph()
      } else if (response.data.status === 'graph_building' && response.data.graph_build_task_id) {
        startGraphPolling()
      }
    } else {
      error.value = response.error || '加载项目失败'
    }
  } catch (err) {
    console.error('Load project error:', err)
    error.value = '加载项目失败: ' + (err.message || '未知错误')
  } finally {
    loading.value = false
  }
}

const updatePhaseByStatus = (status) => {
  switch (status) {
    case 'created':
    case 'ontology_generated':
      currentPhase.value = 0
      break
    case 'graph_building':
      currentPhase.value = 1
      break
    case 'graph_completed':
      currentPhase.value = 2
      break
    case 'failed':
      error.value = projectData.value?.error || '处理失败'
      break
  }
}

// 开始构建图谱
const startBuildGraph = async () => {
  try {
    currentPhase.value = 1
    // 设置初始进度
    buildProgress.value = {
      progress: 0,
      message: '正在启动图谱构建...'
    }
    
    const response = await buildGraph({ project_id: currentProjectId.value })
    
    if (response.success) {
      buildProgress.value.message = '图谱构建任务已启动...'
      
      // 保存 task_id 用于轮询
      const taskId = response.data.task_id
      
      // 启动图谱数据轮询（独立于任务状态轮询）
      startGraphPolling()
      
      // 启动任务状态轮询
      startPollingTask(taskId)
    } else {
      error.value = response.error || '启动图谱构建失败'
      buildProgress.value = null
    }
  } catch (err) {
    console.error('Build graph error:', err)
    error.value = '启动图谱构建失败: ' + (err.message || '未知错误')
    buildProgress.value = null
  }
}

// 重新构建图谱（用户手动触发）
const handleRebuildGraph = async () => {
  if (rebuildingGraph.value) return
  rebuildingGraph.value = true
  error.value = ''
  addLog('用户手动触发图谱重建...')
  try {
    await startBuildGraph()
  } catch (e) {
    console.error('handleRebuildGraph error:', e)
    error.value = '重建图谱失败: ' + (e.message || '未知错误')
  } finally {
    rebuildingGraph.value = false
  }
}

// 图谱数据轮询定时器
let graphPollTimer = null

// 启动图谱数据轮询
const startGraphPolling = () => {
  // 立即获取一次
  fetchGraphData()
  
  // 每 10 秒自动获取一次图谱数据
  graphPollTimer = setInterval(async () => {
    await fetchGraphData()
  }, 10000)
}

// 手动刷新图谱
const refreshGraph = async () => {
  graphLoading.value = true
  await fetchGraphData(true)
  graphLoading.value = false
}

// 停止图谱数据轮询
const stopGraphPolling = () => {
  if (graphPollTimer) {
    clearInterval(graphPollTimer)
    graphPollTimer = null
  }
}

// 获取图谱数据
const fetchGraphData = async (forceRender = false) => {
  try {
    // 先获取项目信息
    const projectResponse = await getProject(currentProjectId.value)
    
    // 优先使用路由中传入的基线 graph_id，其次使用项目全局 graph_id
    const blGid = route.query.baseline_graph_id
    const projGid = projectResponse.success ? projectResponse.data.graph_id : null
    const graphId = blGid || projGid
    
    if (projectResponse.success) projectData.value = projectResponse.data
    
    if (graphId) {
      // 获取图谱数据
      const graphResponse = await getGraphData(graphId)
      
      if (graphResponse.success && graphResponse.data) {
        const newData = graphResponse.data
        const newNodeCount = newData.node_count || newData.nodes?.length || 0
        const oldNodeCount = graphData.value?.node_count || graphData.value?.nodes?.length || 0
        
        console.log('Fetching graph data, nodes:', newNodeCount, 'edges:', newData.edge_count || newData.edges?.length || 0)
        
        // 手动刷新时强制重新渲染；轮询时仅在数据变化时渲染
        if (forceRender || newNodeCount !== oldNodeCount || !graphData.value) {
          graphData.value = newData
          await nextTick()
          renderGraph()
        }
      }
    }
  } catch (err) {
    console.log('Graph data fetch:', err.message || 'not ready')
  }
}

// 轮询任务状态
const startPollingTask = (taskId) => {
  // 立即执行一次查询
  pollTaskStatus(taskId)
  
  // 然后定时轮询
  pollTimer = setInterval(() => {
    pollTaskStatus(taskId)
  }, 2000)
}

// 查询任务状态
const pollTaskStatus = async (taskId) => {
  try {
    const response = await getTaskStatus(taskId)
    
    if (response.success) {
      const task = response.data
      
      // 更新进度显示
      buildProgress.value = {
        progress: task.progress || 0,
        message: task.message || '处理中...'
      }
      
      console.log('Task status:', task.status, 'Progress:', task.progress)
      
      if (task.status === 'completed') {
        console.log('✅ 图谱构建完成，正在加载完整数据...')
        
        stopPolling()
        stopGraphPolling()
        currentPhase.value = 2
        
        // 更新进度显示为完成状态
        buildProgress.value = {
          progress: 100,
          message: '构建完成，正在加载图谱...'
        }
        
        // 重新加载项目数据获取 graph_id
        const projectResponse = await getProject(currentProjectId.value)
        if (projectResponse.success) {
          projectData.value = projectResponse.data
          
          // 最终加载完整图谱数据
          if (projectResponse.data.graph_id) {
            console.log('📊 加载完整图谱:', projectResponse.data.graph_id)
            await loadGraph(projectResponse.data.graph_id)
            console.log('✅ 图谱加载完成')
          }
        }
        
        // 清除进度显示
        buildProgress.value = null
      } else if (task.status === 'failed') {
        stopPolling()
        stopGraphPolling()
        error.value = '图谱构建失败: ' + (task.error || '未知错误')
        buildProgress.value = null
      }
    }
  } catch (err) {
    console.error('Poll task error:', err)
  }
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 加载图谱数据
const loadGraph = async (graphId) => {
  try {
    graphLoading.value = true
    const response = await getGraphData(graphId)
    
    if (response.success) {
      graphData.value = response.data
      await nextTick()
      renderGraph()
    }
  } catch (err) {
    console.error('Load graph error:', err)
  } finally {
    graphLoading.value = false
  }
}

// 渲染图谱 (D3.js) — 高级可视化版
const renderGraph = () => {
  if (!graphSvg.value || !graphData.value) {
    console.log('Cannot render: svg or data missing')
    return
  }
  
  const container = graphContainer.value
  if (!container) {
    console.log('Cannot render: container missing')
    return
  }
  
  const rect = container.getBoundingClientRect()
  const width = rect.width || 800
  const height = (rect.height || 600) - 60
  
  if (width <= 0 || height <= 0) return
  
  console.log('Rendering graph:', width, 'x', height)
  
  const svg = d3.select(graphSvg.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
  
  svg.selectAll('*').remove()

  const nodesData = graphData.value.nodes || []
  const edgesData = graphData.value.edges || []
  
  if (nodesData.length === 0) {
    svg.append('text')
      .attr('x', width / 2).attr('y', height / 2)
      .attr('text-anchor', 'middle').attr('fill', '#64748b')
      .attr('font-size', '14px')
      .text('等待图谱数据...')
    return
  }
  
  const nodeMap = {}
  nodesData.forEach(n => { nodeMap[n.uuid] = n })
  
  const nodes = nodesData.map(n => ({
    id: n.uuid,
    name: n.name || '未命名',
    type: n.labels?.find(l => l !== 'Entity' && l !== 'Node') || 'Entity',
    rawData: n
  }))
  
  const nodeIds = new Set(nodes.map(n => n.id))
  
  const edges = edgesData
    .filter(e => nodeIds.has(e.source_node_uuid) && nodeIds.has(e.target_node_uuid))
    .map(e => ({
      source: e.source_node_uuid,
      target: e.target_node_uuid,
      type: e.fact_type || e.name || 'RELATED_TO',
      rawData: {
        ...e,
        source_name: nodeMap[e.source_node_uuid]?.name || '未知',
        target_name: nodeMap[e.target_node_uuid]?.name || '未知'
      }
    }))
  
  // ── 计算每个节点的度数（连接数），用于决定大小 ──
  const degreeMap = {}
  nodes.forEach(n => { degreeMap[n.id] = 0 })
  edges.forEach(e => {
    const sid = typeof e.source === 'object' ? e.source.id : e.source
    const tid = typeof e.target === 'object' ? e.target.id : e.target
    if (degreeMap[sid] !== undefined) degreeMap[sid]++
    if (degreeMap[tid] !== undefined) degreeMap[tid]++
  })
  nodes.forEach(n => { n.degree = degreeMap[n.id] || 0 })
  
  // ── 视觉主题 ──
  const PALETTE = {
    // 鲜明、高饱和度、深色背景友好的配色
    'Person':          { fill: '#6366f1', glow: '#818cf8', icon: '👤' },
    'Organization':    { fill: '#f59e0b', glow: '#fbbf24', icon: '🏢' },
    'Government':      { fill: '#ef4444', glow: '#f87171', icon: '🏛️' },
    'Location':        { fill: '#10b981', glow: '#34d399', icon: '📍' },
    'Event':           { fill: '#f43f5e', glow: '#fb7185', icon: '📢' },
    'Policy':          { fill: '#8b5cf6', glow: '#a78bfa', icon: '📋' },
    'MediaOutlet':     { fill: '#ec4899', glow: '#f472b6', icon: '📺' },
    'AcademicLead':    { fill: '#14b8a6', glow: '#2dd4bf', icon: '🎓' },
    'University':      { fill: '#0ea5e9', glow: '#38bdf8', icon: '🏛️' },
    'Entity':          { fill: '#38bdf8', glow: '#7dd3fc', icon: '◆' },
  }
  const FALLBACK_COLORS = [
    { fill: '#6366f1', glow: '#818cf8', icon: '●' },
    { fill: '#f59e0b', glow: '#fbbf24', icon: '●' },
    { fill: '#8b5cf6', glow: '#a78bfa', icon: '●' },
    { fill: '#10b981', glow: '#34d399', icon: '●' },
    { fill: '#ef4444', glow: '#f87171', icon: '●' },
    { fill: '#ec4899', glow: '#f472b6', icon: '●' },
    { fill: '#0ea5e9', glow: '#38bdf8', icon: '●' },
    { fill: '#14b8a6', glow: '#2dd4bf', icon: '●' },
  ]
  // 度数分级配色：当所有节点同一类型时，按连接度分层着色
  const DEGREE_TIER_COLORS = [
    { fill: '#38bdf8', glow: '#7dd3fc', icon: '○' },  // 低度数：天蓝
    { fill: '#6366f1', glow: '#818cf8', icon: '◐' },  // 中度数：靛蓝
    { fill: '#a855f7', glow: '#c084fc', icon: '◑' },  // 中高度数：紫
    { fill: '#f43f5e', glow: '#fb7185', icon: '◉' },  // 高度数：玫红
    { fill: '#f59e0b', glow: '#fbbf24', icon: '●' },  // 最高度数：琥珀
  ]
  const types = [...new Set(nodes.map(n => n.type))]
  const typeColorMap = {}
  let fallbackIdx = 0
  types.forEach(t => {
    if (PALETTE[t]) {
      typeColorMap[t] = PALETTE[t]
    } else {
      typeColorMap[t] = FALLBACK_COLORS[fallbackIdx % FALLBACK_COLORS.length]
      fallbackIdx++
    }
  })
  // 是否所有节点同一类型（需要度数分级着色）
  const isSingleType = types.length <= 1
  // 为每个节点分配度数分级颜色
  if (isSingleType) {
    const sortedDeg = [...new Set(nodes.map(n => n.degree))].sort((a, b) => a - b)
    nodes.forEach(n => {
      const rank = sortedDeg.indexOf(n.degree)
      const tier = Math.min(Math.floor(rank / Math.max(sortedDeg.length / DEGREE_TIER_COLORS.length, 1)), DEGREE_TIER_COLORS.length - 1)
      n._color = DEGREE_TIER_COLORS[tier]
      n._colorId = `deg-${tier}`
    })
  }
  const getColor = (typeOrNode) => {
    // 如果传入的是节点对象且为单类型模式，使用度数分级颜色
    if (isSingleType && typeOrNode && typeof typeOrNode === 'object' && typeOrNode._color) {
      return typeOrNode._color
    }
    const type = typeof typeOrNode === 'string' ? typeOrNode : (typeOrNode?.type || 'Entity')
    return typeColorMap[type] || { fill: '#38bdf8', glow: '#7dd3fc' }
  }
  const getColorId = (d) => isSingleType && d._colorId ? d._colorId : d.type.replace(/\s+/g, '_')
  
  // 获取节点图标
  const getNodeIcon = (d) => {
    const colorInfo = getColor(d)
    return colorInfo.icon || '●'
  }
  
  // ── 节点半径：基于度数，高连接度的节点更大更醒目 ──
  const maxDeg = Math.max(...nodes.map(n => n.degree), 1)
  const nodeRadius = (d) => {
    const base = 7
    const scale = 18
    return base + scale * Math.sqrt(d.degree / maxDeg)
  }
  
  // ── SVG Defs: 径向渐变 + 辉光 + 箭头 ──
  const defs = svg.append('defs')
  
  // 创建增强辉光滤镜（多层叠加效果）
  const createEnhancedGlow = (id, c) => {
    // 外层大范围柔和大辉光
    const filterOuter = defs.append('filter')
      .attr('id', `glow-outer-${id}`)
      .attr('x', '-100%').attr('y', '-100%').attr('width', '300%').attr('height', '300%')
    filterOuter.append('feGaussianBlur')
      .attr('in', 'SourceGraphic')
      .attr('stdDeviation', '8')
      .attr('result', 'blur1')
    const mergeOuter = filterOuter.append('feMerge')
    mergeOuter.append('feMergeNode').attr('in', 'blur1')
    mergeOuter.append('feMergeNode').attr('in', 'SourceGraphic')
    
    // 内层精细辉光
    const filterInner = defs.append('filter')
      .attr('id', `glow-inner-${id}`)
      .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
    filterInner.append('feGaussianBlur')
      .attr('in', 'SourceGraphic')
      .attr('stdDeviation', '3')
      .attr('result', 'blur2')
    filterInner.append('feColorMatrix')
      .attr('in', 'blur2')
      .attr('type', 'matrix')
      .attr('values', `0 0 0 0 ${parseInt(c.glow.slice(1, 3), 16) / 255}  0 0 0 0 ${parseInt(c.glow.slice(3, 5), 16) / 255}  0 0 0 0 ${parseInt(c.glow.slice(5, 7), 16) / 255}  0 0 0 0.7 0`)
      .attr('result', 'colorBlur')
    const mergeInner = filterInner.append('feMerge')
    mergeInner.append('feMergeNode').attr('in', 'colorBlur')
    mergeInner.append('feMergeNode').attr('in', 'SourceGraphic')
  }
  
  // 创建渐变和辉光的辅助函数
  const createGradientAndGlow = (id, c) => {
    // 外层辉光
    createEnhancedGlow(id, c)
    
    // 主渐变（带高光效果，更通透）
    const grad = defs.append('radialGradient')
      .attr('id', `grad-${id}`)
      .attr('cx', '35%').attr('cy', '30%').attr('r', '65%')
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff').attr('stop-opacity', 0.95)
    grad.append('stop').attr('offset', '25%').attr('stop-color', c.glow).attr('stop-opacity', 0.85)
    grad.append('stop').attr('offset', '60%').attr('stop-color', c.fill).attr('stop-opacity', 0.9)
    grad.append('stop').attr('offset', '100%').attr('stop-color', d3.color(c.fill).darker(0.5)).attr('stop-opacity', 0.85)
    
    // 内环发光渐变（用于节点边缘光晕，更通透）
    const gradRing = defs.append('radialGradient')
      .attr('id', `grad-ring-${id}`)
      .attr('cx', '50%').attr('cy', '50%').attr('r', '50%')
    gradRing.append('stop').attr('offset', '70%').attr('stop-color', c.fill).attr('stop-opacity', 0)
    gradRing.append('stop').attr('offset', '90%').attr('stop-color', c.glow).attr('stop-opacity', 0.4)
    gradRing.append('stop').attr('offset', '100%').attr('stop-color', c.glow).attr('stop-opacity', 0.15)
  }
  // 每种类型创建渐变和辉光
  types.forEach(t => {
    createGradientAndGlow(t.replace(/\s+/g, '_'), getColor(t))
  })
  // 度数分级颜色也需要创建渐变和辉光
  if (isSingleType) {
    DEGREE_TIER_COLORS.forEach((c, i) => {
      createGradientAndGlow(`deg-${i}`, c)
    })
  }
  
  // 箭头标记
  defs.append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -4 8 8')
    .attr('refX', 20).attr('refY', 0)
    .attr('markerWidth', 6).attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-3.5L7,0L0,3.5')
    .attr('fill', 'rgba(100,116,139,0.35)')
  
  // ── 力导向布局（优化参数） ──
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id)
      .distance(d => {
        const sr = nodeRadius({ degree: degreeMap[typeof d.source === 'object' ? d.source.id : d.source] || 0 })
        const tr = nodeRadius({ degree: degreeMap[typeof d.target === 'object' ? d.target.id : d.target] || 0 })
        return sr + tr + 200
      })
      .strength(0.25))
    .force('charge', d3.forceManyBody().strength(d => -400 - d.degree * 80))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.02))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 45).strength(0.9))
    .force('x', d3.forceX(width / 2).strength(0.015))
    .force('y', d3.forceY(height / 2).strength(0.015))
    .alphaDecay(0.028)
    .velocityDecay(0.35)
  
  const g = svg.append('g')
  
  svg.call(d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.15, 6])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    }))
  
  // ── 绘制边：曲线 + 发光动画 ──
  const linkGroup = g.append('g').attr('class', 'links')
    .selectAll('g').data(edges).enter().append('g')
    .style('cursor', 'pointer')
    .on('click', (event, d) => { event.stopPropagation(); selectEdge(d.rawData) })
  
  // 边外层辉光（模糊的粗线）
  linkGroup.append('path')
    .attr('class', 'link-glow')
    .attr('fill', 'none')
    .attr('stroke', d => {
      const srcNode = typeof d.source === 'object' ? nodes.find(n => n.id === d.source.id) : null
      const c = getColor(srcNode || 'Entity')
      return c.glow || '#7dd3fc'
    })
    .attr('stroke-width', 6)
    .attr('stroke-opacity', 0.15)
    .attr('stroke-linecap', 'round')
  
  // 边发光尾迹（用于动画）
  linkGroup.append('path')
    .attr('class', 'link-trail')
    .attr('fill', 'none')
    .attr('stroke', d => {
      const srcNode = typeof d.source === 'object' ? nodes.find(n => n.id === d.source.id) : null
      const c = getColor(srcNode || 'Entity')
      return c.glow || '#7dd3fc'
    })
    .attr('stroke-width', 2.5)
    .attr('stroke-opacity', 0.5)
    .attr('stroke-linecap', 'round')
  
  // 曲线路径（主线条）
  const linkPath = linkGroup.append('path')
    .attr('class', 'link-main')
    .attr('fill', 'none')
    .attr('stroke', d => {
      const srcNode = typeof d.source === 'object' ? nodes.find(n => n.id === d.source.id) : null
      const c = getColor(srcNode || 'Entity')
      return c.glow || '#7dd3fc'
    })
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.4)
    .attr('marker-end', 'url(#arrow)')
  
  // 透明宽路径用于点击
  const linkHit = linkGroup.append('path')
    .attr('fill', 'none')
    .attr('stroke', 'transparent')
    .attr('stroke-width', 12)
  
  // 边标签（默认隐藏，hover 显示）
  const linkLabel = g.append('g').attr('class', 'link-labels')
    .selectAll('text').data(edges).enter().append('text')
    .attr('font-size', '8px')
    .attr('fill', 'rgba(148,163,184,0.6)')
    .attr('text-anchor', 'middle')
    .attr('font-family', "'Noto Sans SC', 'JetBrains Mono', sans-serif")
    .attr('opacity', 0)
    .text(d => {
      const t = d.type.replace(/_/g, ' ')
      return t.length > 18 ? t.substring(0, 15) + '...' : t
    })
  
  // ── 绘制节点 ──
  const node = g.append('g').attr('class', 'nodes')
    .selectAll('g').data(nodes).enter().append('g')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selectNode(d.rawData, getColor(d).fill)
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
  
  // 主圆：径向渐变 + 辉光滤镜
  node.append('circle')
    .attr('r', nodeRadius)
    .attr('fill', d => `url(#grad-${getColorId(d)})`)
    .attr('filter', d => `url(#glow-outer-${getColorId(d)})`)
    .attr('stroke', d => d3.color(getColor(d).fill).brighter(0.5))
    .attr('stroke-width', d => d.degree >= 5 ? 2.5 : d.degree >= 2 ? 1.8 : 1.2)
    .attr('stroke-opacity', 0.8)
    .attr('class', 'node-circle')

  // 外层大辉光环（所有节点，渐变透明度）
  node.append('circle')
    .attr('class', 'node-outer-glow')
    .attr('r', d => nodeRadius(d) + 12)
    .attr('fill', d => `url(#grad-ring-${getColorId(d)})`)
    .attr('opacity', d => Math.min(0.3 + d.degree * 0.05, 0.7))

  // 脉冲光环动画（仅高度数节点）
  node.filter(d => d.degree >= 3)
    .append('circle')
    .attr('class', 'node-pulse')
    .attr('r', d => nodeRadius(d) + 8)
    .attr('fill', 'none')
    .attr('stroke', d => getColor(d).glow)
    .attr('stroke-width', 2)
    .attr('stroke-opacity', 0)
    .attr('stroke-dasharray', '4 4')

  // 外层辉光圈（仅高度数节点）
  node.filter(d => d.degree >= 3).append('circle')
    .attr('r', d => nodeRadius(d) + 6)
    .attr('fill', 'none')
    .attr('stroke', d => getColor(d).glow)
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.5)
    .attr('stroke-dasharray', '3 3')

  // 节点内部图标
  node.append('text')
    .attr('class', 'node-icon')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('font-size', d => Math.max(8, nodeRadius(d) * 0.7))
    .attr('fill', '#ffffff')
    .attr('opacity', 0.9)
    .attr('pointer-events', 'none')
    .text(d => getNodeIcon(d))

  // 内层光点（高度数节点增加中心亮点）
  node.filter(d => d.degree >= 2)
    .append('circle')
    .attr('class', 'node-core')
    .attr('r', 2)
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('fill', '#ffffff')
    .attr('opacity', 0.8)
  
  // 节点标签：居中在节点下方，重要节点有背景药丸
  const labelG = g.append('g').attr('class', 'node-labels')
  
  // 只显示度数 >= 1 的节点标签（避免孤立点标签干扰）
  const labelData = nodes.filter(d => d.degree >= 1)
  const labelItem = labelG.selectAll('g').data(labelData).enter().append('g')
    .attr('pointer-events', 'none')
  
  // 标签文字
  labelItem.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', d => nodeRadius(d) + 14)
    .attr('font-size', d => d.degree >= 5 ? '11px' : d.degree >= 2 ? '10px' : '9px')
    .attr('font-family', "'Noto Sans SC', 'JetBrains Mono', sans-serif")
    .attr('font-weight', d => d.degree >= 5 ? 600 : 400)
    .attr('fill', d => {
      const c = getColor(d)
      return d.degree >= 2 ? c.glow : 'rgba(200,210,225,0.9)'
    })
    .attr('paint-order', 'stroke')
    .attr('stroke', 'rgba(10,10,26,0.7)')
    .attr('stroke-width', d => d.degree >= 3 ? 3 : 2)
    .attr('stroke-linejoin', 'round')
    .text(d => {
      const maxLen = d.degree >= 5 ? 16 : d.degree >= 2 ? 12 : 8
      return d.name.length > maxLen ? d.name.substring(0, maxLen) + '...' : d.name
    })
  
  // ── Hover 交互：高亮连通子图，边动画加速 ──
  node.on('mouseover', (event, d) => {
    const connected = new Set([d.id])
    const connectedEdges = new Set()
    edges.forEach((e, i) => {
      const sid = typeof e.source === 'object' ? e.source.id : e.source
      const tid = typeof e.target === 'object' ? e.target.id : e.target
      if (sid === d.id) { connected.add(tid); connectedEdges.add(i) }
      if (tid === d.id) { connected.add(sid); connectedEdges.add(i) }
    })
    
    // 节点淡入淡出 + 放大效果
    node.select('.node-circle')
      .transition().duration(200)
      .attr('opacity', n => connected.has(n.id) ? 1 : 0.12)
      .attr('r', n => connected.has(n.id) ? nodeRadius(n) * 1.15 : nodeRadius(n))
    
    // 外层辉光增强
    node.select('.node-outer-glow')
      .transition().duration(200)
      .attr('opacity', n => connected.has(n.id) ? Math.min(0.5 + n.degree * 0.08, 0.9) : 0)
    
    // 边高亮 + 增粗
    linkGroup.select('.link-main')
      .transition().duration(200)
      .attr('stroke-opacity', (e, i) => connectedEdges.has(i) ? 0.9 : 0.04)
      .attr('stroke-width', (e, i) => connectedEdges.has(i) ? 2.5 : 1.2)
    
    // 辉光边增强
    linkGroup.select('.link-glow')
      .transition().duration(200)
      .attr('stroke-opacity', (e, i) => connectedEdges.has(i) ? 0.35 : 0.05)
    
    // 尾迹边增强
    linkGroup.select('.link-trail')
      .transition().duration(200)
      .attr('stroke-opacity', (e, i) => connectedEdges.has(i) ? 0.8 : 0.2)
      .attr('stroke-width', (e, i) => connectedEdges.has(i) ? 4 : 2)
    
    // 标签显隐
    labelItem.select('text')
      .transition().duration(200)
      .attr('opacity', n => connected.has(n.id) ? 1 : 0.08)
    
    // 边标签：只显示关联的
    linkLabel.transition().duration(200)
      .attr('opacity', (e, i) => connectedEdges.has(i) ? 0.9 : 0)
  })
  .on('mouseout', () => {
    node.select('.node-circle')
      .transition().duration(300)
      .attr('opacity', 1)
      .attr('r', nodeRadius)
    
    node.select('.node-outer-glow')
      .transition().duration(300)
      .attr('opacity', d => Math.min(0.3 + d.degree * 0.05, 0.7))
    
    linkGroup.select('.link-main')
      .transition().duration(300)
      .attr('stroke-opacity', 0.4)
      .attr('stroke-width', 1.5)
    
    linkGroup.select('.link-glow')
      .transition().duration(300)
      .attr('stroke-opacity', 0.15)
    
    linkGroup.select('.link-trail')
      .transition().duration(300)
      .attr('stroke-opacity', 0.5)
      .attr('stroke-width', 2.5)
    
    labelItem.select('text')
      .transition().duration(300)
      .attr('opacity', 1)
    
    linkLabel.transition().duration(300)
      .attr('opacity', 0)
  })
  
  // 点击空白关闭
  svg.on('click', () => { closeDetailPanel() })
  
  // ── 曲线路径计算 ──
  function linkArc(d) {
    const sx = d.source.x, sy = d.source.y
    const tx = d.target.x, ty = d.target.y
    const dx = tx - sx, dy = ty - sy
    const dr = Math.sqrt(dx * dx + dy * dy) * 1.5
    return `M${sx},${sy}A${dr},${dr} 0 0,1 ${tx},${ty}`
  }
  
  // ── tick ──
  simulation.on('tick', () => {
    linkPath.attr('d', linkArc)
    linkHit.attr('d', linkArc)
    
    // 更新辉光路径
    linkGroup.select('.link-glow').attr('d', linkArc)
    
    // 更新尾迹路径
    linkGroup.select('.link-trail').attr('d', linkArc)
    
    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 6)
    
    node.attr('transform', d => `translate(${d.x},${d.y})`)
    labelItem.attr('transform', d => `translate(${d.x},${d.y})`)
  })
  
  function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  }
  function dragged(event) {
    event.subject.fx = event.x
    event.subject.fy = event.y
  }
  function dragended(event) {
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  }
  
  // ── 内嵌图例（左下角） ──
  const legendItems = isSingleType
    ? DEGREE_TIER_COLORS.map((c, i) => ({
        color: c.fill,
        label: ['低连接度', '中连接度', '中高连接度', '高连接度', '核心节点'][i]
      }))
    : types.map(t => ({ color: getColor(t).fill, label: t }))

  const legendG = svg.append('g')
    .attr('transform', `translate(16, ${height - legendItems.length * 22 - 16})`)
  
  legendG.append('rect')
    .attr('x', -8).attr('y', -8)
    .attr('width', 140)
    .attr('height', legendItems.length * 22 + 12)
    .attr('rx', 6)
    .attr('fill', 'rgba(10,10,26,0.6)')
    .attr('stroke', 'rgba(100,116,139,0.2)')
    .attr('stroke-width', 1)
  
  legendItems.forEach((item, i) => {
    const row = legendG.append('g').attr('transform', `translate(0, ${i * 22})`)
    row.append('circle')
      .attr('r', 5)
      .attr('cx', 6).attr('cy', 0)
      .attr('fill', item.color)
    row.append('text')
      .attr('x', 18).attr('dy', 4)
      .attr('font-size', '10px')
      .attr('fill', 'rgba(203,213,225,0.85)')
      .attr('font-family', "'Noto Sans SC', sans-serif")
      .text(item.label)
  })
}

// 监听图谱数据变化
watch(graphData, () => {
  if (graphData.value) {
    nextTick(() => renderGraph())
  }
})

// 当从 Step 3+ 切回 Step 1/2 时，左侧图谱面板由 v-if 重新创建，
// 但 graphData 引用未变不会触发上面的 watcher，需要手动重新渲染
// 需等待 panel-slide 过渡动画（300ms）结束后再渲染，否则容器宽度为 0。
watch(currentStep, (newStep, oldStep) => {
  if (newStep <= 2 && oldStep > 2 && graphData.value) {
    setTimeout(() => {
      nextTick(() => renderGraph())
    }, 360)
  }
})

// 生命周期
onMounted(() => {
  // 初始化布局宽度 CSS 变量
  document.documentElement.style.setProperty('--left-panel-width', leftPanelWidth.value + '%')
  initProject()
})

onUnmounted(() => {
  stopPolling()
  stopGraphPolling()
})
</script>

<style scoped>
/* 变量 */
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF6B35;
  --gray-light: #F5F5F5;
  --gray-border: #E0E0E0;
  --gray-text: #666666;
}

.process-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #0d1525 50%, #0a1628 100%);
  font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
  overflow: hidden; /* Prevent body scroll in fullscreen */
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* 导航栏 */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: linear-gradient(90deg, #e6f4f3 0%, #eef7fb 30%, #eff3fc 60%, #f3f0f9 100%);
  backdrop-filter: blur(20px);
  color: #3A5A6A;
  z-index: 100;
  position: relative;
  border-bottom: 1px solid rgba(115, 168, 185, 0.2);
}

.branch-context-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 24px;
  background: linear-gradient(90deg, #e6f4f3 0%, #eef7fb 30%, #eff3fc 60%, #f3f0f9 100%);
  border-bottom: 1px solid rgba(115, 168, 185, 0.2);
  font-size: 12px;
  color: #94a3b8;
  z-index: 99;
  position: relative;
}

.branch-ctx-icon {
  font-size: 15px;
  color: #60a5fa;
}

.branch-ctx-type {
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  background: rgba(59,130,246,0.15);
  color: #60a5fa;
}

.branch-ctx-type.recalibrated { background: rgba(245,158,11,0.15); color: #f59e0b; }
.branch-ctx-type.intervention_a { background: rgba(16,185,129,0.15); color: #10b981; }
.branch-ctx-type.intervention_b { background: rgba(139,92,246,0.15); color: #8b5cf6; }
.branch-ctx-type.intervention_c { background: rgba(236,72,153,0.15); color: #ec4899; }

.branch-ctx-label {
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.branch-ctx-sep {
  color: rgba(148,163,184,0.3);
}

.branch-ctx-baseline {
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

.nav-brand-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-brand {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.2s;
  background: linear-gradient(135deg, #73A8B9, #3A5A6A);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-brand:hover {
  opacity: 0.8;
  transform: translateX(2px);
}

.home-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 1px solid rgba(115, 168, 185, 0.3);
  border-radius: 6px;
  background: rgba(115, 168, 185, 0.1);
  color: #3A5A6A;
  cursor: pointer;
  transition: all 0.2s ease;
}

.home-btn:hover {
  background: rgba(115, 168, 185, 0.25);
  border-color: rgba(115, 168, 185, 0.5);
  transform: translateY(-1px);
}

.incident-back-btn {
  width: auto; padding: 0 10px; gap: 2px; font-size: 11px;
  background: rgba(34, 197, 94, 0.1); border-color: rgba(34, 197, 94, 0.3); color: #22c55e;
}

.incident-back-btn:hover {
  background: rgba(34, 197, 94, 0.25); border-color: rgba(34, 197, 94, 0.5);
}

.nav-center {
  display: flex;
  align-items: center;
  gap: 12px;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.nav-step-dots {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-left: 4px;
}

.nav-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(115, 168, 185, 0.3);
  transition: all 0.25s ease;
}

.nav-dot.active {
  background: #73A8B9;
  box-shadow: 0 0 8px rgba(115, 168, 185, 0.8);
  transform: scale(1.3);
}

.nav-dot.completed {
  background: #5C9EAF;
  box-shadow: 0 0 6px rgba(115, 168, 185, 0.5);
}

.step-badge {
  background: linear-gradient(135deg, #73A8B9, #5C9EAF);
  color: #fff;
  padding: 2px 8px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  border-radius: 2px;
  box-shadow: 0 0 15px rgba(115, 168, 185, 0.4);
}

.step-name {
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  color: #3A5A6A;
  font-weight: 500;
}

.nav-status {
  display: flex;
  align-items: center;
  color: #3A5A6A;
  font-size: 0.8rem;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(115, 168, 185, 0.4);
  margin-right: 8px;
}

.status-dot.processing {
  background: #73A8B9;
  box-shadow: 0 0 10px rgba(115, 168, 185, 0.8);
  animation: pulse 1.5s infinite;
}

.status-dot.completed {
  background: #5C9EAF;
  box-shadow: 0 0 10px rgba(92, 158, 175, 0.8);
}

.status-dot.error {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.8);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 节点脉冲动画 */
.node-pulse {
  animation: pulse-expand 2s ease-in-out infinite;
}

@keyframes pulse-expand {
  0%, 100% {
    transform: scale(1);
    opacity: 0.6;
    stroke-width: 2;
  }
  50% {
    transform: scale(1.4);
    opacity: 0;
    stroke-width: 0.5;
  }
}

/* 节点图标悬浮发光效果 */
.node-icon {
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.95));
  transition: all 0.3s ease;
}

/* 边流动动画 */
.link-main {
  stroke-dasharray: 0;
  animation: edge-glow 3s ease-in-out infinite;
}

@keyframes edge-glow {
  0%, 100% {
    stroke-opacity: 0.3;
  }
  50% {
    stroke-opacity: 0.5;
  }
}

/* 边尾迹动画 */
.link-trail {
  stroke-dasharray: 6 12;
  animation: flow-dash 1.2s linear infinite;
}

@keyframes flow-dash {
  0% {
    stroke-dashoffset: 0;
  }
  100% {
    stroke-dashoffset: -18;
  }
}

/* 高度数节点外层辉光持续呼吸效果 */
.node-outer-glow {
  animation: outer-glow-breathe 3s ease-in-out infinite;
}

@keyframes outer-glow-breathe {
  0%, 100% {
    opacity: 0.2;
    transform: scale(1);
  }
  50% {
    opacity: 0.4;
    transform: scale(1.05);
  }
}

/* 节点hover时的放大效果 */
.nodes g {
  transition: transform 0.2s ease;
}

.nodes g:hover .node-circle {
  filter: brightness(1.25) drop-shadow(0 0 10px currentColor);
}

.nodes g:hover .node-icon {
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 1));
  transform: scale(1.1);
}

.nodes g:hover .node-outer-glow {
  filter: brightness(1.3);
}

.nodes g:hover .link-main,
.nodes g:hover .link-glow,
.nodes g:hover .link-trail {
  filter: brightness(1.2) drop-shadow(0 0 4px currentColor);
}

.status-text {
  font-size: 0.75rem;
  color: #3A5A6A;
  opacity: 0.7;
}

/* 主内容区 */
.main-content {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}

/* 左侧面板 - 50% default（冰蓝浅色底，与右侧工作台协调） */
/* 使用 CSS 变量实现即时响应式更新 */
.left-panel {
  flex: none;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(173, 196, 214, 0.45);
  /* 正常状态有过渡效果 */
  transition: opacity 0.35s ease;
  background: linear-gradient(165deg, #f4f9fb 0%, #eef5f8 45%, #e6f0f4 100%);
  z-index: 5;
  position: relative;
  overflow: hidden;
  /* 使用 CSS 变量控制宽度，实现即时响应 */
  width: var(--left-panel-width, 70%);
}

/* 拖拽时禁用宽度过渡以实现即时响应 */
body.is-resizing .left-panel {
  transition: none !important;
}

/* 左侧面板与右侧面板之间的柔和分隔 */
.left-panel::after {
  content: '';
  position: absolute;
  top: 0;
  right: -1px;
  width: 80px;
  height: 100%;
  background: linear-gradient(
    to right,
    rgba(180, 200, 218, 0) 0%,
    rgba(180, 200, 218, 0.06) 50%,
    rgba(180, 200, 218, 0.12) 100%
  );
  pointer-events: none;
  z-index: 2;
}

/* 图谱区：深色背景，让辉光节点更醒目 */
.graph-view {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
  min-width: 240px;
  background:
    /* 星空粒子效果 */
    radial-gradient(1px 1px at 20% 30%, rgba(255, 255, 255, 0.8) 0%, transparent 100%),
    radial-gradient(1px 1px at 40% 70%, rgba(255, 255, 255, 0.6) 0%, transparent 100%),
    radial-gradient(1px 1px at 60% 20%, rgba(255, 255, 255, 0.7) 0%, transparent 100%),
    radial-gradient(1px 1px at 80% 50%, rgba(255, 255, 255, 0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 10% 80%, rgba(255, 255, 255, 0.6) 0%, transparent 100%),
    radial-gradient(1px 1px at 90% 10%, rgba(255, 255, 255, 0.7) 0%, transparent 100%),
    radial-gradient(1px 1px at 50% 90%, rgba(255, 255, 255, 0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 30% 50%, rgba(255, 255, 255, 0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 70% 80%, rgba(255, 255, 255, 0.6) 0%, transparent 100%),
    radial-gradient(1px 1px at 15% 60%, rgba(255, 255, 255, 0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 85% 35%, rgba(255, 255, 255, 0.4) 0%, transparent 100%),
    radial-gradient(1px 1px at 45% 15%, rgba(255, 255, 255, 0.6) 0%, transparent 100%),
    radial-gradient(1px 1px at 25% 95%, rgba(255, 255, 255, 0.5) 0%, transparent 100%),
    radial-gradient(1px 1px at 75% 45%, rgba(255, 255, 255, 0.4) 0%, transparent 100%),
    /* 星云渐变 */
    radial-gradient(ellipse 80% 60% at 50% 50%, rgba(30, 40, 70, 0.8) 0%, transparent 70%),
    radial-gradient(ellipse 100% 80% at 20% 20%, rgba(60, 40, 90, 0.3) 0%, transparent 50%),
    radial-gradient(ellipse 80% 100% at 80% 80%, rgba(40, 60, 90, 0.25) 0%, transparent 60%),
    /* 主背景渐变 */
    linear-gradient(180deg, #0a0a1a 0%, #0d1020 30%, #0a0e1f 60%, #080818 100%);
  border-radius: 0 0 12px 0;
  overflow: hidden;
}

/* 星空动画层 */
.graph-view::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(2px 2px at 12% 42%, rgba(255, 255, 255, 0.9) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 67% 23%, rgba(200, 220, 255, 0.7) 0%, transparent 100%),
    radial-gradient(2px 2px at 88% 67%, rgba(255, 255, 255, 0.8) 0%, transparent 100%),
    radial-gradient(1px 1px at 33% 88%, rgba(180, 200, 255, 0.6) 0%, transparent 100%),
    radial-gradient(1.5px 1.5px at 55% 12%, rgba(255, 255, 255, 0.7) 0%, transparent 100%),
    radial-gradient(1px 1px at 78% 92%, rgba(200, 220, 255, 0.5) 0%, transparent 100%),
    radial-gradient(2px 2px at 5% 75%, rgba(255, 255, 255, 0.8) 0%, transparent 100%),
    radial-gradient(1px 1px at 92% 8%, rgba(180, 200, 255, 0.6) 0%, transparent 100%);
  animation: twinkle 4s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

/* 星云光效 */
.graph-view::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 40% 30% at 30% 40%, rgba(100, 80, 180, 0.15) 0%, transparent 70%),
    radial-gradient(ellipse 35% 40% at 70% 60%, rgba(60, 100, 160, 0.12) 0%, transparent 70%),
    radial-gradient(ellipse 50% 25% at 50% 80%, rgba(80, 120, 180, 0.1) 0%, transparent 60%);
  animation: nebula-drift 20s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes twinkle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

@keyframes nebula-drift {
  0%, 100% { transform: scale(1) translate(0, 0); opacity: 1; }
  33% { transform: scale(1.05) translate(5px, -5px); opacity: 0.9; }
  66% { transform: scale(0.98) translate(-3px, 3px); opacity: 1; }
}

.left-panel.full-screen {
  width: 100%;
  border-right: none;
}

.left-panel.full-screen::after {
  display: none;
}

/* 左侧图谱：大面积柔光 + 椭圆轮廓 + +/× 符号铺底（参考浅色科技风） */
.graph-left-atmosphere {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.gl-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(36px);
  opacity: 0.55;
}

.gl-glow-a {
  top: 4%;
  left: 8%;
  width: 280px;
  height: 220px;
  background: radial-gradient(circle, rgba(186, 220, 240, 0.55) 0%, rgba(186, 220, 240, 0) 68%);
}

.gl-glow-b {
  top: 18%;
  right: 4%;
  width: 340px;
  height: 260px;
  background: radial-gradient(circle, rgba(200, 228, 242, 0.5) 0%, rgba(200, 228, 242, 0) 65%);
}

.gl-glow-c {
  bottom: 12%;
  left: 28%;
  width: 400px;
  height: 240px;
  background: radial-gradient(circle, rgba(176, 212, 232, 0.45) 0%, rgba(176, 212, 232, 0) 62%);
}

.gl-ellipses {
  position: absolute;
  inset: -5%;
  opacity: 1;
}

.gl-ellipses::before,
.gl-ellipses::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(100, 130, 155, 0.07);
  pointer-events: none;
}

.gl-ellipses::before {
  width: 118%;
  height: 72%;
  left: -9%;
  top: 8%;
  transform: rotate(-7deg);
}

.gl-ellipses::after {
  width: 95%;
  height: 88%;
  left: 2%;
  top: 2%;
  border-color: rgba(120, 150, 175, 0.05);
  transform: rotate(4deg);
}

.gl-symbol-pattern {
  position: absolute;
  inset: 0;
  opacity: 0.42;
  background-image:
    radial-gradient(circle at 11% 21%, rgba(110, 140, 165, 0.14) 0 1.1px, transparent 1.4px),
    radial-gradient(circle at 84% 36%, rgba(110, 140, 165, 0.11) 0 1px, transparent 1.3px),
    radial-gradient(circle at 38% 79%, rgba(110, 140, 165, 0.12) 0 1px, transparent 1.35px),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Cg fill='none' stroke='%2394a8b8' stroke-linecap='round' stroke-width='1.25'%3E%3Cpath d='M30 38h11M35.5 33v11' opacity='0.42'/%3E%3Cpath d='M54 22l7.5 7.5m0-7.5L54 29.5' opacity='0.3'/%3E%3Cpath d='M138 52h10M143 47v10' opacity='0.36'/%3E%3Cpath d='M172 78l8 8m0-8l-8 8' opacity='0.28'/%3E%3Cpath d='M22 128h9M26.5 123v10' opacity='0.32'/%3E%3Cpath d='M92 98l6.5 6.5m0-6.5L92 104.5' opacity='0.38'/%3E%3Cpath d='M158 134h9M162.5 129v10' opacity='0.34'/%3E%3Cpath d='M48 170l7 7m0-7l-7 7' opacity='0.26'/%3E%3Cpath d='M124 174h10M129 169v10' opacity='0.33'/%3E%3Cpath d='M12 88h8M16 84v8' opacity='0.25'/%3E%3Cpath d='M180 24l6 6m0-6l-6 6' opacity='0.22'/%3E%3C/g%3E%3C/svg%3E");
  background-size: auto, auto, auto, 200px 200px;
  background-repeat: no-repeat, no-repeat, no-repeat, repeat;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-bottom: 1px solid rgba(173, 192, 210, 0.55);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(14px);
  height: 50px;
  z-index: 10;
  position: relative;
}

/* 左栏顶栏底边细线，与参考图一致 */
.panel-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(
    to right,
    rgba(59, 130, 246, 0.25) 0%,
    rgba(125, 170, 200, 0.2) 45%,
    rgba(180, 200, 218, 0.12) 100%
  );
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-deco {
  color: #2563eb;
  font-size: 0.8rem;
}

.header-title {
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: #1e3a5f;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 0.75rem;
  color: #5c728a;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-val {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.stat-divider {
  color: rgba(100, 125, 150, 0.35);
}

.action-buttons {
    display: flex;
    align-items: center;
    gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
  color: #5c728a;
  border-radius: 6px;
}

.action-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.08);
  color: #1e40af;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.icon-refresh, .icon-fullscreen {
  font-size: 1rem;
  line-height: 1;
}

.icon-refresh.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 图谱容器 */
.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: transparent;
  z-index: 1;
}

/* 图谱容器底部与图例区的柔和过渡 */
.graph-container::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 64px;
  background: linear-gradient(
    to top,
    rgba(10, 16, 30, 0.6) 0%,
    rgba(12, 18, 32, 0.2) 50%,
    transparent 100%
  );
  pointer-events: none;
  z-index: 2;
}

.graph-loading,
.graph-waiting,
.graph-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  z-index: 50;
}

/* 科技风发光环形加载动画 */
.loading-animation {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 24px;
}

.loading-ring {
  position: absolute;
  border-radius: 50%;
  animation: ring-rotate 2s linear infinite;
}

.loading-ring:nth-child(1) {
  width: 120px;
  height: 120px;
  top: 0;
  left: 0;
  border: 3px solid transparent;
  border-top-color: rgba(59, 130, 246, 0.8);
  box-shadow: 0 0 30px rgba(59, 130, 246, 0.5), inset 0 0 30px rgba(59, 130, 246, 0.1);
}

.loading-ring:nth-child(2) {
  width: 90px;
  height: 90px;
  top: 15px;
  left: 15px;
  border: 2px solid transparent;
  border-right-color: rgba(6, 182, 212, 0.8);
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
  animation-direction: reverse;
  animation-duration: 1.5s;
}

.loading-ring:nth-child(3) {
  width: 60px;
  height: 60px;
  top: 30px;
  left: 30px;
  border: 2px solid transparent;
  border-bottom-color: rgba(139, 92, 246, 0.7);
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);
  animation-duration: 1s;
}

.loading-ring:nth-child(4) {
  width: 30px;
  height: 30px;
  top: 45px;
  left: 45px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.8) 0%, rgba(6, 182, 212, 0.4) 100%);
  border: none;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.6), 0 0 40px rgba(6, 182, 212, 0.4);
  animation: pulse-glow 1s ease-in-out infinite;
}

@keyframes ring-rotate {
  to { transform: rotate(360deg); }
}

@keyframes pulse-glow {
  0%, 100% { 
    transform: scale(1);
    opacity: 1;
  }
  50% { 
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.loading-text,
.waiting-text {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 8px;
  font-weight: 500;
  text-shadow: 0 0 20px rgba(59, 130, 246, 0.5);
}

.graph-container .loading-text,
.graph-container .waiting-text {
  color: #94a3b8;
  text-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
}

.waiting-hint {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.graph-container .waiting-hint {
  color: #64748b;
  text-shadow: none;
}

.waiting-icon {
  margin-bottom: 24px;
}

.tech-ring-icon {
  width: 120px;
  height: 120px;
  filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.5));
}

.graph-svg {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: block;
  background: transparent;
}

.graph-building-hint {
  position: absolute;
  z-index: 2;
  bottom: 16px;
  left: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 107, 53, 0.1);
  border: 1px solid #FF6B35;
  font-size: 0.8rem;
  color: #FF6B35;
}

.building-dot {
  width: 8px;
  height: 8px;
  background: #FF6B35;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

/* 节点/边详情面板 */
.detail-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 320px;
  max-height: calc(100% - 32px);
  background: rgba(12, 18, 32, 0.92);
  border: 1px solid rgba(99, 102, 241, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 16px rgba(99, 102, 241, 0.1);
  backdrop-filter: blur(16px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: 100;
  border-radius: 8px;
}

.detail-panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(15, 23, 42, 0.8);
  border-bottom: 1px solid rgba(99, 102, 241, 0.15);
}

.detail-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
}

.detail-badge {
  padding: 2px 10px;
  font-size: 0.75rem;
  color: #fff;
  border-radius: 2px;
}

.detail-close {
  margin-left: auto;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #999;
  cursor: pointer;
  transition: color 0.2s;
}

.detail-close:hover {
  color: #e2e8f0;
}

.detail-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
}

.detail-label {
  font-size: 0.8rem;
  color: #64748b;
  min-width: 70px;
  flex-shrink: 0;
}

.detail-value {
  font-size: 0.85rem;
  color: #cbd5e1;
  word-break: break-word;
}

.detail-value.uuid {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #94a3b8;
}

.detail-section {
  margin-bottom: 12px;
}

.detail-summary {
  margin: 8px 0 0 0;
  font-size: 0.85rem;
  color: #cbd5e1;
  line-height: 1.6;
  padding: 10px;
  background: rgba(15, 23, 42, 0.6);
  border-left: 3px solid #6366f1;
}

.detail-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.label-tag {
  padding: 2px 8px;
  font-size: 0.75rem;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: #a5b4fc;
  border-radius: 3px;
}

/* 边详情关系展示 */
.edge-relation {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 6px;
}

.edge-source,
.edge-target {
  font-size: 0.85rem;
  font-weight: 500;
  color: #e2e8f0;
}

.edge-arrow {
  color: #64748b;
}

.edge-type {
  padding: 2px 8px;
  font-size: 0.75rem;
  background: #6366f1;
  color: #fff;
  border-radius: 3px;
}

.detail-value.highlight {
  font-weight: 600;
  color: #f1f5f9;
}

.detail-subtitle {
  font-size: 0.9rem;
  font-weight: 600;
  color: #e2e8f0;
  margin: 16px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.15);
}

/* Properties 属性列表 */
.properties-list {
  margin-top: 8px;
  padding: 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 6px;
}

.property-item {
  display: flex;
  margin-bottom: 6px;
  font-size: 0.85rem;
}

.property-item:last-child {
  margin-bottom: 0;
}

.property-key {
  color: #64748b;
  margin-right: 8px;
  font-family: 'JetBrains Mono', monospace;
}

.property-value {
  color: #cbd5e1;
  word-break: break-word;
}

/* Episodes 列表 */
.episodes-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.episode-tag {
  display: block;
  padding: 6px 10px;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(99, 102, 241, 0.15);
  color: #94a3b8;
  word-break: break-all;
  border-radius: 4px;
}

.error-icon {
  font-size: 2rem;
  display: block;
  margin-bottom: 10px;
}

/* 图谱图例（白底条，与参考图一致） */
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(200, 215, 228, 0.85);
  background: #ffffff;
  backdrop-filter: none;
  position: relative;
  z-index: 4;
}

.graph-legend::before,
.graph-legend::after {
  display: none;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.06);
}

.legend-label {
  color: #334155;
}

.legend-count {
  color: #94a3b8;
}

/* 右侧面板 - 50% default */
/* 使用 CSS 变量实现即时响应式更新 */
.right-panel {
  flex: none;
  display: flex;
  flex-direction: column;
  background: #F8FAFC;
  box-shadow: -4px 0 24px rgba(115, 168, 185, 0.08);
  /* 正常状态有过渡效果，但拖拽时禁用 */
  transition: opacity 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  opacity: 1;
  position: relative;
  /* 使用 CSS 变量控制宽度，实现即时响应 */
  width: calc(100% - var(--left-panel-width, 70%));
}

/* 拖拽时禁用宽度过渡以实现即时响应 */
body.is-resizing .right-panel {
  transition: none !important;
}

/* 右侧面板左侧渐变边框 - 与左侧深色面板过渡 */
.right-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(
    to bottom,
    rgba(59, 130, 246, 0.5) 0%,
    rgba(6, 182, 212, 0.4) 30%,
    rgba(115, 168, 185, 0.3) 60%,
    rgba(115, 168, 185, 0.2) 100%
  );
  z-index: 10;
}

.right-panel.hidden {
  width: 0;
  opacity: 0;
  transform: translateX(20px);
  pointer-events: none;
}

/* Step 3-5：右侧全屏 */
.right-panel.full-screen-step {
  flex: 1;
  width: auto !important;
}

/* Step 导航条（旧实现已替换为“流程卡片”） */
.step-nav-bar,
.step-nav-item,
.step-content {
  display: none;
}

.right-panel .panel-header.dark-header {
  background: linear-gradient(90deg, #e6f4f3 0%, #eef7fb 30%, #eff3fc 60%, #f3f0f9 100%);
  backdrop-filter: blur(20px);
  color: #3A5A6A;
  border-bottom: 1px solid rgba(115, 168, 185, 0.2);
  position: relative;
}

/* 右侧面板header顶部渐变 - 呼应左侧极光色调 */
.right-panel .panel-header.dark-header::after {
  content: '';
  position: absolute;
  top: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(
    to right,
    rgba(59, 130, 246, 0.4) 0%,
    rgba(6, 182, 212, 0.3) 30%,
    rgba(115, 168, 185, 0.2) 60%,
    rgba(115, 168, 185, 0.1) 100%
  );
}

.right-panel .header-icon {
  color: #73A8B9;
  margin-right: 8px;
}

/* ── Step dot 指示器 ── */
.step-dots {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
}

.step-dot-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  position: relative;
  flex: 1;
  min-width: 64px;
}

.step-dot-wrap:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 12px;
  left: calc(50% + 12px);
  width: calc(100% - 8px);
  height: 1px;
  background: rgba(255, 255, 255, 0.12);
}

.step-dot-wrap:last-child::before {
  display: none;
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.25s ease;
  border: 1.5px solid rgba(115, 168, 185, 0.3);
  background: rgba(230, 242, 247, 0.6);
  color: #73A8B9;
}

.step-dot.active {
  background: linear-gradient(135deg, #73A8B9, #5C9EAF);
  border-color: transparent;
  color: #fff;
  box-shadow: 0 0 14px rgba(115, 168, 185, 0.6), 0 0 28px rgba(115, 168, 185, 0.3);
  transform: scale(1.1);
  animation: dot-pulse 1.8s ease-in-out infinite;
}

.step-dot.completed {
  background: rgba(92, 158, 175, 0.2);
  border-color: rgba(92, 158, 175, 0.5);
  color: #5C9EAF;
  box-shadow: 0 0 8px rgba(92, 158, 175, 0.3);
}

.step-dot.pending {
  opacity: 0.5;
}

.dot-check,
.dot-num {
  line-height: 1;
}

.step-dot-label {
  font-size: 0.6rem;
  color: rgba(115, 168, 185, 0.6);
  white-space: nowrap;
  transition: color 0.2s;
  letter-spacing: 0.02em;
}

.step-dot-wrap:has(.step-dot.active) .step-dot-label,
.step-dot-wrap:has(.step-dot.completed) .step-dot-label {
  color: #3A5A6A;
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 14px rgba(115, 168, 185, 0.6), 0 0 28px rgba(115, 168, 185, 0.3); }
  50%       { box-shadow: 0 0 20px rgba(115, 168, 185, 0.9), 0 0 40px rgba(115, 168, 185, 0.5); }
}

/* ── 本体/图谱进度条 ── */
.progress-strip {
  padding: 10px 20px;
  background: rgba(115, 168, 185, 0.1);
  border-bottom: 1px solid rgba(115, 168, 185, 0.15);
}

.strip-ontology {
  display: flex;
  align-items: center;
  gap: 10px;
}

.strip-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(115, 168, 185, 0.2);
  border-top-color: #73A8B9;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.strip-text {
  font-size: 0.75rem;
  color: #3A5A6A;
  font-family: 'JetBrains Mono', monospace;
}

.strip-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.7rem;
  color: #3A5A6A;
  opacity: 0.6;
  margin-bottom: 5px;
  font-family: 'JetBrains Mono', monospace;
}

.strip-pct {
  color: #73A8B9;
  font-weight: 600;
}

.strip-bar {
  height: 3px;
  background: rgba(115, 168, 185, 0.15);
  border-radius: 2px;
  overflow: hidden;
}

.strip-fill {
  height: 100%;
  background: linear-gradient(90deg, #73A8B9, #5C9EAF);
  border-radius: 2px;
  transition: width 0.5s ease;
  box-shadow: 0 0 8px rgba(115, 168, 185, 0.5);
}

.strip-done {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.72rem;
  color: #3A5A6A;
}

.strip-done-icon {
  color: #5C9EAF;
  font-size: 0.6rem;
}

.strip-done-text {
  font-family: 'JetBrains Mono', monospace;
  color: #3A5A6A;
  opacity: 0.7;
}

/* Step 2 与 Step 1 共用外层包裹 */
.workbench-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.14), transparent 28%),
    radial-gradient(circle at bottom left, rgba(191, 219, 254, 0.4), transparent 34%),
    linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
}

.workbench-wrapper .scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: #93c5fd #e0effe;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar {
  width: 8px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-track {
  background: #e0effe;
  border-radius: 999px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #93c5fd, #60a5fa);
  border: 2px solid #e0effe;
  border-radius: 999px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #60a5fa, #3b82f6);
}

/* ── Step 内容区 ── */
.step-area {
  flex: 1;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.step-area-inner {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: #93c5fd #e0effe;
  align-items: stretch;
}

.step-area-inner::-webkit-scrollbar {
  width: 8px;
}

.step-area-inner::-webkit-scrollbar-track {
  background: #e0effe;
  border-radius: 999px;
}

.step-area-inner::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #93c5fd, #60a5fa);
  border: 2px solid #e0effe;
  border-radius: 999px;
}

.step-area-inner::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #60a5fa, #3b82f6);
}

/* Step 3-5 全屏时：内容占满，隐藏内部终端 */
.right-panel.full-screen-step :deep(.system-logs) {
  display: none !important;
}

/* Step 1-2 分屏时：隐藏各组件底部终端 */
.step-area :deep(.system-logs) {
  display: none !important;
}

/* Step 3-5 全屏时：Step 组件本身背景透明，全屏展示 */
.right-panel.full-screen-step :deep(.simulation-panel),
.right-panel.full-screen-step :deep(.report-panel),
.right-panel.full-screen-step :deep(.interaction-panel) {
  background: transparent;
  height: 100%;
}

/* Step 切换动画：向左滑入 */
.step-slide-enter-active,
.step-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.step-slide-enter-from {
  opacity: 0;
  transform: translateX(18px);
}

.step-slide-leave-to {
  opacity: 0;
  transform: translateX(-18px);
}

/* 左侧面板滑入/出动画 */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: width 0.3s ease, opacity 0.3s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  width: 0;
  opacity: 0;
}

/* 可拖拽分隔条 */
.resize-handle {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  margin-left: -6px;
  width: 12px;
  height: 64px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.08) 0%, rgba(115, 168, 185, 0.15) 50%, rgba(59, 130, 246, 0.08) 100%);
  border-radius: 6px;
  cursor: col-resize;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.15s ease, background 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.1);
  /* 使用 CSS 变量动态控制位置 */
  left: var(--left-panel-width, 70%);
}

.resize-handle:hover,
.resize-handle.dragging {
  width: 14px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.25) 50%, rgba(59, 130, 246, 0.15) 100%);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.2), 0 0 0 1px rgba(59, 130, 246, 0.2);
}

.resize-handle.dragging {
  opacity: 0.9;
}

.handle-indicator {
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: none;
}

.handle-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.4);
  transition: all 0.2s ease;
}

.resize-handle:hover .handle-dot,
.resize-handle.dragging .handle-dot {
  background: rgba(59, 130, 246, 0.8);
  transform: scale(1.2);
}

/* 拖拽时的视觉反馈 - 统一使用 body.is-resizing 类 */
body.is-resizing .left-panel,
body.is-resizing .right-panel {
  pointer-events: none;
}

body.is-resizing .resize-handle {
  pointer-events: auto;
}
</style>