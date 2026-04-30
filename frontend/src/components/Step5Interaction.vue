<template>
  <div class="interaction-panel">
    <!-- Main Split Layout -->
    <div class="main-split-layout">
      <!-- LEFT PANEL: Report Style -->
      <div class="left-panel report-style" ref="leftPanel">
        <div v-if="reportOutline" class="report-content-wrapper">
          <!-- Report Header -->
          <div class="report-header-block">
            <div class="report-meta">
              <span class="report-tag">决策预测报告</span>
              <span class="report-id">ID: {{ reportId || 'REF-2024-X92' }}</span>
            </div>
            <h1 class="main-title">{{ reportOutline.title }}</h1>
            <p class="sub-title">{{ reportOutline.summary }}</p>
            <div class="header-divider"></div>
          </div>

          <!-- Sections List -->
          <div class="sections-list">
            <div 
              v-for="(section, idx) in reportOutline.sections" 
              :key="idx"
              class="report-section-item"
              :class="{ 
                'is-active': currentSectionIndex === idx + 1,
                'is-completed': isSectionCompleted(idx + 1),
                'is-pending': !isSectionCompleted(idx + 1) && currentSectionIndex !== idx + 1
              }"
            >
              <div class="section-header-row" @click="toggleSectionCollapse(idx)" :class="{ 'clickable': isSectionCompleted(idx + 1) }">
                <span class="section-number">{{ String(idx + 1).padStart(2, '0') }}</span>
                <h3 class="section-title">{{ section.title }}</h3>
                <svg 
                  v-if="isSectionCompleted(idx + 1)" 
                  class="collapse-icon" 
                  :class="{ 'is-collapsed': collapsedSections.has(idx) }"
                  viewBox="0 0 24 24" 
                  width="20" 
                  height="20" 
                  fill="none" 
                  stroke="currentColor" 
                  stroke-width="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              
              <Transition name="section-slide">
                <div class="section-body" v-show="!collapsedSections.has(idx)">
                  <!-- Completed Content -->
                  <div v-if="generatedSections[idx + 1]" class="generated-content" v-html="renderMarkdown(generatedSections[idx + 1])"></div>

                  <!-- Loading State -->
                  <div v-else-if="currentSectionIndex === idx + 1" class="loading-state">
                    <div class="loading-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="10" stroke-width="4" stroke="#E5E7EB"></circle>
                        <path d="M12 2a10 10 0 0 1 10 10" stroke-width="4" stroke="#4B5563" stroke-linecap="round"></path>
                      </svg>
                    </div>
                    <span class="loading-text">正在生成{{ section.title }}...</span>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </div>

        <!-- Waiting State -->
        <div v-if="!reportOutline" class="waiting-placeholder">
          <div class="waiting-animation">
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
            <div class="waiting-ring"></div>
          </div>
          <span class="waiting-text">等待决策简报生成...</span>
        </div>
      </div>

      <!-- RIGHT PANEL: Interaction Interface -->
      <div class="right-panel" ref="rightPanel">
        <!-- Unified Action Bar - Professional Design -->
        <div class="action-bar">
        <div class="action-bar-header">
          <svg class="action-bar-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <div class="action-bar-text">
            <span class="action-bar-title">智能研判工作台</span>
            <span class="action-bar-subtitle mono">{{ profiles.length || 25 }} 个角色可访谈</span>
          </div>
        </div>
          <div class="action-bar-tabs">
            <button 
              class="tab-pill"
              :class="{ active: activeTab === 'chat' && chatTarget === 'report_agent' }"
              @click="selectReportAgentChat"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
              </svg>
              <span>追问决策简报</span>
            </button>
            <div class="agent-dropdown" v-if="profiles.length > 0">
              <button 
                class="tab-pill agent-pill"
                :class="{ active: activeTab === 'chat' && chatTarget === 'agent' }"
                @click="toggleAgentDropdown"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                </svg>
                <span>{{ selectedAgent ? selectedAgent.username : '访谈模拟角色' }}</span>
                <svg class="dropdown-arrow" :class="{ open: showAgentDropdown }" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
              <div v-if="showAgentDropdown" class="dropdown-menu">
                <div class="dropdown-header">选择对话对象</div>
                <div 
                  v-for="(agent, idx) in profiles" 
                  :key="idx"
                  class="dropdown-item"
                  @click="selectAgent(agent, idx)"
                >
                  <div class="agent-avatar">{{ (agent.username || 'A')[0] }}</div>
                  <div class="agent-info">
                    <span class="agent-name">{{ agent.username }}</span>
                    <span class="agent-role">{{ agent.profession || '未知职业' }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="tab-divider"></div>
            <button 
              class="tab-pill survey-pill"
              :class="{ active: activeTab === 'survey' }"
              @click="selectSurveyTab"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"></path>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
              </svg>
              <span>发布群体问卷</span>
            </button>
          </div>
        </div>

        <!-- Chat Mode -->
        <div v-if="activeTab === 'chat'" class="chat-container">

          <!-- Report Agent Tools Card -->
          <div v-if="chatTarget === 'report_agent'" class="report-agent-tools-card">
            <div class="tools-card-header">
              <div class="tools-card-avatar">R</div>
              <div class="tools-card-info">
                <div class="tools-card-name">ReportAgent 决策追问</div>
                <div class="tools-card-subtitle">围绕报告结论追问因果、证据与处置建议，自动调用图谱检索与虚拟访谈工具</div>
              </div>
              <button class="tools-card-toggle" @click="showToolsDetail = !showToolsDetail">
                <svg :class="{ 'is-expanded': showToolsDetail }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div v-if="showToolsDetail" class="tools-card-body">
              <div class="tools-grid">
                <div class="tool-item tool-agent tool-active">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 3l7 4v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V7l7-4z"></path>
                      <path d="M9 12l2 2 4-5"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">ReportAgent 决策追问</div>
                    <div class="tool-desc">围绕报告结论、证据来源与处置建议进行多轮追问</div>
                  </div>
                </div>
                <div class="tool-item tool-purple">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.5V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.5A7 7 0 0 0 12 2z"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InsightForge 因果归因</div>
                    <div class="tool-desc">对齐种子材料与推演状态，定位关键转折、风险诱因与处置窗口</div>
                  </div>
                </div>
                <div class="tool-item tool-blue">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">PanoramaSearch 传播追踪</div>
                    <div class="tool-desc">沿事件图谱追踪信息扩散链路，复盘议题聚合与放大路径</div>
                  </div>
                </div>
                <div class="tool-item tool-orange">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">QuickSearch 证据检索</div>
                    <div class="tool-desc">快速提取图谱节点、事实片段与报告依据，支撑可解释追问</div>
                  </div>
                </div>
                <div class="tool-item tool-green">
                  <div class="tool-icon-wrapper">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                      <circle cx="9" cy="7" r="4"></circle>
                      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                  </div>
                  <div class="tool-content">
                    <div class="tool-name">InterviewSubAgent 群体访谈</div>
                    <div class="tool-desc">并行访谈模拟角色，采集立场变化、关注议题与潜在反应</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Agent Profile Card -->
          <div v-if="chatTarget === 'agent' && selectedAgent" class="agent-profile-card">
            <div class="profile-card-header">
              <div class="profile-card-avatar">{{ (selectedAgent.username || 'A')[0] }}</div>
              <div class="profile-card-info">
                <div class="profile-card-name">{{ selectedAgent.username }}</div>
                <div class="profile-card-meta">
                  <span v-if="selectedAgent.name" class="profile-card-handle">@{{ selectedAgent.name }}</span>
                  <span class="profile-card-profession">{{ selectedAgent.profession || '未知职业' }}</span>
                </div>
              </div>
              <button class="profile-card-toggle" @click="showFullProfile = !showFullProfile">
                <svg :class="{ 'is-expanded': showFullProfile }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>
            </div>
            <div v-if="showFullProfile && selectedAgent.bio" class="profile-card-body">
              <div class="profile-card-bio">
                <div class="profile-card-label">简介</div>
                <p>{{ selectedAgent.bio }}</p>
              </div>
            </div>
          </div>

          <!-- Chat Messages -->
          <div class="chat-messages" ref="chatMessages">
            <div v-if="chatHistory.length === 0" class="chat-empty">
              <div class="empty-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <p class="empty-text">
                {{ chatTarget === 'report_agent' ? '追问报告结论、证据来源与下一步处置建议' : '访谈模拟角色，了解群体立场与情绪变化' }}
              </p>
            </div>
            <div 
              v-for="(msg, idx) in chatHistory" 
              :key="idx"
              class="chat-message"
              :class="msg.role"
            >
              <div class="message-avatar">
                <span v-if="msg.role === 'user'">U</span>
                <span v-else>{{ msg.role === 'assistant' && chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
              </div>
              <div class="message-content">
                <div class="message-header">
                  <span class="sender-name">
                    {{ msg.role === 'user' ? 'You' : (chatTarget === 'report_agent' ? 'Report Agent' : (selectedAgent?.username || 'Agent')) }}
                  </span>
                  <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                </div>
                <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>
            <div v-if="isSending" class="chat-message assistant">
              <div class="message-avatar">
                <span>{{ chatTarget === 'report_agent' ? 'R' : (selectedAgent?.username?.[0] || 'A') }}</span>
              </div>
              <div class="message-content">
                <div class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Input -->
          <div class="chat-input-area">
            <textarea 
              v-model="chatInput"
              class="chat-input"
              placeholder="输入追问，例如：当前最值得优先处置的风险点是什么？"
              @keydown.enter.exact.prevent="sendMessage"
              :disabled="isSending || (!selectedAgent && chatTarget === 'agent')"
              rows="1"
              ref="chatInputRef"
            ></textarea>
            <button 
              class="send-btn"
              @click="sendMessage"
              :disabled="!chatInput.trim() || isSending || (!selectedAgent && chatTarget === 'agent')"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>

        <!-- Survey Mode -->
        <div v-if="activeTab === 'survey'" class="survey-container">
          <!-- Panel 1: 选择调查对象 -->
          <div class="survey-panel" :style="{ height: surveyPanelHeights[0] + 'px' }">
            <div class="panel-inner">
              <div class="section-header">
                <span class="section-title">选择调查对象</span>
                <span class="selection-count">已选 {{ selectedAgentsCount }} / {{ profiles.length }}</span>
              </div>
              <div class="agents-grid">
                <div 
                  v-for="(agent, idx) in profiles" 
                  :key="idx"
                  class="agent-checkbox"
                  :class="{ checked: !!selectedAgentsMap[idx] }"
                  @click="toggleAgentSelection(idx)"
                >
                  <div class="checkbox-avatar">{{ (agent.username || 'A')[0] }}</div>
                  <div class="checkbox-info">
                    <span class="checkbox-name">{{ agent.username }}</span>
                    <span class="checkbox-role">{{ agent.profession || '未知职业' }}</span>
                  </div>
                  <div class="checkbox-indicator">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  </div>
                </div>
              </div>
              <div class="selection-actions">
                <button class="action-link" @click="selectAllAgents">全选</button>
                <span class="action-divider">|</span>
                <button class="action-link" @click="clearAgentSelection">清空</button>
              </div>
            </div>
          </div>

          <!-- Divider 1 -->
          <div class="resize-divider" @mousedown="startResize($event, 0)">
            <div class="divider-line"></div>
          </div>

          <!-- Panel 2: 问卷问题 + 发送 -->
          <div class="survey-panel" :style="{ height: surveyPanelHeights[1] + 'px' }">
            <div class="panel-inner">
              <div class="section-header">
                <span class="section-title">问卷问题</span>
              </div>
              <textarea 
                v-model="surveyQuestion"
                class="survey-input"
                placeholder="输入您想问所有被选中对象的问题..."
              ></textarea>
              <button 
                class="survey-submit-btn"
                :disabled="selectedAgentsCount === 0 || !surveyQuestion.trim() || isSurveying"
                @click="submitSurvey"
              >
                <span v-if="isSurveying" class="loading-spinner"></span>
                <span v-else>发送问卷</span>
              </button>
            </div>
          </div>

          <!-- Divider 2 (only when results exist) -->
          <div v-if="surveyResults.length > 0" class="resize-divider" @mousedown="startResize($event, 1)">
            <div class="divider-line"></div>
          </div>

          <!-- Panel 3: 调查结果 -->
          <div v-if="surveyResults.length > 0" class="survey-panel survey-panel-results" :style="{ flex: '1 1 auto', minHeight: surveyPanelHeights[2] + 'px' }">
            <div class="panel-inner">
              <div class="results-header">
                <span class="results-title">调查结果</span>
                <span class="results-count">{{ surveyResults.length }} 条回复</span>
              </div>
              <div class="results-list">
                <div 
                  v-for="(result, idx) in surveyResults" 
                  :key="idx"
                  class="result-card"
                >
                  <div class="result-header">
                    <div class="result-avatar">{{ (result.agent_name || 'A')[0] }}</div>
                    <div class="result-info">
                      <span class="result-name">{{ result.agent_name }}</span>
                      <span class="result-role">{{ result.profession || '未知职业' }}</span>
                    </div>
                  </div>
                  <div class="result-question">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                      <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    <span>{{ result.question }}</span>
                  </div>
                  <div class="result-answer" v-html="renderMarkdown(result.answer)"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { chatWithReport, getReport, getAgentLog } from '../api/report'
import { interviewAgents, interviewAgentOffline, getSimulationProfilesRealtime, getEnvStatus } from '../api/simulation'

const props = defineProps({
  reportId: String,
  simulationId: String
})

const emit = defineEmits(['add-log', 'update-status'])

// State
const activeTab = ref('chat')
const chatTarget = ref('report_agent')
const showAgentDropdown = ref(false)
const selectedAgent = ref(null)
const selectedAgentIndex = ref(null)
const showFullProfile = ref(true)
const showToolsDetail = ref(true)

// Chat State
const chatInput = ref('')
const chatHistory = ref([])
const chatHistoryCache = ref({}) // 缓存所有对话记录: { 'report_agent': [], 'agent_0': [], 'agent_1': [], ... }
const isSending = ref(false)
const chatMessages = ref(null)
const chatInputRef = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight
    }
  })
}

// --- sessionStorage 持久化 ---
const CHAT_CACHE_VERSION = 2 // 递增此值可强制清除旧缓存
const storageKey = computed(() => `nexusmind_step5_chat_${props.simulationId || 'default'}`)

const persistToStorage = () => {
  try {
    const payload = {
      cacheVersion: CHAT_CACHE_VERSION,
      chatHistoryCache: chatHistoryCache.value,
      activeTarget: chatTarget.value,
      selectedAgentIdx: selectedAgentIndex.value,
      surveyResults: surveyResults.value
    }
    localStorage.setItem(storageKey.value, JSON.stringify(payload))
  } catch { /* quota exceeded, ignore */ }
}

const restoreFromStorage = () => {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (!raw) return
    const payload = JSON.parse(raw)
    // 版本不匹配时清除旧的对话缓存（保留问卷结果）
    if (payload.cacheVersion !== CHAT_CACHE_VERSION) {
      localStorage.removeItem(storageKey.value)
      if (payload.surveyResults) {
        surveyResults.value = payload.surveyResults
      }
      return
    }
    if (payload.chatHistoryCache) {
      chatHistoryCache.value = payload.chatHistoryCache
    }
    if (payload.surveyResults) {
      surveyResults.value = payload.surveyResults
    }
    // 恢复当前对话目标的历史
    const targetKey = payload.activeTarget === 'agent' && payload.selectedAgentIdx !== null
      ? `agent_${payload.selectedAgentIdx}`
      : 'report_agent'
    chatHistory.value = chatHistoryCache.value[targetKey] || []
  } catch { /* parse error, ignore */ }
}

// Survey State
const selectedAgentsMap = ref({})  // { 0: true, 2: true, ... } 普通对象保证Vue反应性
const selectedAgentsCount = computed(() => Object.keys(selectedAgentsMap.value).filter(k => selectedAgentsMap.value[k]).length)
const surveyQuestion = ref('')
const surveyResults = ref([])
const isSurveying = ref(false)

// Survey panel resizable heights (px): [agents, question, results]
const surveyPanelHeights = ref([280, 220, 200])
let resizingIdx = null
let resizeStartY = 0
let resizeStartHeights = [0, 0]

const startResize = (e, dividerIdx) => {
  e.preventDefault()
  resizingIdx = dividerIdx
  resizeStartY = e.clientY
  resizeStartHeights = [surveyPanelHeights.value[dividerIdx], surveyPanelHeights.value[dividerIdx + 1]]
  document.addEventListener('mousemove', onResizeMove)
  document.addEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = 'row-resize'
  document.body.style.userSelect = 'none'
}

const onResizeMove = (e) => {
  if (resizingIdx === null) return
  const delta = e.clientY - resizeStartY
  const minH = 80
  let newTop = resizeStartHeights[0] + delta
  let newBottom = resizeStartHeights[1] - delta
  if (newTop < minH) { newTop = minH; newBottom = resizeStartHeights[0] + resizeStartHeights[1] - minH }
  if (newBottom < minH) { newBottom = minH; newTop = resizeStartHeights[0] + resizeStartHeights[1] - minH }
  const copy = [...surveyPanelHeights.value]
  copy[resizingIdx] = newTop
  copy[resizingIdx + 1] = newBottom
  surveyPanelHeights.value = copy
}

const onResizeEnd = () => {
  resizingIdx = null
  document.removeEventListener('mousemove', onResizeMove)
  document.removeEventListener('mouseup', onResizeEnd)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// Report Data
const reportOutline = ref(null)
const generatedSections = ref({})
const collapsedSections = ref(new Set())
const currentSectionIndex = ref(null)
const profiles = ref([])

// Helper Methods
const isSectionCompleted = (sectionIndex) => {
  return !!generatedSections.value[sectionIndex]
}

// Refs
const leftPanel = ref(null)
const rightPanel = ref(null)

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

const toggleSectionCollapse = (idx) => {
  if (!generatedSections.value[idx + 1]) return
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(idx)) {
    newSet.delete(idx)
  } else {
    newSet.add(idx)
  }
  collapsedSections.value = newSet
}

const selectChatTarget = (target) => {
  chatTarget.value = target
  if (target === 'report_agent') {
    showAgentDropdown.value = false
  }
}

// 保存当前对话记录到缓存
const saveChatHistory = () => {
  if (chatHistory.value.length === 0) return
  
  if (chatTarget.value === 'report_agent') {
    chatHistoryCache.value['report_agent'] = [...chatHistory.value]
  } else if (selectedAgentIndex.value !== null) {
    chatHistoryCache.value[`agent_${selectedAgentIndex.value}`] = [...chatHistory.value]
  }
  persistToStorage()
}

const selectReportAgentChat = () => {
  // 保存当前对话记录
  saveChatHistory()
  
  activeTab.value = 'chat'
  chatTarget.value = 'report_agent'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
  
  // 恢复 Report Agent 的对话记录
  chatHistory.value = chatHistoryCache.value['report_agent'] || []
}

const selectSurveyTab = () => {
  activeTab.value = 'survey'
  selectedAgent.value = null
  selectedAgentIndex.value = null
  showAgentDropdown.value = false
}

const toggleAgentSelection = (idx) => {
  const copy = { ...selectedAgentsMap.value }
  if (copy[idx]) {
    delete copy[idx]
  } else {
    copy[idx] = true
  }
  selectedAgentsMap.value = copy
}

const selectAllAgents = () => {
  const map = {}
  profiles.value.forEach((_, idx) => { map[idx] = true })
  selectedAgentsMap.value = map
}

const clearAgentSelection = () => {
  selectedAgentsMap.value = {}
}

const toggleAgentDropdown = () => {
  showAgentDropdown.value = !showAgentDropdown.value
  if (showAgentDropdown.value) {
    activeTab.value = 'chat'
    chatTarget.value = 'agent'
  }
}

const selectAgent = (agent, idx) => {
  // 保存当前对话记录
  saveChatHistory()
  
  selectedAgent.value = agent
  selectedAgentIndex.value = idx
  chatTarget.value = 'agent'
  showAgentDropdown.value = false
  
  // 恢复该 Agent 的对话记录
  chatHistory.value = chatHistoryCache.value[`agent_${idx}`] || []
  addLog(`选择对话对象: ${agent.username}`)
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit'
    })
  } catch {
    return ''
  }
}

const renderMarkdown = (content) => {
  if (!content) return ''
  
  let processedContent = content.replace(/^##\s+.+\n+/, '')
  let html = processedContent.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  
  // 处理列表 - 支持子列表
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })
  
  // 包装无序列表
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  // 包装有序列表
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')
  
  // 清理列表项之间的所有空白
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  // 清理列表开始标签后的空白
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  // 清理列表结束标签前的空白
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')
  
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5])/g, '$1')
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, '$1')
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')
  // 清理块级元素前后的 <br> 标签
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, '$1')
  // 清理 <p><br> 紧跟块级元素的情况（多余空行导致）
  html = html.replace(/<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g, '$2')
  // 清理连续的 <br> 标签
  html = html.replace(/(<br>\s*){2,}/g, '<br>')
  // 清理块级元素后紧跟的段落开始标签前的 <br>
  html = html.replace(/(<\/ol>|<\/ul>|<\/blockquote>)<br>(<p|<div)/g, '$1$2')

  // 修复非连续有序列表的编号：当单项 <ol> 被段落内容隔开时，保持编号递增
  const tokens = html.split(/(<ol class="md-ol">(?:<li class="md-oli"[^>]*>[\s\S]*?<\/li>)+<\/ol>)/g)
  let olCounter = 0
  let inSequence = false
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].startsWith('<ol class="md-ol">')) {
      const liCount = (tokens[i].match(/<li class="md-oli"/g) || []).length
      if (liCount === 1) {
        olCounter++
        if (olCounter > 1) {
          tokens[i] = tokens[i].replace('<ol class="md-ol">', `<ol class="md-ol" start="${olCounter}">`)
        }
        inSequence = true
      } else {
        olCounter = 0
        inSequence = false
      }
    } else if (inSequence) {
      if (/<h[2-5]/.test(tokens[i])) {
        olCounter = 0
        inSequence = false
      }
    }
  }
  html = tokens.join('')

  return html
}

// Chat Methods
const sendMessage = async () => {
  console.log('[Chat] sendMessage called, isSending:', isSending.value, 'chatTarget:', chatTarget.value, 'simId:', props.simulationId)
  if (!chatInput.value.trim() || isSending.value) {
    console.warn('[Chat] blocked: empty input or isSending=true')
    return
  }
  
  const message = chatInput.value.trim()
  chatInput.value = ''
  
  // Add user message
  chatHistory.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })
  
  scrollToBottom()
  isSending.value = true
  
  try {
    if (chatTarget.value === 'report_agent') {
      console.log('[Chat] calling sendToReportAgent')
      await sendToReportAgent(message)
    } else {
      console.log('[Chat] calling sendToAgent')
      await sendToAgent(message)
    }
  } catch (err) {
    const errMsg = err?.message || String(err) || '未知错误'
    const isTimeout = errMsg.includes('timeout') || errMsg.includes('ECONNABORTED')
    const isNetwork = errMsg === 'Network Error' || errMsg.includes('ECONNREFUSED')
    let userMsg = `抱歉，发生了错误: ${errMsg}`
    if (isTimeout) userMsg = '请求超时，后端可能正在处理其他任务。请稍后重试。'
    else if (isNetwork) userMsg = '无法连接后端服务，请确认后端已启动。'
    addLog(`发送失败: ${errMsg}`)
    chatHistory.value.push({
      role: 'assistant',
      content: userMsg,
      timestamp: new Date().toISOString()
    })
  } finally {
    isSending.value = false
    scrollToBottom()
    // 自动保存对话记录到缓存
    saveChatHistory()
  }
}

const sendToReportAgent = async (message) => {
  addLog(`向 Report Agent 发送: ${message.substring(0, 50)}...`)
  console.log('[Chat] sendToReportAgent, simulationId:', props.simulationId)
  
  // Build chat history for API
  const historyForApi = chatHistory.value
    .filter(msg => msg.role !== 'user' || msg.content !== message)
    .slice(-10) // Keep last 10 messages
    .map(msg => ({
      role: msg.role,
      content: msg.content
    }))
  
  console.log('[Chat] calling chatWithReport API...')
  const res = await chatWithReport({
    simulation_id: props.simulationId,
    message: message,
    chat_history: historyForApi
  })
  console.log('[Chat] chatWithReport response:', res)
  
  if (res.success && res.data) {
    chatHistory.value.push({
      role: 'assistant',
      content: res.data.response || res.data.answer || '无响应',
      timestamp: new Date().toISOString()
    })
    addLog('Report Agent 已回复')
  } else {
    throw new Error(res.error || '请求失败')
  }
}

const extractAgentResponseContent = (res, agentId) => {
  if (!res?.success || !res?.data) return null

  const resultData = res.data.result || res.data
  const resultsDict = resultData.results || resultData

  if (typeof resultsDict === 'object' && !Array.isArray(resultsDict)) {
    const redditKey = `reddit_${agentId}`
    const twitterKey = `twitter_${agentId}`
    const agentResult = resultsDict[redditKey] || resultsDict[twitterKey] || Object.values(resultsDict)[0]
    return agentResult?.response || agentResult?.answer || null
  }

  if (Array.isArray(resultsDict) && resultsDict.length > 0) {
    const matchedResult = resultsDict.find(r => r.agent_id === agentId) || resultsDict[0]
    return matchedResult?.response || matchedResult?.answer || null
  }

  return null
}

const sendToAgent = async (message) => {
  if (!selectedAgent.value || selectedAgentIndex.value === null) {
    throw new Error('请先选择一个模拟个体')
  }

  addLog(`向 ${selectedAgent.value.username} 发送: ${message.substring(0, 50)}...`)
  
  // Build clean chat history: only keep paired user→assistant turns
  const pairedHistory = []
  const allMsgs = chatHistory.value.filter(m => m.content !== message)
  for (let i = 0; i < allMsgs.length; i++) {
    if (allMsgs[i].role === 'user' && allMsgs[i + 1]?.role === 'assistant') {
      pairedHistory.push(allMsgs[i], allMsgs[i + 1])
      i++ // skip assistant
    }
  }
  const recentPairs = pairedHistory.slice(-6)

  let prompt = message
  if (recentPairs.length > 0) {
    const historyContext = recentPairs
      .map(msg => `${msg.role === 'user' ? '提问者' : '你'}：${msg.content}`)
      .join('\n')
    prompt = `以下是我们之前的对话：\n${historyContext}\n\n现在我的新问题是：${message}`
  }

  // 检查模拟环境是否存活，决定使用在线还是离线模式
  let useOffline = false
  try {
    const envRes = await getEnvStatus({ simulation_id: props.simulationId })
    useOffline = !envRes?.data?.env_alive
  } catch {
    useOffline = true
  }

  let res
  if (useOffline) {
    // 离线模式：用存储的人设+记忆，LLM模拟Agent回答
    addLog(`[离线模式] 模拟环境未运行，使用本地数据模拟对话`)
    const chatHistoryForApi = recentPairs.map(msg => ({ role: msg.role, content: msg.content }))
    res = await interviewAgentOffline({
      simulation_id: props.simulationId,
      agent_id: selectedAgentIndex.value,
      prompt: prompt,
      chat_history: chatHistoryForApi
    })
  } else {
    // 在线模式：通过OASIS模拟环境真实采访
    res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: [{
        agent_id: selectedAgentIndex.value,
        prompt: prompt
      }]
    })
  }
  
  if (res.success && res.data) {
    const responseContent = extractAgentResponseContent(res, selectedAgentIndex.value)
    
    if (responseContent) {
      chatHistory.value.push({
        role: 'assistant',
        content: responseContent,
        timestamp: new Date().toISOString()
      })
      addLog(`${selectedAgent.value.username} 已回复${useOffline ? '（离线模式）' : ''}`)
    } else {
      throw new Error('无响应数据')
    }
  } else {
    throw new Error(res.error || '请求失败')
  }
}

const submitSurvey = async () => {
  if (selectedAgentsCount.value === 0 || !surveyQuestion.value.trim()) return
  
  isSurveying.value = true
  addLog(`发送问卷给 ${selectedAgentsCount.value} 个对象...`)
  
  try {
    const interviews = Object.keys(selectedAgentsMap.value)
      .filter(k => selectedAgentsMap.value[k])
      .map(k => ({
        agent_id: Number(k),
        prompt: surveyQuestion.value.trim()
      }))

    let useOffline = false
    try {
      const envRes = await getEnvStatus({ simulation_id: props.simulationId })
      useOffline = !envRes?.data?.env_alive
    } catch {
      useOffline = true
    }

    if (useOffline) {
      addLog('[离线模式] 模拟环境未运行，使用本地数据批量模拟问卷回复')
      const surveyResultsList = []

      for (const interview of interviews) {
        const agentIdx = interview.agent_id
        const agent = profiles.value[agentIdx]
        let responseContent = '无响应'

        try {
          const offlineRes = await interviewAgentOffline({
            simulation_id: props.simulationId,
            agent_id: agentIdx,
            prompt: interview.prompt,
            chat_history: []
          })
          responseContent = extractAgentResponseContent(offlineRes, agentIdx) || '无响应'
        } catch (err) {
          responseContent = `请求失败：${err.message}`
        }

        surveyResultsList.push({
          agent_id: agentIdx,
          agent_name: agent?.username || `Agent ${agentIdx}`,
          profession: agent?.profession,
          question: surveyQuestion.value.trim(),
          answer: responseContent
        })
      }

      surveyResults.value = surveyResultsList
      persistToStorage()
      addLog(`收到 ${surveyResults.value.length} 条回复（离线模式）`)
      return
    }
    
    const res = await interviewAgents({
      simulation_id: props.simulationId,
      interviews: interviews
    })
    
    if (res.success && res.data) {
      // 正确的数据路径: res.data.result.results 是一个对象字典
      // 格式: {"twitter_0": {...}, "reddit_0": {...}, "twitter_1": {...}, ...}
      const resultData = res.data.result || res.data
      const resultsDict = resultData.results || resultData
      
      // 将对象字典转换为数组格式
      const surveyResultsList = []
      
      for (const interview of interviews) {
        const agentIdx = interview.agent_id
        const agent = profiles.value[agentIdx]
        
        // 优先使用 reddit 平台回复，其次 twitter
        let responseContent = '无响应'
        
        if (typeof resultsDict === 'object' && !Array.isArray(resultsDict)) {
          const redditKey = `reddit_${agentIdx}`
          const twitterKey = `twitter_${agentIdx}`
          const agentResult = resultsDict[redditKey] || resultsDict[twitterKey]
          if (agentResult) {
            responseContent = agentResult.response || agentResult.answer || '无响应'
          }
        } else if (Array.isArray(resultsDict)) {
          // 兼容数组格式
          const matchedResult = resultsDict.find(r => r.agent_id === agentIdx)
          if (matchedResult) {
            responseContent = matchedResult.response || matchedResult.answer || '无响应'
          }
        }
        
        surveyResultsList.push({
          agent_id: agentIdx,
          agent_name: agent?.username || `Agent ${agentIdx}`,
          profession: agent?.profession,
          question: surveyQuestion.value.trim(),
          answer: responseContent
        })
      }
      
      surveyResults.value = surveyResultsList
      persistToStorage()
      addLog(`收到 ${surveyResults.value.length} 条回复`)
    } else {
      throw new Error(res.error || '请求失败')
    }
  } catch (err) {
    addLog(`问卷发送失败: ${err.message}`)
  } finally {
    isSurveying.value = false
  }
}

// Load Report Data
const loadReportData = async () => {
  if (!props.reportId) return
  
  try {
    addLog(`加载报告数据: ${props.reportId}`)
    
    // Get report info
    const reportRes = await getReport(props.reportId)
    if (reportRes.success && reportRes.data) {
      // Load agent logs to get report outline and sections
      await loadAgentLogs()
    }
  } catch (err) {
    addLog(`加载报告失败: ${err.message}`)
  }
}

const loadAgentLogs = async () => {
  if (!props.reportId) return
  
  try {
    const res = await getAgentLog(props.reportId, 0)
    if (res.success && res.data) {
      const logs = res.data.logs || []
      
      logs.forEach(log => {
        if (log.action === 'planning_complete' && log.details?.outline) {
          reportOutline.value = log.details.outline
        }
        
        if (log.action === 'section_complete' && log.section_index < 100 && log.details?.content) {
          generatedSections.value[log.section_index] = log.details.content
        }
      })
      
      addLog('报告数据加载完成')
    }
  } catch (err) {
    addLog(`加载报告日志失败: ${err.message}`)
  }
}

const loadProfiles = async () => {
  if (!props.simulationId) return
  
  try {
    const res = await getSimulationProfilesRealtime(props.simulationId, 'reddit')
    if (res.success && res.data) {
      profiles.value = res.data.profiles || []
      addLog(`加载了 ${profiles.value.length} 个模拟个体`)
    }
  } catch (err) {
    addLog(`加载模拟个体失败: ${err.message}`)
  }
}

// Click outside to close dropdown
const handleClickOutside = (e) => {
  const dropdown = document.querySelector('.agent-dropdown')
  if (dropdown && !dropdown.contains(e.target)) {
    showAgentDropdown.value = false
  }
}

// Lifecycle
onMounted(() => {
  addLog('Step5 智能追问研判初始化')
  restoreFromStorage()
  loadReportData()
  loadProfiles()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  saveChatHistory()
  document.removeEventListener('click', handleClickOutside)
})

watch(() => props.reportId, (newId) => {
  if (newId) {
    loadReportData()
  }
}, { immediate: true })

watch(() => props.simulationId, (newId) => {
  if (newId) {
    loadProfiles()
  }
}, { immediate: true })
</script>

<style scoped>
.interaction-panel {
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 10% 0%, rgba(37, 99, 235, 0.08), transparent 30%),
    linear-gradient(135deg, #F5F8FC 0%, #ECF4F8 100%);
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  overflow: hidden;
}

/* Utility Classes */
.mono {
  font-family: 'JetBrains Mono', 'SF Mono', 'Monaco', 'Consolas', monospace;
}

/* Main Split Layout */
.main-split-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
  gap: 12px;
  padding: 12px;
}

/* Left Panel - Report Style (与 Step4Report.vue 完全一致) */
.left-panel.report-style {
  width: 38%;
  min-width: 420px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 252, 255, 0.98));
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 34px 46px 56px 46px;
}

.left-panel::-webkit-scrollbar {
  width: 6px;
}

.left-panel::-webkit-scrollbar-track {
  background: transparent;
}

.left-panel::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 3px;
  transition: background 0.3s ease;
}

.left-panel:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.left-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

/* Report Header */
.report-content-wrapper {
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
}

.report-header-block {
  position: relative;
  margin-bottom: 28px;
  padding: 0 0 8px;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.report-tag {
  background: linear-gradient(135deg, #0F766E, #2563EB);
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 700;
  padding: 6px 10px;
  border-radius: 999px;
  letter-spacing: 0.05em;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.16);
}

.report-id {
  font-size: 11px;
  color: #9CA3AF;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.main-title {
  font-family: 'Inter', 'Noto Serif SC', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 34px;
  font-weight: 700;
  color: #0F172A;
  line-height: 1.2;
  margin: 0 0 16px 0;
  letter-spacing: -0.03em;
}

.sub-title {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 14px;
  color: #64748B;
  line-height: 1.75;
  margin: 0 0 24px 0;
  font-weight: 400;
}

.header-divider {
  height: 3px;
  background: linear-gradient(90deg, #2563EB, rgba(20, 184, 166, 0.45), transparent);
  border-radius: 999px;
  width: 100%;
}

/* Sections List */
.sections-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.report-section-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 18px 20px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.04);
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  transition: background-color 0.2s ease;
  padding: 0;
  margin: 0;
  border-radius: 14px;
}

.section-header-row.clickable {
  cursor: pointer;
}

.section-header-row.clickable:hover {
  background-color: #F9FAFB;
}

.collapse-icon {
  margin-left: auto;
  color: #9CA3AF;
  transition: transform 0.3s ease;
  flex-shrink: 0;
  align-self: center;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.section-number {
  font-family: 'JetBrains Mono', monospace;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  font-size: 13px;
  color: #2563EB;
  background: rgba(37, 99, 235, 0.08);
  font-weight: 800;
  transition: color 0.3s ease;
}

.section-title {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 19px;
  font-weight: 800;
  color: #0F172A;
  margin: 0;
  transition: color 0.3s ease;
}

/* States */
.report-section-item.is-pending .section-number {
  color: #E5E7EB;
}
.report-section-item.is-pending .section-title {
  color: #D1D5DB;
}

.report-section-item.is-active .section-number,
.report-section-item.is-completed .section-number {
  color: #2563EB;
}

.report-section-item.is-active .section-title,
.report-section-item.is-completed .section-title {
  color: #111827;
}

.section-body {
  padding-left: 46px;
  overflow: hidden;
}

/* Generated Content */
.generated-content {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.85;
  color: #334155;
}

.generated-content :deep(p) {
  margin-bottom: 1em;
}

.generated-content :deep(.md-h2),
.generated-content :deep(.md-h3),
.generated-content :deep(.md-h4) {
  font-family: 'Times New Roman', Times, serif;
  color: #111827;
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  font-weight: 700;
}

.generated-content :deep(.md-h2) { font-size: 20px; border-bottom: 1px solid #F3F4F6; padding-bottom: 8px; }
.generated-content :deep(.md-h3) { font-size: 18px; }
.generated-content :deep(.md-h4) { font-size: 16px; }

.generated-content :deep(.md-ul),
.generated-content :deep(.md-ol) {
  padding-left: 20px;
  margin-bottom: 1em;
}

.generated-content :deep(.md-li) {
  margin-bottom: 0.5em;
}

.generated-content :deep(.md-quote) {
  border-left: 3px solid #E5E7EB;
  padding-left: 16px;
  margin: 1.5em 0;
  color: #6B7280;
  font-style: italic;
  font-family: 'Times New Roman', Times, serif;
}

.generated-content :deep(.code-block) {
  background: #F9FAFB;
  padding: 12px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  overflow-x: auto;
  margin: 1em 0;
  border: 1px solid #E5E7EB;
}

.generated-content :deep(strong) {
  font-weight: 600;
  color: #111827;
}

/* Loading State */
.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6B7280;
  font-size: 14px;
  margin-top: 4px;
}

.loading-icon {
  width: 18px;
  height: 18px;
  animation: spin 1s linear infinite;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-text {
  font-family: 'Times New Roman', Times, serif;
  font-size: 15px;
  color: #4B5563;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Content Styles Override */
.generated-content :deep(.md-h2) {
  font-family: 'Times New Roman', Times, serif;
  font-size: 18px;
  margin-top: 0;
}

/* Waiting Placeholder */
.waiting-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 40px;
  color: #9CA3AF;
}

.waiting-animation {
  position: relative;
  width: 48px;
  height: 48px;
}

.waiting-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid #E5E7EB;
  border-radius: 50%;
  animation: ripple 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.waiting-ring:nth-child(2) {
  animation-delay: 0.4s;
}

.waiting-ring:nth-child(3) {
  animation-delay: 0.8s;
}

@keyframes ripple {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.waiting-text {
  font-size: 14px;
}

/* Right Panel - Interaction */
.right-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.96));
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

/* Action Bar - Professional Design */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.85), rgba(240, 253, 250, 0.62));
  gap: 16px;
}

.action-bar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 160px;
}

.action-bar-icon {
  color: #2563EB;
  flex-shrink: 0;
}

.action-bar-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-bar-title {
  font-size: 15px;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.01em;
}

.action-bar-subtitle {
  font-size: 11px;
  color: #9CA3AF;
}

.action-bar-subtitle.mono {
  font-family: 'JetBrains Mono', 'SF Mono', monospace;
}

.action-bar-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  justify-content: flex-end;
}

.tab-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-pill:hover {
  background: #E5E7EB;
  color: #374151;
}

.tab-pill.active {
  background: linear-gradient(135deg, #0F172A, #2563EB);
  color: #FFFFFF;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
}

.tab-pill svg {
  flex-shrink: 0;
  opacity: 0.7;
}

.tab-pill.active svg {
  opacity: 1;
}

.tab-divider {
  width: 1px;
  height: 24px;
  background: #E5E7EB;
  margin: 0 6px;
}

.agent-pill {
  width: 200px;
  justify-content: space-between;
}

.agent-pill span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
}

.survey-pill {
  background: #ECFDF5;
  color: #047857;
}

.survey-pill:hover {
  background: #D1FAE5;
  color: #065F46;
}

.survey-pill.active {
  background: #047857;
  color: #FFFFFF;
  box-shadow: 0 2px 8px rgba(4, 120, 87, 0.2);
}

/* Interaction Header */
.interaction-header {
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
  background: #FAFAFA;
}

.tab-switcher {
  display: flex;
  gap: 8px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  background: transparent;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}

.tab-btn.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

.tab-btn svg {
  flex-shrink: 0;
}

/* Chat Container */
.chat-container {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  grid-template-areas:
    "side messages"
    "side input";
  gap: 14px;
  padding: 14px;
  overflow: hidden;
  background:
    radial-gradient(circle at 100% 0%, rgba(20, 184, 166, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.35), rgba(255, 255, 255, 0.86));
}

/* Report Agent Tools Card */
.report-agent-tools-card {
  grid-area: side;
  margin: 0;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 20px;
  background:
    radial-gradient(circle at 0% 0%, rgba(37, 99, 235, 0.08), transparent 34%),
    linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.tools-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.tools-card-avatar {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  background: linear-gradient(135deg, #0F172A 0%, #2563EB 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.2);
}

.tools-card-info {
  flex: 1;
  min-width: 0;
}

.tools-card-name {
  font-size: 15px;
  font-weight: 800;
  color: #0F172A;
  margin-bottom: 2px;
}

.tools-card-subtitle {
  font-size: 12px;
  color: #64748B;
  line-height: 1.45;
}

.tools-card-toggle {
  width: 28px;
  height: 28px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.tools-card-toggle:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}

.tools-card-toggle svg {
  transition: transform 0.3s ease;
}

.tools-card-toggle svg.is-expanded {
  transform: rotate(180deg);
}

.tools-card-body {
  padding: 0 14px 14px;
  overflow-y: auto;
}

.tools-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.tool-item {
  display: flex;
  gap: 10px;
  padding: 13px;
  background: #FFFFFF;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  transition: all 0.2s ease;
}

.tool-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.tool-icon-wrapper {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tool-purple .tool-icon-wrapper {
  background: rgba(139, 92, 246, 0.1);
  color: #8B5CF6;
}

.tool-blue .tool-icon-wrapper {
  background: rgba(59, 130, 246, 0.1);
  color: #3B82F6;
}

.tool-orange .tool-icon-wrapper {
  background: rgba(249, 115, 22, 0.1);
  color: #F97316;
}

.tool-green .tool-icon-wrapper {
  background: rgba(34, 197, 94, 0.1);
  color: #22C55E;
}

.tool-content {
  flex: 1;
  min-width: 0;
}

.tool-name {
  font-size: 12px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 4px;
}

.tool-desc {
  font-size: 11px;
  color: #6B7280;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Agent Profile Card */
.agent-profile-card {
  grid-area: side;
  min-height: 0;
  align-self: stretch;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 20px;
  background:
    radial-gradient(circle at 0% 0%, rgba(20, 184, 166, 0.1), transparent 32%),
    linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.profile-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
}

.profile-card-avatar {
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  background: linear-gradient(135deg, #1F2937 0%, #374151 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(31, 41, 55, 0.2);
}

.profile-card-info {
  flex: 1;
  min-width: 0;
}

.profile-card-name {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 2px;
}

.profile-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #6B7280;
}

.profile-card-handle {
  color: #9CA3AF;
}

.profile-card-profession {
  padding: 2px 8px;
  background: #E5E7EB;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.profile-card-toggle {
  width: 28px;
  height: 28px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.profile-card-toggle:hover {
  background: #F9FAFB;
  border-color: #D1D5DB;
}

.profile-card-toggle svg {
  transition: transform 0.3s ease;
}

.profile-card-toggle svg.is-expanded {
  transform: rotate(180deg);
}

.profile-card-body {
  padding: 0 20px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-card-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}

.profile-card-bio {
  background: #FFFFFF;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid #E5E7EB;
}

.profile-card-bio p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4B5563;
}

/* Target Selector */
.target-selector {
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
}

.selector-label {
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 10px;
}

.selector-options {
  display: flex;
  gap: 12px;
}

.target-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.target-option:hover {
  border-color: #D1D5DB;
}

.target-option.active {
  background: #1F2937;
  color: #FFFFFF;
  border-color: #1F2937;
}

/* Agent Dropdown */
.agent-dropdown {
  position: relative;
}

.dropdown-arrow {
  margin-left: 4px;
  transition: transform 0.2s ease;
  opacity: 0.6;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 240px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
  max-height: 320px;
  overflow-y: auto;
  z-index: 100;
}

.dropdown-header {
  padding: 12px 16px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #F3F4F6;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  border-left: 3px solid transparent;
}

.dropdown-item:hover {
  background: #F9FAFB;
  border-left-color: #1F2937;
}

.dropdown-item:first-of-type {
  margin-top: 4px;
}

.dropdown-item:last-child {
  margin-bottom: 4px;
}

.agent-avatar {
  width: 32px;
  height: 32px;
  min-width: 32px;
  min-height: 32px;
  background: linear-gradient(135deg, #1F2937 0%, #374151 100%);
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(31, 41, 55, 0.1);
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #1F2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-role {
  font-size: 11px;
  color: #9CA3AF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Chat Messages */
.chat-messages {
  grid-area: messages;
  flex: 1;
  overflow-y: auto;
  padding: 26px 30px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #94A3B8;
}

.empty-icon {
  opacity: 0.3;
}

.empty-text {
  font-size: 14px;
  text-align: center;
  max-width: 280px;
  line-height: 1.6;
}

.chat-message {
  display: flex;
  gap: 12px;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #1F2937;
  color: #FFFFFF;
}

.chat-message.assistant .message-avatar {
  background: #F3F4F6;
  color: #374151;
}

.message-content {
  max-width: 82%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-message.user .message-content {
  align-items: flex-end;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-message.user .message-header {
  flex-direction: row-reverse;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

.message-time {
  font-size: 11px;
  color: #9CA3AF;
}

.message-text {
  padding: 12px 15px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.65;
}

.chat-message.user .message-text {
  background: linear-gradient(135deg, #0F172A, #1E40AF);
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .message-text {
  background: #FFFFFF;
  color: #334155;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
  border-bottom-left-radius: 4px;
}

.message-text :deep(.md-p) {
  margin: 0;
}

.message-text :deep(.md-p:last-child) {
  margin-bottom: 0;
}

/* 修复有序列表编号 - 使用 CSS 计数器让多个 ol 连续编号 */
.message-text {
  counter-reset: list-counter;
}

.message-text :deep(.md-ol) {
  list-style: none;
  padding-left: 0;
  margin: 8px 0;
}

.message-text :deep(.md-oli) {
  counter-increment: list-counter;
  display: flex;
  gap: 8px;
  margin: 4px 0;
}

.message-text :deep(.md-oli)::before {
  content: counter(list-counter) ".";
  font-weight: 600;
  color: #374151;
  min-width: 20px;
  flex-shrink: 0;
}

/* 无序列表样式 */
.message-text :deep(.md-ul) {
  padding-left: 20px;
  margin: 8px 0;
}

.message-text :deep(.md-li) {
  margin: 4px 0;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
  background: #F3F4F6;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9CA3AF;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

/* Chat Input */
.chat-input-area {
  grid-area: input;
  padding: 0;
  border-top: none;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: transparent;
}

.chat-input {
  flex: 1;
  padding: 13px 16px;
  font-size: 14px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 16px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.2s ease;
}

.chat-input:focus {
  outline: none;
  border-color: #2563EB;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.chat-input:disabled {
  background: #F9FAFB;
  cursor: not-allowed;
}

.send-btn {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #0F172A, #2563EB);
  color: #FFFFFF;
  border: none;
  border-radius: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.2);
}

.send-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

/* Survey Container */
.survey-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Resizable survey panels */
.survey-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.survey-panel-results {
  flex-shrink: 1;
}

.panel-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  overflow-y: auto;
  min-height: 0;
}

/* Resize divider */
.resize-divider {
  flex-shrink: 0;
  height: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: row-resize;
  background: #F3F4F6;
  transition: background 0.15s;
  position: relative;
  z-index: 2;
}

.resize-divider:hover,
.resize-divider:active {
  background: #E0E7EF;
}

.divider-line {
  width: 40px;
  height: 3px;
  border-radius: 2px;
  background: #C4CDD5;
  transition: background 0.15s, width 0.15s;
}

.resize-divider:hover .divider-line,
.resize-divider:active .divider-line {
  background: #6B7280;
  width: 56px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.setup-section .section-header .section-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.selection-count {
  font-size: 12px;
  color: #9CA3AF;
}

/* Agents Grid */
.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  flex: 1;
  overflow-y: auto;
  padding: 4px;
  align-content: start;
  min-height: 0;
}

.agent-checkbox {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.agent-checkbox:hover {
  border-color: #D1D5DB;
}

.agent-checkbox.checked {
  background: #F0FDF4;
  border-color: #10B981;
}

.agent-checkbox input {
  display: none;
}

.agent-checkbox {
  user-select: none;
  -webkit-user-select: none;
}

.checkbox-avatar {
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  background: #E5E7EB;
  color: #374151;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.agent-checkbox.checked .checkbox-avatar {
  background: #10B981;
  color: #FFFFFF;
}

.checkbox-info {
  flex: 1;
  min-width: 0;
}

.checkbox-name {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #1F2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.checkbox-role {
  display: block;
  font-size: 10px;
  color: #9CA3AF;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.checkbox-indicator {
  width: 20px;
  height: 20px;
  border: 2px solid #E5E7EB;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.agent-checkbox.checked .checkbox-indicator {
  background: #10B981;
  border-color: #10B981;
  color: #FFFFFF;
}

.checkbox-indicator svg {
  opacity: 0;
  transform: scale(0.5);
  transition: all 0.2s ease;
}

.agent-checkbox.checked .checkbox-indicator svg {
  opacity: 1;
  transform: scale(1);
}

.selection-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-link {
  font-size: 12px;
  color: #6B7280;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.action-link:hover {
  color: #1F2937;
  text-decoration: underline;
}

.action-divider {
  color: #E5E7EB;
}

/* Survey Input */
.survey-input {
  width: 100%;
  flex: 1;
  min-height: 48px;
  padding: 14px 16px;
  font-size: 14px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  resize: none;
  font-family: inherit;
  line-height: 1.5;
  transition: border-color 0.2s ease;
}

.survey-input:focus {
  outline: none;
  border-color: #1F2937;
}

.survey-submit-btn {
  width: 100%;
  padding: 14px 24px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #1F2937;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 20px;
}

.survey-submit-btn:hover:not(:disabled) {
  background: #374151;
}

.survey-submit-btn:disabled {
  background: #E5E7EB;
  color: #9CA3AF;
  cursor: not-allowed;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Survey Results */
.survey-results {
  flex: 1;
  overflow-y: auto;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.results-title {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
}

.results-count {
  font-size: 12px;
  color: #9CA3AF;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.result-avatar {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
  background: #1F2937;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
}

.result-role {
  font-size: 12px;
  color: #9CA3AF;
}

.result-question {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  background: #FFFFFF;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #6B7280;
}

.result-question svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.result-answer {
  font-size: 14px;
  line-height: 1.7;
  color: #374151;
}

/* Markdown Styles */
:deep(.md-p) {
  margin: 0 0 12px 0;
}

:deep(.md-h2) {
  font-size: 20px;
  font-weight: 700;
  color: #1F2937;
  margin: 24px 0 12px 0;
}

:deep(.md-h3) {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 20px 0 10px 0;
}

:deep(.md-h4) {
  font-size: 14px;
  font-weight: 600;
  color: #4B5563;
  margin: 16px 0 8px 0;
}

:deep(.md-h5) {
  font-size: 13px;
  font-weight: 600;
  color: #6B7280;
  margin: 12px 0 6px 0;
}

:deep(.md-ul), :deep(.md-ol) {
  margin: 12px 0;
  padding-left: 24px;
}

:deep(.md-li), :deep(.md-oli) {
  margin: 6px 0;
}

/* 聊天/问卷区域的引用样式 */
.chat-messages :deep(.md-quote),
.result-answer :deep(.md-quote) {
  margin: 12px 0;
  padding: 12px 16px;
  background: #F9FAFB;
  border-left: 3px solid #1F2937;
  color: #4B5563;
}

:deep(.code-block) {
  margin: 12px 0;
  padding: 12px 16px;
  background: #1F2937;
  border-radius: 6px;
  overflow-x: auto;
}

:deep(.code-block code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: #E5E7EB;
}

:deep(.inline-code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  background: #F3F4F6;
  padding: 2px 6px;
  border-radius: 4px;
  color: #1F2937;
}

:deep(.md-hr) {
  border: none;
  border-top: 1px solid #E5E7EB;
  margin: 24px 0;
}

.interaction-panel {
  position: relative;
  background:
    radial-gradient(circle at 8% 10%, rgba(22, 93, 255, 0.12), transparent 28%),
    radial-gradient(circle at 92% 8%, rgba(37, 99, 235, 0.07), transparent 26%),
    radial-gradient(circle at 78% 92%, rgba(100, 116, 139, 0.08), transparent 30%),
    linear-gradient(135deg, #F5F7FA 0%, #ECF4FF 48%, #F7FBFF 100%);
}

.interaction-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(22, 93, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(22, 93, 255, 0.045) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.95), rgba(0, 0, 0, 0.32));
  pointer-events: none;
  z-index: -2;
}

.interaction-panel::after {
  content: '';
  position: absolute;
  right: 38px;
  top: 34px;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background:
    radial-gradient(circle, rgba(22, 93, 255, 0.12) 0 2px, transparent 3px),
    radial-gradient(circle, rgba(100, 116, 139, 0.1) 0 1px, transparent 2px);
  background-size: 26px 26px, 18px 18px;
  filter: blur(0.2px);
  animation: particleDrift 9s ease-in-out infinite alternate;
  pointer-events: none;
  z-index: -1;
}

.main-split-layout {
  display: grid;
  grid-template-columns: minmax(380px, 30%) minmax(0, 1fr);
  gap: 24px;
  padding: 24px;
}

.left-panel.report-style {
  width: auto;
  min-width: 0;
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(22, 93, 255, 0.12);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05), 0 20px 48px rgba(22, 93, 255, 0.08);
  backdrop-filter: blur(22px) saturate(1.16);
}

.left-panel::-webkit-scrollbar {
  width: 8px;
}

.left-panel::-webkit-scrollbar-thumb {
  background: rgba(22, 93, 255, 0);
  border: 2px solid transparent;
  background-clip: content-box;
}

.left-panel:hover::-webkit-scrollbar-thumb {
  background: rgba(22, 93, 255, 0.28);
  background-clip: content-box;
}

.report-content-wrapper {
  max-width: none;
}

.report-header-block {
  margin-bottom: 24px;
  padding-bottom: 16px;
}

.report-meta {
  margin-bottom: 16px;
}

.report-tag {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.16);
}

.report-id {
  font-size: 12px;
  line-height: 18px;
  color: #86909C;
}

.main-title {
  font-size: 24px;
  line-height: 32px;
  font-weight: 600;
  color: #1D2129;
  letter-spacing: -0.02em;
}

.sub-title {
  font-size: 14px;
  line-height: 22px;
  font-weight: 400;
  color: #4E5969;
  margin-bottom: 20px;
}

.header-divider {
  height: 2px;
  background: linear-gradient(90deg, #2563EB, rgba(37, 99, 235, 0.22) 58%, transparent);
}

.sections-list {
  gap: 16px;
}

.report-section-item {
  position: relative;
  gap: 8px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(229, 230, 235, 0.86);
  background: rgba(255, 255, 255, 0.58);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease, background 0.24s ease;
  overflow: hidden;
}

.report-section-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 14px;
  bottom: 14px;
  width: 3px;
  border-radius: 999px;
  background: transparent;
  transition: background 0.24s ease, box-shadow 0.24s ease;
}

.report-section-item.is-active,
.report-section-item.is-completed {
  background: rgba(255, 255, 255, 0.76);
  border-color: rgba(22, 93, 255, 0.18);
}

.report-section-item.is-active::before {
  background: linear-gradient(180deg, #2563EB, #1D4ED8);
  box-shadow: 0 0 16px rgba(37, 99, 235, 0.22);
}

.section-header-row {
  gap: 10px;
}

.section-header-row.clickable:hover {
  background: rgba(22, 93, 255, 0.05);
}

.section-number {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  font-size: 12px;
  color: #2563EB;
  background: rgba(37, 99, 235, 0.08);
}

.section-title {
  font-size: 18px;
  line-height: 24px;
  font-weight: 500;
  color: #1D2129;
}

.collapse-icon {
  color: #86909C;
  transition: transform 0.24s ease, color 0.24s ease;
}

.section-header-row:hover .collapse-icon {
  color: #2563EB;
}

.section-body {
  padding-left: 40px;
}

.section-slide-enter-active,
.section-slide-leave-active {
  transition: max-height 0.28s ease, opacity 0.24s ease, transform 0.24s ease;
  max-height: 960px;
}

.section-slide-enter-from,
.section-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
  max-height: 0;
}

.generated-content {
  font-size: 14px;
  line-height: 22px;
  font-weight: 400;
  color: #4E5969;
}

.generated-content :deep(.md-h2) {
  font-size: 18px;
  line-height: 24px;
  font-weight: 600;
  color: #1D2129;
}

.generated-content :deep(.md-h3),
.generated-content :deep(.md-h4) {
  font-family: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
  color: #1D2129;
}

.right-panel {
  border-radius: 24px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05), 0 22px 56px rgba(22, 93, 255, 0.08);
  backdrop-filter: blur(24px) saturate(1.18);
}

.action-bar {
  padding: 16px 20px;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(15, 23, 42, 0.03)),
    rgba(255, 255, 255, 0.52);
  border-bottom: 1px solid rgba(37, 99, 235, 0.1);
}

.action-bar-icon {
  color: #2563EB;
  filter: drop-shadow(0 8px 16px rgba(37, 99, 235, 0.14));
}

.action-bar-title {
  font-size: 18px;
  line-height: 24px;
  font-weight: 700;
  color: #1D2129;
}

.action-bar-subtitle {
  font-size: 12px;
  line-height: 18px;
  color: #86909C;
}

.action-bar-tabs {
  gap: 8px;
}

.tab-pill {
  min-height: 36px;
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: rgba(255, 255, 255, 0.7);
  color: #4E5969;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.tab-pill:hover {
  background: rgba(37, 99, 235, 0.06);
  color: #2563EB;
  border-color: rgba(37, 99, 235, 0.24);
  transform: translateY(-1px);
}

.tab-pill:active {
  transform: translateY(0) scale(0.98);
}

.tab-pill.active {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
}

.survey-pill {
  color: #0F766E;
  background: rgba(20, 184, 166, 0.08);
  border-color: rgba(20, 184, 166, 0.18);
}

.survey-pill.active {
  background: linear-gradient(135deg, #0F766E, #0D9488);
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.2);
}

.chat-container {
  grid-template-columns: minmax(288px, 340px) minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 16px;
  padding: 16px;
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.06), transparent 30%),
    linear-gradient(180deg, rgba(245, 247, 250, 0.6), rgba(255, 255, 255, 0.72));
}

.report-agent-tools-card,
.agent-profile-card {
  border-radius: 22px;
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(18px);
}

.tools-card-header,
.profile-card-header {
  padding: 16px;
}

.tools-card-avatar,
.profile-card-avatar,
.agent-avatar,
.message-avatar,
.result-avatar {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);
}

.tools-card-name,
.profile-card-name {
  font-size: 14px;
  line-height: 20px;
  font-weight: 700;
  color: #1D2129;
}

.tools-card-subtitle {
  font-size: 12px;
  line-height: 18px;
  color: #86909C;
}

.tools-card-toggle,
.profile-card-toggle {
  border-radius: 10px;
  border-color: rgba(22, 93, 255, 0.12);
  color: #4E5969;
}

.tools-card-toggle:hover,
.profile-card-toggle:hover {
  color: #2563EB;
  border-color: rgba(37, 99, 235, 0.24);
  background: rgba(37, 99, 235, 0.06);
}

.tools-card-body {
  padding: 0 14px 14px;
}

.tools-grid {
  gap: 12px;
}

.tool-item {
  position: relative;
  padding: 13px;
  border-radius: 16px;
  border: 1px solid transparent;
  background:
    linear-gradient(rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.86)) padding-box,
    linear-gradient(135deg, rgba(37, 99, 235, 0.22), rgba(148, 163, 184, 0.2)) border-box;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.tool-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.1), 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.tool-active {
  background:
    linear-gradient(rgba(37, 99, 235, 0.1), rgba(255, 255, 255, 0.94)) padding-box,
    linear-gradient(135deg, #2563EB, rgba(37, 99, 235, 0.28)) border-box;
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.08), 0 12px 28px rgba(37, 99, 235, 0.1);
}

.tool-icon-wrapper {
  width: 34px;
  height: 34px;
  min-width: 34px;
  border-radius: 12px;
}

.tool-agent .tool-icon-wrapper {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.tool-purple .tool-icon-wrapper {
  background: rgba(99, 102, 241, 0.1);
  color: #4F46E5;
}

.tool-blue .tool-icon-wrapper {
  background: rgba(37, 99, 235, 0.1);
  color: #2563EB;
}

.tool-orange .tool-icon-wrapper {
  background: rgba(255, 125, 0, 0.12);
  color: #FF7D00;
}

.tool-green .tool-icon-wrapper {
  background: rgba(20, 184, 166, 0.1);
  color: #0F766E;
}

.tool-name {
  font-size: 12px;
  line-height: 18px;
  font-weight: 700;
  color: #1D2129;
}

.tool-desc {
  font-size: 12px;
  line-height: 18px;
  color: #86909C;
  -webkit-line-clamp: 3;
}

.chat-messages {
  border-radius: 22px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background:
    radial-gradient(circle at 50% 0%, rgba(22, 93, 255, 0.05), transparent 34%),
    rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78), 0 2px 8px rgba(0, 0, 0, 0.04);
}

.chat-message {
  animation: messageIn 0.28s ease both;
}

.chat-message.user .message-avatar {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
}

.chat-message.assistant .message-avatar {
  background: linear-gradient(135deg, #334155, #2563EB);
  color: #FFFFFF;
}

.message-text {
  font-size: 14px;
  line-height: 22px;
  border-radius: 18px;
}

.chat-message.user .message-text {
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.16);
}

.chat-message.assistant .message-text {
  border-color: rgba(22, 93, 255, 0.1);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 10px 24px rgba(29, 33, 41, 0.06);
}

.chat-empty {
  color: #86909C;
}

.empty-icon {
  opacity: 0.34;
  color: #2563EB;
}

.empty-text {
  font-size: 14px;
  line-height: 22px;
}

.typing-indicator {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(22, 93, 255, 0.1);
  box-shadow: 0 8px 18px rgba(29, 33, 41, 0.05);
}

.typing-indicator span {
  background: #2563EB;
}

.chat-input-area {
  position: relative;
}

.chat-input {
  min-height: 48px;
  padding: 14px 16px;
  font-size: 14px;
  line-height: 22px;
  border: 1px solid transparent;
  border-radius: 18px;
  background:
    linear-gradient(#FFFFFF, #FFFFFF) padding-box,
    linear-gradient(135deg, rgba(37, 99, 235, 0.22), rgba(148, 163, 184, 0.16)) border-box;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #1D2129;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.chat-input:focus {
  border-color: transparent;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1), 0 12px 30px rgba(37, 99, 235, 0.1);
}

.send-btn {
  width: 48px;
  height: 48px;
  border-radius: 18px;
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.22);
  animation: sendPulse 2.4s ease-in-out infinite;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.26);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.96);
}

.send-btn:disabled {
  animation: none;
  background: #E5E6EB;
  box-shadow: none;
}

.dropdown-menu {
  border: 1px solid rgba(22, 93, 255, 0.12);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(18px);
}

.dropdown-item:hover {
  background: rgba(22, 93, 255, 0.06);
  border-left-color: #2563EB;
}

.survey-container {
  padding: 16px;
  gap: 12px;
  background: linear-gradient(180deg, rgba(245, 247, 250, 0.62), rgba(255, 255, 255, 0.74));
}

.survey-panel {
  border-radius: 18px;
  border: 1px solid rgba(22, 93, 255, 0.1);
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.resize-divider {
  height: 8px;
  border-radius: 999px;
  background: transparent;
}

.divider-line {
  background: rgba(22, 93, 255, 0.18);
}

.agent-checkbox,
.result-card {
  border-radius: 14px;
  border-color: rgba(22, 93, 255, 0.1);
  background: rgba(255, 255, 255, 0.82);
}

.agent-checkbox:hover {
  border-color: rgba(22, 93, 255, 0.24);
  transform: translateY(-1px);
}

.agent-checkbox.checked {
  background: rgba(20, 184, 166, 0.08);
  border-color: rgba(20, 184, 166, 0.3);
}

.survey-input {
  border-radius: 16px;
  border-color: rgba(22, 93, 255, 0.12);
}

.survey-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.survey-submit-btn {
  border-radius: 16px;
  background: linear-gradient(135deg, #2563EB, #1D4ED8);
}

.survey-submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #1D4ED8, #1E40AF);
  transform: translateY(-1px);
}

@keyframes particleDrift {
  from {
    transform: translate3d(0, 0, 0) rotate(0deg);
    opacity: 0.58;
  }
  to {
    transform: translate3d(-18px, 16px, 0) rotate(10deg);
    opacity: 0.9;
  }
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes sendPulse {
  0%, 100% {
    box-shadow: 0 12px 28px rgba(22, 93, 255, 0.24);
  }
  50% {
    box-shadow: 0 12px 28px rgba(22, 93, 255, 0.26), 0 0 0 7px rgba(22, 93, 255, 0.08);
  }
}

@media (max-width: 1280px) {
  .main-split-layout {
    grid-template-columns: minmax(340px, 34%) minmax(0, 1fr);
    gap: 16px;
    padding: 16px;
  }

  .chat-container {
    grid-template-columns: minmax(248px, 300px) minmax(0, 1fr);
  }
}

</style>
