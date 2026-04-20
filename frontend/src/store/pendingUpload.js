/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 * 
 * 支持两种模式：
 *   - "file"：用户上传文件作为种子材料
 *   - "web"：用户输入关键词，自动网络搜索作为种子材料
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  isPending: false,
  mode: 'file',   // "file" | "web"
  webQuery: '',    // 网络搜索关键词（mode=web 时使用）
})

export function setPendingUpload(files, requirement) {
  state.files = files
  state.simulationRequirement = requirement
  state.isPending = true
  state.mode = 'file'
  state.webQuery = ''
}

export function setPendingWebSearch(query, requirement) {
  state.files = []
  state.simulationRequirement = requirement
  state.isPending = true
  state.mode = 'web'
  state.webQuery = query
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    isPending: state.isPending,
    mode: state.mode,
    webQuery: state.webQuery,
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.isPending = false
  state.mode = 'file'
  state.webQuery = ''
}

export default state
