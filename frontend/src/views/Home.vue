<template>
  <div class="home-container">
    <nav class="navbar">
      <div class="nav-brand">
        <div class="brand-mark">
          <img src="../assets/logo/NexusMind Logo.png" alt="NexusMind Mark" class="brand-mark-image" />
        </div>
        <div class="brand-copy">
          <div class="brand-name">NexusMind</div>
        </div>
      </div>
      <div class="nav-links">
        <a href="https://github.com/simpur-dev/NexusMind" target="_blank" class="github-link github-link-ghost">
          访问我们的 GitHub 主页 <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <section class="hero-section">
        <div class="hero-left">
          <div class="hero-panel">
            <div class="hero-panel-top">
              <div class="tag-row">
                <span class="orange-tag">简洁通用的群体智能引擎</span>
                <span class="version-text">/ v0.1-预览版</span>
              </div>
              <div class="status-stack">
                <span>// NexusCore: Operational</span>
                <span>// Status: System Ready</span>
              </div>
            </div>

            <h1 class="main-title">
              载入现实锚点<br>
              <span class="gradient-text">即刻映射未来</span>
            </h1>

            <div class="feature-cards">
              <article class="feature-card">
                <div class="feature-icon">
                  <span class="feature-glyph">⌁</span>
                </div>
                <p>
                  哪怕只是一份简报，<span class="highlight-bold">NexusMind</span> 擎亦能捕获其中的现实参数。瞬息之间，全自动完成百万量级 Agent 的自组织，构建高保真数字平行世界。
                </p>
              </article>

              <article class="feature-card">
                <div class="feature-icon">
                  <span class="feature-glyph">⌬</span>
                </div>
                <p>
                  开启全局观测与参数干预。在复杂多智能体（Multi-Agent）的动态博弈网络中，系统将持续演算，精准捕捉环境演变的
                  <span class="highlight-code">“最优解”</span>。
                </p>
              </article>
            </div>

            <div class="hero-cta-banner">
             在千万次演算中穷尽变数，于破局之时立于不败
            </div>

            <div class="hero-footer">
              <span>// 并行世界: v1.0.3</span>
              <span>// Agent 数量: 2,100,000</span>
            </div>

            <div class="hero-left-spacer" aria-hidden="true"></div>
          </div>
        </div>

        <div class="hero-right">
          <div class="hero-actions">

          </div>

          <div class="hero-visual">
            <div class="visual-hud">
              <span class="hud-pill">实时演算</span>
              <span class="hud-pill">多线程代理</span>
              <span class="hud-pill hud-pill-accent">未来推演中</span>
            </div>

            <div class="visual-dots">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>

            <div class="hex-cluster">
              <span class="hex hex-1"></span>
              <span class="hex hex-2"></span>
              <span class="hex hex-3"></span>
              <span class="hex hex-4"></span>
              <span class="hex hex-5"></span>
            </div>

            <div class="data-ribbon data-ribbon-one"></div>
            <div class="data-ribbon data-ribbon-two"></div>

            <div class="visual-text visual-text-top">// NexusCore: Operational</div>
            <div class="visual-text visual-text-right">// Status: System Ready</div>
            <div class="visual-text visual-text-bottom">变量注入节点</div>

            <div class="logo-container">
              <div class="logo-aura"></div>
              <div class="orbit-ring orbit-ring-one"></div>
              <div class="orbit-ring orbit-ring-two"></div>
              <div class="orbit-ring orbit-ring-three"></div>
              <img src="../assets/logo/NexusMind Logo.png" alt="NexusMind Logo" class="hero-logo" />
            </div>

            <div class="visual-card">
              <div class="visual-card-title">Agent 模拟网络</div>
              <div class="network-map">
                <span class="network-line line-1"></span>
                <span class="network-line line-2"></span>
                <span class="network-line line-3"></span>
                <span class="network-line line-4"></span>
                <span class="network-line line-5"></span>
                <span class="network-node node-1"></span>
                <span class="network-node node-2"></span>
                <span class="network-node network-node-core node-3"></span>
                <span class="network-node node-4"></span>
                <span class="network-node network-node-hub node-5"></span>
                <span class="network-node node-6"></span>
              </div>
            </div>
          </div>

        </div>
      </section>

      <div class="hero-scroll-row">
        <button class="scroll-down-btn" @click="scrollToBottom">
          <span class="scroll-copy">
            <span class="scroll-kicker">NEXT LAYER</span>
            <span class="scroll-label">向下探索 / 进入模拟控制台</span>
          </span>
          <span class="scroll-arrow-wrap">
            <span class="scroll-arrow">↓</span>
          </span>
        </button>
      </div>

      <section class="dashboard-section">
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">●</span> 系统状态
          </div>

          <h2 class="section-title">准备就绪</h2>
          <p class="section-desc">
            预测引擎待命中，可上传多份非结构化数据以初始化模拟序列。
          </p>

          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">零试错</div>
              <div class="metric-label">全场景决策推演未来最优解</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">高可扩</div>
              <div class="metric-label">百万级 Agent 并行构建数字平行世界</div>
            </div>
          </div>

          <div class="steps-container">
            <div class="steps-header">
              <span class="diamond-icon">◆</span> 工作流序列
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">图谱构建</div>
                  <div class="step-desc">提取现实种子数据，注入记忆，完成 GraphRAG 知识图谱构建</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">环境搭建</div>
                  <div class="step-desc">抽取实体关联关系，生成智能体设定，完成环境配置与仿真参数部署</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">开始模拟</div>
                  <div class="step-desc">双平台并行启动仿真，自动解析预测任务，动态更新时序化交互记忆</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">报告生成</div>
                  <div class="step-desc">ReportAgent与仿真后环境深度交互，自动生成专业预测报告</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">05</span>
                <div class="step-info">
                  <div class="step-title">深度互动</div>
                  <div class="step-desc">与模拟世界中的任意角色对话，或与 ReportAgent 连续追问</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="console-box">
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">01 / 现实种子</span>
                <span class="console-meta">支持格式: PDF, MD, TXT</span>
              </div>

              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">↑</div>
                  <div class="upload-title">拖拽文件上传</div>
                  <div class="upload-hint">或点击浏览文件系统</div>
                </div>

                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">FILE</span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">x</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="console-divider">
              <span>输入参数</span>
            </div>

            <div class="console-section">
              <div class="console-header">
                <span class="console-label">02 / 模拟提示词</span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  placeholder="// 用自然语言输入模拟或预测需求，例如：某地若发布撤销某处分的公告，会引发什么舆情走向？"
                  rows="6"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">引擎: NexusMind</div>
              </div>
            </div>

            <div class="console-section btn-section">
              <button
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">启动引擎</span>
                <span v-else>初始化中...</span>
                <span class="btn-arrow">↗</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

const formData = ref({
  simulationRequirement: ''
})

const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

const handleDragOver = () => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (event) => {
  isDragOver.value = false
  if (loading.value) return

  const droppedFiles = Array.from(event.dataTransfer.files)
  addFiles(droppedFiles)
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter((file) => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })

  files.value.push(...validFiles)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)

    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
.home-container {
  /* ================= 青蓝主题变量（参考 Process.vue） ================= */
  --black: #000000;
  --white: #ffffff;
  --teal-primary: #73A8B9;
  --teal-secondary: #5C9EAF;
  --teal-light: #8EBDCB;
  --teal-deep: #3A5A6A;
  --border: rgba(115, 168, 185, 0.3);
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  --font-cn: 'Noto Sans SC', system-ui, sans-serif;
  --bg-panel: rgba(230, 242, 247, 0.75);
  --bg-panel-soft: rgba(218, 235, 240, 0.65);
  --bg-card: rgba(255, 255, 255, 0.6);
  --line-cyan: rgba(115, 168, 185, 0.4);
  --text-primary: #3A5A6A;
  --text-secondary: rgba(58, 90, 106, 0.78);
  --text-muted: rgba(58, 90, 106, 0.52);

  /* ================= 容器基础设置 ================= */
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  font-family: var(--font-sans);
  color: var(--text-primary);
  
  /* ================= 核心：高亮科技感背景 ================= */
  /* 1. 极深的基底色，用来反衬高光 */
  background-color: #F0F5F7;
  
  background-image: 
    /* 层级1：全息坐标网格 (细锐的青色线，构建空间秩序感) */
    linear-gradient(rgba(115, 168, 185, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115, 168, 185, 0.06) 1px, transparent 1px),
    
    /* 层级2：高亮核心光源 (大幅提升透明度，制造“发光”错觉) */
    radial-gradient(ellipse 50% 35% at 20% 75%, rgba(89, 158, 175, 0.1) 0%, transparent 50%),
    /* 右上科技蓝副光源 */
    radial-gradient(ellipse 50% 40% at 85% 20%, rgba(6, 182, 212, 0.1) 0%, transparent 60%),
    radial-gradient(ellipse 40% 50% at 70% 70%, rgba(115, 168, 185, 0.14) 0%, transparent 55%),
    linear-gradient(135deg, rgba(240, 245, 247, 0.9) 0%, rgba(218, 235, 240, 0.6) 50%, rgba(200, 225, 232, 0.8) 100%);

  /* 定义网格大小(40px)和光晕铺满 */
  background-size: 
    40px 40px, 40px 40px, /* 网格尺寸 */
    100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%;
    
  /* 保证页面滚动时，背景光影和网格锁定不动，质感拉满 */
  background-attachment: fixed;
  z-index: 1;
}

/* 浅色磨砂噪点层 */
.home-container::before {
  content: "";
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: -1;
}

/* 确保内容在噪点层上方 */
.home-container > * {
  position: relative;
  z-index: 1;
}

/* 网格 + 渐变遮罩伪层 */
.home-container::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(rgba(115, 168, 185, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115, 168, 185, 0.04) 1px, transparent 1px);
  background-size: 88px 88px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.3), transparent 82%);
  z-index: 0;
}

:global(html) {
  scrollbar-width: thin;
  scrollbar-color: #73a8b9 #e6f2f7;
}

:global(body) {
  scrollbar-width: thin;
  scrollbar-color: #73a8b9 #e6f2f7;
}

:global(html::-webkit-scrollbar),
:global(body::-webkit-scrollbar) {
  width: 10px;
}

:global(html::-webkit-scrollbar-track),
:global(body::-webkit-scrollbar-track) {
  background: #e6f2f7;
  border-left: 1px solid rgba(115, 168, 185, 0.12);
}

:global(html::-webkit-scrollbar-thumb),
:global(body::-webkit-scrollbar-thumb) {
  background: linear-gradient(180deg, #8ebdcb, #73a8b9);
  border: 2px solid #e6f2f7;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(248, 250, 252, 0.5);
}

:global(html::-webkit-scrollbar-thumb:hover),
:global(body::-webkit-scrollbar-thumb:hover) {
  background: linear-gradient(180deg, #73a8b9, #5c9eaf);
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 18px 28px 8px;
  position: relative;
  z-index: 1;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid rgba(115, 168, 185, 0.4);
  box-shadow:
    0 0 0 1px rgba(115, 168, 185, 0.12),
    0 0 20px rgba(115, 168, 185, 0.25);
  background: rgba(230, 242, 247, 0.8);
}

.brand-mark-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scale(1.18);
}

.brand-name {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
  color: var(--teal-primary);
}

.nav-links {
  display: flex;
  align-items: center;
}

.github-link {
  color: var(--teal-deep);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.92rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
}

.github-link-ghost,
.github-link-solid {
  padding: 13px 18px;
  border: 1px solid rgba(115, 168, 185, 0.4);
  background: rgba(230, 242, 247, 0.7);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.6),
    0 0 16px rgba(115, 168, 185, 0.15);
  clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px));
}

.github-link-solid {
  padding: 14px 24px;
  font-size: 1rem;
  background: rgba(255, 255, 255, 0.65);
  box-shadow:
    inset 0 0 0 1px rgba(115, 168, 185, 0.18),
    0 0 20px rgba(115, 168, 185, 0.15),
    0 0 0 1px rgba(115, 168, 185, 0.1);
}

.github-link:hover {
  transform: translateY(-2px);
  border-color: rgba(115, 168, 185, 0.7);
  box-shadow:
    inset 0 0 0 1px rgba(115, 168, 185, 0.12),
    0 0 22px rgba(115, 168, 185, 0.25);
  color: var(--teal-secondary);
}

.arrow {
  font-family: var(--font-sans);
}

.main-content {
  max-width: 1440px;
  margin: 0 auto;
  padding: 22px 24px 80px;
  position: relative;
  z-index: 1;
}

.hero-section {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(420px, 0.95fr);
  gap: 28px;
  align-items: stretch;
  margin-bottom: 28px;
  position: relative;
}

.hero-left {
  min-width: 0;
  align-self: stretch;
}

.hero-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 620px;
  position: relative;
  padding: 34px 38px 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), transparent 12%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.65), rgba(230, 242, 247, 0.7));
  border: 1px solid rgba(115, 168, 185, 0.42);
  clip-path: polygon(0 18px, 18px 0, calc(100% - 24px) 0, 100% 24px, 100% calc(100% - 24px), calc(100% - 24px) 100%, 18px 100%, 0 calc(100% - 18px));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.8),
    0 0 34px rgba(115, 168, 185, 0.16);
  overflow: hidden;
}

.hero-panel::before,
.hero-panel::after {
  content: '';
  position: absolute;
  pointer-events: none;
}

.hero-panel::before {
  inset: 12px;
  border: 1px solid rgba(115, 168, 185, 0.2);
  clip-path: polygon(0 10px, 10px 0, calc(100% - 12px) 0, 100% 12px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 12px 100%, 0 calc(100% - 10px));
}

.hero-panel::after {
  right: -40px;
  top: 90px;
  width: 340px;
  height: 340px;
  background: radial-gradient(circle, rgba(115, 168, 185, 0.2), transparent 70%);
  filter: blur(10px);
}

.hero-panel-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 26px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: linear-gradient(180deg, rgba(115, 168, 185, 0.18), rgba(92, 158, 175, 0.28));
  color: var(--teal-deep);
  padding: 8px 14px;
  font-weight: 700;
  letter-spacing: 0.8px;
  font-size: 0.75rem;
  border: 1px solid rgba(115, 168, 185, 0.34);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.5);
}

.version-text {
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.5px;
}

.status-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: right;
  font-family: var(--font-mono);
  font-size: 0.73rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.main-title {
  font-size: clamp(3.6rem, 6vw, 5.6rem);
  line-height: 1.05;
  font-weight: 700;
  margin: 0 0 30px 0;
  letter-spacing: -3px;
  color: var(--teal-deep);
  text-shadow: 0 0 18px rgba(115, 168, 185, 0.18);
}

.gradient-text {
  background: linear-gradient(180deg, var(--teal-secondary) 0%, var(--teal-primary) 48%, var(--teal-light) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.feature-cards {
  display: grid;
  gap: 18px;
  margin-bottom: 28px;
}

.feature-card {
  display: grid;
  grid-template-columns: 52px 1fr;
  gap: 16px;
  align-items: center;
  padding: 20px 22px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(115, 168, 185, 0.4);
  border-radius: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 18px rgba(115, 168, 185, 0.12);
}

.feature-card p {
  font-size: 1.02rem;
  line-height: 1.75;
  color: var(--text-secondary);
}

.feature-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(115, 168, 185, 0.4);
  background: rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 0 12px rgba(115, 168, 185, 0.08);
}

.feature-glyph {
  font-family: var(--font-mono);
  font-size: 1.35rem;
  color: var(--teal-primary);
}

.highlight-bold {
  color: var(--teal-deep);
  font-weight: 700;
}

.highlight-code {
  background: rgba(115, 168, 185, 0.12);
  padding: 3px 8px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--teal-secondary);
  font-weight: 600;
  border: 1px solid rgba(115, 168, 185, 0.18);
}

.hero-cta-banner {
  display: inline-flex;
  align-items: center;
  padding: 18px 26px;
  margin-bottom: 20px;
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: var(--teal-deep);
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(115, 168, 185, 0.5);
  border-radius: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(115, 168, 185, 0.16);
}

.hero-footer {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-family: var(--font-mono);
  font-size: 0.92rem;
  color: var(--text-muted);
}

.hero-left-spacer {
  flex: 1;
  min-height: 84px;
}

.hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: flex-end;
  min-height: 0;
  position: relative;
  align-self: stretch;
}

.hero-actions {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  margin-bottom: 18px;
}

.hero-actions:empty {
  display: none;
}

.hero-visual {
  flex: 1;
  width: 100%;
  position: relative;
  min-height: 560px;
  padding: 22px 18px 96px;
  border: 1px solid rgba(115, 168, 185, 0.2);
  border-radius: 24px;
  background:
    rgba(255, 255, 255, 0.55),
    radial-gradient(circle at 50% 42%, rgba(115, 168, 185, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.6), rgba(230, 242, 247, 0.4));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.8),
    inset 0 -30px 60px rgba(200, 225, 232, 0.3);
  overflow: hidden;
}

.hero-scroll-row {
  display: flex;
  justify-content: center;
  width: 100%;
  margin: 0 0 28px;
}

.hero-visual::before,
.hero-visual::after {
  content: '';
  position: absolute;
  pointer-events: none;
}

.hero-visual::before {
  inset: 16px 18px 22px;
  border: 1px solid rgba(115, 168, 185, 0.15);
  border-radius: 20px;
  mask-image: linear-gradient(135deg, rgba(0, 0, 0, 0.05), rgba(0, 0, 0, 0.45));
}

.hero-visual::after {
  left: 10%;
  right: 10%;
  bottom: 24px;
  height: 1px;
  background: linear-gradient(90deg, rgba(115, 168, 185, 0), rgba(115, 168, 185, 0.38), rgba(115, 168, 185, 0));
}

.visual-hud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  position: relative;
  z-index: 2;
}

.hud-pill {
  padding: 7px 12px;
  border: 1px solid rgba(115, 168, 185, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.65);
  color: var(--teal-deep);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
}

.hud-pill-accent {
  border-color: rgba(115, 168, 185, 0.5);
  color: var(--teal-secondary);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.6),
    0 0 18px rgba(115, 168, 185, 0.12);
}

.visual-dots {
  position: absolute;
  left: 18px;
  top: 108px;
  display: grid;
  gap: 8px;
  z-index: 1;
}

.visual-dots span {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(115, 168, 185, 0.62);
  box-shadow: 0 0 10px rgba(115, 168, 185, 0.28);
}

.hex-cluster {
  position: absolute;
  top: 34px;
  right: 52px;
  width: 230px;
  height: 170px;
  opacity: 0.9;
}

.hex {
  position: absolute;
  width: 58px;
  height: 66px;
  clip-path: polygon(25% 5%, 75% 5%, 100% 50%, 75% 95%, 25% 95%, 0 50%);
  background: linear-gradient(180deg, rgba(115, 168, 185, 0.12), rgba(115, 168, 185, 0.04));
  border: 1px solid rgba(115, 168, 185, 0.25);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.5);
}

.hex-1 { top: 0; left: 68px; }
.hex-2 { top: 30px; left: 128px; }
.hex-3 { top: 58px; left: 70px; }
.hex-4 { top: 88px; left: 130px; }
.hex-5 { top: 86px; left: 10px; }

.data-ribbon {
  position: absolute;
  height: 12px;
  border-radius: 999px;
  filter: blur(0.2px);
  box-shadow:
    0 0 20px rgba(115, 168, 185, 0.3),
    0 0 36px rgba(115, 168, 185, 0.14);
}

.data-ribbon-one {
  top: 228px;
  left: 30px;
  width: 88%;
  transform: rotate(8deg);
  background: linear-gradient(90deg, rgba(115, 168, 185, 0), rgba(115, 168, 185, 0.74) 36%, rgba(115, 168, 185, 0.2) 70%, rgba(115, 168, 185, 0));
}

.data-ribbon-two {
  top: 318px;
  left: -6px;
  width: 92%;
  transform: rotate(-9deg);
  background: linear-gradient(90deg, rgba(115, 168, 185, 0), rgba(115, 168, 185, 0.48) 28%, rgba(115, 168, 185, 0.92) 56%, rgba(115, 168, 185, 0));
}

.visual-text {
  position: absolute;
  font-family: var(--font-mono);
  font-size: 0.74rem;
  color: var(--text-muted);
  letter-spacing: 0.4px;
}

.visual-text-top {
  top: 198px;
  left: 48px;
}

.visual-text-right {
  right: 22px;
  top: 346px;
  text-align: left;
}

.visual-text-bottom {
  left: 86px;
  bottom: 138px;
  font-size: 0.88rem;
  color: var(--teal-deep);
  letter-spacing: 0.8px;
}

.logo-container {
  width: min(100%, 620px);
  aspect-ratio: 1 / 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: 16px auto 0;
}

.logo-aura {
  position: absolute;
  inset: 12% 16%;
  background: radial-gradient(circle, rgba(115, 168, 185, 0.3), rgba(115, 168, 185, 0.14) 34%, transparent 70%);
  filter: blur(16px);
}

.orbit-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(115, 168, 185, 0.2);
  box-shadow:
    inset 0 0 30px rgba(115, 168, 185, 0.06),
    0 0 24px rgba(115, 168, 185, 0.08);
}

.orbit-ring-one {
  width: 74%;
  height: 56%;
  transform: rotate(18deg);
}

.orbit-ring-two {
  width: 58%;
  height: 80%;
  transform: rotate(-26deg);
}

.orbit-ring-three {
  width: 82%;
  height: 34%;
  transform: rotate(-8deg);
}

.hero-logo {
  max-width: 100%;
  width: min(100%, 590px);
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 40px rgba(115, 168, 185, 0.25)) drop-shadow(0 0 70px rgba(115, 168, 185, 0.22));
  animation: logo-float 7s ease-in-out infinite;
}

@keyframes logo-float {
  0%, 100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(0, -10px, 0) scale(1.015);
  }
}

.visual-card {
  position: absolute;
  left: 50%;
  right: auto;
  bottom: 26px;
  width: 278px;
  padding: 15px 18px 18px;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(115, 168, 185, 0.34);
  border-radius: 14px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(115, 168, 185, 0.14);
}


.visual-card-title {
  font-size: 0.9rem;
  color: var(--teal-deep);
  margin-bottom: 14px;
  text-align: center;
  letter-spacing: 0.8px;
}

.network-map {
  position: relative;
  height: 116px;
  background:
    radial-gradient(circle at center, rgba(115, 168, 185, 0.18), transparent 62%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.1)),
    linear-gradient(135deg, rgba(255, 255, 255, 0.4), rgba(255, 255, 255, 0.2));
  border: 1px solid rgba(115, 168, 185, 0.2);
  border-radius: 10px;
  overflow: hidden;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    inset 0 -16px 28px rgba(200, 225, 232, 0.3);
}

.network-line,
.network-node {
  position: absolute;
}

.network-line {
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(115, 168, 185, 0.1), rgba(115, 168, 185, 0.82), rgba(115, 168, 185, 0.1));
  transform-origin: left center;
  box-shadow:
    0 0 10px rgba(115, 168, 185, 0.12),
    0 0 18px rgba(115, 168, 185, 0.08);
}

.line-1 { left: 32px; top: 82px; width: 118px; transform: rotate(-26deg); }
.line-2 { left: 70px; top: 72px; width: 92px; transform: rotate(22deg); }
.line-3 { left: 86px; top: 44px; width: 102px; transform: rotate(3deg); }
.line-4 { left: 148px; top: 64px; width: 74px; transform: rotate(-36deg); }
.line-5 { left: 36px; top: 42px; width: 188px; transform: rotate(14deg); }

.network-node {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.98), rgba(115, 168, 185, 0.88) 18%, rgba(115, 168, 185, 0.92) 42%, rgba(58, 90, 106, 0.96) 72%, rgba(58, 90, 106, 0.98) 100%);
  border: 1px solid rgba(115, 168, 185, 0.3);
  box-shadow:
    inset -2px -3px 6px rgba(200, 225, 232, 0.5),
    inset 2px 2px 5px rgba(255, 255, 255, 0.3),
    0 0 14px rgba(115, 168, 185, 0.42);
}

.network-node::before {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0) 55%);
  opacity: 0.95;
}

.network-node::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(115, 168, 185, 0.22), rgba(115, 168, 185, 0) 72%);
  z-index: -1;
}

.network-node-core {
  background:
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 1), rgba(230, 242, 247, 0.95) 22%, rgba(115, 168, 185, 0.98) 44%, rgba(92, 158, 175, 0.95) 70%, rgba(58, 90, 106, 0.98) 100%);
  box-shadow:
    inset -2px -3px 6px rgba(200, 225, 232, 0.5),
    inset 2px 2px 6px rgba(255, 255, 255, 0.3),
    0 0 18px rgba(115, 168, 185, 0.7),
    0 0 32px rgba(115, 168, 185, 0.28);
}

.network-node-hub {
  background:
    radial-gradient(circle at 30% 26%, rgba(255, 255, 255, 1), rgba(255, 247, 219, 0.95) 18%, rgba(115, 168, 185, 0.98) 42%, rgba(92, 158, 175, 0.96) 66%, rgba(58, 90, 106, 0.98) 100%);
  border-color: rgba(115, 168, 185, 0.38);
  box-shadow:
    inset -2px -3px 6px rgba(200, 225, 232, 0.4),
    inset 2px 2px 6px rgba(255, 255, 255, 0.3),
    0 0 18px rgba(115, 168, 185, 0.82),
    0 0 34px rgba(115, 168, 185, 0.3);
}

.node-1 { left: 30px; top: 76px; }
.node-2 { left: 74px; top: 64px; }
.node-3 { left: 124px; top: 28px; }
.node-4 { left: 164px; top: 56px; }
.node-5 { left: 210px; top: 18px; }
.node-6 { left: 214px; top: 70px; }

.scroll-down-btn {
  width: 100%;
  margin-top: 0;
  padding: 14px 18px;
  border: 1px solid rgba(115, 168, 185, 0.24);
  border-radius: 18px;
  background:
    rgba(255, 255, 255, 0.6),
    linear-gradient(90deg, rgba(255, 255, 255, 0.5), rgba(230, 242, 247, 0.5));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  cursor: pointer;
  color: var(--teal-deep);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  letter-spacing: 0.4px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(115, 168, 185, 0.12);
  transition: color 0.25s ease, transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}

.scroll-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  min-width: 0;
}

.scroll-kicker {
  font-size: 0.68rem;
  letter-spacing: 1.8px;
  color: var(--text-muted);
}

.scroll-label {
  font-size: 0.96rem;
  color: var(--teal-deep);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scroll-arrow-wrap {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(115, 168, 185, 0.28);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 18px rgba(115, 168, 185, 0.12);
}

.scroll-down-btn:hover {
  color: var(--teal-secondary);
  transform: translateY(2px);
  border-color: rgba(115, 168, 185, 0.5);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.6),
    0 0 28px rgba(115, 168, 185, 0.18);
}

.scroll-arrow {
  font-size: 1.7rem;
  line-height: 1;
  text-shadow: 0 0 18px rgba(115, 168, 185, 0.36);
}

.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid rgba(115, 168, 185, 0.2);
  padding-top: 52px;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

.left-panel {
  flex: 0.8;
}

.panel-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--teal-primary);
  font-size: 0.8rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
  color: var(--text-primary);
}

.section-desc {
  color: var(--text-secondary);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  border: 1px solid rgba(115, 168, 185, 0.25);
  background: rgba(255, 255, 255, 0.55);
  padding: 20px 30px;
  min-width: 150px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 520;
  margin-bottom: 5px;
  color: var(--teal-deep);
}

.metric-label {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.steps-container {
  border: 1px solid rgba(115, 168, 185, 0.25);
  background: rgba(255, 255, 255, 0.55);
  padding: 30px;
  position: relative;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7);
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--teal-primary);
  opacity: 0.5;
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.step-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.right-panel {
  flex: 1.2;
}

.console-box {
  border: 1px solid rgba(115, 168, 185, 0.3);
  background: rgba(255, 255, 255, 0.55);
  padding: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(115, 168, 185, 0.12);
}

.console-section {
  padding: 20px;
}

.console-section.btn-section {
  padding-top: 0;
}

.console-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.upload-zone {
  border: 1px dashed rgba(115, 168, 185, 0.3);
  height: 200px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: rgba(255, 255, 255, 0.4);
}

.upload-zone.has-files {
  align-items: flex-start;
}

.upload-zone.drag-over,
.upload-zone:hover {
  background: rgba(255, 255, 255, 0.7);
  border-color: rgba(115, 168, 185, 0.6);
}

.upload-placeholder {
  text-align: center;
}

.upload-icon {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(115, 168, 185, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 15px;
  color: var(--teal-primary);
}

.upload-title {
  font-weight: 500;
  font-size: 0.9rem;
  margin-bottom: 5px;
  color: var(--text-primary);
}

.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
}

.file-list {
  width: 100%;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.5);
  padding: 8px 12px;
  border: 1px solid rgba(115, 168, 185, 0.2);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.file-icon {
  font-size: 0.7rem;
  letter-spacing: 1px;
  color: var(--teal-primary);
}

.file-name {
  flex: 1;
  margin-right: 10px;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: var(--teal-secondary);
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(115, 168, 185, 0.15);
}

.console-divider span {
  padding: 0 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid rgba(115, 168, 185, 0.25);
  background: rgba(255, 255, 255, 0.4);
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
  color: var(--text-secondary);
}

.code-input::placeholder {
  color: rgba(58, 90, 106, 0.4);
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-muted);
}

.start-engine-btn {
  width: 100%;
  background: linear-gradient(90deg, rgba(115, 168, 185, 0.2), rgba(92, 158, 175, 0.15));
  color: var(--teal-deep);
  border: 1px solid rgba(115, 168, 185, 0.4);
  padding: 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
}

.start-engine-btn:not(:disabled) {
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: linear-gradient(90deg, rgba(115, 168, 185, 0.3), rgba(92, 158, 175, 0.25));
  border-color: rgba(115, 168, 185, 0.7);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: rgba(200, 225, 232, 0.5);
  color: rgba(58, 90, 106, 0.5);
  cursor: not-allowed;
  transform: none;
  border: 1px solid rgba(115, 168, 185, 0.12);
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(115, 168, 185, 0.2); }
  70% { box-shadow: 0 0 0 8px rgba(115, 168, 185, 0); }
  100% { box-shadow: 0 0 0 0 rgba(115, 168, 185, 0); }
}

@media (max-width: 1180px) {
  .hero-section {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .hero-right {
    min-height: auto;
  }

  .hero-visual {
    min-height: 480px;
    padding-bottom: 92px;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .hero-scroll-row {
    margin-bottom: 24px;
  }
}

@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }

  .hero-left {
    margin-bottom: 0;
  }

  .hero-panel {
    padding: 28px 24px;
    min-height: auto;
  }

  .hero-panel-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-stack {
    text-align: left;
  }

  .main-title {
    letter-spacing: -1.5px;
  }

  .feature-card {
    grid-template-columns: 1fr;
  }

  .logo-container {
    width: min(100%, 520px);
  }

  .visual-card {
    bottom: 18px;
    width: 220px;
  }

  .visual-text-bottom {
    left: 48px;
  }
}

@media (max-width: 640px) {
  .navbar {
    padding: 18px 16px 8px;
    align-items: flex-start;
    flex-direction: column;
  }

  .main-content {
    padding: 18px 14px 64px;
  }

  .hero-section {
    gap: 18px;
    margin-bottom: 18px;
  }

  .tag-row {
    flex-wrap: wrap;
  }

  .main-title {
    font-size: 2.8rem;
  }

  .feature-card p {
    font-size: 0.95rem;
  }

  .hero-cta-banner {
    font-size: 1rem;
    padding: 16px 18px;
  }

  .hero-visual {
    min-height: 360px;
    padding-bottom: 92px;
    padding-inline: 12px;
  }

  .hex-cluster,
  .visual-text-top,
  .visual-text-right,
  .visual-dots {
    display: none;
  }

  .visual-text-bottom {
    left: 10px;
    bottom: 92px;
    font-size: 0.8rem;
  }

  .visual-card {
    position: absolute;
    left: 50%;
    right: auto;
    bottom: 6px;
    width: min(100%, 248px);
    transform: translateX(-50%);
  }

  .scroll-down-btn {
    padding: 12px 14px;
    border-radius: 16px;
  }

  .scroll-label {
    font-size: 0.86rem;
    white-space: normal;
  }

  .scroll-arrow-wrap {
    width: 44px;
    height: 44px;
  }

  .metrics-row,
  .console-header {
    flex-direction: column;
  }
}
</style>
