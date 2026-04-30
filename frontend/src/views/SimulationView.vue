<template>
  <div class="main-view">
    <!-- 极光渐变背景层 -->
    <div class="aurora-bg">
      <div class="aurora-orb aurora-orb-1"></div>
      <div class="aurora-orb aurora-orb-2"></div>
      <div class="aurora-orb aurora-orb-3"></div>
      <div class="aurora-orb aurora-orb-4"></div>
    </div>
    
    <!-- 十字星点阵背景层 -->
    <canvas ref="starCanvas" class="star-canvas"></canvas>
    
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">NexusMind</div>
      </div>
      
      <div class="header-center">
        <div class="view-switcher">
          <button 
            v-for="mode in ['graph', 'split', 'workbench']" 
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: '图谱', split: '双栏', workbench: '工作台' }[mode] }}
          </button>
        </div>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">Step 2/5</span>
          <span class="step-name">群体环境建模</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel 
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="2"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step2 群体环境建模 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
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
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step2EnvSetup from '../components/Step2EnvSetup.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, stopSimulation, getEnvStatus, closeSimulationEnv } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// 十字星点阵画布引用
const starCanvas = ref(null)
let starAnimationId = null

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing') // processing | completed | error

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Ready'
  return 'Preparing'
})

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 100) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

const handleGoBack = () => {
  // 返回到 process 页面
  if (projectData.value?.project_id) {
    router.push({ name: 'Process', params: { projectId: projectData.value.project_id } })
  } else {
    router.push('/')
  }
}

const handleNextStep = (params = {}) => {
  addLog('进入 Step 3: 舆情态势推演')
  
  // 记录模拟轮数配置
  if (params.maxRounds) {
    addLog(`自定义模拟轮数: ${params.maxRounds} 轮`)
  } else {
    addLog('使用自动配置的模拟轮数')
  }
  
  // 构建路由参数
  const routeParams = {
    name: 'SimulationRun',
    params: { simulationId: currentSimulationId.value }
  }
  
  // 如果有自定义轮数，通过 query 参数传递
  if (params.maxRounds) {
    routeParams.query = { maxRounds: params.maxRounds }
  }
  
  // 跳转到 Step 3 页面
  router.push(routeParams)
}

// --- Data Logic ---

/**
 * 检查并关闭正在运行的模拟
 * 当用户从 Step 3 返回到 Step 2 时，默认用户要退出模拟
 */
const checkAndStopRunningSimulation = async () => {
  if (!currentSimulationId.value) return
  
  try {
    // 先检查模拟环境是否存活
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })
    
    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('检测到模拟环境正在运行，正在关闭...')
      
      // 尝试优雅关闭模拟环境
      try {
        const closeRes = await closeSimulationEnv({ 
          simulation_id: currentSimulationId.value,
          timeout: 10  // 10秒超时
        })
        
        if (closeRes.success) {
          addLog('✓ 模拟环境已关闭')
        } else {
          addLog(`关闭模拟环境失败: ${closeRes.error || '未知错误'}`)
          // 如果优雅关闭失败，尝试强制停止
          await forceStopSimulation()
        }
      } catch (closeErr) {
        addLog(`关闭模拟环境异常: ${closeErr.message}`)
        // 如果优雅关闭异常，尝试强制停止
        await forceStopSimulation()
      }
    } else {
      // 环境未运行，但可能进程还在，检查模拟状态
      const simRes = await getSimulation(currentSimulationId.value)
      if (simRes.success && simRes.data?.status === 'running') {
        addLog('检测到模拟状态为运行中，正在停止...')
        await forceStopSimulation()
      }
    }
  } catch (err) {
    // 检查环境状态失败不影响后续流程
    console.warn('检查模拟状态失败:', err)
  }
}

/**
 * 强制停止模拟
 */
const forceStopSimulation = async () => {
  try {
    const stopRes = await stopSimulation({ simulation_id: currentSimulationId.value })
    if (stopRes.success) {
      addLog('✓ 模拟已强制停止')
    } else {
      addLog(`强制停止模拟失败: ${stopRes.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`强制停止模拟异常: ${err.message}`)
  }
}

const loadSimulationData = async () => {
  try {
    addLog(`加载模拟数据: ${currentSimulationId.value}`)
    
    // 获取 simulation 信息
    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data
      
      // 获取 project 信息
      if (simData.project_id) {
        const projRes = await getProject(simData.project_id)
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data
          addLog(`项目加载成功: ${projRes.data.project_id}`)
          
          // 获取 graph 数据
          if (projRes.data.graph_id) {
            await loadGraph(projRes.data.graph_id)
          }
        }
      }
    } else {
      addLog(`加载模拟数据失败: ${simRes.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`加载异常: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  graphLoading.value = true
  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      addLog('图谱数据加载成功')
    }
  } catch (err) {
    addLog(`图谱加载失败: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    loadGraph(projectData.value.graph_id)
  }
}

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
  const starCount = 60 // 十字星数量
  
  for (let i = 0; i < starCount; i++) {
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.1,
      speed: Math.random() * 0.02 + 0.01,
      angle: Math.random() * Math.PI / 2,
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
    ctx.shadowColor = `rgba(16, 185, 129, ${alpha})`
    
    ctx.strokeStyle = `rgba(110, 231, 183, ${alpha})`
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
    animationTime += 16
    
    stars.forEach(star => {
      star.x += Math.sin(animationTime * 0.0001 + star.twinkleOffset) * 0.3
      star.y += Math.cos(animationTime * 0.0001 + star.twinkleOffset) * 0.3
      
      if (star.x < -20) star.x = canvas.width + 20
      if (star.x > canvas.width + 20) star.x = -20
      if (star.y < -20) star.y = canvas.height + 20
      if (star.y > canvas.height + 20) star.y = -20
      
      star.angle += star.speed * 0.01
    })
    
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

onMounted(async () => {
  addLog('SimulationView 初始化')
  
  // 初始化十字星画布
  initStarCanvas()
  
  // 检查并关闭正在运行的模拟（用户从 Step 3 返回时）
  await checkAndStopRunningSimulation()
  
  // 加载模拟数据
  loadSimulationData()
})

onUnmounted(() => {
  stopStarAnimation()
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #0a0f1a 0%, #0d1a25 50%, #0a1220 100%);
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  position: relative;
}

/* 极光渐变背景 */
.aurora-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.aurora-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.35;
  animation: aurora-float 25s ease-in-out infinite;
}

.aurora-orb-1 {
  width: 700px;
  height: 700px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.5) 0%, rgba(16, 185, 129, 0) 70%);
  top: -15%;
  left: -10%;
  animation-delay: 0s;
}

.aurora-orb-2 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.5) 0%, rgba(6, 182, 212, 0) 70%);
  bottom: -15%;
  right: -10%;
  animation-delay: -7s;
}

.aurora-orb-3 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, rgba(59, 130, 246, 0) 70%);
  top: 30%;
  left: 40%;
  animation-delay: -14s;
}

.aurora-orb-4 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, rgba(139, 92, 246, 0) 70%);
  bottom: 30%;
  left: 10%;
  animation-delay: -21s;
}

@keyframes aurora-float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  25% {
    transform: translate(40px, -40px) scale(1.05);
  }
  50% {
    transform: translate(-30px, 30px) scale(0.95);
  }
  75% {
    transform: translate(25px, 15px) scale(1.02);
  }
}

/* 十字星点阵画布 */
.star-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  pointer-events: none;
  z-index: 1;
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(10, 15, 26, 0.85);
  backdrop-filter: blur(20px);
  z-index: 100;
  position: relative;
}

.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  cursor: pointer;
  background: linear-gradient(135deg, #10b981, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  transition: transform 0.2s;
}

.brand:hover {
  transform: translateX(2px);
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.view-switcher {
  display: flex;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: 8px;
  gap: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: rgba(16, 185, 129, 0.3);
  color: #34d399;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.4);
}

.step-name {
  font-weight: 700;
  color: rgba(255, 255, 255, 0.9);
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: rgba(255, 255, 255, 0.2);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
}

.status-indicator.processing .dot { 
  background: #10b981; 
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.8);
  animation: pulse 1s infinite; 
}
.status-indicator.completed .dot { 
  background: #06b6d4; 
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.8);
}
.status-indicator.error .dot { 
  background: #ef4444; 
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.8);
}

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
  z-index: 10;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
  background: rgba(10, 15, 26, 0.6);
  backdrop-filter: blur(10px);
}

.panel-wrapper.left {
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}
</style>

