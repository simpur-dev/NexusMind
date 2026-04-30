<template>
  <div class="workbench-panel">
    <div class="scroll-container">
      <!-- Step 01: Ontology -->
      <div class="step-card" :class="{ 'active': currentPhase === 0, 'completed': currentPhase > 0 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">01</span>
            <span class="step-title">事件要素建模</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 0" class="badge success">已完成</span>
            <span v-else-if="currentPhase === 0" class="badge processing">生成中</span>
            <span v-else class="badge pending">等待</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/graph/ontology/generate</p>
          <p class="description">
            解析种子材料与推演目标，抽取角色、机构、议题与行动关系，生成面向舆情推演的事件本体。
          </p>

          <!-- Loading / Progress -->
          <div v-if="currentPhase === 0 && ontologyProgress" class="progress-section">
            <div class="spinner-sm"></div>
            <span>{{ ontologyProgress.message || '正在分析文档...' }}</span>
          </div>

          <!-- Detail Overlay -->
          <div v-if="selectedOntologyItem" class="ontology-detail-overlay">
            <div class="detail-header">
               <div class="detail-title-group">
                  <span class="detail-type-badge">{{ selectedOntologyItem.itemType === 'entity' ? 'ENTITY' : 'RELATION' }}</span>
                  <span class="detail-name">{{ selectedOntologyItem.name }}</span>
               </div>
               <button class="close-btn" @click="selectedOntologyItem = null">×</button>
            </div>
            <div class="detail-body">
               <div class="detail-desc">{{ selectedOntologyItem.description }}</div>
               
               <!-- Attributes -->
               <div class="detail-section" v-if="selectedOntologyItem.attributes?.length">
                  <span class="section-label">ATTRIBUTES</span>
                  <div class="attr-list">
                     <div v-for="attr in selectedOntologyItem.attributes" :key="attr.name" class="attr-item">
                        <span class="attr-name">{{ attr.name }}</span>
                        <span class="attr-type">({{ attr.type }})</span>
                        <span class="attr-desc">{{ attr.description }}</span>
                     </div>
                  </div>
               </div>

               <!-- Examples (Entity) -->
               <div class="detail-section" v-if="selectedOntologyItem.examples?.length">
                  <span class="section-label">EXAMPLES</span>
                  <div class="example-list">
                     <span v-for="ex in selectedOntologyItem.examples" :key="ex" class="example-tag">{{ ex }}</span>
                  </div>
               </div>

               <!-- Source/Target (Relation) -->
               <div class="detail-section" v-if="selectedOntologyItem.source_targets?.length">
                  <span class="section-label">CONNECTIONS</span>
                  <div class="conn-list">
                     <div v-for="(conn, idx) in selectedOntologyItem.source_targets" :key="idx" class="conn-item">
                        <span class="conn-node">{{ conn.source }}</span>
                        <span class="conn-arrow">→</span>
                        <span class="conn-node">{{ conn.target }}</span>
                     </div>
                  </div>
               </div>
            </div>
          </div>

          <!-- Generated Entity Tags -->
          <div v-if="projectData?.ontology?.entity_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">识别的关键对象</span>
            <div class="tags-list">
              <span 
                v-for="entity in projectData.ontology.entity_types" 
                :key="entity.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(entity, 'entity')"
              >
                {{ translateEntityType(entity.name) }}
              </span>
            </div>
          </div>

          <!-- Generated Relation Tags -->
          <div v-if="projectData?.ontology?.edge_types" class="tags-container" :class="{ 'dimmed': selectedOntologyItem }">
            <span class="tag-label">识别的行动关系</span>
            <div class="tags-list">
              <span 
                v-for="rel in projectData.ontology.edge_types" 
                :key="rel.name" 
                class="entity-tag clickable"
                @click="selectOntologyItem(rel, 'relation')"
              >
                {{ translateRelationType(rel.name) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 02: Graph Build -->
      <div class="step-card" :class="{ 'active': currentPhase === 1, 'completed': currentPhase > 1 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">02</span>
            <span class="step-title">事件记忆图谱构建</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase > 1" class="badge success">已完成</span>
            <span v-else-if="currentPhase === 1" class="badge processing">{{ buildProgress?.progress || 0 }}%</span>
            <span v-else class="badge pending">等待</span>
          </div>
        </div>

        <div class="card-content">
          <p class="api-note">POST /api/graph/build</p>
          <p class="description">
            将材料切分并写入 Graphiti + Neo4j，沉淀对象关系、时序记忆与社区摘要，为后续推演提供可追溯依据。
          </p>
          
          <!-- Stats Cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.nodes }}</span>
              <span class="stat-label">对象节点</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.edges }}</span>
              <span class="stat-label">关系链路</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ graphStats.types }}</span>
              <span class="stat-label">要素类型</span>
            </div>
          </div>
          <!-- 数据为空时显示重建按钮 -->
          <button
            v-if="currentPhase >= 1 && graphStats.nodes === 0 && !rebuildingGraph"
            class="action-btn rebuild-btn"
            @click="$emit('rebuild-graph')"
          >
            ↻ 重新构建记忆图谱
          </button>
          <div v-if="rebuildingGraph" class="rebuild-hint">
            <span class="spinner-sm"></span>
            <span>正在重新构建记忆图谱...</span>
          </div>
        </div>
      </div>

      <!-- Step 03: Complete -->
      <div class="step-card" :class="{ 'active': currentPhase === 2, 'completed': currentPhase >= 2 }">
        <div class="card-header">
          <div class="step-info">
            <span class="step-num">03</span>
            <span class="step-title">推演底座就绪</span>
          </div>
          <div class="step-status">
            <span v-if="currentPhase >= 2" class="badge accent">进行中</span>
          </div>
        </div>
        
        <div class="card-content">
          <p class="api-note">POST /api/simulation/create</p>
          <p class="description">事件记忆图谱已完成，可进入群体环境建模，生成面向舆情演化的智能体场域。</p>
          <button 
            class="action-btn" 
            :disabled="currentPhase < 2 || creatingSimulation"
            @click="handleEnterEnvSetup"
          >
            <span v-if="creatingSimulation" class="spinner-sm"></span>
            {{ creatingSimulation ? '创建中...' : '进入群体环境建模 ➝' }}
          </button>
          <button 
            class="action-btn action-btn-workspace" 
            :disabled="currentPhase < 2"
            @click="goToWorkspace"
          >
            ⌁ 进入事件工作台
          </button>
        </div>
      </div>
    </div>

    <!-- Floating System Terminal (已隐藏) -->
    <div v-if="false" class="system-terminal" :class="{ 'is-live': hasActiveTerminalLine }">
      <div class="terminal-progress-bar"></div>
      <div class="terminal-header">
        <div class="terminal-controls" aria-hidden="true">
          <span class="control-dot dot-deep"></span>
          <span class="control-dot dot-mid"></span>
          <span class="control-dot dot-soft"></span>
        </div>
        <span class="terminal-label">SYSTEM TERMINAL</span>
      </div>
      <div class="terminal-meta">
        <span class="terminal-project">{{ projectData?.project_id || 'NO_PROJECT' }}</span>
        <span class="terminal-phase">{{ terminalPhaseLabel }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div
          class="log-line"
          v-for="(log, idx) in terminalLogs"
          :key="`${log.time}-${idx}`"
          :class="{
            current: log.isCurrent,
            success: log.visualStatus === 'success',
            error: log.visualStatus === 'error',
            running: log.visualStatus === 'running'
          }"
        >
          <span class="log-status" :class="log.visualStatus" aria-hidden="true">
            <svg v-if="log.visualStatus === 'success'" viewBox="0 0 16 16" class="status-icon">
              <path d="M3.5 8.5 6.5 11.5 12.5 4.5" />
            </svg>
            <svg v-else-if="log.visualStatus === 'error'" viewBox="0 0 16 16" class="status-icon">
              <path d="M4.5 4.5 11.5 11.5M11.5 4.5 4.5 11.5" />
            </svg>
            <svg v-else viewBox="0 0 16 16" class="status-icon spinner-icon">
              <circle cx="8" cy="8" r="5.5" />
              <path d="M8 2.5A5.5 5.5 0 0 1 13.5 8" />
            </svg>
          </span>
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
          <span v-if="log.isCurrent" class="terminal-cursor">_</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSimulation } from '../api/simulation'

const router = useRouter()

const props = defineProps({
  currentPhase: { type: Number, default: 0 },
  projectData: Object,
  ontologyProgress: Object,
  buildProgress: Object,
  graphData: Object,
  systemLogs: { type: Array, default: () => [] },
  rebuildingGraph: { type: Boolean, default: false }
})

const emit = defineEmits(['next-step', 'simulation-created', 'rebuild-graph'])

const selectedOntologyItem = ref(null)
const logContent = ref(null)
const creatingSimulation = ref(false)
const currentLogIndex = computed(() => props.systemLogs.length - 1)

const isErrorMessage = (message = '') => /error|failed|exception|no pending/i.test(String(message))

const hasActiveTerminalLine = computed(() => {
  const latestLog = props.systemLogs[currentLogIndex.value]
  if (!latestLog) return false
  if (latestLog.status === 'error' || isErrorMessage(latestLog.msg)) return false
  return props.currentPhase >= 0 && props.currentPhase < 2
})

const terminalPhaseLabel = computed(() => {
  if (props.currentPhase >= 2) return 'READY'
  if (props.currentPhase === 1) return `GRAPH ${props.buildProgress?.progress || 0}%`
  if (props.currentPhase === 0) return 'ONTOLOGY'
  return 'BOOTING'
})

const resolveLogState = (log, idx) => {
  if (log?.status === 'error' || isErrorMessage(log?.msg)) return 'error'
  if (idx === currentLogIndex.value && hasActiveTerminalLine.value) return 'running'
  return 'success'
}

const terminalLogs = computed(() =>
  props.systemLogs.map((log, idx) => {
    const visualStatus = resolveLogState(log, idx)
    return {
      ...log,
      visualStatus,
      isCurrent: idx === currentLogIndex.value && visualStatus === 'running'
    }
  })
)

// 进入群体环境建模 - 创建 simulation 并通知父组件
const handleEnterEnvSetup = async () => {
  if (!props.projectData?.project_id || !props.projectData?.graph_id) {
    console.error('缺少项目或图谱信息')
    return
  }

  creatingSimulation.value = true

  try {
    const res = await createSimulation({
      project_id: props.projectData.project_id,
      graph_id: props.projectData.graph_id,
      enable_twitter: true,
      enable_reddit: true
    })

    if (res.success && res.data?.simulation_id) {
      // 通知父组件 simulation 已创建，由父组件统一处理导航
      emit('simulation-created', { simulationId: res.data.simulation_id })
    } else {
      console.error('创建模拟失败:', res.error)
      alert('创建模拟失败: ' + (res.error || '未知错误'))
    }
  } catch (err) {
    console.error('创建模拟异常:', err)
    alert('创建模拟异常: ' + err.message)
  } finally {
    creatingSimulation.value = false
  }
}

const entityTypeChinese = {
  'Student': '学生', 'GraduateStudent': '研究生', 'FacultyMember': '教职人员',
  'UniversityAdministrator': '校方管理者', 'AcademicAdvisor': '导师',
  'University': '学校', 'College': '学院', 'Court': '法院',
  'ExpertPanel': '专家委员会', 'Organization': '组织机构',
  'GovernmentAgency': '政府机构', 'RegulatoryAgency': '监管机构',
  'AcademicAssociation': '学术团体', 'Person': '人物',
  'Media': '媒体', 'MediaOutlet': '媒体机构', 'OnlineInfluencer': '网络大V',
  'Event': '事件', 'Policy': '政策', 'PublicFigure': '公众人物',
  'Platform': '平台', 'Company': '企业', 'Location': '地点',
  'Document': '文件', 'Entity': '实体',
}
const relationTypeChinese = {
  'SUBMITTED_COMPLAINT_AGAINST': '投诉',
  'SUPERVISES': '指导',
  'BELONGS_TO_COLLEGE': '所属学院',
  'AFFILIATED_WITH_UNIVERSITY': '所属学校',
  'REPORTS_ON': '报道',
  'INVESTIGATES': '调查',
  'ISSUES_GUIDANCE_TO': '发布指导',
  'AMPLIFIES_DISCUSSION_OF': '扩大讨论',
  'RELATED_TO': '相关',
  'WORKS_AT': '工作于',
  'STUDIES_AT': '就读于',
  'MANAGES': '管理',
  'SUPPORTS': '支持',
  'OPPOSES': '反对',
  'COMMENTS_ON': '评论',
  'PUBLISHES': '发布',
  'FOLLOWS': '关注',
  'MEMBER_OF': '成员',
  'PARTICIPATES_IN': '参与',
}
const translateEntityType = (name) => entityTypeChinese[name] || name
const translateRelationType = (name) => relationTypeChinese[name] || name.replace(/_/g, ' ')

const selectOntologyItem = (item, type) => {
  selectedOntologyItem.value = { ...item, itemType: type }
}

const goToWorkspace = () => {
  if (props.projectData?.project_id) {
    router.push({ name: 'IncidentWorkspace', params: { projectId: props.projectData.project_id } })
  }
}

const graphStats = computed(() => {
  const nodes = props.graphData?.node_count || props.graphData?.nodes?.length || 0
  const edges = props.graphData?.edge_count || props.graphData?.edges?.length || 0
  const types = props.projectData?.ontology?.entity_types?.length || 0
  return { nodes, edges, types }
})

const formatDate = (dateStr) => {
  if (!dateStr) return '--:--:--'
  const d = new Date(dateStr)
  return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + d.getMilliseconds()
}

// Auto-scroll logs
watch(() => props.systemLogs.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.workbench-panel {
  height: 100%;
  background:
    radial-gradient(circle at top right, rgba(96, 165, 250, 0.14), transparent 28%),
    radial-gradient(circle at bottom left, rgba(191, 219, 254, 0.4), transparent 34%),
    linear-gradient(180deg, #f8fbff 0%, #f3f7fc 100%);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  --accent: #3b82f6;
  --accent-strong: #2563eb;
  --accent-soft: rgba(59, 130, 246, 0.12);
  --panel-border: rgba(148, 163, 184, 0.22);
  --panel-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step-card {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(14px);
  border-radius: 18px;
  padding: 20px;
  box-shadow: var(--panel-shadow);
  border: 1px solid var(--panel-border);
  transition: all 0.3s ease;
  position: relative; /* For absolute overlay */
}

.step-card.active {
  border-color: rgba(59, 130, 246, 0.38);
  box-shadow: 0 18px 36px rgba(37, 99, 235, 0.12);
}

.step-card.completed {
  border-color: rgba(96, 165, 250, 0.26);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #cbd5e1;
}

.step-card.active .step-num,
.step-card.completed .step-num {
  color: var(--accent-strong);
}

.step-title {
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
  color: var(--text-primary);
}

.badge {
  font-size: 10px;
  padding: 5px 10px;
  border-radius: 999px;
  font-weight: 600;
  text-transform: uppercase;
  border: 1px solid transparent;
  transition: all 0.3s ease;
}

.badge.success {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
  border-color: rgba(34, 197, 94, 0.18);
}

.badge.processing,
.badge.accent {
  background: rgba(59, 130, 246, 0.12);
  color: var(--accent-strong);
  border-color: rgba(59, 130, 246, 0.2);
}

.badge.pending {
  background: rgba(255, 255, 255, 0.7);
  color: var(--text-muted);
  border-color: rgba(148, 163, 184, 0.2);
}

.api-note {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.description {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Step 01 Tags */
.tags-container {
  margin-top: 12px;
  transition: opacity 0.3s;
}

.tags-container.dimmed {
    opacity: 0.3;
    pointer-events: none;
}

.tag-label {
  display: block;
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 8px;
  font-weight: 600;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.entity-tag {
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  transition: all 0.3s ease;
}

.entity-tag.clickable {
    cursor: pointer;
}

.entity-tag.clickable:hover {
    background: rgba(219, 234, 254, 0.95);
    border-color: rgba(59, 130, 246, 0.26);
    color: var(--accent-strong);
    transform: translateY(-1px);
}

/* Ontology Detail Overlay */
.ontology-detail-overlay {
    position: absolute;
    top: 60px; /* Below header roughly */
    left: 20px;
    right: 20px;
    bottom: 20px;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(4px);
    z-index: 10;
    border: 1px solid #EAEAEA;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

.detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #EAEAEA;
    background: #FAFAFA;
}

.detail-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.detail-type-badge {
    font-size: 9px;
    font-weight: 700;
    color: #FFF;
    background: #000;
    padding: 2px 6px;
    border-radius: 2px;
    text-transform: uppercase;
}

.detail-name {
    font-size: 14px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

.close-btn {
    background: none;
    border: none;
    font-size: 18px;
    color: #999;
    cursor: pointer;
    line-height: 1;
}

.close-btn:hover {
    color: #333;
}

.detail-body {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.detail-desc {
    font-size: 12px;
    color: #444;
    line-height: 1.5;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px dashed #EAEAEA;
}

.detail-section {
    margin-bottom: 16px;
}

.section-label {
    display: block;
    font-size: 10px;
    font-weight: 600;
    color: #AAA;
    margin-bottom: 8px;
}

.attr-list, .conn-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.attr-item {
    font-size: 11px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: baseline;
    padding: 4px;
    background: #F9F9F9;
    border-radius: 4px;
}

.attr-name {
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: #000;
}

.attr-type {
    color: #999;
    font-size: 10px;
}

.attr-desc {
    color: #555;
    flex: 1;
    min-width: 150px;
}

.example-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.example-tag {
    font-size: 11px;
    background: #FFF;
    border: 1px solid #E0E0E0;
    padding: 3px 8px;
    border-radius: 12px;
    color: #555;
}

.conn-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    padding: 6px;
    background: #F5F5F5;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
}

.conn-node {
    font-weight: 600;
    color: #333;
}

.conn-arrow {
    color: #BBB;
}

/* Step 02 Stats */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  background: rgba(248, 250, 252, 0.9);
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.stat-card {
  text-align: center;
  padding: 12px 10px;
  background: rgba(255, 255, 255, 0.68);
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-strong);
  font-family: 'JetBrains Mono', monospace;
}

.stat-label {
  font-size: 9px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-top: 4px;
  display: block;
}

/* Step 03 Button */
.action-btn {
  width: 100%;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #eff6ff;
  border: 1px solid rgba(59, 130, 246, 0.24);
  padding: 14px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.2);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 18px 32px rgba(37, 99, 235, 0.24);
}

.action-btn:disabled {
  background: rgba(148, 163, 184, 0.48);
  border-color: rgba(148, 163, 184, 0.2);
  cursor: not-allowed;
  box-shadow: none;
}

.action-btn-workspace {
  margin-top: 8px;
  background: linear-gradient(135deg, rgba(99, 179, 237, 0.15) 0%, rgba(59, 130, 246, 0.1) 100%);
  color: #63b3ed;
  border: 1px solid rgba(99, 179, 237, 0.3);
  box-shadow: none;
}
.action-btn-workspace:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(99, 179, 237, 0.25) 0%, rgba(59, 130, 246, 0.18) 100%);
  box-shadow: 0 8px 20px rgba(99, 179, 237, 0.15);
}

.rebuild-btn {
  margin-top: 12px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(234, 88, 12, 0.1) 100%);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.3);
  box-shadow: none;
}
.rebuild-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.25) 0%, rgba(234, 88, 12, 0.18) 100%);
  box-shadow: 0 8px 20px rgba(245, 158, 11, 0.15);
}
.rebuild-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #d97706;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(254, 243, 199, 0.6);
  border: 1px solid rgba(245, 158, 11, 0.14);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--accent-strong);
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(219, 234, 254, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.14);
}

.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Floating System Terminal */
.system-terminal {
  position: absolute;
  right: 24px;
  bottom: 24px;
  width: min(460px, calc(100% - 48px));
  padding: 0 16px 16px;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-top: 1px solid rgba(59, 130, 246, 0.5);
  border-radius: 18px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.3);
  font-family: 'JetBrains Mono', monospace;
  z-index: 20;
  overflow: hidden;
  transition: all 0.3s ease;
}

.system-terminal.is-live {
  box-shadow:
    0 20px 50px rgba(15, 23, 42, 0.3),
    0 0 0 1px rgba(59, 130, 246, 0.08),
    0 0 28px rgba(59, 130, 246, 0.14);
}

.terminal-progress-bar {
  height: 2px;
  margin: 0 -16px 0;
  background: linear-gradient(90deg, transparent 0%, rgba(96, 165, 250, 0.18) 14%, rgba(59, 130, 246, 0.95) 50%, rgba(96, 165, 250, 0.18) 86%, transparent 100%);
  background-size: 180% 100%;
  animation: terminal-flow 2.2s linear infinite;
}

@keyframes terminal-flow {
  0% { background-position: 180% 0; }
  100% { background-position: -180% 0; }
}

.terminal-header {
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  margin-bottom: 10px;
}

.terminal-controls {
  display: flex;
  gap: 8px;
}

.control-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.dot-deep { background: #1e293b; }
.dot-mid { background: #334155; }
.dot-soft { background: #475569; }

.terminal-label {
  font-size: 10px;
  letter-spacing: 0.18em;
  color: rgba(226, 232, 240, 0.78);
}

.terminal-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  font-size: 10px;
}

.terminal-project {
  color: #93c5fd;
}

.terminal-phase {
  color: rgba(148, 163, 184, 0.86);
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 188px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar {
  width: 4px;
}

.log-content::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.65);
  border-radius: 2px;
}

.log-line {
  font-size: 11px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  line-height: 1.5;
  color: #94a3b8;
  transition: all 0.3s ease;
}

.log-time {
  color: #64748b;
  min-width: 78px;
}

.log-msg {
  color: #94a3b8;
  word-break: break-word;
  flex: 1;
}

.log-status {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.status-icon {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.log-status.success {
  color: #22c55e;
}

.log-status.error {
  color: #ef4444;
}

.log-status.running {
  color: #60a5fa;
}

.spinner-icon {
  animation: spin 1s linear infinite;
}

.log-line.current .log-time,
.log-line.current .log-msg {
  color: #60a5fa;
}

.log-line.error .log-time,
.log-line.error .log-msg {
  color: #fca5a5;
}

.terminal-cursor {
  color: #60a5fa;
  animation: terminal-caret 1s steps(1, end) infinite;
}

@keyframes terminal-caret {
  0%, 50% { opacity: 1; }
  50.01%, 100% { opacity: 0; }
}

@media (max-width: 768px) {
  .scroll-container {
    padding: 18px;
  }

  .system-terminal {
    right: 18px;
    bottom: 18px;
    width: calc(100% - 36px);
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .terminal-meta,
  .log-line {
    font-size: 10px;
  }

  .log-time {
    min-width: 68px;
  }
}

</style>
