import service, { requestWithRetry } from './index'

const SIM_API = '/api/simulation'
const simUrl = (path) => `${SIM_API}${path}`
const getSim = (path, params) => service.get(simUrl(path), params ? { params } : undefined)
const postSim = (path, data, config) => service.post(simUrl(path), data, config)
const deleteSim = (path) => service.delete(simUrl(path))
const retryPost = (path, data, retries = 3, delay = 1000, config) => {
  return requestWithRetry(() => postSim(path, data, config), retries, delay)
}

export const createSimulation = (data) => retryPost('/create', data)

export const prepareSimulation = (data) => retryPost('/prepare', data)

export const getPrepareStatus = (data) => postSim('/prepare/status', data)

export const getSimulation = (simulationId) => getSim(`/${simulationId}`)

export const deleteSimulation = (simulationId) => deleteSim(`/${simulationId}`)

export const getSimulationProfiles = (simulationId, platform = 'reddit') => {
  return getSim(`/${simulationId}/profiles`, { platform })
}

export const getSimulationProfilesRealtime = (simulationId, platform = 'reddit') => {
  return getSim(`/${simulationId}/profiles/realtime`, { platform })
}

export const getSimulationConfig = (simulationId) => getSim(`/${simulationId}/config`)

export const getSimulationConfigRealtime = (simulationId) => {
  return getSim(`/${simulationId}/config/realtime`)
}

export const listSimulations = (projectId) => {
  return getSim('/list', projectId ? { project_id: projectId } : {})
}

export const startSimulation = (data) => retryPost('/start', data)

export const stopSimulation = (data) => postSim('/stop', data)

export const getRunStatus = (simulationId) => getSim(`/${simulationId}/run-status`)

export const getRunStatusDetail = (simulationId) => getSim(`/${simulationId}/run-status/detail`)

export const getWorldState = (simulationId, params = {}) => {
  return getSim(`/${simulationId}/world-state`, params)
}

export const getWorldEvents = (simulationId, params = {}) => {
  return getSim(`/${simulationId}/events`, params)
}

export const getCausalGraph = (simulationId, params = {}) => {
  return getSim(`/${simulationId}/causal-graph`, params)
}

export const getSimulationPosts = (simulationId, platform = 'reddit', limit = 50, offset = 0) => {
  return getSim(`/${simulationId}/posts`, { platform, limit, offset })
}

export const getSimulationTimeline = (simulationId, startRound = 0, endRound = null) => {
  const params = { start_round: startRound }
  if (endRound !== null) params.end_round = endRound
  return getSim(`/${simulationId}/timeline`, params)
}

export const getAgentStats = (simulationId) => getSim(`/${simulationId}/agent-stats`)

export const getSimulationActions = (simulationId, params = {}) => {
  return getSim(`/${simulationId}/actions`, params)
}

export const injectEvent = (data) => postSim('/inject-event', data)

export const closeSimulationEnv = (data) => postSim('/close-env', data)

export const getEnvStatus = (data) => postSim('/env-status', data)

export const interviewAgents = (data) => {
  return retryPost('/interview/batch', data, 2, 1000, { timeout: 60000 })
}

export const interviewAgentOffline = (data) => {
  return retryPost('/interview/offline', data, 2, 1000, { timeout: 60000 })
}

export const getSimGraph = (simulationId, params = {}) => {
  return getSim(`/${simulationId}/sim-graph`, params)
}

export const getSimulationHistory = (limit = 20) => {
  return getSim('/history', { limit })
}
