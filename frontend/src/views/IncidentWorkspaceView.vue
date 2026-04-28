<template>
  <div class="incident-workspace">
    <!-- ========== 顶栏 ========== -->
    <header class="ws-header">
      <div class="ws-header-left">
        <button class="ws-back-btn" @click="goHome" title="返回首页">
          <span class="back-icon">&#8592;</span>
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
        <button class="ws-action-btn ws-secondary" @click="showExportReport = true">
          <span class="btn-icon">&#128202;</span> 导出报告
        </button>
        <button class="ws-action-btn ws-primary" @click="showAppendDialog = true">
          <span class="btn-icon">+</span> 追加材料
        </button>
      </div>
    </header>

    <!-- ========== 三栏主体 ========== -->
    <main class="ws-body">
      <!-- 左栏：材料 & 基线 -->
      <section class="ws-panel ws-panel-left">
        <!-- 项目概览卡片 -->
        <div class="overview-card">
          <div class="overview-header">
            <span class="overview-icon">&#128203;</span>
            <span class="overview-title">项目概览</span>
          </div>
          <div class="overview-name" v-if="projectName">{{ projectName }}</div>
          <div class="overview-stage" v-if="activeBaseline?.current_stage">
            <span class="stage-dot"></span>
            当前阶段：{{ activeBaseline.current_stage }}
          </div>
          <div class="overview-stats">
            <div class="stat-item">
              <span class="stat-icon">&#128193;</span>
              <span class="stat-num">{{ materials.length }}</span>
              <span class="stat-label">材料</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-icon">&#128200;</span>
              <span class="stat-num">{{ baselines.length }}</span>
              <span class="stat-label">基线</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-icon">&#128440;</span>
              <span class="stat-num">{{ forecastRuns.length }}</span>
              <span class="stat-label">分支</span>
            </div>
          </div>
        </div>

        <!-- 材料时间线 -->
        <div class="panel-section">
          <h2 class="panel-title">
            <span class="title-icon">&#128193;</span> 材料时间线
          </h2>
          <div v-if="isBootstrapping" class="panel-loading">
            <div class="loading-spinner"></div>
            <span>正在导入项目数据并分析...</span>
          </div>
          <div v-else-if="materials.length === 0" class="panel-empty">
            <div class="empty-illustration">&#128444;</div>
            <p>尚未追加材料</p>
            <button class="empty-action" @click="showAppendDialog = true">+ 添加材料</button>
          </div>
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

        <!-- 基线版本 -->
        <div class="panel-section">
          <h2 class="panel-title">
            <span class="title-icon">&#128200;</span> 基线版本
            <button class="panel-title-action" @click="onRebuildBaseline" :disabled="materials.length === 0 || baselineRebuilding || graphRebuilding">
              {{ (baselineRebuilding || graphRebuilding) ? '构建中...' : '重建' }}
            </button>
          </h2>
          <div v-if="baselineRebuilding || graphRebuilding" class="panel-loading">
            <div class="loading-spinner"></div>
            <span>{{ baselineRebuilding ? baselineRebuildMsg : graphRebuildMsg }}</span>
            <div class="rebuild-elapsed" v-if="rebuildElapsed">已用时 {{ rebuildElapsed }}</div>
            <div class="mini-progress">
              <div class="mini-progress-fill" :style="{ width: (baselineRebuilding ? baselineRebuildProgress : graphRebuildProgress) + '%' }"></div>
            </div>
          </div>
          <div v-else-if="baselines.length === 0" class="panel-empty-small">
            <div class="empty-illustration">&#128451;</div>
            <p>暂无基线</p>
          </div>
          <ul class="baseline-list" v-else>
            <li v-for="(b, idx) in baselines" :key="b.baseline_id" class="baseline-item"
                :class="{ current: b.baseline_id === currentBaselineId }"
                @click="onSwitchBaseline(b)">
              <span class="baseline-version">v{{ idx + 1 }}</span>
              <span class="baseline-stage">{{ b.current_stage || '—' }}</span>
              <span class="baseline-time">{{ formatTime(b.created_at) }}</span>
              <button class="baseline-del-btn" @click.stop="onDeleteBaseline(b.baseline_id)" title="删除">&#215;</button>
            </li>
          </ul>

          <!-- 基线详情 -->
          <div class="baseline-detail" v-if="activeBaseline">
            <div class="bd-section bd-graph-stats">
              <div class="bd-label">
                关联图谱
                <button
                  class="bd-rebuild-btn bd-view-graph-btn"
                  @click="goToStep(1)"
                  title="前往图谱构建页查看"
                >&#128065; 查看</button>
                <button
                  v-if="!baselineGraphRebuilding"
                  class="bd-rebuild-btn"
                  @click="onRebuildBaselineGraph"
                  title="为当前基线重建独立图谱"
                >↻ 重建图谱</button>
                <span v-else class="bd-rebuild-hint">构建中...</span>
              </div>
              <div class="bd-tags" v-if="baselineGraphStats">
                <span class="bd-tag">{{ baselineGraphStats.nodes }} 节点</span>
                <span class="bd-tag">{{ baselineGraphStats.edges }} 关系</span>
              </div>
              <div v-if="baselineGraphRebuilding" class="mini-progress" style="margin-top:4px">
                <div class="mini-progress-fill" :style="{ width: baselineGraphRebuildProgress + '%' }"></div>
              </div>
            </div>
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
        <!-- 全局状态（深色视觉焦点卡片） -->
        <div class="global-status-card">
          <div class="gsc-header">
            <span class="gsc-icon">&#127760;</span>
            <span class="gsc-title">全局状态</span>
            <span class="gsc-badge" v-if="activeRunId">LIVE</span>
          </div>
          <div class="gsc-body">
            <div class="state-grid" v-if="worldState">
              <div class="state-card" v-for="(val, key) in worldState" :key="key">
                <div class="state-label">{{ stateVarCN[key] || key }}</div>
                <div class="state-bar-track">
                  <div class="state-bar-fill" :style="{ width: (val * 100) + '%', background: stateColor(key, val) }"></div>
                </div>
                <div class="state-value">{{ (val * 100).toFixed(0) }}%</div>
              </div>
            </div>
            <div v-else class="gsc-empty">
              <p>启动预测分支后可查看态势</p>
            </div>
          </div>
        </div>

        <!-- 事件因果图 -->
        <div class="panel-section causal-graph-section">
          <h2 class="panel-title">
            <span class="title-icon">&#128279;</span> 事件因果图
          </h2>
          <div v-if="causalGraphLoading" class="panel-loading">
            <div class="loading-spinner"></div>
            <span>正在生成事件因果图...</span>
          </div>
          <div v-else-if="causalGraph.events.length === 0" class="panel-empty-small">
            <div class="empty-illustration">&#128302;</div>
            <p>重建基线后自动生成</p>
          </div>
          <div v-else class="causal-timeline">
            <div class="causal-summary" v-if="causalGraph.summary">{{ causalGraph.summary }}</div>
            <div class="causal-events">
              <div
                v-for="(evt, idx) in causalGraph.events"
                :key="evt.id"
                class="causal-node"
                :class="[evt.type, { 'has-edge': getOutEdges(evt.id).length > 0 }]"
              >
                <div class="causal-node-dot" :class="evt.type"></div>
                <div class="causal-node-connector" v-if="idx < causalGraph.events.length - 1"></div>
                <div class="causal-node-content">
                  <div class="causal-node-header">
                    <span class="causal-time">{{ evt.time }}</span>
                    <span class="causal-type-badge" :class="evt.type">{{ eventTypeCN[evt.type] || evt.type }}</span>
                    <span class="causal-stage-badge" v-if="evt.stage">{{ evt.stage }}</span>
                  </div>
                  <div class="causal-node-title">{{ evt.title }}</div>
                  <div class="causal-node-actor">{{ evt.actor }}</div>
                  <div class="causal-node-desc" v-if="evt.description">{{ evt.description }}</div>
                  <div class="causal-edges" v-if="getOutEdges(evt.id).length > 0">
                    <span v-for="e in getOutEdges(evt.id)" :key="e.target" class="causal-edge-tag" :class="e.relation">
                      {{ e.label }} &#8594; {{ getEventTitle(e.target) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 预测分支管理 -->
        <div class="panel-section">
          <h2 class="panel-title">
            <span class="title-icon">&#128440;</span> 预测分支
            <button class="panel-title-action" @click="onCreateRun" :disabled="!currentBaselineId">+ 新建</button>
          </h2>
          <div v-if="forecastRuns.length === 0" class="panel-empty">
            <div class="empty-illustration">&#127793;</div>
            <p>暂无预测分支</p>
            <div class="empty-hint">
              <button class="empty-action" @click="onCreateRun" :disabled="!currentBaselineId">创建第一个分支</button>
            </div>
          </div>
          <ul class="run-list" v-else>
            <li v-for="r in forecastRuns" :key="r.run_id" class="run-item"
                :class="{ active: activeRunId === r.run_id }"
                @click="onSelectRun(r.run_id)">
              <span class="run-type-badge" :class="r.branch_type">{{ branchTypeCN[r.branch_type] || r.branch_type }}</span>
              <span class="run-label">{{ r.branch_label || r.run_id.slice(-8) }}</span>
              <span class="run-status" :class="r.status">{{ statusCN[r.status] || r.status }}</span>
              <span class="run-actions" v-if="activeRunId === r.run_id" @click.stop>
                <span v-if="r.status === 'created'" class="run-start-group">
                  <input type="number" v-model.number="startRounds" min="1" max="100" class="rounds-input" placeholder="轮" />
                  <button class="run-action-btn" @click="onPrepareAndStart(r.run_id)" :disabled="runActionLoading">
                    {{ runActionLoading ? '准备中...' : '准备并启动' }}
                  </button>
                </span>
                <button v-else-if="r.status === 'preparing'" class="run-action-btn run-view-btn"
                  @click="goToProcess(r, 2)">查看进度</button>
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
                <button class="run-action-btn run-delete-btn" @click="onDeleteRun(r.run_id)" title="删除分支">✕</button>
              </span>
            </li>
          </ul>
        </div>

        <!-- 预测路径 -->
        <div class="panel-section" v-if="forecastPaths.length">
          <h2 class="panel-title">
            <span class="title-icon">&#128692;</span> 预测路径
          </h2>
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

        <!-- 快捷操作 -->
        <div class="quick-actions">
          <div class="quick-action-card" @click="onCreateRun" :class="{ disabled: !currentBaselineId }">
            <span class="qa-icon">&#128260;</span>
            <span class="qa-label">新建分支</span>
          </div>
          <div class="quick-action-card" @click="goToProcessView" :class="{ disabled: !activeRunId }">
            <span class="qa-icon">&#128202;</span>
            <span class="qa-label">推演视图</span>
          </div>
          <div class="quick-action-card" @click="showExportReport = true">
            <span class="qa-icon">&#128209;</span>
            <span class="qa-label">生成报告</span>
          </div>
        </div>

        <!-- 主链路步骤跳转 -->
        <div class="step-nav-bar">
          <div class="step-nav-header">
            <span class="step-nav-title">构建流程</span>
            <span class="step-nav-branch" v-if="activeRun">
              {{ activeRun.branch_label || activeRun.run_id.slice(-8) }}
              <span class="step-nav-branch-status" :class="activeRun.status">{{ statusCN[activeRun.status] || activeRun.status }}</span>
            </span>
            <span class="step-nav-branch step-nav-branch-none" v-else>请选择分支</span>
          </div>
          <div class="step-nav-btns">
            <button class="step-nav-btn" :class="stepState(1)" @click="goToStep(1)">
              <span class="step-nav-num">01</span><span class="step-nav-name">图谱构建</span>
              <span class="step-nav-check" v-if="stepState(1) === 'done'">&#10003;</span>
            </button>
            <button class="step-nav-btn" :class="stepState(2)" @click="goToStep(2)">
              <span class="step-nav-num">02</span><span class="step-nav-name">环境搭建</span>
              <span class="step-nav-check" v-if="stepState(2) === 'done'">&#10003;</span>
              <span class="step-nav-spinner" v-if="stepState(2) === 'active' && activeRun?.status === 'preparing'"></span>
            </button>
            <button class="step-nav-btn" :class="stepState(3)" @click="goToStep(3)">
              <span class="step-nav-num">03</span><span class="step-nav-name">世界模型推演</span>
              <span class="step-nav-check" v-if="stepState(3) === 'done'">&#10003;</span>
              <span class="step-nav-spinner" v-if="stepState(3) === 'active' && activeRun?.status === 'running'"></span>
            </button>
            <button class="step-nav-btn" :class="stepState(4)" @click="goToStep(4)">
              <span class="step-nav-num">04</span><span class="step-nav-name">报告生成</span>
              <span class="step-nav-check" v-if="stepState(4) === 'done'">&#10003;</span>
            </button>
            <button class="step-nav-btn" :class="stepState(5)" @click="goToStep(5)">
              <span class="step-nav-num">05</span><span class="step-nav-name">深度互动</span>
              <span class="step-nav-check" v-if="stepState(5) === 'done'">&#10003;</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 右栏：动作 & 决策 -->
      <section class="ws-panel ws-panel-right">
        <!-- 推荐动作 -->
        <div class="panel-section">
          <h2 class="panel-title">
            <span class="title-icon">&#128161;</span> 推荐动作
          </h2>
          <div v-if="recommendedActions.length === 0" class="panel-empty">
            <div class="empty-illustration">&#127919;</div>
            <p>获取决策简报后显示</p>
            <div class="empty-hint">运行预测分支后获取推荐</div>
          </div>
          <ul class="action-list" v-else>
            <li v-for="a in recommendedActions" :key="a.action_id" class="action-item">
              <div class="action-rank">#{{ a.recommendation_rank }}</div>
              <div class="action-body">
                <div class="action-title">{{ a.title }}</div>
                <div class="action-why">{{ a.why_now }}</div>
                <div class="action-meta">
                  <span class="meta-tag confidence">置信 {{ (a.confidence * 100).toFixed(0) }}%</span>
                  <span class="meta-tag delay">见效 ~{{ a.estimated_delay_hours }}h</span>
                </div>
              </div>
            </li>
          </ul>
        </div>

        <!-- 不作为风险 -->
        <div class="panel-section" v-if="noActionRisk">
          <h2 class="panel-title">
            <span class="title-icon">&#9888;</span> 不作为风险
          </h2>
          <div class="no-action-card" :class="noActionRisk.severity">
            <div class="risk-gauge">
              <div class="gauge-value">{{ (noActionRisk.risk_score * 100).toFixed(0) }}%</div>
              <div class="gauge-label">风险指数</div>
            </div>
            <div class="no-action-label">{{ noActionRisk.recommendation }}</div>
            <ul class="no-action-reasons">
              <li v-for="(reason, i) in noActionRisk.reasons" :key="i">{{ reason }}</li>
            </ul>
          </div>
        </div>

        <!-- 监测信号 -->
        <div class="panel-section" v-if="monitoringSignals.length">
          <h2 class="panel-title">
            <span class="title-icon">&#128246;</span> 监测信号
          </h2>
          <ul class="signal-list">
            <li v-for="(s, i) in monitoringSignals" :key="i" class="signal-item" :class="s.priority">
              <span class="signal-priority">{{ s.priority }}</span>
              <span class="signal-text">{{ s.signal }}</span>
            </li>
          </ul>
        </div>

        <!-- 操作按钮 -->
        <div class="panel-section panel-actions-bar">
          <button class="ws-action-btn ws-primary ws-full" @click="onGetDecisionBrief" :disabled="!activeRunId">
            <span class="btn-icon">&#128203;</span> 获取决策简报
          </button>
          <button class="ws-action-btn ws-secondary ws-full" @click="onRecalibrate" :disabled="!activeRunId">
            <span class="btn-icon">&#128295;</span> 校准 & 重新预测
          </button>
        </div>

        <!-- 帮助提示 -->
        <div class="help-tips">
          <div class="tip-header">&#128172; 使用提示</div>
          <ul class="tip-list">
            <li>1. 追加材料并重建基线</li>
            <li>2. 创建并运行预测分支</li>
            <li>3. 获取决策简报分析</li>
          </ul>
        </div>
      </section>
    </main>

    <!-- ========== 导出报告对话框 ========== -->
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

    <!-- ========== 追加材料对话框 ========== -->
    <div class="modal-overlay" v-if="showAppendDialog" @click.self="closeAppendDialog">
      <div class="modal-box append-material-modal">
        <h3>+ 追加材料</h3>

        <!-- 文件上传区 -->
        <div class="append-section">
          <div class="append-section-header">&#128193; 文件上传</div>
          <div class="file-drop-zone" @click="triggerFileInput" @dragover.prevent @drop.prevent="onFileDrop">
            <div class="drop-icon">&#128196;</div>
            <p>点击选择或拖拽文件到此处</p>
            <p class="drop-hint">支持 PDF、MD、TXT 格式，可多选</p>
          </div>
          <div v-if="appendFileNames.length" class="file-list-preview">
            <div v-for="(name, i) in appendFileNames" :key="i" class="file-preview-item">
              &#128196; {{ name }}
              <span class="file-remove" @click.stop="removeFile(i)" title="移除">&times;</span>
            </div>
          </div>
          <button
            v-if="appendFiles.length"
            class="ws-action-btn ws-primary append-upload-btn"
            @click="onUploadFiles"
            :disabled="appendUploading"
          >{{ appendUploading ? '上传中...' : '&#10003; 上传文件' }}</button>
          <div v-if="appendFileUploaded" class="append-done-hint">&#10003; 已上传 {{ appendFileUploaded }} 个文件</div>
        </div>

        <!-- 分割线 -->
        <div class="append-divider"><span>也可以</span></div>

        <!-- 网络抓取区 -->
        <div class="append-section">
          <div class="append-section-header">&#127760; 网络抓取</div>
          <p class="section-desc">输入关键词自动搜索互联网舆情信息并导入</p>
          <div class="web-search-form">
            <input
              class="web-search-input"
              v-model="webSearchQuery"
              placeholder="搜索关键词，如：华中农大 研究生 举报导师"
              @keydown.enter="onWebSearch"
              :disabled="webSearchLoading"
            />
            <button
              class="ws-action-btn ws-primary web-search-btn"
              @click="onWebSearch"
              :disabled="webSearchLoading || !webSearchQuery.trim()"
            >
              <span v-if="webSearchLoading" class="btn-spinner"></span>
              <span v-else>&#128269;</span>
              {{ webSearchLoading ? '搜索中...' : '搜索导入' }}
            </button>
          </div>
          <p class="web-search-error" v-if="webSearchError">{{ webSearchError }}</p>
          <div class="web-search-result" v-if="webSearchResults">
            <div class="web-search-success">
              <span class="success-icon">&#10003;</span>
              已导入 <strong>{{ webSearchResults.added }}</strong> 条网络材料
            </div>
            <ul class="web-search-sources" v-if="webSearchResults.sources?.length">
              <li v-for="(s, i) in webSearchResults.sources" :key="i" class="web-source-item">
                <a :href="s.url" target="_blank" rel="noopener" class="web-source-link">{{ s.title }}</a>
              </li>
            </ul>
          </div>
        </div>

        <!-- 底部关闭 -->
        <div class="modal-actions">
          <button class="ws-action-btn ws-secondary" @click="closeAppendDialog">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { listMaterials, listBaselines, rebuildBaseline, appendMaterialFiles, appendMaterialFromWeb, deleteBaseline, getCausalGraph } from '../api/incident'
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
const showAppendDialog = ref(false)
const appendFiles = ref([])
const appendFileNames = ref([])
const appendUploading = ref(false)
const appendFileUploaded = ref(0)
const webSearchQuery = ref('')
const webSearchLoading = ref(false)
const webSearchError = ref('')
const webSearchResults = ref(null)
const isBootstrapping = ref(false)
const runActionLoading = ref(false)
const activeBaseline = ref(null)
const baselineGraphStats = ref(null) // { nodes, edges } for active baseline's graph
const projectGraphId = ref('') // project-level graph_id (fallback for old baselines)
const baselineGraphRebuilding = ref(false)
const baselineGraphRebuildProgress = ref(0)

// 事件因果图
const causalGraph = ref({ events: [], edges: [], summary: '' })
const causalGraphLoading = ref(false)
const eventTypeCN = {
  trigger: '触发', response: '回应', escalation: '升级',
  mitigation: '缓和', turning_point: '转折', outcome: '结果'
}
function getOutEdges(evtId) {
  return (causalGraph.value.edges || []).filter(e => e.source === evtId)
}
function getEventTitle(evtId) {
  const evt = (causalGraph.value.events || []).find(e => e.id === evtId)
  return evt ? evt.title : evtId
}
async function loadCausalGraph() {
  try {
    causalGraphLoading.value = true
    const res = await getCausalGraph(projectId.value, currentBaselineId.value)
    if (res?.success && res.data) {
      causalGraph.value = res.data
    }
  } catch (e) { console.warn('loadCausalGraph', e) }
  finally { causalGraphLoading.value = false }
}

const stateVarCN = {
  attention_level: '关注度',
  panic_level: '恐慌度',
  trust_level: '信任度',
  polarization_level: '极化度',
  risk_level: '风险等级',
  stability_level: '稳定性',
}

const branchTypeCN = {
  base: '基准',
  recalibrated: '校准',
  intervention_a: '干预A',
  intervention_b: '干预B',
  intervention_c: '干预C',
}
const statusCN = {
  created: '已创建',
  preparing: '准备中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  superseded: '已替代',
}

// 当前选中分支的构建进度（映射 status → 当前活跃步骤）
const activeRun = computed(() => forecastRuns.value.find(r => r.run_id === activeRunId.value) || null)
const activeRunStep = computed(() => {
  if (!activeRun.value) return 0
  const s = activeRun.value.status
  if (s === 'created') return 1          // 图谱已构建，待环境搭建
  if (s === 'preparing') return 2         // 环境搭建中
  if (['prepared', 'ready'].includes(s)) return 2 // 环境搭建完成
  if (s === 'running') return 3           // 推演中
  if (s === 'completed') return 5         // 全部完成
  return 0
})
function stepState(stepNum) {
  if (!activeRun.value) return stepNum <= 1 ? '' : 'disabled'
  const cur = activeRunStep.value
  if (cur >= 5 && stepNum <= 5) return 'done'       // 全流程完成
  if (stepNum < cur) return 'done'
  if (stepNum === cur) return 'active'
  return 'pending'
}

// ── 初始化 ──
onMounted(async () => {
  await loadProjectInfo()
  await Promise.all([loadMaterials(), loadBaselines(), loadForecastRuns()])
  if (currentBaselineId.value) {
    loadCausalGraph()
    loadBaselineGraphStats()
  }
  if (materials.value.length === 0 && projectHasText.value) {
    await autoImportProjectText()
  }
})
onBeforeUnmount(() => { _stopElapsedTimer() })

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
      projectGraphId.value = d.project?.graph_id || ''
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

async function autoImportProjectText() {
  isBootstrapping.value = true
  try {
    const { autoBootstrapMaterials } = await import('../api/incident')
    const res = await autoBootstrapMaterials(projectId.value)
    if (res?.success) {
      await loadMaterials()
      await onRebuildBaseline()
    }
  } catch (e) {
    console.warn('autoImportProjectText', e)
  } finally {
    isBootstrapping.value = false
  }
}

// ── 操作 ──
function triggerFileInput() {
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.pdf,.md,.txt'
  input.onchange = (e) => {
    const files = e.target.files
    if (!files.length) return
    appendFiles.value = Array.from(files)
    appendFileNames.value = Array.from(files).map(f => f.name)
  }
  input.click()
}

function onFileDrop(e) {
  const files = e.dataTransfer.files
  if (!files.length) return
  appendFiles.value = Array.from(files).filter(f => /\.(pdf|md|txt)$/i.test(f.name))
  appendFileNames.value = appendFiles.value.map(f => f.name)
}

function removeFile(index) {
  appendFiles.value.splice(index, 1)
  appendFileNames.value.splice(index, 1)
}

async function onUploadFiles() {
  if (!appendFiles.value.length || appendUploading.value) return
  appendUploading.value = true
  try {
    const formData = new FormData()
    for (const f of appendFiles.value) formData.append('files', f)
    await appendMaterialFiles(projectId.value, formData)
    await loadMaterials()
    appendFileUploaded.value += appendFiles.value.length
    appendFiles.value = []
    appendFileNames.value = []
  } catch (err) { console.error('onUploadFiles', err) } finally {
    appendUploading.value = false
  }
}

async function onWebSearch() {
  if (!webSearchQuery.value.trim() || webSearchLoading.value) return
  webSearchLoading.value = true
  webSearchError.value = ''
  webSearchResults.value = null
  try {
    const res = await appendMaterialFromWeb(projectId.value, { query: webSearchQuery.value.trim(), max_results: 8 })
    if (res?.success) {
      webSearchResults.value = {
        added: res.data?.added_material_ids?.length || 0,
        sources: res.data?.sources || [],
      }
      await loadMaterials()
    } else {
      webSearchError.value = res?.error || '搜索失败，请重试'
    }
  } catch (err) {
    webSearchError.value = err?.message || '网络请求失败'
    console.error('onWebSearch', err)
  } finally {
    webSearchLoading.value = false
  }
}

function closeAppendDialog() {
  showAppendDialog.value = false
  appendFiles.value = []
  appendFileNames.value = []
  appendFileUploaded.value = 0
  webSearchQuery.value = ''
  webSearchError.value = ''
  webSearchResults.value = null
}

const baselineRebuilding = ref(false)
const baselineRebuildProgress = ref(0)
const baselineRebuildMsg = ref('')
const graphRebuilding = ref(false)
const graphRebuildProgress = ref(0)
const graphRebuildMsg = ref('')
const rebuildElapsed = ref('')
let _rebuildTimer = null

function _startElapsedTimer() {
  const t0 = Date.now()
  rebuildElapsed.value = '0 秒'
  _rebuildTimer = setInterval(() => {
    const sec = Math.floor((Date.now() - t0) / 1000)
    if (sec < 60) rebuildElapsed.value = `${sec} 秒`
    else rebuildElapsed.value = `${Math.floor(sec / 60)} 分 ${sec % 60} 秒`
  }, 1000)
}
function _stopElapsedTimer() {
  if (_rebuildTimer) { clearInterval(_rebuildTimer); _rebuildTimer = null }
  rebuildElapsed.value = ''
}

async function onRebuildBaseline() {
  // 防止重复触发
  if (baselineRebuilding.value || graphRebuilding.value) return
  try {
    // Phase 1: LLM 基线分析（同步等待）
    baselineRebuilding.value = true
    baselineRebuildProgress.value = 10
    baselineRebuildMsg.value = '正在分析材料并提取事实基线（LLM 推理中）...'
    _startElapsedTimer()

    const materialIds = materials.value.map(m => m.material_id)

    // 模拟中间进度：每 8 秒推进一点，让用户知道还在工作
    const fakeProgress = setInterval(() => {
      if (baselineRebuildProgress.value < 80) {
        baselineRebuildProgress.value += 5
      }
      // 更新阶段提示
      if (baselineRebuildProgress.value >= 30 && baselineRebuildProgress.value < 55) {
        baselineRebuildMsg.value = '正在提取事件因果关系...'
      } else if (baselineRebuildProgress.value >= 55) {
        baselineRebuildMsg.value = '正在整合分析结果...'
      }
    }, 8000)

    const res = await rebuildBaseline(projectId.value, { material_ids: materialIds })
    clearInterval(fakeProgress)

    if (res?.success && res.data?.baseline_id) {
      currentBaselineId.value = res.data.baseline_id
    }
    baselineRebuildProgress.value = 90
    baselineRebuildMsg.value = '基线已生成，正在刷新数据...'
    await loadBaselines()
    await loadProjectInfo()
    await loadCausalGraph()
    baselineRebuilding.value = false
    baselineRebuildProgress.value = 0

    // Phase 2: 异步图谱重建
    const taskId = res?.data?.graph_task_id
    if (taskId) {
      graphRebuilding.value = true
      graphRebuildProgress.value = 0
      graphRebuildMsg.value = '正在重建知识图谱...'
      const { getTaskStatus } = await import('../api/graph')
      const poll = setInterval(async () => {
        try {
          const tr = await getTaskStatus(taskId)
          if (tr?.success) {
            graphRebuildProgress.value = tr.data?.progress || 0
            graphRebuildMsg.value = tr.data?.message || '图谱构建中...'
            if (tr.data?.status === 'completed' || tr.data?.status === 'failed') {
              clearInterval(poll)
              graphRebuilding.value = false
              _stopElapsedTimer()
              await loadProjectInfo()
            }
          }
        } catch { /* ignore */ }
      }, 3000)
    } else {
      _stopElapsedTimer()
    }
  } catch (e) {
    console.error('rebuildBaseline', e)
    baselineRebuilding.value = false
    graphRebuilding.value = false
    _stopElapsedTimer()
  }
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

async function onDeleteRun(runId) {
  if (!confirm('确定删除此预测分支？')) return
  try {
    const { deleteForecastRun } = await import('../api/incident')
    const res = await deleteForecastRun(projectId.value, runId)
    if (res?.success) {
      if (activeRunId.value === runId) activeRunId.value = ''
      await loadForecastRuns()
      await loadProjectInfo()
    }
  } catch (e) { console.error('deleteRun', e) }
}

async function onCreateRun() {
  try {
    const res = await createForecastRun({
      project_id: projectId.value,
      baseline_id: currentBaselineId.value,
      branch_type: 'base',
      branch_label: (() => {
        const blIdx = baselines.value.findIndex(b => b.baseline_id === currentBaselineId.value) + 1
        const stage = activeBaseline.value?.current_stage
        const ver = `v${blIdx || (baselines.value.length)}`
        return stage ? `预测 基线${ver}-${stage}` : `预测 基线${ver}`
      })(),
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
      await loadForecastRuns()
      await pollRunStatus(runId, ['preparing'], 300)
    }
    await loadForecastRuns()
  } catch (e) { console.error('prepareRun', e) }
  finally { runActionLoading.value = false }
}

const startRounds = ref(10)

async function onPrepareAndStart(runId) {
  runActionLoading.value = true
  try {
    const res = await prepareForecastRun(runId)
    if (!res?.success) return
    await loadForecastRuns()
    // 等待 prepare 完成
    const finalStatus = await pollRunStatus(runId, ['preparing', 'created'], 300)
    await loadForecastRuns()
    // prepare 完成后自动启动
    if (['prepared', 'ready'].includes(finalStatus)) {
      const rounds = startRounds.value || 10
      const startRes = await startForecastRun(runId, { max_rounds: rounds, enable_graph_memory_update: false })
      if (startRes?.success) {
        await loadForecastRuns()
        pollRunStatus(runId, ['running'], 1800)
          .then(() => loadForecastRuns())
          .catch(() => {})
      }
    }
  } catch (e) { console.error('prepareAndStart', e) }
  finally { runActionLoading.value = false }
}

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

async function loadBaselineGraphStats() {
  baselineGraphStats.value = null
  const graphId = activeBaseline.value?.graph_id
  if (!graphId) {
    baselineGraphStats.value = { nodes: 0, edges: 0 }
    return
  }
  try {
    const { getGraphData } = await import('../api/graph')
    const res = await getGraphData(graphId)
    const nodes = res?.data?.node_count || res?.data?.nodes?.length || 0
    const edges = res?.data?.edge_count || res?.data?.edges?.length || 0
    baselineGraphStats.value = { nodes, edges }
  } catch (e) { console.warn('loadBaselineGraphStats', e) }
}

async function onRebuildBaselineGraph() {
  if (!activeBaseline.value || baselineGraphRebuilding.value) return
  baselineGraphRebuilding.value = true
  baselineGraphRebuildProgress.value = 0
  try {
    const { rebuildBaselineGraph } = await import('../api/incident')
    const res = await rebuildBaselineGraph(projectId.value, activeBaseline.value.baseline_id)
    if (!res?.success || !res.data?.task_id) {
      alert(res?.error || '启动图谱重建失败')
      baselineGraphRebuilding.value = false
      return
    }
    const taskId = res.data.task_id
    const { getTaskStatus } = await import('../api/graph')
    const poll = setInterval(async () => {
      try {
        const tr = await getTaskStatus(taskId)
        if (tr?.success) {
          baselineGraphRebuildProgress.value = tr.data?.progress || 0
          if (tr.data?.status === 'completed' || tr.data?.status === 'failed') {
            clearInterval(poll)
            baselineGraphRebuilding.value = false
            baselineGraphRebuildProgress.value = 0
            await loadBaselines()
            // refresh activeBaseline to get updated graph_id
            const updated = baselines.value.find(b => b.baseline_id === activeBaseline.value?.baseline_id)
            if (updated) activeBaseline.value = updated
            await loadBaselineGraphStats()
          }
        }
      } catch { /* ignore */ }
    }, 3000)
  } catch (e) {
    console.error('onRebuildBaselineGraph', e)
    baselineGraphRebuilding.value = false
  }
}

function onSwitchBaseline(b) {
  currentBaselineId.value = b.baseline_id
  activeBaseline.value = b
  loadCausalGraph()
  loadBaselineGraphStats()
  if (recommendedActions.value.length > 0 && activeRunId.value) {
    onGetDecisionBrief()
  }
}

async function onGetDecisionBrief() {
  if (!activeRunId.value) return
  if (activeRun.value && !['running', 'completed'].includes(activeRun.value.status)) {
    alert(`当前分支状态为"${statusCN[activeRun.value.status] || activeRun.value.status}"，需先完成"准备→启动"流程后才能获取决策简报。`)
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
      if (d.current_diagnosis?.current_state) {
        worldState.value = d.current_diagnosis.current_state
      }
    }
  } catch (e) { console.error('getDecisionBrief', e) }
}

async function onRecalibrate() {
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
  router.push({
    path: `/process/${projectId.value}`,
    query: {
      step: String(step),
      sim: run.simulation_id || '',
      baseline_id: run.baseline_id || '',
      branch_label: run.branch_label || '',
      branch_type: run.branch_type || '',
    }
  })
}
function goToProcessView() {
  router.push({ path: `/process/${projectId.value}`, query: { step: '3' } })
}
function goToStep(step) {
  const run = activeRun.value
  if (!run && step > 1) return // 未选分支时仅允许步骤1
  const query = { step: String(step) }
  if (run) {
    if (run.simulation_id) query.sim = run.simulation_id
    if (run.baseline_id) query.baseline_id = run.baseline_id
    if (run.branch_label) query.branch_label = run.branch_label
    if (run.branch_type) query.branch_type = run.branch_type
  }
  // 传递当前基线的 graph_id，避免 Process 页面使用可能已过期的 project.graph_id
  const blGraphId = activeBaseline.value?.graph_id
  if (blGraphId) query.baseline_graph_id = blGraphId
  router.push({ path: `/process/${projectId.value}`, query })
}
function goHome() { router.push('/') }
function goToReport() {
  showExportReport.value = false
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
  if (['panic_level', 'polarization_level', 'risk_level', 'attention_level'].includes(key)) {
    return val > 0.6 ? '#ef4444' : val > 0.4 ? '#f59e0b' : '#22c55e'
  }
  return val > 0.6 ? '#22c55e' : val > 0.4 ? '#f59e0b' : '#ef4444'
}
</script>

<style scoped>
/* ==================== 浅色科技风 Teal 配色 ==================== */
:root {
  --color-white: #FFFFFF;
  --color-snow: #F8FAFB;
  --color-slate: #F1F5F9;
  --color-border: #E2E8F0;
  --color-black: #0F172A;
  --color-muted: #64748b;
  --teal-50:  #F0FDFA;
  --teal-100: #CCFBF1;
  --teal-200: #99F6E4;
  --teal-300: #5EEAD4;
  --teal-400: #2DD4BF;
  --teal-500: #14B8A6;
  --teal-600: #0D9488;
  --teal-700: #0F766E;
}

/* ========== 布局 ========== */
.incident-workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(160deg, #e6f4f3 0%, #eef7fb 30%, #eff3fc 60%, #f3f0f9 100%);
  color: var(--color-black);
  font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
  position: relative;
}

.incident-workspace::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(115, 168, 185, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(115, 168, 185, 0.04) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
  z-index: 0;
}

.incident-workspace > * { position: relative; z-index: 1; }

/* Header */
.ws-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  background: linear-gradient(90deg, #e6f4f3 0%, #eef7fb 30%, #eff3fc 60%, #f3f0f9 100%);
  flex-shrink: 0;
  border-bottom: 1px solid rgba(100, 116, 139, 0.08);
  box-shadow: 0 2px 12px rgba(100, 116, 139, 0.05);
}
.ws-header-left { display: flex; align-items: center; gap: 12px; }
.ws-header-center { display: flex; align-items: center; gap: 12px; }
.ws-header-right { display: flex; align-items: center; gap: 8px; }

.ws-back-btn {
  background: rgba(79, 144, 148, 0.1);
  border: 1px solid rgba(79, 144, 148, 0.18);
  color: #4f9094;
  font-size: 16px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s;
}
.ws-back-btn:hover { background: rgba(79, 144, 148, 0.18); border-color: rgba(79, 144, 148, 0.3); }

.ws-brand-name { font-weight: 700; font-size: 16px; color: #3d7a80; }
.ws-mode-badge {
  background: rgba(79, 144, 148, 0.1);
  color: #4f9094;
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  margin-left: 8px;
  border: 1px solid rgba(79, 144, 148, 0.16);
}
.ws-project-title { font-size: 16px; font-weight: 600; color: #3d7a80; }
.ws-baseline-tag {
  font-size: 11px;
  color: #8a9bb0;
  background: rgba(100, 116, 139, 0.05);
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.08);
}

/* ========== 三栏主体 ========== */
.ws-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 16px;
  padding: 16px;
}

.ws-panel {
  overflow-y: auto;
  padding: 20px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.03);
  border: 1px solid var(--color-border);
  transition: box-shadow 0.25s ease;
}
.ws-panel:hover { box-shadow: 0 8px 30px rgba(20, 184, 166, 0.08), 0 2px 6px rgba(0,0,0,0.04); }
.ws-panel::-webkit-scrollbar { width: 5px; }
.ws-panel::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--teal-200), var(--teal-400)); border-radius: 3px; }
.ws-panel::-webkit-scrollbar-track { background: var(--teal-50); }

.ws-panel-left { width: 300px; flex-shrink: 0; }
.ws-panel-center { flex: 1; min-width: 420px; }
.ws-panel-right { width: 340px; flex-shrink: 0; }

/* ========== 按钮 ========== */
.ws-action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-icon { font-size: 14px; }

.ws-primary {
  background: linear-gradient(135deg, #4f9094 0%, #5a9ba0 100%);
  color: #fff;
  box-shadow: 0 2px 10px rgba(79, 144, 148, 0.3);
}
.ws-primary:hover {
  background: linear-gradient(135deg, #3d7a80 0%, #4f9094 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(79, 144, 148, 0.4);
}
.ws-primary:disabled { background: #e2e8f0; color: #94a3b8; cursor: not-allowed; transform: none; box-shadow: none; }

.ws-secondary {
  background: #fff;
  color: #4f9094;
  border: 1px solid rgba(79, 144, 148, 0.25);
}
.ws-secondary:hover { background: #EEF7FB; border-color: rgba(79, 144, 148, 0.4); color: #3d7a80; }

.ws-full { width: 100%; margin-bottom: 8px; justify-content: center; }

/* ========== 项目概览卡片 ========== */
.overview-card {
  background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%);
  border-radius: 16px;
  padding: 16px 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 15px rgba(13, 148, 136, 0.35);
  position: relative;
  overflow: hidden;
}
.overview-card::before {
  content: '';
  position: absolute;
  top: -30px; right: -30px;
  width: 100px; height: 100px;
  background: rgba(255,255,255,0.08);
  border-radius: 50%;
  pointer-events: none;
}
.overview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.overview-icon { font-size: 16px; }
.overview-title { font-size: 11px; font-weight: 700; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 0.08em; }
.overview-name {
  font-size: 14px; font-weight: 700; color: #fff;
  margin-bottom: 8px; line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.overview-stage {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: rgba(255,255,255,0.9);
  margin-bottom: 12px; font-weight: 500;
}
.stage-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #5EEAD4; box-shadow: 0 0 6px #5EEAD4;
  flex-shrink: 0;
}
.overview-stats {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: rgba(0, 0, 0, 0.15);
  border-radius: 10px;
  padding: 10px 6px;
}
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 1px; }
.stat-icon { font-size: 13px; margin-bottom: 2px; }
.stat-num { font-size: 20px; font-weight: 800; color: #fff; line-height: 1.1; }
.stat-label { font-size: 9px; color: rgba(255, 255, 255, 0.65); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
.stat-divider { width: 1px; height: 28px; background: rgba(255, 255, 255, 0.15); }

/* ========== 全局状态卡片（深色视觉焦点） ========== */
.global-status-card {
  background: linear-gradient(145deg, #0d2b3e 0%, #0f3d52 50%, #0d4a62 100%);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 24px;
  box-shadow: 0 8px 30px rgba(15, 60, 82, 0.35), 0 0 0 1px rgba(20, 184, 166, 0.15);
  position: relative;
  overflow: hidden;
}
.global-status-card::before {
  content: '';
  position: absolute;
  top: -40px;
  right: -40px;
  width: 160px;
  height: 160px;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.15) 0%, transparent 70%);
  pointer-events: none;
}
.global-status-card::after {
  content: '';
  position: absolute;
  bottom: -20px;
  left: -20px;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(20, 184, 166, 0.1) 0%, transparent 70%);
  pointer-events: none;
}
.gsc-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.gsc-icon { font-size: 18px; }
.gsc-title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.gsc-badge {
  font-size: 9px;
  font-weight: 700;
  color: var(--teal-400);
  background: rgba(20, 184, 166, 0.15);
  border: 1px solid rgba(20, 184, 166, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  letter-spacing: 0.1em;
  animation: pulse-badge 2s ease-in-out infinite;
}
@keyframes pulse-badge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.gsc-body { position: relative; z-index: 1; }
.gsc-empty p { font-size: 13px; color: rgba(255, 255, 255, 0.4); }

/* ========== 通用面板 ========== */
.panel-section { margin-bottom: 24px; }
.panel-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--teal-600);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.title-icon { font-size: 14px; }
.panel-title-action {
  font-size: 11px;
  background: linear-gradient(135deg, var(--teal-100), var(--teal-200));
  color: var(--teal-700);
  border: 1px solid var(--teal-200);
  padding: 3px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  margin-left: auto;
}
.panel-title-action:hover:not(:disabled) { background: linear-gradient(135deg, var(--teal-200), var(--teal-300)); }
.panel-title-action:disabled { opacity: 0.4; cursor: not-allowed; }

.panel-empty {
  color: var(--color-muted);
  font-size: 12px;
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}
.panel-empty-small { padding: 16px 12px; }
.empty-illustration { font-size: 32px; opacity: 0.6; }
.empty-hint { font-size: 11px; color: var(--color-muted); margin-top: 4px; }
.empty-action {
  background: linear-gradient(135deg, var(--teal-100), var(--teal-200));
  border: 1px solid var(--teal-300);
  color: var(--teal-700);
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}
.empty-action:hover { background: linear-gradient(135deg, var(--teal-200), var(--teal-300)); }
.empty-action:disabled { opacity: 0.5; cursor: not-allowed; }

.panel-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 12px;
  font-size: 12px;
  color: var(--teal-600);
}
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--teal-100);
  border-top-color: var(--teal-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.mini-progress { width: 100%; height: 4px; background: var(--teal-100); border-radius: 2px; overflow: hidden; }
.mini-progress-fill { height: 100%; background: linear-gradient(90deg, var(--teal-400), var(--teal-500)); border-radius: 2px; transition: width 0.3s; }
.rebuild-elapsed { font-size: 11px; color: var(--teal-500); margin-top: 4px; font-variant-numeric: tabular-nums; }

/* ========== 态势状态条 ========== */
.state-grid { display: flex; flex-direction: column; gap: 8px; }
.state-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.state-label { width: 70px; font-size: 11px; color: rgba(255, 255, 255, 0.6); text-align: right; }
.state-bar-track { flex: 1; height: 6px; background: rgba(255, 255, 255, 0.08); border-radius: 3px; overflow: hidden; }
.state-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s, background 0.4s; }
.state-value { width: 40px; font-size: 12px; font-weight: 600; color: rgba(255, 255, 255, 0.9); text-align: right; }

/* ========== 材料列表 ========== */
.material-list { list-style: none; padding: 0; }
.material-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  margin-bottom: 4px;
  transition: all 0.15s;
  color: var(--color-black);
  border: 1px solid transparent;
  background: transparent;
}
.material-item:hover { background: var(--teal-50); border-color: var(--teal-100); }
.material-item.active { background: var(--teal-50); border-color: var(--teal-300); }
.material-type-badge {
  font-size: 10px;
  background: linear-gradient(135deg, var(--teal-100), var(--teal-200));
  color: var(--teal-700);
  padding: 2px 8px;
  border-radius: 6px;
  flex-shrink: 0;
  border: 1px solid var(--teal-200);
}
.material-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--color-black); }
.material-time { font-size: 10px; color: #94a3b8; flex-shrink: 0; }

/* ========== 基线列表 ========== */
.baseline-list { list-style: none; padding: 0; }
.baseline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  font-size: 12px;
  border-radius: 10px;
  margin-bottom: 4px;
  cursor: pointer;
  color: var(--color-black);
  transition: all 0.15s;
  border: 1px solid transparent;
  background: transparent;
}
.baseline-item:hover { background: var(--teal-50); border-color: var(--teal-100); }
.baseline-item.current { background: var(--teal-50); border-color: var(--teal-300); }
.baseline-version { font-weight: 700; color: var(--teal-500); min-width: 32px; }
.baseline-stage { color: var(--color-muted); flex: 1; }
.baseline-time { font-size: 10px; color: #94a3b8; }
.baseline-del-btn {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 6px;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s;
}
.baseline-item:hover .baseline-del-btn { opacity: 1; }
.baseline-del-btn:hover { color: #ef4444; }

/* ========== 基线详情 ========== */
.baseline-detail { margin-top: 12px; padding: 12px; border-radius: 12px; background: var(--teal-50); border: 1px solid var(--teal-100); }
.bd-section { margin-bottom: 12px; }
.bd-section:last-child { margin-bottom: 0; }
.bd-label { font-size: 10px; font-weight: 700; color: var(--teal-600); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.04em; display: flex; align-items: center; gap: 8px; }
.bd-rebuild-btn { font-size: 10px; padding: 1px 6px; border: 1px solid var(--teal-200); border-radius: 4px; background: var(--teal-50); color: var(--teal-600); cursor: pointer; margin-left: auto; }
.bd-rebuild-btn:hover { background: var(--teal-100); }
.bd-view-graph-btn { margin-left: auto; margin-right: 0; background: #eef2ff; border-color: #c7d2fe; color: #4f46e5; }
.bd-view-graph-btn:hover { background: #e0e7ff; }
.bd-rebuild-hint { font-size: 10px; color: var(--teal-500); margin-left: auto; }
.bd-list { list-style: none; padding: 0; margin: 0; }
.bd-list li { font-size: 11px; color: var(--color-black); padding: 4px 0; line-height: 1.4; border-bottom: 1px solid var(--teal-100); }
.bd-list li:last-child { border-bottom: none; }
.bd-list.bd-risk li { color: #f59e0b; }
.bd-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.bd-tag { font-size: 10px; padding: 3px 8px; border-radius: 6px; background: var(--teal-100); color: var(--teal-700); border: 1px solid var(--teal-200); }

/* ========== 预测分支列表 ========== */
.run-list { list-style: none; padding: 0; }
.run-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  margin-bottom: 4px;
  transition: all 0.15s;
  color: var(--color-black);
  border: 1px solid transparent;
  background: transparent;
}
.run-item:hover { background: var(--teal-50); border-color: var(--teal-100); }
.run-item.active { background: var(--teal-50); border-color: var(--teal-300); }
.run-type-badge {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--teal-100), rgba(20, 184, 166, 0.15));
  color: var(--teal-600);
}
.run-type-badge.intervention_a { background: linear-gradient(135deg, #FEF3C7, #FDE68A); color: #B45309; }
.run-type-badge.recalibrated { background: var(--teal-100); color: var(--teal-700); }
.run-label { flex: 1; color: var(--color-black); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.run-actions { flex-shrink: 0; }
.run-action-btn {
  font-size: 10px;
  padding: 3px 10px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, var(--teal-100), rgba(20, 184, 166, 0.15));
  color: var(--teal-700);
  font-weight: 600;
}
.run-action-btn:hover:not(:disabled) { background: var(--teal-300); color: var(--teal-700); }
.run-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.run-view-btn { background: rgba(20, 184, 166, 0.15); }
.run-view-btn:hover { background: var(--teal-300); }
.run-delete-btn { background: rgba(239, 68, 68, 0.12); color: #ef4444; font-size: 11px; padding: 2px 7px; margin-left: 4px; }
.run-delete-btn:hover:not(:disabled) { background: rgba(239, 68, 68, 0.25); color: #dc2626; }
.run-start-group { display: inline-flex; align-items: center; gap: 6px; }
.rounds-input {
  width: 48px;
  height: 22px;
  padding: 0 6px;
  font-size: 11px;
  text-align: center;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-snow);
  color: var(--teal-600);
  outline: none;
}
.rounds-input:focus { border-color: var(--teal-400); }
.rounds-input::-webkit-inner-spin-button { -webkit-appearance: none; }
.run-status { font-size: 10px; padding: 3px 8px; border-radius: 6px; }
.run-status.created { background: var(--teal-50); color: var(--color-muted); }
.run-status.running { background: rgba(20, 184, 166, 0.15); color: var(--teal-600); }
.run-status.completed { background: linear-gradient(135deg, var(--teal-100), rgba(20, 184, 166, 0.15)); color: var(--teal-600); }
.run-status.failed { background: rgba(239, 68, 68, 0.1); color: #DC2626; }
.run-status.superseded { background: var(--color-slate); color: #94a3b8; }

/* ========== 预测路径 ========== */
.paths-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.path-card {
  padding: 14px;
  border-radius: 14px;
  font-size: 11px;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.path-card:hover { border-color: var(--teal-300); box-shadow: 0 4px 15px rgba(20, 184, 166, 0.1); transform: translateY(-2px); }
.path-card.risk-high { border-color: #FECACA; background: #FEF2F2; }
.path-card.risk-mid { border-color: #FDE68A; background: #FFFBEB; }
.path-card.risk-low { border-color: var(--teal-200); background: var(--teal-50); }
.path-header { display: flex; justify-content: space-between; align-items: center; }
.path-label { font-weight: 700; color: var(--color-black); }
.path-risk-badge { font-size: 10px; padding: 2px 8px; border-radius: 6px; font-weight: 600; }
.path-risk-badge.high { background: #FEE2E2; color: #DC2626; }
.path-risk-badge.mid { background: #FEF3C7; color: #B45309; }
.path-risk-badge.low { background: rgba(20, 184, 166, 0.2); color: var(--teal-600); }
.path-desc { color: var(--color-muted); line-height: 1.5; }
.path-changes { display: flex; flex-wrap: wrap; gap: 4px; }
.path-change-tag { font-size: 9px; padding: 2px 6px; border-radius: 6px; background: var(--teal-50); color: var(--teal-600); border: 1px solid var(--teal-100); }
.path-outcome { color: var(--color-black); font-size: 11px; line-height: 1.5; border-top: 1px solid var(--color-border); padding-top: 8px; }
.path-prob { font-size: 10px; color: #94a3b8; }

/* ========== 推荐动作 ========== */
.action-list { list-style: none; padding: 0; }
.action-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  margin-bottom: 8px;
  background: var(--color-white);
  border: 1px solid var(--color-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
}
.action-item:hover { border-color: var(--teal-300); box-shadow: 0 4px 15px rgba(20, 184, 166, 0.1); transform: translateY(-1px); }
.action-rank { font-size: 20px; font-weight: 800; color: var(--teal-500); min-width: 32px; text-align: center; }
.action-body { flex: 1; }
.action-title { font-size: 13px; font-weight: 700; color: var(--color-black); margin-bottom: 6px; }
.action-why { font-size: 11px; color: var(--color-muted); line-height: 1.5; margin-bottom: 8px; }
.action-meta { display: flex; gap: 8px; }
.meta-tag { font-size: 10px; padding: 3px 8px; border-radius: 6px; }
.meta-tag.confidence { background: var(--teal-100); color: var(--teal-700); }
.meta-tag.delay { background: var(--teal-50); color: var(--color-muted); border: 1px solid var(--teal-100); }

/* ========== 不作为风险 ========== */
.no-action-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--teal-100);
  background: var(--teal-50);
}
.no-action-card.high { border-color: #FECACA; background: #FEF2F2; }
.no-action-card.medium { border-color: #FDE68A; background: #FFFBEB; }
.risk-gauge {
  text-align: center;
  margin-bottom: 12px;
  padding: 12px;
  background: linear-gradient(135deg, var(--teal-50), rgba(20, 184, 166, 0.08));
  border-radius: 12px;
  border: 1px solid var(--teal-100);
}
.gauge-value { font-size: 32px; font-weight: 800; color: var(--teal-500); }
.gauge-label { font-size: 10px; color: var(--color-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.no-action-label { font-size: 12px; color: var(--color-muted); margin-bottom: 10px; }
.no-action-reasons { list-style: disc; padding-left: 18px; font-size: 11px; color: var(--color-muted); }
.no-action-reasons li { margin-bottom: 6px; }

/* ========== 监测信号 ========== */
.signal-list { list-style: none; padding: 0; }
.signal-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 0;
  font-size: 11px;
  border-bottom: 1px solid var(--teal-50);
}
.signal-item:last-child { border-bottom: none; }
.signal-priority { font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; flex-shrink: 0; background: var(--teal-100); color: var(--teal-700); }
.signal-item.high .signal-priority { background: #FEE2E2; color: #DC2626; }
.signal-text { color: var(--color-black); line-height: 1.4; }

/* ========== 操作按钮区 ========== */
.panel-actions-bar { margin-top: 8px; }

/* ========== 快捷操作 ========== */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 20px;
}
.quick-action-card {
  background: linear-gradient(135deg, var(--color-white), var(--teal-50));
  border: 1px solid var(--teal-100);
  border-radius: 14px;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.quick-action-card:hover:not(.disabled) {
  border-color: var(--teal-400);
  background: linear-gradient(135deg, var(--color-white), rgba(20, 184, 166, 0.08));
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(20, 184, 166, 0.15);
}
.quick-action-card.disabled { opacity: 0.5; cursor: not-allowed; }
.qa-icon { font-size: 24px; }
.qa-label { font-size: 12px; font-weight: 600; color: var(--teal-600); }

/* ========== 主链路步骤导航 ========== */
.step-nav-bar {
  margin-top: 16px;
  background: linear-gradient(135deg, var(--color-white), var(--teal-50));
  border: 1px solid var(--teal-100);
  border-radius: 14px;
  padding: 12px 14px;
}
.step-nav-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.step-nav-title {
  font-size: 11px;
  font-weight: 700;
  color: var(--teal-500);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.step-nav-branch {
  font-size: 11px;
  font-weight: 600;
  color: var(--teal-700);
  background: rgba(20, 184, 166, 0.08);
  padding: 2px 8px;
  border-radius: 6px;
  margin-left: auto;
}
.step-nav-branch-none {
  color: var(--teal-400);
  background: none;
  font-style: italic;
}
.step-nav-branch-status {
  font-size: 10px;
  font-weight: 700;
  margin-left: 4px;
  padding: 1px 5px;
  border-radius: 4px;
}
.step-nav-branch-status.completed { background: #d1fae5; color: #065f46; }
.step-nav-branch-status.running { background: #dbeafe; color: #1e40af; }
.step-nav-branch-status.preparing { background: #fef3c7; color: #92400e; }
.step-nav-branch-status.created { background: #f1f5f9; color: #64748b; }
.step-nav-branch-status.failed { background: #fee2e2; color: #991b1b; }
.step-nav-branch-status.superseded { background: #f1f5f9; color: #94a3b8; }
.step-nav-btns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.step-nav-btn {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 7px 8px;
  border: 1px solid var(--teal-200);
  border-radius: 8px;
  background: var(--color-white);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.step-nav-btn:hover:not(.disabled) {
  border-color: var(--teal-400);
  background: rgba(20, 184, 166, 0.06);
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(20, 184, 166, 0.12);
}
.step-nav-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.step-nav-num {
  font-size: 10px;
  font-weight: 800;
  color: var(--teal-400);
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.step-nav-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--teal-700);
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Step states */
.step-nav-btn.done {
  background: #d1fae5;
  border-color: #6ee7b7;
}
.step-nav-btn.done .step-nav-num { color: #065f46; }
.step-nav-btn.done .step-nav-name { color: #065f46; }
.step-nav-btn.active {
  background: rgba(20, 184, 166, 0.12);
  border-color: var(--teal-400);
  box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.15);
  animation: step-pulse 2s ease-in-out infinite;
}
.step-nav-btn.active .step-nav-num { color: var(--teal-600); }
.step-nav-btn.active .step-nav-name { color: var(--teal-800); font-weight: 700; }
.step-nav-btn.pending {
  opacity: 0.4;
  cursor: not-allowed;
}
@keyframes step-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.15); }
  50% { box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.25); }
}
.step-nav-check {
  font-size: 10px;
  font-weight: 800;
  color: #065f46;
  margin-left: auto;
}
.step-nav-spinner {
  width: 10px; height: 10px;
  border: 2px solid var(--teal-200);
  border-top-color: var(--teal-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-left: auto;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ========== 事件因果图 ========== */
.causal-graph-section { max-height: 420px; overflow-y: auto; }
.causal-summary {
  font-size: 12px; color: var(--teal-600); font-weight: 600;
  padding: 8px 12px; margin-bottom: 8px;
  background: rgba(20, 184, 166, 0.06); border-radius: 8px;
  line-height: 1.5;
}
.causal-events { position: relative; padding-left: 20px; }
.causal-node {
  position: relative; padding: 0 0 16px 16px; min-height: 40px;
}
.causal-node:last-child { padding-bottom: 0; }
.causal-node-dot {
  position: absolute; left: -20px; top: 4px;
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid var(--teal-300); background: var(--color-white);
  z-index: 2;
}
.causal-node-dot.trigger { background: #ef4444; border-color: #ef4444; }
.causal-node-dot.escalation { background: #f97316; border-color: #f97316; }
.causal-node-dot.response { background: #3b82f6; border-color: #3b82f6; }
.causal-node-dot.mitigation { background: #22c55e; border-color: #22c55e; }
.causal-node-dot.turning_point { background: #a855f7; border-color: #a855f7; }
.causal-node-dot.outcome { background: #6366f1; border-color: #6366f1; }
.causal-node-connector {
  position: absolute; left: -15px; top: 16px; bottom: 0;
  width: 2px; background: var(--teal-200);
}
.causal-node-content {
  background: var(--color-white); border: 1px solid var(--teal-100);
  border-radius: 10px; padding: 10px 12px;
  transition: all 0.2s ease;
}
.causal-node-content:hover {
  border-color: var(--teal-300); box-shadow: 0 3px 12px rgba(20,184,166,0.1);
}
.causal-node-header { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
.causal-time { font-size: 10px; font-weight: 700; color: var(--teal-500); font-family: 'SF Mono', monospace; }
.causal-type-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
  text-transform: uppercase; letter-spacing: 0.3px;
}
.causal-type-badge.trigger { background: rgba(239,68,68,0.12); color: #dc2626; }
.causal-type-badge.escalation { background: rgba(249,115,22,0.12); color: #ea580c; }
.causal-type-badge.response { background: rgba(59,130,246,0.12); color: #2563eb; }
.causal-type-badge.mitigation { background: rgba(34,197,94,0.12); color: #16a34a; }
.causal-type-badge.turning_point { background: rgba(168,85,247,0.12); color: #9333ea; }
.causal-type-badge.outcome { background: rgba(99,102,241,0.12); color: #4f46e5; }
.causal-stage-badge { font-size: 9px; color: var(--color-muted); background: var(--teal-50); padding: 1px 5px; border-radius: 3px; }
.causal-node-title { font-size: 13px; font-weight: 700; color: var(--color-text); line-height: 1.4; }
.causal-node-actor { font-size: 11px; color: var(--teal-500); font-weight: 600; margin-top: 1px; }
.causal-node-desc { font-size: 11px; color: var(--color-muted); line-height: 1.5; margin-top: 4px; }
.causal-edges { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
.causal-edge-tag {
  font-size: 9px; padding: 2px 6px; border-radius: 4px;
  background: rgba(20,184,166,0.08); color: var(--teal-600);
  border: 1px solid var(--teal-100); line-height: 1.3;
}
.causal-edge-tag.triggered { background: rgba(239,68,68,0.06); color: #dc2626; border-color: rgba(239,68,68,0.2); }
.causal-edge-tag.escalated { background: rgba(249,115,22,0.06); color: #ea580c; border-color: rgba(249,115,22,0.2); }
.causal-edge-tag.caused { background: rgba(249,115,22,0.06); color: #ea580c; border-color: rgba(249,115,22,0.2); }
.causal-edge-tag.responded_to { background: rgba(59,130,246,0.06); color: #2563eb; border-color: rgba(59,130,246,0.2); }
.causal-edge-tag.mitigated { background: rgba(34,197,94,0.06); color: #16a34a; border-color: rgba(34,197,94,0.2); }
.causal-edge-tag.led_to { background: rgba(99,102,241,0.06); color: #4f46e5; border-color: rgba(99,102,241,0.2); }

/* ========== 帮助提示 ========== */
.help-tips {
  background: linear-gradient(135deg, var(--teal-50), rgba(20, 184, 166, 0.05));
  border: 1px solid var(--teal-100);
  border-radius: 14px;
  padding: 14px;
  margin-top: 16px;
}
.tip-header { font-size: 12px; font-weight: 700; color: var(--teal-600); margin-bottom: 10px; }
.tip-list { list-style: none; padding: 0; margin: 0; }
.tip-list li { font-size: 11px; color: var(--color-muted); padding: 4px 0; line-height: 1.4; }
.tip-list li::before { content: '\2192 '; color: var(--teal-400); font-weight: bold; }

/* ========== 模态框 ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-box {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  max-width: 420px;
  width: 90%;
  border: 1px solid var(--teal-100);
  box-shadow: 0 20px 40px rgba(20, 184, 166, 0.15);
  opacity: 1;
}
.modal-box h3 { font-size: 16px; color: var(--color-black); margin-bottom: 12px; }
.modal-box p { font-size: 13px; color: var(--color-muted); line-height: 1.6; margin-bottom: 8px; }
.modal-hint { font-size: 11px; color: #94a3b8; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }

/* 追加材料对话框 */
.append-material-modal { max-width: 520px; }
.append-section { margin-bottom: 4px; }
.append-section-header {
  font-size: 13px; font-weight: 600; color: var(--color-black);
  margin-bottom: 8px;
}
.section-desc { font-size: 12px; color: var(--color-muted); margin-bottom: 8px; }
.append-divider {
  display: flex; align-items: center; gap: 12px;
  margin: 14px 0; color: #94a3b8; font-size: 11px;
}
.append-divider::before, .append-divider::after {
  content: ''; flex: 1; height: 1px; background: #e2e8f0;
}
.file-drop-zone {
  border: 2px dashed var(--teal-200); border-radius: 12px;
  padding: 20px 16px; text-align: center; cursor: pointer;
  transition: all 0.2s; background: #fafffe;
}
.file-drop-zone:hover { border-color: var(--teal-400); background: #f0fdfa; }
.file-drop-zone .drop-icon { font-size: 28px; margin-bottom: 4px; }
.file-drop-zone p { font-size: 12px; color: var(--color-muted); margin: 2px 0; }
.file-drop-zone .drop-hint { font-size: 11px; color: #94a3b8; }
.file-list-preview {
  margin-top: 8px; padding: 6px 8px; border-radius: 8px;
  background: #f8fffe; max-height: 100px; overflow-y: auto;
}
.file-preview-item {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 12px; color: var(--color-black); padding: 4px 6px;
  border-bottom: 1px solid #f1f5f9;
}
.file-preview-item:last-child { border-bottom: none; }
.file-remove {
  cursor: pointer; color: #94a3b8; font-size: 16px; line-height: 1;
  padding: 0 4px; border-radius: 4px;
}
.file-remove:hover { color: #ef4444; background: #fef2f2; }
.append-upload-btn { margin-top: 8px; width: 100%; }
.append-done-hint {
  margin-top: 6px; font-size: 12px; color: #059669; font-weight: 500;
}
.web-search-modal .modal-desc { font-size: 13px; color: var(--color-muted); margin-bottom: 16px; }
.web-search-form { display: flex; gap: 8px; margin-bottom: 12px; }
.web-search-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--teal-200);
  border-radius: 10px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  background: #f8fffe;
  color: var(--color-black);
}
.web-search-input:focus { border-color: var(--teal-400); box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1); }
.web-search-input:disabled { opacity: 0.6; }
.web-search-btn { white-space: nowrap; flex-shrink: 0; }
.web-search-error { color: #ef4444; font-size: 12px; margin-bottom: 8px; }
.web-search-result { margin-top: 12px; }
.web-search-success {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: 10px;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  color: #065f46; font-size: 13px; font-weight: 500;
  margin-bottom: 10px;
}
.success-icon { font-size: 16px; color: #10b981; }
.web-search-sources {
  list-style: none; padding: 0; margin: 0;
  max-height: 180px; overflow-y: auto;
}
.web-source-item {
  padding: 6px 10px;
  font-size: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.web-source-item:last-child { border-bottom: none; }
.web-source-link {
  color: var(--teal-600);
  text-decoration: none;
  word-break: break-all;
}
.web-source-link:hover { text-decoration: underline; }
.btn-spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
