import service, { requestWithRetry } from './index'

// ============================================================
// 材料管理
// ============================================================

/**
 * 向项目追加文件类型的种子材料
 * @param {string} projectId
 * @param {FormData} formData - 含 files 字段
 */
export const appendMaterialFiles = (projectId, formData) => {
  return requestWithRetry(() =>
    service({
      url: `/api/incident/project/${projectId}/materials/append`,
      method: 'post',
      data: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  )
}

/**
 * 向项目追加手工文本类型的种子材料
 * @param {string} projectId
 * @param {Object} data - { title, text, source_type?, source_url?, source_time?, credibility?, tags? }
 */
export const appendMaterialText = (projectId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/materials/append`, data)
  )
}

/**
 * 通过网络搜索抓取内容作为种子材料追加
 * @param {string} projectId
 * @param {Object} data - { query, max_results? }
 */
export const appendMaterialFromWeb = (projectId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/materials/append-web`, data)
  )
}

/**
 * 获取项目材料时间线
 * @param {string} projectId
 */
export const listMaterials = (projectId) => {
  return service.get(`/api/incident/project/${projectId}/materials`)
}

/**
 * 获取单条材料详情
 * @param {string} projectId
 * @param {string} materialId
 */
export const getMaterial = (projectId, materialId) => {
  return service.get(`/api/incident/project/${projectId}/materials/${materialId}`)
}

// ============================================================
// 基线管理
// ============================================================

/**
 * 重建事实基线
 * @param {string} projectId
 * @param {Object} data - { material_ids?, current_stage?, confirmed_facts?, ... }
 */
export const rebuildBaseline = (projectId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/baseline/rebuild`, data)
  )
}

/**
 * 获取当前基线
 * @param {string} projectId
 */
export const getCurrentBaseline = (projectId) => {
  return service.get(`/api/incident/project/${projectId}/baseline/current`)
}

/**
 * 获取历史基线版本列表
 * @param {string} projectId
 */
export const listBaselines = (projectId) => {
  return service.get(`/api/incident/project/${projectId}/baseline/history`)
}

/**
 * 对比两个基线版本
 * @param {string} projectId
 * @param {Object} data - { baseline_a, baseline_b }
 */
export const diffBaselines = (projectId, data) => {
  return service.post(`/api/incident/project/${projectId}/baseline/diff`, data)
}

/**
 * 删除指定基线版本
 * @param {string} projectId
 * @param {string} baselineId
 */
export const deleteBaseline = (projectId, baselineId) => {
  return service.delete(`/api/incident/project/${projectId}/baseline/${baselineId}`)
}

/**
 * 为指定基线单独重建图谱
 * @param {string} projectId
 * @param {string} baselineId
 */
export const rebuildBaselineGraph = (projectId, baselineId) => {
  return service.post(`/api/incident/project/${projectId}/baseline/${baselineId}/rebuild-graph`)
}

/**
 * 获取事件因果图
 * @param {string} projectId
 * @param {string} baselineId - 可选，默认使用当前基线
 */
export const getCausalGraph = (projectId, baselineId) => {
  const params = baselineId ? { baseline_id: baselineId } : {}
  return service.get(`/api/incident/project/${projectId}/causal-graph`, { params })
}

// ============================================================
// 预测分支管理
// ============================================================

/**
 * 创建预测分支
 * @param {string} projectId
 * @param {Object} data - { baseline_id, branch_type?, branch_label?, parent_run_id?, forecast_horizon_hours?, intervention_plan? }
 */
export const createForecastRun = (projectId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/forecast/create`, data)
  )
}

/**
 * 列出项目下所有预测分支
 * @param {string} projectId
 */
export const listForecastRuns = (projectId) => {
  return service.get(`/api/incident/project/${projectId}/forecast/list`)
}

/**
 * 获取单个预测分支详情
 * @param {string} projectId
 * @param {string} runId
 */
export const getForecastRun = (projectId, runId) => {
  return service.get(`/api/incident/project/${projectId}/forecast/${runId}`)
}

/**
 * 删除指定预测分支
 * @param {string} projectId
 * @param {string} runId
 */
export const deleteForecastRun = (projectId, runId) => {
  return service.delete(`/api/incident/project/${projectId}/forecast/${runId}`)
}

/**
 * 对比多个预测分支
 * @param {string} projectId
 * @param {Object} data - { run_ids: [...] }
 */
export const compareForecastRuns = (projectId, data) => {
  return service.post(`/api/incident/project/${projectId}/forecast/compare`, data)
}

// ============================================================
// 自动引导
// ============================================================

/**
 * 自动将项目已有的 extracted_text 导入为初始材料
 * @param {string} projectId
 */
export const autoBootstrapMaterials = (projectId) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/bootstrap`)
  )
}

// ============================================================
// 工作台概览
// ============================================================

/**
 * 获取项目工作台概览
 * @param {string} projectId
 */
export const getProjectOverview = (projectId) => {
  return service.get(`/api/incident/project/${projectId}/overview`)
}

/**
 * 向项目追加网络抓取材料
 * @param {string} projectId
 * @param {Object} data - { query, ... }
 */
export const appendMaterialFromWeb = (projectId, data) => {
  return requestWithRetry(() =>
    service.post(`/api/incident/project/${projectId}/materials/append-web`, data)
  )
}

/**
 * 获取因果图谱
 * @param {string} projectId
 * @param {string} baselineId
 */
export const getCausalGraph = (projectId, baselineId) => {
  return service.get(`/api/incident/project/${projectId}/baseline/${baselineId}/causal-graph`)
}

/**
 * 删除预测分支
 * @param {string} projectId
 * @param {string} runId
 */
export const deleteForecastRun = (projectId, runId) => {
  return service.delete(`/api/incident/project/${projectId}/forecast/${runId}`)
}

export const rebuildBaselineGraph = (projectId, baselineId) => {
  return requestWithRetry(() =>
    service.post('/api/graph/build', {
      project_id: projectId,
    })
  )
}
