import service, { requestWithRetry } from './index'

const REPORT_API = '/api/report'
const reportUrl = (path) => `${REPORT_API}${path}`
const getReportApi = (path, params) => service.get(reportUrl(path), params ? { params } : undefined)
const postReportApi = (path, data, config) => service.post(reportUrl(path), data, config)
const postReportRetry = (path, data, retries = 3, delay = 1000, config) => {
  return requestWithRetry(() => postReportApi(path, data, config), retries, delay)
}

/**
 * Report API wrapper
 */
export const generateReport = (data) => {
  return postReportRetry('/generate', data)
}

/**
 * Report API wrapper
 */
export const getReportStatus = (reportId) => {
  return getReportApi('/generate/status', { report_id: reportId })
}

/**
 * Report API wrapper
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return getReportApi(`/${reportId}/agent-log`, { from_line: fromLine })
}

/**
 * Report API wrapper
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return getReportApi(`/${reportId}/console-log`, { from_line: fromLine })
}

/**
 * Report API wrapper
 */
export const getReport = (reportId) => {
  return getReportApi(`/${reportId}`)
}

/**
 * Report API wrapper
 */
export const getReportSections = (reportId) => {
  return getReportApi(`/${reportId}/sections`)
}

/**
 * Report API wrapper
 */
export const chatWithReport = (data) => {
  return postReportRetry('/chat', data, 2, 1000, { timeout: 60000 })
}
