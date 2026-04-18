<template>
  <div class="action-card" :class="action.platform">
    <div class="card-header">
      <div class="agent-info">
        <div class="avatar-placeholder">{{ realisticName(action.agent_name)[0] }}</div>
        <span class="agent-name" :title="action.agent_name">{{ realisticName(action.agent_name) }}</span>
      </div>
      <div class="action-badge" :class="getActionTypeClass(action.action_type)">
        {{ getActionTypeLabel(action.action_type) }}
      </div>
    </div>

    <div class="card-body">
      <!-- CREATE_POST -->
      <div v-if="action.action_type === 'CREATE_POST' && action.action_args?.content"
           class="content-text main-text">
        {{ cleanContent(action.action_args.content) }}
      </div>

      <!-- QUOTE_POST -->
      <template v-if="action.action_type === 'QUOTE_POST'">
        <div v-if="action.action_args?.quote_content" class="content-text">
          {{ cleanContent(action.action_args.quote_content) }}
        </div>
        <div v-if="action.action_args?.original_content" class="quoted-block">
          <div class="quote-header">
            <span class="quote-label">@{{ prettifyAuthor(action.action_args.original_author_name) }}</span>
          </div>
          <div class="quote-text">{{ truncate(cleanContent(action.action_args.original_content), 150) }}</div>
        </div>
      </template>

      <!-- REPOST -->
      <template v-if="action.action_type === 'REPOST'">
        <div class="meta-info">
          <span>↻ 转发自 @{{ prettifyAuthor(action.action_args?.original_author_name) }}</span>
        </div>
        <div v-if="action.action_args?.original_content" class="quoted-block">
          {{ truncate(cleanContent(action.action_args.original_content), 180) }}
        </div>
      </template>

      <!-- LIKE_POST / LIKE_COMMENT -->
      <template v-if="action.action_type === 'LIKE_POST' || action.action_type === 'LIKE_COMMENT'">
        <div class="meta-info">
          <span>♡ 点赞 @{{ prettifyAuthor(action.action_args?.post_author_name) }}</span>
        </div>
        <div v-if="action.action_args?.post_content" class="quoted-block mini">
          "{{ truncate(cleanContent(action.action_args.post_content), 100) }}"
        </div>
      </template>

      <!-- CREATE_COMMENT -->
      <template v-if="action.action_type === 'CREATE_COMMENT'">
        <div v-if="action.action_args?.content" class="content-text">
          {{ cleanContent(action.action_args.content) }}
        </div>
        <div v-if="action.action_args?.post_id" class="meta-info dim">
          ↳ 回复帖子 #{{ action.action_args.post_id }}
        </div>
      </template>

      <!-- SEARCH_POSTS -->
      <template v-if="action.action_type === 'SEARCH_POSTS'">
        <div class="meta-info">
          <span>🔍 "{{ action.action_args?.query || '' }}"</span>
        </div>
      </template>

      <!-- FOLLOW -->
      <template v-if="action.action_type === 'FOLLOW'">
        <div class="meta-info">
          <span>+ 关注 @{{ prettifyAuthor(action.action_args?.target_user || action.action_args?.user_id) }}</span>
        </div>
      </template>

      <!-- UPVOTE / DOWNVOTE -->
      <template v-if="action.action_type === 'UPVOTE_POST' || action.action_type === 'DOWNVOTE_POST'">
        <div class="meta-info">
          <span>{{ action.action_type === 'UPVOTE_POST' ? '▲' : '▼' }}
            {{ action.action_type === 'UPVOTE_POST' ? '赞同' : '反对' }}</span>
        </div>
        <div v-if="action.action_args?.post_content" class="quoted-block mini">
          "{{ truncate(cleanContent(action.action_args.post_content), 100) }}"
        </div>
      </template>

      <!-- DO_NOTHING -->
      <template v-if="action.action_type === 'DO_NOTHING'">
        <div class="meta-info dim"><span>∘ 静默</span></div>
      </template>

      <!-- Fallback: unknown type but content available -->
      <div v-if="!KNOWN_TYPES.includes(action.action_type) && action.action_args?.content"
           class="content-text">
        {{ cleanContent(action.action_args.content) }}
      </div>
    </div>

    <div class="card-footer">
      <span class="time-tag">R{{ action.round_num }} · {{ formatTime(action.timestamp) }}</span>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  action: { type: Object, required: true }
})

// ---- 自然化昵称映射 ----
// 图谱实体名 → 社交媒体风格用户名，确定性哈希选取
const NICKNAME_POOL = [
  '珞珈山下的猫', '不喝咖啡会死星人', '今天也在摸鱼', '毕业遥遥无期',
  '图书馆占座侠', '认真生活的小王', '吃瓜第一线', '理性讨论bot',
  '路过的研究生', '实验室蹲守人', '默默围观群众', '社科搬砖工',
  '新传考研人', '法学生不秃头', '隔壁院的同学', '深夜emo选手',
  '数据不会骗人', '较真的旁观者', '爱吃热干面', '珞珈夜跑族',
  '公共事务观察员', '键盘侠已上线', '沉默的大多数', '理工科直男',
  '吐槽小能手', '不想毕业的本科生', '新闻系小林', '教育学研一',
  '学术打工人', '今天截止了吗', '信息素养课代表', '舆情监测实习',
  '文科转码中', '经管小陈', '微博冲浪达人', '知乎答题家',
  '行政楼保安老张', '食堂阿姨视角', '教务处常客', '图书馆流浪汉',
  '投稿被拒第n次', '准备答辩ing', '工学部的风', '凌波门观日',
  '东湖畔散步', '保研边缘人', '选课抢不到', '辅导员说得对',
  '校友回来看看', '退休教授闲聊', '后勤报修达人', '奖学金差0.1',
  '社团会长已疯', '武大兼职群主', '夜猫子自习室', '体测不及格',
  '传媒圈小记者', '央媒实习编辑', '评论区考古学家', '平台治理研究',
]

function _simpleHash(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

// 缓存映射，确保同一 agent_name 始终得到同一昵称
const _nicknameCache = new Map()
let _poolIndex = 0
const _usedIndices = new Set()

function realisticName(raw) {
  if (!raw) return '匿名用户'
  const key = String(raw).trim()
  if (_nicknameCache.has(key)) return _nicknameCache.get(key)

  // 用 hash 选一个未被占用的昵称
  let idx = _simpleHash(key) % NICKNAME_POOL.length
  let attempts = 0
  while (_usedIndices.has(idx) && attempts < NICKNAME_POOL.length) {
    idx = (idx + 1) % NICKNAME_POOL.length
    attempts++
  }

  if (attempts >= NICKNAME_POOL.length) {
    // 池子用完了，加序号
    const fallback = `用户${_poolIndex++}`
    _nicknameCache.set(key, fallback)
    return fallback
  }

  _usedIndices.add(idx)
  const nick = NICKNAME_POOL[idx]
  _nicknameCache.set(key, nick)
  return nick
}

const KNOWN_TYPES = [
  'CREATE_POST', 'QUOTE_POST', 'REPOST', 'LIKE_POST', 'LIKE_COMMENT',
  'CREATE_COMMENT', 'SEARCH_POSTS', 'FOLLOW', 'UPVOTE_POST',
  'DOWNVOTE_POST', 'DO_NOTHING'
]

const ACTION_LABELS = {
  CREATE_POST: '发帖',
  QUOTE_POST: '引用',
  REPOST: '转发',
  LIKE_POST: '点赞',
  LIKE_COMMENT: '点赞',
  CREATE_COMMENT: '评论',
  SEARCH_POSTS: '搜索',
  FOLLOW: '关注',
  UPVOTE_POST: '赞同',
  DOWNVOTE_POST: '反对',
  DO_NOTHING: '静默'
}

const getActionTypeLabel = (type) => ACTION_LABELS[type] || type || '未知'

// ---- 内容系统性清洗 ----
// 处理 LLM 输出的常见污染：MBTI 自我介绍、内部 ID、角色描述泄漏
const MBTI_TYPES = new Set([
  'ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP',
  'ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ'
])

function cleanContent(text) {
  if (!text) return text
  let s = String(text).trim()

  // 1. 移除内部 ID 后缀: xxx_688, yyy_526
  s = s.replace(/_\d{3,4}\b/g, '')

  // 2. 去除英文 "As a(n)/the/someone [自我介绍], I/we/let's..." 前导
  if (/^As (?:an?|the|someone)\b/i.test(s)) {
    const m = s.match(/^As (?:an?|the|someone)\b[\s\S]*?[,;—–]\s*(?=I\s|[Ww]e\s|[Ll]et|[Tt]his\s|[Yy]our\s)/i)
    if (m && m[0].length < s.length * 0.85) {
      s = s.slice(m[0].length)
    }
  }

  // 3. 去除中文 "作为[角色/身份描述]，" 前导
  s = s.replace(/^作为[^。！？\n]{2,80}[，,]\s*/, '')

  // 4. 移除 "MBTI视角：" 模式
  s = s.replace(/\b[EI][NS][TF][JP]\s*视角[：:]\s*/g, '')

  // 5. 移除 "(来自xxx)" 括号信息
  s = s.replace(/[（(]来自[^)）]{2,30}[)）]/g, '')

  // 6. 移除内容中泄漏的原始实体名+ID, 如 "护校蛆来也！" → "来也！"
  //    及 "严欢教授团队" 等非自然名
  s = s.replace(/(?:护校蛆|境外势力|声望悖论|塔西佗陷阱|共振器)\s*/g, '')

  // 7. 清理开头残留标点
  s = s.replace(/^[,;:\s—–\-]+/, '')

  // 8. 英文首字母大写
  if (/^[a-z]/.test(s)) s = s[0].toUpperCase() + s.slice(1)

  return s.trim()
}

const prettifyAuthor = (name) => {
  if (!name) return '用户'
  return realisticName(name)
}

const getActionTypeClass = (type) => {
  const map = {
    CREATE_POST: 'post',
    CREATE_COMMENT: 'comment',
    QUOTE_POST: 'quote',
    REPOST: 'repost',
    LIKE_POST: 'like',
    LIKE_COMMENT: 'like',
    UPVOTE_POST: 'vote-up',
    DOWNVOTE_POST: 'vote-down',
    SEARCH_POSTS: 'search',
    FOLLOW: 'follow',
    DO_NOTHING: 'idle'
  }
  return map[type] || 'generic'
}

const truncate = (s, n) => {
  if (!s) return ''
  const str = String(s)
  return str.length > n ? str.slice(0, n) + '…' : str
}

const formatTime = (ts) => {
  if (!ts) return '—'
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return String(ts).slice(0, 8)
  }
}
</script>

<style scoped>
.action-card {
  background: #18181f;
  border: 1px solid #2a2a33;
  border-left: 3px solid #64748b;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.action-card.twitter { border-left-color: #3b82f6; }
.action-card.reddit { border-left-color: #f97316; }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.agent-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.avatar-placeholder {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.agent-name {
  color: #e5e7eb;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.action-badge {
  background: rgba(255, 255, 255, 0.06);
  color: #94a3b8;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}
.action-badge.post { background: rgba(59, 130, 246, 0.18); color: #93c5fd; }
.action-badge.comment { background: rgba(16, 185, 129, 0.18); color: #6ee7b7; }
.action-badge.like { background: rgba(239, 68, 68, 0.18); color: #fca5a5; }
.action-badge.quote,
.action-badge.repost { background: rgba(168, 85, 247, 0.18); color: #d8b4fe; }
.action-badge.vote-up { background: rgba(34, 197, 94, 0.18); color: #86efac; }
.action-badge.vote-down { background: rgba(249, 115, 22, 0.18); color: #fdba74; }
.action-badge.idle { background: rgba(148, 163, 184, 0.12); color: #94a3b8; }

.card-body {
  font-size: 13px;
  line-height: 1.45;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.content-text { color: #f1f5f9; }
.content-text.main-text { font-weight: 500; }

.quoted-block {
  background: rgba(255, 255, 255, 0.03);
  border-left: 2px solid #2a2a33;
  padding: 6px 10px;
  font-size: 12px;
  color: #cbd5e1;
  border-radius: 0 4px 4px 0;
}
.quoted-block.mini { font-size: 11px; color: #94a3b8; }
.quote-header {
  font-size: 10px;
  color: #60a5fa;
  margin-bottom: 2px;
  font-weight: 600;
}
.quote-text { color: #cbd5e1; }

.meta-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #cbd5e1;
  font-size: 12px;
}
.meta-info.dim { color: #64748b; font-size: 11px; }

.card-footer {
  border-top: 1px solid #22222a;
  padding-top: 5px;
  display: flex;
  justify-content: flex-end;
}
.time-tag {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
  color: #64748b;
  letter-spacing: 0.05em;
}
</style>
