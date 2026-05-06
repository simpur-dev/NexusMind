import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
const DEFAULT_TIMEOUT = 300000

const unwrapResponse = (response) => {
  const payload = response.data
  if (payload && payload.success === false) {
    throw new Error(payload.error || payload.message || 'API request failed')
  }
  return payload
}

const normalizeRequestError = (error) => {
  const message = error?.response?.data?.error ||
    error?.response?.data?.message ||
    error?.message ||
    'Network request failed'
  const normalized = new Error(message)
  normalized.cause = error
  normalized.status = error?.response?.status
  normalized.code = error?.code
  return normalized
}

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))

// 创建axios实例
const service = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => config,
  error => {
    return Promise.reject(normalizeRequestError(error))
  }
)

// 响应拦截器（容错重试机制）
service.interceptors.response.use(
  response => unwrapResponse(response),
  error => {
    return Promise.reject(normalizeRequestError(error))
  }
)

// 带重试的请求函数
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  let lastError
  const attempts = Math.max(1, maxRetries)
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      return await requestFn()
    } catch (error) {
      lastError = error
      if (attempt + 1 >= attempts) break
      await wait(delay * (2 ** attempt))
    }
  }
  throw lastError
}

export default service
