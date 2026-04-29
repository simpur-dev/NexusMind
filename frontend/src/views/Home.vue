<template>
  <div class="home-container">
    <nav class="navbar">
      <div class="nav-brand">
        <div class="brand-mark">
          <img src="../assets/logo/NexusMind Logo.png" alt="NexusMind Mark" class="brand-mark-image" />
        </div>
        <div class="brand-copy">
          <div class="brand-name">NexusMind</div>
          <div class="brand-badge">群体智能引擎</div>
        </div>
      </div>
      <div class="nav-links">
        <template v-if="!isLoggedIn">
          <button class="auth-btn login-btn" @click="showAuthModal = true; authMode = 'login'">
            登录
          </button>
        </template>
        <template v-else>
          <div class="user-info">
            <span class="user-avatar">{{ currentUser.charAt(0).toUpperCase() }}</span>
            <span class="user-name">{{ currentUser }}</span>
            <button class="auth-btn logout-btn" @click="handleLogout">退出</button>
          </div>
        </template>
        <a href="https://github.com/simpur-dev/NexusMind" target="_blank" class="github-link github-link-ghost">
          访问 GitHub <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <!-- 登录/注册弹窗 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showAuthModal" class="modal-overlay" @click.self="showAuthModal = false">
          <div class="auth-modal">
            <button class="modal-close" @click="showAuthModal = false">×</button>

            <!-- 标题区域 -->
            <div class="modal-header">
              <div class="modal-brand">
                <img src="../assets/logo/NexusMind Logo.png" alt="Logo" class="modal-logo" />
              </div>
              <h2 class="modal-title">{{ authMode === 'login' ? '欢迎回来' : '创建账户' }}</h2>
              <p class="modal-subtitle">
                {{ authMode === 'login' ? '登录以继续使用 NexusMind' : '注册账户开始体验群体智能' }}
              </p>
            </div>

            <!-- 表单 -->
            <form @submit.prevent="handleAuth" class="auth-form">
              <div class="form-group">
                <label class="form-label">账号</label>
                <input
                  v-model="authForm.username"
                  type="text"
                  class="form-input"
                  placeholder="请输入账号"
                  required
                />
              </div>

              <div class="form-group">
                <label class="form-label">密码</label>
                <div class="password-wrapper">
                  <input
                    v-model="authForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    class="form-input"
                    placeholder="请输入密码"
                    required
                  />
                  <button type="button" class="password-toggle" @click="showPassword = !showPassword">
                    {{ showPassword ? '隐藏' : '显示' }}
                  </button>
                </div>
              </div>

              <template v-if="authMode === 'register'">
                <div class="form-group">
                  <label class="form-label">确认密码</label>
                  <input
                    v-model="authForm.confirmPassword"
                    type="password"
                    class="form-input"
                    placeholder="请再次输入密码"
                    required
                  />
                </div>
              </template>

              <div v-if="authMode === 'login'" class="form-options">
                <label class="remember-me">
                  <input type="checkbox" v-model="authForm.remember" />
                  <span>记住我</span>
                </label>
                <a href="#" class="forgot-link">忘记密码？</a>
              </div>

              <button type="submit" class="submit-btn">
                {{ authMode === 'login' ? '登 录' : '注 册' }}
              </button>
            </form>

            <!-- 社交登录 - 仅登录时显示 -->
            <template v-if="authMode === 'login'">
              <div class="divider">
                <span>或</span>
              </div>
              <div class="social-login">
                <button type="button" class="social-btn">
                  <svg class="social-icon" viewBox="0 0 24 24" width="20" height="20">
                    <path fill="currentColor" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
                  </svg>
                  GitHub
                </button>
                <button type="button" class="social-btn">
                  <svg class="social-icon" viewBox="0 0 24 24" width="20" height="20">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Google
                </button>
              </div>
            </template>

            <!-- 切换模式 -->
            <div class="mode-switch">
              <span>{{ authMode === 'login' ? '还没有账户？' : '已有账户？' }}</span>
              <button type="button" class="switch-btn" @click="authMode = authMode === 'login' ? 'register' : 'login'">
                {{ authMode === 'login' ? '立即注册' : '立即登录' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div class="main-content">
      <section v-if="!isLoggedIn" class="hero-section">
        <div class="hero-left" :class="{ 'slide-in-left': isMounted }">
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

        <div class="hero-right" :class="{ 'slide-in-right': isMounted }">
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


      <section v-if="isLoggedIn" class="dashboard-section">
        <div class="left-panel" :class="{ 'slide-in-left': isMounted }">
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
                  <div class="step-desc">抽取实体关联关系，生成含内部目标与价值权重的智能体设定，完成环境配置与仿真参数部署</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">世界模型推演</div>
                  <div class="step-desc">双平台并行启动仿真。世界状态每轮写回每个 Agent 的 prompt，使其感知讨论演化、自主决策</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">报告生成</div>
                  <div class="step-desc">ReportAgent 融合世界状态轨迹与因果图谱，自动生成可解释的专业预测报告</div>
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

        <div class="right-panel" :class="{ 'slide-in-right': isMounted }">
          <div class="console-box">
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">01 / 现实种子</span>
              </div>

              <div class="source-tabs">
                <button
                  class="source-tab"
                  :class="{ active: sourceMode === 'file' }"
                  @click="sourceMode = 'file'"
                  :disabled="loading"
                >
                  文件上传
                </button>
                <button
                  class="source-tab"
                  :class="{ active: sourceMode === 'web' }"
                  @click="sourceMode = 'web'"
                  :disabled="loading"
                >
                  网络抓取
                </button>
              </div>

              <div v-if="sourceMode === 'file'" class="source-panel">
                <div class="console-meta" style="margin-bottom: 8px;">支持格式: PDF, MD, TXT</div>
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

                <div class="web-toggle-section">
                  <label class="web-toggle-label">
                    <input
                      type="checkbox"
                      v-model="enableWebSearch"
                      :disabled="loading"
                      class="web-toggle-checkbox"
                    />
                    <span class="web-toggle-text">同时启用网络抓取</span>
                    <span class="web-toggle-hint">（补充公开舆情信息）</span>
                  </label>
                  <div v-if="enableWebSearch" class="web-search-input" style="margin-top: 8px;">
                    <input
                      v-model="webQueryForFile"
                      class="code-input web-query-input"
                      placeholder="// 输入搜索关键词，例如：武汉大学 舆论"
                      :disabled="loading"
                    />
                    <div class="search-badge">Tavily Search</div>
                  </div>
                </div>
              </div>

              <div v-else class="source-panel">
                <div class="console-meta" style="margin-bottom: 8px;">输入关键词，自动搜索公开舆情信息作为种子</div>
                <div class="web-search-input">
                  <input
                    v-model="webQuery"
                    class="code-input web-query-input"
                    placeholder="// 输入舆情话题关键词，例如：某某事件 舆论 社交媒体"
                    :disabled="loading"
                    @keyup.enter="startSimulation"
                  />
                  <div class="search-badge">Tavily Search</div>
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
                  placeholder="// 描述事件背景与决策问题，例如：&#10;// 武汉大学图书馆争议事件：校方撤销肖某瑫记过处分并维持杨某媛硕士学位。&#10;// 请模拟各利益群体（学生、校友、教职工、公众）对此决定的反应，&#10;// 评估舆情风险、信任修复路径，并给出分阶段的处置建议。"
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

      <HistoryDatabase v-if="isLoggedIn" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

const isMounted = ref(false)

// 登录/注册弹窗状态
const showAuthModal = ref(false)
const authMode = ref('login') // 'login' | 'register'
const showPassword = ref(false)
const authForm = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  remember: false
})

const isLoggedIn = ref(false)
const currentUser = ref('')

const DEMO_PASSWORD = '123456'

const handleAuth = () => {
  if (authMode.value === 'register') {
    const name = authForm.value.username || 'User'
    doLogin(name)
    return
  }
  // 登录：密码为 123456 即可
  if (authForm.value.password === DEMO_PASSWORD && authForm.value.username.trim()) {
    doLogin(authForm.value.username.trim())
  } else {
    alert('账号或密码错误')
  }
}

const doLogin = (username) => {
  isLoggedIn.value = true
  currentUser.value = username
  localStorage.setItem('nexusmind_logged_in', 'true')
  localStorage.setItem('nexusmind_user', username)
  showAuthModal.value = false
  // 回到顶部（dashboard 会自动显示）
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleLogout = () => {
  isLoggedIn.value = false
  currentUser.value = ''
  localStorage.removeItem('nexusmind_logged_in')
  localStorage.removeItem('nexusmind_user')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  // 恢复登录状态
  if (localStorage.getItem('nexusmind_logged_in') === 'true') {
    isLoggedIn.value = true
    currentUser.value = localStorage.getItem('nexusmind_user') || 'User'
  }
  // 延迟一点触发动画，确保页面渲染完成
  setTimeout(() => {
    isMounted.value = true
  }, 50)
})

const formData = ref({
  simulationRequirement: ''
})

const sourceMode = ref('file') // 'file' | 'web'
const webQuery = ref('')
const webQueryForFile = ref('') // 文件上传模式下的可选网络搜索关键词
const enableWebSearch = ref(false) // 文件上传模式下是否同时启用网络抓取
const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

const canSubmit = computed(() => {
  const hasRequirement = formData.value.simulationRequirement.trim() !== ''
  if (sourceMode.value === 'file') {
    const hasFiles = files.value.length > 0
    // 如果启用了网络抓取，还需要填写搜索关键词
    if (enableWebSearch.value) {
      return hasRequirement && hasFiles && webQueryForFile.value.trim() !== ''
    }
    return hasRequirement && hasFiles
  } else {
    return hasRequirement && webQuery.value.trim() !== ''
  }
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

  if (sourceMode.value === 'file' && enableWebSearch.value) {
    // 混合模式：文件 + 网络抓取
    import('../store/pendingUpload.js').then(({ setPendingFileAndWeb }) => {
      setPendingFileAndWeb(files.value, webQueryForFile.value.trim(), formData.value.simulationRequirement)
      router.push({ name: 'Process', params: { projectId: 'new' } })
    })
  } else if (sourceMode.value === 'file') {
    import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
      setPendingUpload(files.value, formData.value.simulationRequirement)
      router.push({ name: 'Process', params: { projectId: 'new' } })
    })
  } else {
    import('../store/pendingUpload.js').then(({ setPendingWebSearch }) => {
      setPendingWebSearch(webQuery.value.trim(), formData.value.simulationRequirement)
      router.push({ name: 'Process', params: { projectId: 'new' } })
    })
  }
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
  /* 青色变量（与主题一致） */
  --blue-primary: #3A5A6A;
  --blue-accent: #73A8B9;
  --blue-light: #8EBDCB;

  /* ================= 容器基础设置 ================= */
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  font-family: var(--font-sans);
  color: var(--text-primary);
  
  /* ================= 核心：高亮科技感背景 ================= */
  background-color: #f8fbff;
  
  background-image: 
    /* 层级1：全息坐标网格 (细锐的青色线，构建空间秩序感) */
    linear-gradient(rgba(147, 197, 253, 0.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(147, 197, 253, 0.15) 1px, transparent 1px),
    
    /* 层级2：高亮核心光源 (大幅提升透明度，制造“发光”错觉) */
    radial-gradient(ellipse 50% 40% at 20% 80%, rgba(96, 165, 250, 0.12) 0%, transparent 50%),
    radial-gradient(ellipse 50% 35% at 85% 15%, rgba(59, 130, 246, 0.1) 0%, transparent 55%),
    radial-gradient(ellipse 60% 50% at 60% 60%, rgba(147, 197, 253, 0.15) 0%, transparent 50%),
    linear-gradient(180deg, #f8fbff 0%, #f3f7fc 50%, #eef4fc 100%);

  /* 定义网格大小(40px)和光晕铺满 */
  background-size:
    40px 40px, 40px 40px,
    100% 100%, 100% 100%, 100% 100%, 100% 100%;
    
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
    linear-gradient(rgba(147, 197, 253, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(147, 197, 253, 0.08) 1px, transparent 1px);
  background-size: 88px 88px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.2), transparent 82%);
  z-index: 0;
}

:global(html) {
  scrollbar-width: thin;
  scrollbar-color: #93c5fd #e0effe;
}

:global(body) {
  scrollbar-width: thin;
  scrollbar-color: #93c5fd #e0effe;
}

:global(html::-webkit-scrollbar),
:global(body::-webkit-scrollbar) {
  width: 10px;
}

:global(html::-webkit-scrollbar-track),
:global(body::-webkit-scrollbar-track) {
  background: #e0effe;
  border-left: 1px solid rgba(147, 197, 253, 0.2);
}

:global(html::-webkit-scrollbar-thumb),
:global(body::-webkit-scrollbar-thumb) {
  background: linear-gradient(180deg, #93c5fd, #60a5fa);
  border: 2px solid #e0effe;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.5);
}

:global(html::-webkit-scrollbar-thumb:hover),
:global(body::-webkit-scrollbar-thumb:hover) {
  background: linear-gradient(180deg, #60a5fa, #3b82f6);
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
  border: 1.5px solid rgba(147, 197, 253, 0.5);
  box-shadow:
    0 0 0 1px rgba(96, 165, 250, 0.15),
    0 0 20px rgba(96, 165, 250, 0.3);
  background: rgba(227, 242, 255, 0.8);
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
  color: var(--blue-primary);
}

.brand-badge {
  font-size: 0.7rem;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}

.nav-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-tag {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--blue-accent);
  background: rgba(96, 165, 250, 0.1);
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(96, 165, 250, 0.2);
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
  border: 1px solid rgba(147, 197, 253, 0.5);
  background: rgba(227, 242, 255, 0.7);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.6),
    0 0 16px rgba(96, 165, 250, 0.15);
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
  border-color: rgba(96, 165, 250, 0.7);
  box-shadow:
    inset 0 0 0 1px rgba(96, 165, 250, 0.15),
    0 0 22px rgba(96, 165, 250, 0.25);
  color: var(--blue-accent);
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
    linear-gradient(180deg, rgba(255, 255, 255, 0.8), transparent 12%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.75), rgba(227, 242, 255, 0.7));
  border: 1px solid rgba(147, 197, 253, 0.5);
  clip-path: polygon(0 18px, 18px 0, calc(100% - 24px) 0, 100% 24px, 100% calc(100% - 24px), calc(100% - 24px) 100%, 18px 100%, 0 calc(100% - 18px));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.8),
    0 0 34px rgba(96, 165, 250, 0.15);
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
  border: 1px solid rgba(147, 197, 253, 0.25);
  clip-path: polygon(0 10px, 10px 0, calc(100% - 12px) 0, 100% 12px, 100% calc(100% - 12px), calc(100% - 12px) 100%, 12px 100%, 0 calc(100% - 10px));
}

.hero-panel::after {
  right: -40px;
  top: 90px;
  width: 340px;
  height: 340px;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.25), transparent 70%);
  filter: blur(6px);
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
  color: var(--blue-primary);
  text-shadow: 0 0 18px rgba(96, 165, 250, 0.2);
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
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(147, 197, 253, 0.5);
  border-radius: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 18px rgba(96, 165, 250, 0.1);
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
  border: 1px solid rgba(147, 197, 253, 0.5);
  background: rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 0 12px rgba(96, 165, 250, 0.08);
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
  background: rgba(96, 165, 250, 0.12);
  padding: 3px 8px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--blue-primary);
  font-weight: 600;
  border: 1px solid rgba(96, 165, 250, 0.2);
}

.hero-cta-banner {
  display: inline-flex;
  align-items: center;
  padding: 18px 26px;
  margin-bottom: 20px;
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: var(--blue-primary);
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(147, 197, 253, 0.5);
  border-radius: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(96, 165, 250, 0.15);
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
  border: 1px solid rgba(147, 197, 253, 0.3);
  border-radius: 24px;
  background:
    rgba(255, 255, 255, 0.6),
    radial-gradient(circle at 50% 42%, rgba(96, 165, 250, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.65), rgba(227, 242, 255, 0.4));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.8),
    inset 0 -30px 60px rgba(200, 220, 255, 0.3);
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
  background: rgba(96, 165, 250, 0.7);
  box-shadow: 0 0 10px rgba(96, 165, 250, 0.35);
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
  background: linear-gradient(180deg, rgba(96, 165, 250, 0.12), rgba(96, 165, 250, 0.04));
  border: 1px solid rgba(96, 165, 250, 0.25);
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
    0 0 20px rgba(96, 165, 250, 0.35),
    0 0 36px rgba(96, 165, 250, 0.18);
}

.data-ribbon-one {
  top: 228px;
  left: 30px;
  width: 88%;
  transform: rotate(8deg);
  background: linear-gradient(90deg, rgba(96, 165, 250, 0), rgba(96, 165, 250, 0.8) 36%, rgba(96, 165, 250, 0.25) 70%, rgba(96, 165, 250, 0));
}

.data-ribbon-two {
  top: 318px;
  left: -6px;
  width: 92%;
  transform: rotate(-9deg);
  background: linear-gradient(90deg, rgba(96, 165, 250, 0), rgba(96, 165, 250, 0.5) 28%, rgba(96, 165, 250, 0.95) 56%, rgba(96, 165, 250, 0));
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
  filter: blur(10px);
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

.logo-container {
  contain: layout paint;
}

.hero-logo {
  max-width: 100%;
  width: min(100%, 590px);
  position: relative;
  z-index: 1;
  /* perf: 单层 drop-shadow，避免双重滤镜与动画叠加造成的帧重绘 */
  filter: drop-shadow(0 0 28px rgba(115, 168, 185, 0.28));
  animation: logo-float 7s ease-in-out infinite;
  will-change: transform;
  transform: translateZ(0);
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
    radial-gradient(circle at center, rgba(96, 165, 250, 0.2), transparent 62%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.1)),
    linear-gradient(135deg, rgba(255, 255, 255, 0.4), rgba(255, 255, 255, 0.2));
  border: 1px solid rgba(96, 165, 250, 0.25);
  border-radius: 10px;
  overflow: hidden;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    inset 0 -16px 28px rgba(200, 220, 255, 0.3);
}

.network-line,
.network-node {
  position: absolute;
}

.network-line {
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.1), rgba(96, 165, 250, 0.85), rgba(96, 165, 250, 0.1));
  transform-origin: left center;
  box-shadow:
    0 0 10px rgba(96, 165, 250, 0.15),
    0 0 18px rgba(96, 165, 250, 0.1);
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
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.98), rgba(96, 165, 250, 0.9) 18%, rgba(96, 165, 250, 0.95) 42%, rgba(59, 130, 246, 0.98) 72%, rgba(30, 64, 175, 0.98) 100%);
  border: 1px solid rgba(96, 165, 250, 0.35);
  box-shadow:
    inset -2px -3px 6px rgba(200, 220, 255, 0.5),
    inset 2px 2px 5px rgba(255, 255, 255, 0.3),
    0 0 14px rgba(96, 165, 250, 0.5);
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
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 1), rgba(227, 242, 255, 0.95) 22%, rgba(96, 165, 250, 0.98) 44%, rgba(59, 130, 246, 0.95) 70%, rgba(30, 64, 175, 0.98) 100%);
  box-shadow:
    inset -2px -3px 6px rgba(200, 220, 255, 0.5),
    inset 2px 2px 6px rgba(255, 255, 255, 0.3),
    0 0 18px rgba(96, 165, 250, 0.75),
    0 0 32px rgba(96, 165, 250, 0.35);
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
  border: 1px solid rgba(147, 197, 253, 0.3);
  border-radius: 18px;
  background:
    rgba(255, 255, 255, 0.6),
    linear-gradient(90deg, rgba(255, 255, 255, 0.5), rgba(227, 242, 255, 0.5));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  cursor: pointer;
  color: var(--blue-primary);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  letter-spacing: 0.4px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(96, 165, 250, 0.12);
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
  color: var(--blue-primary);
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
  border: 1px solid rgba(147, 197, 253, 0.35);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 18px rgba(96, 165, 250, 0.15);
}

.scroll-down-btn:hover {
  color: var(--blue-accent);
  transform: translateY(2px);
  border-color: rgba(96, 165, 250, 0.5);
  box-shadow:
    inset 0 0 0 1px rgba(96, 165, 250, 0.1),
    0 0 28px rgba(96, 165, 250, 0.2);
}

.scroll-arrow {
  font-size: 1.7rem;
  line-height: 1;
  text-shadow: 0 0 18px rgba(96, 165, 250, 0.4);
}

.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid rgba(147, 197, 253, 0.25);
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
  border: 1px solid rgba(147, 197, 253, 0.3);
  background: rgba(255, 255, 255, 0.6);
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
  border: 1px solid rgba(147, 197, 253, 0.3);
  background: rgba(255, 255, 255, 0.6);
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
  border: 1px solid rgba(147, 197, 253, 0.35);
  background: rgba(255, 255, 255, 0.6);
  padding: 8px;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.7),
    0 0 22px rgba(96, 165, 250, 0.1);
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

.source-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 12px;
  border: 1px solid rgba(115, 168, 185, 0.25);
  border-radius: 6px;
  overflow: hidden;
}

.source-tab {
  flex: 1;
  padding: 9px 0;
  border: none;
  background: rgba(255, 255, 255, 0.3);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s;
}

.source-tab + .source-tab {
  border-left: 1px solid rgba(115, 168, 185, 0.2);
}

.source-tab.active {
  background: rgba(96, 165, 250, 0.15);
  color: var(--blue-primary);
  box-shadow: inset 0 -2px 0 var(--blue-accent);
}

.source-tab:not(.active):hover {
  background: rgba(255, 255, 255, 0.55);
  color: var(--text-secondary);
}

.source-panel {
  min-height: 0;
}

.web-search-input {
  position: relative;
}

.web-query-input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(115, 168, 185, 0.3);
  background: rgba(255, 255, 255, 0.4);
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: var(--text-primary);
  transition: all 0.25s;
  outline: none;
  box-sizing: border-box;
}

.web-query-input::placeholder {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.web-query-input:focus {
  border-color: var(--teal-primary);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: 0 0 0 3px rgba(115, 168, 185, 0.12);
}

.search-badge {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.5px;
  color: var(--teal-primary);
  background: rgba(115, 168, 185, 0.1);
  border: 1px solid rgba(115, 168, 185, 0.2);
  padding: 3px 8px;
  border-radius: 4px;
  pointer-events: none;
}

.web-toggle-section {
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(115, 168, 185, 0.06);
  border: 1px solid rgba(115, 168, 185, 0.15);
  border-radius: 6px;
}

.web-toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.web-toggle-checkbox {
  accent-color: var(--teal-primary);
  width: 15px;
  height: 15px;
  cursor: pointer;
}

.web-toggle-text {
  font-family: var(--font-cn);
  font-size: 0.85rem;
  color: var(--text-primary);
  font-weight: 500;
}

.web-toggle-hint {
  font-family: var(--font-cn);
  font-size: 0.75rem;
  color: var(--text-muted);
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
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.2), rgba(59, 130, 246, 0.15));
  color: var(--blue-primary);
  border: 1px solid rgba(96, 165, 250, 0.5);
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
  will-change: box-shadow;
}

.start-engine-btn:not(:disabled):hover {
  animation: pulse-border-blue 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: linear-gradient(90deg, rgba(96, 165, 250, 0.3), rgba(59, 130, 246, 0.25));
  border-color: rgba(96, 165, 250, 0.7);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: rgba(227, 242, 255, 0.5);
  color: rgba(59, 130, 246, 0.5);
  cursor: not-allowed;
  transform: none;
  border: 1px solid rgba(147, 197, 253, 0.2);
}

@keyframes pulse-border-blue {
  0% { box-shadow: 0 0 0 0 rgba(96, 165, 250, 0.3); }
  70% { box-shadow: 0 0 0 8px rgba(96, 165, 250, 0); }
  100% { box-shadow: 0 0 0 0 rgba(96, 165, 250, 0); }
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

/* ========== 入场动画 ========== */
.hero-left,
.hero-right,
.left-panel,
.right-panel {
  opacity: 0;
}

/* Hero 区域动画 */
.hero-left.slide-in-left {
  animation: slideInLeft 1.2s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.hero-right.slide-in-right {
  animation: slideInRight 1.2s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.15s;
}

/* Dashboard 区域动画 - 延迟执行，等 Hero 完成后 */
.left-panel.slide-in-left {
  animation: slideInLeft 1s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.5s;
}

.right-panel.slide-in-right {
  animation: slideInRight 1s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.65s;
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-80px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(80px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ========== 登录/注册弹窗样式 ========== */
.auth-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.login-btn {
  background: rgba(96, 165, 250, 0.15);
  color: var(--blue-primary);
  border: 1px solid rgba(96, 165, 250, 0.4);
  margin: 0 8px;
}

.login-btn:hover {
  background: rgba(96, 165, 250, 0.25);
  border-color: rgba(96, 165, 250, 0.6);
  transform: translateY(-1px);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 8px;
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #73A8B9, #5C9EAF);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--blue-primary);
  font-family: var(--font-mono);
}

.logout-btn {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
  font-size: 12px;
  padding: 4px 10px;
}

.logout-btn:hover {
  background: rgba(96, 165, 250, 0.1);
  color: var(--blue-primary);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.auth-modal {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 251, 255, 0.98));
  border: 1px solid rgba(147, 197, 253, 0.5);
  border-radius: 20px;
  padding: 32px;
  width: 100%;
  max-width: 440px;
  position: relative;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.8),
    0 25px 50px rgba(59, 130, 246, 0.15),
    0 10px 30px rgba(0, 0, 0, 0.1);
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(147, 197, 253, 0.2);
  border-radius: 8px;
  font-size: 1.2rem;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: rgba(96, 165, 250, 0.2);
  color: var(--teal-primary);
}

.modal-header {
  text-align: center;
  margin-bottom: 24px;
}

.modal-brand {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.modal-logo {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid rgba(147, 197, 253, 0.5);
  box-shadow: 0 0 20px rgba(96, 165, 250, 0.2);
}

.modal-title {
  font-family: var(--font-sans);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.modal-subtitle {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin: 0;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.form-input {
  padding: 14px 16px;
  border: 1px solid rgba(147, 197, 253, 0.4);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--text-primary);
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--blue-accent);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.15);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.password-wrapper {
  position: relative;
}

.password-wrapper .form-input {
  padding-right: 60px;
}

.password-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--blue-accent);
  font-size: 0.8rem;
  cursor: pointer;
  font-family: var(--font-mono);
}

.password-toggle:hover {
  color: var(--blue-primary);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.remember-me {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-secondary);
}

.remember-me input {
  accent-color: var(--blue-accent);
}

.forgot-link {
  color: var(--blue-accent);
  text-decoration: none;
}

.forgot-link:hover {
  color: var(--blue-primary);
  text-decoration: underline;
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  color: white;
  border: none;
  border-radius: 10px;
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s ease;
  letter-spacing: 1px;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
}

.submit-btn:hover {
  background: linear-gradient(135deg, #1D4ED8, #1E40AF);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5);
}

.divider {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 16px 0;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(147, 197, 253, 0.4);
}

.social-login {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.social-btn {
  width: 100%;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(147, 197, 253, 0.4);
  border-radius: 10px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.social-btn:hover {
  background: rgba(147, 197, 253, 0.1);
  border-color: rgba(96, 165, 250, 0.5);
  transform: translateY(-1px);
}

.social-icon {
  width: 20px;
  height: 20px;
}

.mode-switch {
  text-align: center;
  margin-top: 16px;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.switch-btn {
  background: none;
  border: none;
  color: var(--blue-accent);
  font-weight: 600;
  cursor: pointer;
  margin-left: 6px;
  font-family: var(--font-mono);
}

.switch-btn:hover {
  color: var(--blue-primary);
  text-decoration: underline;
}

/* 弹窗动画 */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .auth-modal,
.modal-fade-leave-active .auth-modal {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.modal-fade-enter-from .auth-modal,
.modal-fade-leave-to .auth-modal {
  transform: scale(0.95) translateY(20px);
  opacity: 0;
}
</style>
