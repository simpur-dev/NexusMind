import service, { requestWithRetry } from './index'

const GRAPH_API = '/api/graph'
const graphUrl = (path) => `${GRAPH_API}${path}`
const getGraph = (path) => service.get(graphUrl(path))
const postGraph = (path, data, config) => service({ url: graphUrl(path), method: 'post', data, ...config })
const postGraphRetry = (path, data, config) => requestWithRetry(() => postGraph(path, data, config))

/**
 * Graph API wrapper
 */
export function generateOntology(formData) {
  return postGraphRetry('/ontology/generate', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * Graph API wrapper
 */
export function generateOntologyFromWeb(data) {
  return postGraphRetry('/ontology/generate-from-web', data)
}

/**
 * Graph API wrapper
 */
export function buildGraph(data) {
  return postGraphRetry('/build', data)
}

/**
 * Graph API wrapper
 */
export function getTaskStatus(taskId) {
  return getGraph(`/task/${taskId}`)
}

/**
 * Graph API wrapper
 */
export function getGraphData(graphId) {
  return getGraph(`/data/${graphId}`)
}

/**
 * Graph API wrapper
 */
export function getProject(projectId) {
  return getGraph(`/project/${projectId}`)
}
