<template>
  <div class="process-page">
    <!-- 极光渐变背景层 -->
    <div class="aurora-bg">
      <div class="aurora-orb aurora-orb-1"></div>
      <div class="aurora-orb aurora-orb-2"></div>
      <div class="aurora-orb aurora-orb-3"></div>
      <div class="aurora-orb aurora-orb-4"></div>
    </div>
    
    <!-- 十字星点阵背景层 -->
    <canvas ref="starCanvas" class="star-canvas"></canvas>
    
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="nav-brand" @click="goHome">NexusMind</div>
      
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
            <div class="graph-symbol-decor" aria-hidden="true">
              <span
                v-for="(s, i) in GRAPH_DECOR_SYMBOLS"
                :key="i"
                class="sym-chip"
                :class="'sym-drift-' + s.drift"
                :style="{
                  left: s.left,
                  top: s.top,
                  fontSize: s.size + 'px',
                  animationDuration: s.f + 's, ' + s.d + 's',
                  animationDelay: s.fd + 's, ' + s.dd + 's'
                }"
              >{{ s.kind === 'plus' ? '+' : '×' }}</span>
            </div>
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

        <!-- Step 内容区 -->
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
                @next-step="handleNextStep"
                @simulation-created="handleSimulationCreated"
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
import { generateOntology, getProject, buildGraph, getTaskStatus, getGraphData } from '../api/graph'
import { getPendingUpload, clearPendingUpload } from '../store/pendingUpload'
import Step1GraphBuild from '../components/Step1GraphBuild.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import Step3Simulation from '../components/Step3Simulation.vue'
import Step4Report from '../components/Step4Report.vue'
import Step5Interaction from '../components/Step5Interaction.vue'
import * as d3 from 'd3'

const route = useRoute()
const router = useRouter()

// 十字星点阵画布引用
const starCanvas = ref(null)
let starAnimationId = null

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
const selectedItem = ref(null) // 选中的节点或边
const isFullScreen = ref(false)

// Step 导航状态
const currentStep = ref(1) // 1: 图谱构建, 2: 环境搭建, 3: 开始模拟, 4: 报告生成, 5: 深度互动
const maxReachedStep = ref(1) // 已到达过的最高步骤，允许在已访问步骤间自由跳转
const stepNames = ['图谱构建', '环境搭建', '世界模型推演', '报告生成', '深度互动']
const currentSimulationId = ref(null)
const currentReportId = ref(null)
const maxRounds = ref(null) // 从 Step2 传入的模拟轮数配置
const pendingFreshStart = ref(false) // Step2 点击"开始推演"时置 true，让 Step3 跳过 resume 直接启动
const systemLogs = ref([])

// DOM引用
const graphContainer = ref(null)
const graphSvg = ref(null)

/** 图谱画布背后 HTML 装饰：+/× 各自闪烁与漂移周期（勿放进 SVG：CSS transform 会覆盖 g 的 translate） */
const GRAPH_DECOR_SYMBOLS = [
  { kind: 'plus', left: '6%', top: '6%', f: 9.2, d: 14.5, fd: 0, dd: -2.1, drift: 'a', size: 28 },
  { kind: 'cross', left: '14%', top: '3%', f: 15.8, d: 11.2, fd: -4, dd: -1.3, drift: 'b', size: 26 },
  { kind: 'plus', left: '35%', top: '8%', f: 12.4, d: 17.6, fd: -7, dd: -5.2, drift: 'c', size: 30 },
  { kind: 'cross', left: '52%', top: '11%', f: 17.1, d: 13.4, fd: -2, dd: -8.4, drift: 'a', size: 25 },
  { kind: 'plus', left: '72%', top: '5%', f: 10.6, d: 19.2, fd: -5, dd: -3.7, drift: 'b', size: 28 },
  { kind: 'cross', left: '88%', top: '9%', f: 14.3, d: 15.1, fd: -9, dd: -6.8, drift: 'c', size: 26 },
  { kind: 'plus', left: '8%', top: '22%', f: 16.5, d: 10.8, fd: -3, dd: -0.9, drift: 'a', size: 26 },
  { kind: 'cross', left: '28%', top: '19%', f: 11.7, d: 16.3, fd: -8, dd: -4.4, drift: 'b', size: 28 },
  { kind: 'plus', left: '48%', top: '16%', f: 13.9, d: 12.6, fd: -1, dd: -7.1, drift: 'c', size: 25 },
  { kind: 'cross', left: '66%', top: '21%', f: 18.2, d: 14.8, fd: -6, dd: -2.6, drift: 'a', size: 30 },
  { kind: 'plus', left: '82%', top: '17%', f: 10.1, d: 18.4, fd: -11, dd: -9.2, drift: 'b', size: 26 },
  { kind: 'cross', left: '20%', top: '34%', f: 15.4, d: 11.9, fd: -4, dd: -1.8, drift: 'c', size: 28 },
  { kind: 'plus', left: '40%', top: '38%', f: 12.8, d: 16.7, fd: -8, dd: -5.5, drift: 'a', size: 26 },
  { kind: 'cross', left: '60%', top: '36%', f: 9.8, d: 13.2, fd: -2, dd: -3.1, drift: 'b', size: 26 },
  { kind: 'plus', left: '78%', top: '42%', f: 17.6, d: 10.4, fd: -5, dd: -6.9, drift: 'c', size: 28 },
  { kind: 'cross', left: '92%', top: '45%', f: 14, d: 17.9, fd: -10, dd: -4.7, drift: 'a', size: 25 },
  { kind: 'plus', left: '12%', top: '55%', f: 11.3, d: 15.6, fd: -1, dd: -8.1, drift: 'b', size: 26 },
  { kind: 'cross', left: '34%', top: '52%', f: 16.1, d: 12.1, fd: -7, dd: -2.4, drift: 'c', size: 30 },
  { kind: 'plus', left: '56%', top: '60%', f: 13.5, d: 18.8, fd: -9, dd: -5.9, drift: 'a', size: 25 },
  { kind: 'cross', left: '76%', top: '58%', f: 10.4, d: 14.2, fd: -3, dd: -0.6, drift: 'b', size: 28 },
  { kind: 'plus', left: '4%', top: '72%', f: 18.9, d: 11.5, fd: -6, dd: -7.3, drift: 'c', size: 26 },
  { kind: 'cross', left: '24%', top: '78%', f: 12.2, d: 16, fd: -2, dd: -4.2, drift: 'a', size: 26 },
  { kind: 'plus', left: '46%', top: '80%', f: 15.7, d: 13.7, fd: -12, dd: -1.5, drift: 'b', size: 28 },
  { kind: 'cross', left: '68%', top: '84%', f: 9.6, d: 19.4, fd: -5, dd: -8.8, drift: 'c', size: 26 },
  { kind: 'plus', left: '86%', top: '76%', f: 14.6, d: 10.2, fd: -4, dd: -3.4, drift: 'a', size: 25 },
  { kind: 'cross', left: '14%', top: '92%', f: 11.1, d: 15.3, fd: -9, dd: -6.1, drift: 'b', size: 28 },
  { kind: 'plus', left: '60%', top: '94%', f: 17.3, d: 12.8, fd: -1, dd: -2.9, drift: 'c', size: 26 },
  { kind: 'cross', left: '38%', top: '88%', f: 13.1, d: 17.1, fd: -8, dd: -5, drift: 'a', size: 25 },
  { kind: 'plus', left: '90%', top: '66%', f: 10.9, d: 14.6, fd: -7, dd: -4.5, drift: 'b', size: 30 },
  { kind: 'cross', left: '50%', top: '26%', f: 16.8, d: 11.3, fd: -3, dd: -9.4, drift: 'c', size: 26 },
  { kind: 'plus', left: '30%', top: '68%', f: 12.6, d: 18.2, fd: -5, dd: -1.1, drift: 'a', size: 26 },
  { kind: 'cross', left: '70%', top: '30%', f: 15.2, d: 13.5, fd: -10, dd: -7.6, drift: 'b', size: 28 },
  { kind: 'plus', left: '2%', top: '44%', f: 11.5, d: 16.4, fd: -2, dd: -3.8, drift: 'c', size: 24 },
  { kind: 'cross', left: '96%', top: '62%', f: 13.8, d: 12.2, fd: -6, dd: -1.2, drift: 'a', size: 25 },
]

// 轮询定时器
let pollTimer = null

// 初始化十字星点阵动画
const initStarCanvas = () => {
  const canvas = starCanvas.value
  if (!canvas) return
  
  const ctx = canvas.getContext('2d')
  
  // 设置画布尺寸
  const resizeCanvas = () => {
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height
  }
  
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  
  // 十字星配置
  const stars = []
  const starCount = 80 // 十字星数量
  
  for (let i = 0; i < starCount; i++) {
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.1,
      speed: Math.random() * 0.02 + 0.01,
      angle: Math.random() * Math.PI / 2, // 45度基准
      twinkleSpeed: Math.random() * 0.02 + 0.01,
      twinkleOffset: Math.random() * Math.PI * 2
    })
  }
  
  // 绘制十字星
  const drawStar = (star, time) => {
    const twinkle = Math.sin(time * star.twinkleSpeed + star.twinkleOffset) * 0.3 + 0.7
    const alpha = star.opacity * twinkle
    
    ctx.save()
    ctx.translate(star.x, star.y)
    ctx.rotate(star.angle)
    
    // 发光效果
    ctx.shadowBlur = 10
    ctx.shadowColor = `rgba(59, 130, 246, ${alpha})`
    
    ctx.strokeStyle = `rgba(147, 197, 253, ${alpha})`
    ctx.lineWidth = star.size * 0.5
    
    // 横线
    ctx.beginPath()
    ctx.moveTo(-star.size * 3, 0)
    ctx.lineTo(star.size * 3, 0)
    ctx.stroke()
    
    // 竖线
    ctx.beginPath()
    ctx.moveTo(0, -star.size * 3)
    ctx.lineTo(0, star.size * 3)
    ctx.stroke()
    
    // 中心点
    ctx.fillStyle = `rgba(255, 255, 255, ${alpha * 0.8})`
    ctx.beginPath()
    ctx.arc(0, 0, star.size * 0.5, 0, Math.PI * 2)
    ctx.fill()
    
    ctx.restore()
  }
  
  // 动画循环
  let animationTime = 0
  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    animationTime += 16 // 约60fps
    
    // 更新星星位置（缓慢漂移）
    stars.forEach(star => {
      star.x += Math.sin(animationTime * 0.0001 + star.twinkleOffset) * 0.3
      star.y += Math.cos(animationTime * 0.0001 + star.twinkleOffset) * 0.3
      
      // 边界检查
      if (star.x < -20) star.x = canvas.width + 20
      if (star.x > canvas.width + 20) star.x = -20
      if (star.y < -20) star.y = canvas.height + 20
      if (star.y > canvas.height + 20) star.y = -20
      
      // 旋转
      star.angle += star.speed * 0.01
    })
    
    // 绘制所有星星
    stars.forEach(star => drawStar(star, animationTime))
    
    starAnimationId = requestAnimationFrame(animate)
  }
  
  animate()
}

// 停止十字星动画
const stopStarAnimation = () => {
  if (starAnimationId) {
    cancelAnimationFrame(starAnimationId)
    starAnimationId = null
  }
}

// 计算属性
const statusClass = computed(() => {
  if (error.value) return 'error'
  if (currentPhase.value >= 2) return 'completed'
  return 'processing'
})

const statusText = computed(() => {
  if (error.value) return '构建失败'
  if (currentPhase.value >= 2) return '构建完成'
  if (currentPhase.value === 1) return '图谱构建中'
  if (currentPhase.value === 0) return '本体生成中'
  return '初始化中'
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
  // status reflected in statusClass/statusText
}

// 把 currentStep 同步到 URL ?step=N，这样浏览器前进/后退可以切 Step
// isSyncingFromRoute 防止"路由变化 → 改 step → 又去改路由"的死循环
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
    addLog(`配置模拟轮数: ${params.maxRounds} 轮`)
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

// 处理新建项目 - 调用 ontology/generate API
const handleNewProject = async () => {
  const pending = getPendingUpload()
  
  if (!pending.isPending || pending.files.length === 0) {
    error.value = '没有待上传的文件，请返回首页重新操作'
    loading.value = false
    return
  }
  
  try {
    loading.value = true
    currentPhase.value = 0 // 本体生成阶段
    ontologyProgress.value = { message: '正在上传文件并分析文档...' }
    
    // 构建 FormData
    const formDataObj = new FormData()
    pending.files.forEach(file => {
      formDataObj.append('files', file)
    })
    formDataObj.append('simulation_requirement', pending.simulationRequirement)
    
    // 调用本体生成 API
    const response = await generateOntology(formDataObj)
    
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
    const response = await getProject(currentProjectId.value)

    if (response.success) {
      projectData.value = response.data
      updatePhaseByStatus(response.data.status)

      // 从项目数据恢复 Step 导航状态
      if (response.data.report_id) {
        // 报告已生成，恢复到 Step 4
        currentStep.value = 4
        maxReachedStep.value = 4
        currentSimulationId.value = response.data.simulation_id
        currentReportId.value = response.data.report_id
        addLog(`从历史记录恢复项目，已在 Step 4 (报告生成)`)
      } else if (response.data.simulation_id) {
        // 模拟已创建，恢复到 Step 2（环境搭建会自动检查是否已准备完成）
        currentSimulationId.value = response.data.simulation_id
        currentStep.value = 2
        maxReachedStep.value = 3
        if (response.data.graph_id) {
          currentPhase.value = 2
          await loadGraph(response.data.graph_id)
        }
        addLog(`从历史记录恢复项目，模拟ID: ${response.data.simulation_id}`)
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
  await fetchGraphData()
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
const fetchGraphData = async () => {
  try {
    // 先获取项目信息以获取 graph_id
    const projectResponse = await getProject(currentProjectId.value)
    
    if (projectResponse.success && projectResponse.data.graph_id) {
      const graphId = projectResponse.data.graph_id
      projectData.value = projectResponse.data
      
      // 获取图谱数据
      const graphResponse = await getGraphData(graphId)
      
      if (graphResponse.success && graphResponse.data) {
        const newData = graphResponse.data
        const newNodeCount = newData.node_count || newData.nodes?.length || 0
        const oldNodeCount = graphData.value?.node_count || graphData.value?.nodes?.length || 0
        
        console.log('Fetching graph data, nodes:', newNodeCount, 'edges:', newData.edge_count || newData.edges?.length || 0)
        
        // 数据有变化时更新渲染
        if (newNodeCount !== oldNodeCount || !graphData.value) {
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

// 渲染图谱 (D3.js)
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
  
  // 获取容器尺寸
  const rect = container.getBoundingClientRect()
  const width = rect.width || 800
  const height = (rect.height || 600) - 60
  
  if (width <= 0 || height <= 0) {
    console.log('Cannot render: invalid dimensions', width, height)
    return
  }
  
  console.log('Rendering graph:', width, 'x', height)
  
  const svg = d3.select(graphSvg.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
  
  svg.selectAll('*').remove()

  // 处理节点数据
  const nodesData = graphData.value.nodes || []
  const edgesData = graphData.value.edges || []
  
  if (nodesData.length === 0) {
    console.log('No nodes to render')
    // 显示空状态
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', height / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#999')
      .text('等待图谱数据...')
    return
  }
  
  // 创建节点映射用于查找名称
  const nodeMap = {}
  nodesData.forEach(n => {
    nodeMap[n.uuid] = n
  })
  
  const nodes = nodesData.map(n => ({
    id: n.uuid,
    name: n.name || '未命名',
    type: n.labels?.find(l => l !== 'Entity' && l !== 'Node') || 'Entity',
    rawData: n // 保存原始数据
  }))
  
  // 创建节点ID集合用于过滤有效边
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
  
  console.log('Nodes:', nodes.length, 'Edges:', edges.length)
  
  // 颜色映射
  const types = [...new Set(nodes.map(n => n.type))]
  const colorScale = d3.scaleOrdinal()
    .domain(types)
    .range(['#FF6B35', '#004E89', '#7B2D8E', '#1A936F', '#C5283D', '#E9724C', '#2D3436', '#6C5CE7'])
  
  // 力导向布局
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(100).strength(0.5))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(40))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05))
  
  // 添加缩放功能
  const g = svg.append('g')
  
  svg.call(d3.zoom()
    .extent([[0, 0], [width, height]])
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    }))
  
  // 绘制边（包含可点击的透明宽线）
  const linkGroup = g.append('g')
    .attr('class', 'links')
    .selectAll('g')
    .data(edges)
    .enter()
    .append('g')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selectEdge(d.rawData)
    })
  
  // 可见的细线
  const link = linkGroup.append('line')
    .attr('stroke', '#ccc')
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.6)
  
  // 透明的宽线用于点击
  linkGroup.append('line')
    .attr('stroke', 'transparent')
    .attr('stroke-width', 10)
  
  // 边标签
  const linkLabel = g.append('g')
    .attr('class', 'link-labels')
    .selectAll('text')
    .data(edges)
    .enter()
    .append('text')
    .attr('font-size', '9px')
    .attr('fill', '#999')
    .attr('text-anchor', 'middle')
    .text(d => d.type.length > 15 ? d.type.substring(0, 12) + '...' : d.type)
  
  // 绘制节点
  const node = g.append('g')
    .attr('class', 'nodes')
    .selectAll('g')
    .data(nodes)
    .enter()
    .append('g')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      selectNode(d.rawData, colorScale(d.type))
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
  
  node.append('circle')
    .attr('r', 10)
    .attr('fill', d => colorScale(d.type))
    .attr('stroke', 'rgba(15, 23, 42, 0.14)')
    .attr('stroke-width', 2)
    .attr('class', 'node-circle')
  
  node.append('text')
    .attr('dx', 14)
    .attr('dy', 4)
    .text(d => d.name?.substring(0, 12) || '')
    .attr('font-size', '11px')
    .attr('fill', '#333')
    .attr('font-family', 'JetBrains Mono, monospace')
  
  // 点击空白处关闭详情面板
  svg.on('click', () => {
    closeDetailPanel()
  })
  
  simulation.on('tick', () => {
    // 更新所有边的位置（包括可见线和透明点击区域）
    linkGroup.selectAll('line')
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
    
    // 更新边标签位置
    linkLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 5)
    
    node.attr('transform', d => `translate(${d.x},${d.y})`)
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
}

// 监听图谱数据变化
watch(graphData, () => {
  if (graphData.value) {
    nextTick(() => renderGraph())
  }
})

// 生命周期
onMounted(() => {
  initProject()
})

onUnmounted(() => {
  stopPolling()
  stopGraphPolling()
  stopStarAnimation()
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
}

/* 导航栏 */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #E6F2F7;
  backdrop-filter: blur(20px);
  color: #3A5A6A;
  z-index: 100;
  position: relative;
  border-bottom: 1px solid rgba(115, 168, 185, 0.2);
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

.status-text {
  font-size: 0.75rem;
  color: #3A5A6A;
  opacity: 0.7;
}

/* 主内容区 */
.main-content {
  display: flex;
  height: calc(100vh - 56px);
  position: relative;
}

/* 左侧面板 - 50% default（冰蓝浅色底，与右侧工作台协调） */
.left-panel {
  width: 50%;
  flex: none; /* Fixed width initially */
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(173, 196, 214, 0.45);
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(165deg, #f4f9fb 0%, #eef5f8 45%, #e6f0f4 100%);
  z-index: 5;
  position: relative;
  overflow: hidden;
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

/* 图谱区：中心略亮的径向高光 + 浅青灰底；+/× 在 .graph-symbol-decor（HTML）避免与 SVG transform 冲突 */
.graph-view {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
  min-width: 240px;
  background:
    radial-gradient(ellipse 72% 58% at 50% 44%, rgba(255, 255, 255, 0.88) 0%, rgba(244, 249, 251, 0.35) 42%, transparent 68%),
    linear-gradient(180deg, #f0f7f9 0%, #e8f2f5 55%, #e2edf1 100%);
  border-radius: 0 0 12px 0;
}

.graph-symbol-decor {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.graph-symbol-decor .sym-chip {
  position: absolute;
  margin: 0;
  padding: 0;
  transform: translate(-50%, -50%);
  font-family: 'JetBrains Mono', 'Noto Sans SC', ui-monospace, monospace;
  font-weight: 500;
  line-height: 1;
  color: rgba(95, 125, 150, 0.52);
  user-select: none;
  will-change: opacity, transform;
  animation-name: graph-decor-flicker, graph-decor-drift-a;
  animation-timing-function: ease-in-out, ease-in-out;
  animation-iteration-count: infinite, infinite;
}

.graph-symbol-decor .sym-chip.sym-drift-b {
  animation-name: graph-decor-flicker, graph-decor-drift-b;
}

.graph-symbol-decor .sym-chip.sym-drift-c {
  animation-name: graph-decor-flicker, graph-decor-drift-c;
}

@keyframes graph-decor-flicker {
  0%, 100% { opacity: 0.58; }
  18% { opacity: 0.14; }
  33% { opacity: 0.52; }
  52% { opacity: 0.82; }
  71% { opacity: 0.1; }
  88% { opacity: 0.46; }
}

@keyframes graph-decor-drift-a {
  0%, 100% { transform: translate(-50%, -50%) translate(0, 0); }
  28% { transform: translate(-50%, -50%) translate(3px, -2px); }
  55% { transform: translate(-50%, -50%) translate(-2px, 2px); }
  82% { transform: translate(-50%, -50%) translate(2px, 1px); }
}

@keyframes graph-decor-drift-b {
  0%, 100% { transform: translate(-50%, -50%) translate(0, 0); }
  32% { transform: translate(-50%, -50%) translate(-3px, 2px); }
  58% { transform: translate(-50%, -50%) translate(2px, -2px); }
  84% { transform: translate(-50%, -50%) translate(-1px, -1px); }
}

@keyframes graph-decor-drift-c {
  0%, 100% { transform: translate(-50%, -50%) translate(0, 0); }
  24% { transform: translate(-50%, -50%) translate(2px, 3px); }
  48% { transform: translate(-50%, -50%) translate(-2px, -1px); }
  74% { transform: translate(-50%, -50%) translate(1px, -2px); }
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

/* 左侧已改用面板内浅色氛围层，极光层关闭以免叠色 */
.aurora-bg {
  display: none;
}

.aurora-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.4;
  animation: aurora-float 20s ease-in-out infinite;
}

.aurora-orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.5) 0%, rgba(59, 130, 246, 0) 70%);
  top: -10%;
  left: -15%;
  animation-delay: 0s;
}

.aurora-orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.5) 0%, rgba(6, 182, 212, 0) 70%);
  bottom: -10%;
  right: -10%;
  animation-delay: -5s;
}

.aurora-orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.4) 0%, rgba(139, 92, 246, 0) 70%);
  top: 40%;
  left: 30%;
  animation-delay: -10s;
}

.aurora-orb-4 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.35) 0%, rgba(34, 211, 238, 0) 70%);
  top: 20%;
  right: 20%;
  animation-delay: -15s;
}

@keyframes aurora-float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(30px, -30px) scale(1.05);
  }
  50% {
    transform: translate(-20px, 20px) scale(0.95);
  }
  75% {
    transform: translate(20px, 10px) scale(1.02);
  }
}

/* 十字星画布已改为面板内 CSS 图案，固定画布关闭 */
.star-canvas {
  display: none;
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
    rgba(255, 255, 255, 0.55) 0%,
    rgba(244, 249, 251, 0.2) 50%,
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
  color: #1e3a5f;
  text-shadow: none;
}

.waiting-hint {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.graph-container .waiting-hint {
  color: #64748b;
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
  background: #fff;
  border: 1px solid #E0E0E0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.detail-panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #FAFAFA;
  border-bottom: 1px solid #E0E0E0;
}

.detail-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
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
  color: #333;
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
  color: #999;
  min-width: 70px;
  flex-shrink: 0;
}

.detail-value {
  font-size: 0.85rem;
  color: #333;
  word-break: break-word;
}

.detail-value.uuid {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #666;
}

.detail-section {
  margin-bottom: 12px;
}

.detail-summary {
  margin: 8px 0 0 0;
  font-size: 0.85rem;
  color: #333;
  line-height: 1.6;
  padding: 10px;
  background: #F9F9F9;
  border-left: 3px solid #FF6B35;
}

.detail-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.label-tag {
  padding: 2px 8px;
  font-size: 0.75rem;
  background: #F0F0F0;
  border: 1px solid #E0E0E0;
  color: #666;
}

/* 边详情关系展示 */
.edge-relation {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: #F9F9F9;
  border: 1px solid #E0E0E0;
}

.edge-source,
.edge-target {
  font-size: 0.85rem;
  font-weight: 500;
  color: #333;
}

.edge-arrow {
  color: #999;
}

.edge-type {
  padding: 2px 8px;
  font-size: 0.75rem;
  background: #FF6B35;
  color: #fff;
}

.detail-value.highlight {
  font-weight: 600;
  color: #000;
}

.detail-subtitle {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
  margin: 16px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #E0E0E0;
}

/* Properties 属性列表 */
.properties-list {
  margin-top: 8px;
  padding: 10px;
  background: #F9F9F9;
  border: 1px solid #E0E0E0;
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
  color: #666;
  margin-right: 8px;
  font-family: 'JetBrains Mono', monospace;
}

.property-value {
  color: #333;
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
  background: #F0F0F0;
  border: 1px solid #E0E0E0;
  color: #666;
  word-break: break-all;
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
.right-panel {
  width: 50%;
  flex: none;
  display: flex;
  flex-direction: column;
  background: #F8FAFC;
  box-shadow: -4px 0 24px rgba(115, 168, 185, 0.08);
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  opacity: 1;
  position: relative;
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
  background: #E6F2F7;
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
  background: #F8FAFC;
}

.workbench-wrapper .scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: #73a8b9 #e6f2f7;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar {
  width: 8px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-track {
  background: #e6f2f7;
  border-radius: 999px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #8ebdcb, #73a8b9);
  border: 2px solid #e6f2f7;
  border-radius: 999px;
}

.workbench-wrapper .scroll-container::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #73a8b9, #5c9eaf);
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
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: #73a8b9 #e6f2f7;
}

.step-area-inner::-webkit-scrollbar {
  width: 8px;
}

.step-area-inner::-webkit-scrollbar-track {
  background: #e6f2f7;
  border-radius: 999px;
}

.step-area-inner::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #8ebdcb, #73a8b9);
  border: 2px solid #e6f2f7;
  border-radius: 999px;
}

.step-area-inner::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #73a8b9, #5c9eaf);
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
</style>