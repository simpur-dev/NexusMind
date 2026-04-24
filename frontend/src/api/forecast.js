import service, { requestWithRetry } from './index'

// ============================================================
// 预测分支生命周期
// ============================================================

/**
 * 创建预测分支（同时创建底层 Simulation）
 * @param {Object} data - { project_id, baseline_id, branch_type?, branch_label?, parent_run_id?, forecast_horizon_hours?, intervention_plan? }
 */
export const createForecastRun = (data) => {
  return requestWithRetry(() =>
    service.post('/api/forecast/run/create', data)
  )
}

/**
 * 准备预测分支的模拟环境
 * @param {string} runId
 * @param {Object} data - { entity_types?, use_llm_for_profiles?, parallel_profile_count?, force_regenerate? }
 */
export const prepareForecastRun = (runId, data = {}) => {
  return requestWithRetry(() =>
    service.post(`/api/forecast/run/${runId}/prepare`, data)
  )
}

/**
 * 启动预测分支模拟运行
 * @param {string} runId
 * @param {Object} data - { platform?, max_rounds?, enable_graph_memory_update?, force?, resume? }
 */
export const startForecastRun = (runId, data = {}) => {
  return requestWithRetry(() =>
    service.post(`/api/forecast/run/${runId}/start`, data)
  )
}

/**
 * 现实校准：基于新基线创建校准后的预测分支
 * @param {string} runId
 * @param {Object} data - { new_baseline_id, branch_label? }
 */
export const recalibrateForecastRun = (runId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/forecast/run/${runId}/recalibrate`, data)
  )
}

/**
 * 获取预测分支运行状态
 * @param {string} runId
 */
export const getForecastRunStatus = (runId) => {
  return service.get(`/api/forecast/run/${runId}/status`)
}

// ============================================================
// 分支对比
// ============================================================

/**
 * 对比多个预测分支
 * @param {Object} data - { project_id, run_ids: [...] }
 */
export const compareForecastRuns = (data) => {
  return service.post('/api/forecast/compare', data)
}

// ============================================================
// 干预动作模板 & 决策简报
// ============================================================

/**
 * 获取全部干预动作模板
 */
export const listInterventionTemplates = () => {
  return service.get('/api/forecast/interventions')
}

/**
 * 评估一组干预动作对预测分支的组合效果
 * @param {string} runId
 * @param {Object} data - { action_ids: [...] }
 */
export const evaluateInterventions = (runId, data) => {
  return service.post(`/api/forecast/run/${runId}/evaluate-interventions`, data)
}

/**
 * 获取结构化决策简报
 * @param {string} runId
 */
export const getDecisionBrief = (runId, params = {}) => {
  return service.get(`/api/forecast/run/${runId}/decision-brief`, { params })
}

/**
 * 推荐最合适的 Top-N 干预动作
 * @param {string} runId
 * @param {number} maxResults
 */
export const recommendActions = (runId, maxResults = 3) => {
  return service.get(`/api/forecast/run/${runId}/recommend-actions`, { params: { max_results: maxResults } })
}
