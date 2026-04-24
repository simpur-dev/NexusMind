import service from './index'

/**
 * 获取完整评估报告
 * @param {string} simulationId
 */
export const getEvaluationReport = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/report`)
}

/**
 * 获取情感时序数据
 * @param {string} simulationId
 */
export const getSentimentTimeline = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/sentiment`)
}

/**
 * 获取行为多样性指标
 * @param {string} simulationId
 */
export const getBehaviorDiversity = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/diversity`)
}

/**
 * 获取世界状态演化
 * @param {string} simulationId
 */
export const getStateEvolution = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/state-evolution`)
}

/**
 * 获取影响力分析
 * @param {string} simulationId
 */
export const getInfluenceAnalysis = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/influence`)
}

/**
 * 获取 Benchmark 三级评分（Tier A/B/C）
 * @param {string} simulationId
 */
export const getBenchmarkScores = (simulationId) => {
  return service.get(`/api/evaluation/${simulationId}/benchmark`)
}

/**
 * 列出所有可评估的模拟
 */
export const listEvaluableSimulations = () => {
  return service.get('/api/evaluation/simulations')
}
