<template>
  <div class="action-card-wrapper">
    <!-- ====== Twitter 风格 ====== -->
    <div v-if="action.platform === 'twitter'" class="tweet-card">
      <div class="tweet-avatar" :style="{ background: avatarGradient }">
        {{ realisticName(action.agent_name)[0] }}
      </div>
      <div class="tweet-main">
        <div class="tweet-header">
          <span class="tweet-name">{{ realisticName(action.agent_name, action) }}</span>
          <span class="tweet-handle">@{{ handleName(action.agent_name) }}</span>
          <span class="tweet-dot">·</span>
          <span class="tweet-time">R{{ action.round_num }}</span>
          <span class="tweet-badge" :class="getActionTypeClass(action.action_type)">{{ getActionTypeLabel(action.action_type) }}</span>
        </div>
        <div class="tweet-body">
          <!-- 有内容的类型：发帖/引用/转发 -->
          <template v-if="hasContent">
            <!-- REPOST: 显示转发标记 + 原帖引用块 -->
            <template v-if="action.action_type === 'REPOST'">
              <div class="tweet-repost-tag">↻ 转发</div>
              <div class="tweet-quote">
                <span v-if="prettifyAuthor(action.action_args?.original_author_name)" class="tq-author">@{{ prettifyAuthor(action.action_args.original_author_name) }}</span>
                <span class="tq-text">{{ expanded ? fullText : collapsedText }}</span>
              </div>
              <button v-if="needsFold" class="fold-btn" @click.stop="expanded = !expanded">
                {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
              </button>
            </template>
            <!-- QUOTE: 自己的内容 + 原帖引用块 -->
            <template v-else-if="action.action_type === 'QUOTE_POST'">
              <p class="tweet-text">{{ expanded ? fullText : collapsedText }}</p>
              <button v-if="needsFold" class="fold-btn" @click.stop="expanded = !expanded">
                {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
              </button>
              <div v-if="action.action_args?.original_content" class="tweet-quote">
                <span v-if="prettifyAuthor(action.action_args?.original_author_name)" class="tq-author">@{{ prettifyAuthor(action.action_args.original_author_name) }}</span>
                <span class="tq-text">{{ truncate(cleanContent(action.action_args.original_content), 100) }}</span>
              </div>
            </template>
            <!-- 普通发帖/评论 -->
            <template v-else>
              <p class="tweet-text">{{ expanded ? fullText : collapsedText }}</p>
              <button v-if="needsFold" class="fold-btn" @click.stop="expanded = !expanded">
                {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
              </button>
            </template>
          </template>
          <!-- 轻量操作 -->
          <template v-else>
            <div v-if="action.action_type === 'LIKE_POST' || action.action_type === 'LIKE_COMMENT'" class="tweet-action-line"><span class="heart">♥</span> 赞了 <b v-if="prettifyAuthor(action.action_args?.post_author_name)">@{{ prettifyAuthor(action.action_args.post_author_name) }}</b><span v-else>一条动态</span></div>
            <div v-else-if="action.action_type === 'FOLLOW'" class="tweet-action-line">关注了 <b>@{{ prettifyAuthor(action.action_args?.target_user || action.action_args?.user_id) || '某用户' }}</b></div>
            <div v-else-if="action.action_type === 'SEARCH_POSTS'" class="tweet-action-line">🔍 "{{ action.action_args?.query || '' }}"</div>
            <div v-else-if="action.action_type === 'SEARCH_USER'" class="tweet-action-line">🔍 查找用户</div>
            <div v-else-if="action.action_type === 'UPVOTE_POST' || action.action_type === 'DOWNVOTE_POST' || action.action_type === 'DISLIKE_POST'" class="tweet-action-line">{{ action.action_type === 'UPVOTE_POST' ? '👍' : '👎' }} {{ getActionTypeLabel(action.action_type) }}</div>
            <div v-else-if="action.action_type === 'TREND'" class="tweet-action-line">📈 浏览热门</div>
            <div v-else-if="action.action_type === 'DO_NOTHING'" class="tweet-action-line dim">💤 静默</div>
            <div v-else class="tweet-action-line dim">{{ getActionTypeLabel(action.action_type) }}</div>
          </template>
        </div>
        <!-- 只有有内容的卡片才显示底部操作栏 -->
        <div v-if="hasContent" class="tweet-foot">
          <span class="tf-btn">💬</span>
          <span class="tf-btn">🔁</span>
          <span class="tf-btn">♡</span>
          <span class="tf-btn">↗</span>
        </div>
      </div>
    </div>

    <!-- ====== Reddit 完整卡片 ====== -->
    <div v-else-if="isRedditFullCard" class="reddit-card">
      <div class="reddit-votes">
        <span class="vote-arrow up" :class="{ active: action.action_type === 'UPVOTE_POST' }">▲</span>
        <span class="vote-score">{{ randomScore(action) }}</span>
        <span class="vote-arrow down" :class="{ active: action.action_type === 'DOWNVOTE_POST' }">▼</span>
      </div>
      <div class="reddit-main">
        <div class="reddit-meta">
          <span class="reddit-sub">r/{{ subRedditFor(action) }}</span>
          <span class="reddit-sep">·</span>
          <span class="reddit-author">u/{{ realisticName(action.agent_name, action) }}</span>
          <span class="reddit-sep">·</span>
          <span class="reddit-time">R{{ action.round_num }}</span>
          <span class="reddit-badge" :class="getActionTypeClass(action.action_type)">{{ getActionTypeLabel(action.action_type) }}</span>
        </div>
        <div class="reddit-body">
          <!-- REPOST -->
          <template v-if="action.action_type === 'REPOST'">
            <div class="reddit-repost-tag">⟳ 转帖</div>
            <div class="reddit-quote-block">
              <span v-if="prettifyAuthor(action.action_args?.original_author_name)" class="rq-author">u/{{ prettifyAuthor(action.action_args.original_author_name) }}</span>
              <span class="rq-text">{{ expanded ? fullText : collapsedText }}</span>
            </div>
            <button v-if="needsFold" class="fold-btn reddit-fold" @click.stop="expanded = !expanded">
              {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
            </button>
          </template>
          <!-- QUOTE -->
          <template v-else-if="action.action_type === 'QUOTE_POST'">
            <p class="reddit-text">{{ expanded ? fullText : collapsedText }}</p>
            <button v-if="needsFold" class="fold-btn reddit-fold" @click.stop="expanded = !expanded">
              {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
            </button>
            <div v-if="action.action_args?.original_content" class="reddit-quote-block">
              <span v-if="prettifyAuthor(action.action_args?.original_author_name)" class="rq-author">u/{{ prettifyAuthor(action.action_args.original_author_name) }}</span>
              <span class="rq-text">{{ truncate(cleanContent(action.action_args.original_content), 100) }}</span>
            </div>
          </template>
          <!-- 普通发帖/评论 -->
          <template v-else>
            <p class="reddit-text" :class="{ 'comment-style': action.action_type === 'CREATE_COMMENT' }">
              {{ expanded ? fullText : collapsedText }}
            </p>
            <button v-if="needsFold" class="fold-btn reddit-fold" @click.stop="expanded = !expanded">
              {{ expanded ? '收起 ▴' : '展开全文 ▾' }}
            </button>
          </template>
        </div>
        <div class="reddit-foot">
          <span class="rf-btn">💬 评论</span>
          <span class="rf-btn">↗ 分享</span>
          <span class="rf-btn">⚑ 收藏</span>
        </div>
      </div>
    </div>

    <!-- ====== Reddit 紧凑 mini-card ====== -->
    <div v-else class="reddit-mini" :class="getActionTypeClass(action.action_type)">
      <span class="rm-icon">{{ miniIcon }}</span>
      <span class="rm-user">{{ realisticName(action.agent_name, action) }}</span>
      <span class="rm-desc">
        <template v-if="action.action_type === 'LIKE_POST' || action.action_type === 'LIKE_COMMENT'">赞了 <b v-if="prettifyAuthor(action.action_args?.post_author_name)">{{ prettifyAuthor(action.action_args.post_author_name) }}</b><span v-else>一篇帖子</span></template>
        <template v-else-if="action.action_type === 'UPVOTE_POST'">赞同了一篇帖子</template>
        <template v-else-if="action.action_type === 'DOWNVOTE_POST'">反对了一篇帖子</template>
        <template v-else-if="action.action_type === 'DISLIKE_POST'">踩了一篇帖子</template>
        <template v-else-if="action.action_type === 'SEARCH_POSTS'">搜索 "{{ truncate(action.action_args?.query || '', 20) }}"</template>
        <template v-else-if="action.action_type === 'SEARCH_USER'">查找用户</template>
        <template v-else-if="action.action_type === 'FOLLOW'">关注了 {{ prettifyAuthor(action.action_args?.target_user || action.action_args?.user_id) || '某用户' }}</template>
        <template v-else-if="action.action_type === 'TREND'">浏览热门话题</template>
        <template v-else-if="action.action_type === 'DO_NOTHING'">静默浏览</template>
        <template v-else>{{ getActionTypeLabel(action.action_type) }}</template>
      </span>
      <span class="rm-round">R{{ action.round_num }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  action: { type: Object, required: true }
})

const FOLD_LIMIT = 120

const expanded = ref(false)

const fullText = computed(() => {
  const a = props.action
  const args = a.action_args || {}
  const raw = args.content || args.quote_content || args.original_content || ''
  return cleanContent(raw)
})

const hasContent = computed(() => {
  const t = props.action.action_type
  const hasText = !!fullText.value
  return hasText && ['CREATE_POST', 'CREATE_COMMENT', 'QUOTE_POST', 'REPOST'].includes(t)
})

const needsFold = computed(() => fullText.value.length > FOLD_LIMIT)

const collapsedText = computed(() => {
  if (!needsFold.value) return fullText.value
  return fullText.value.slice(0, FOLD_LIMIT) + '…'
})

const MINI_ICONS = {
  LIKE_POST: '♥', LIKE_COMMENT: '♥',
  UPVOTE_POST: '▲', DOWNVOTE_POST: '▼', DISLIKE_POST: '👎',
  SEARCH_POSTS: '🔍', SEARCH_USER: '🔍',
  FOLLOW: '➕', TREND: '📈', DO_NOTHING: '💤'
}
const miniIcon = computed(() => MINI_ICONS[props.action.action_type] || '•')

// Avatar gradient based on agent name hash
const GRADIENTS = [
  'linear-gradient(135deg, #3b82f6, #8b5cf6)',
  'linear-gradient(135deg, #6366f1, #ec4899)',
  'linear-gradient(135deg, #f59e0b, #ef4444)',
  'linear-gradient(135deg, #10b981, #3b82f6)',
  'linear-gradient(135deg, #8b5cf6, #06b6d4)',
  'linear-gradient(135deg, #ec4899, #f97316)',
  'linear-gradient(135deg, #14b8a6, #a855f7)',
  'linear-gradient(135deg, #f43e5c, #f59e0b)',
]
const avatarGradient = computed(() => {
  const h = _simpleHash(props.action.agent_name || '')
  return GRADIENTS[h % GRADIENTS.length]
})

function handleName(raw) {
  const nick = realisticName(raw)
  return nick.replace(/\s/g, '_').slice(0, 10)
}

function randomScore(action) {
  const h = _simpleHash((action.agent_name || '') + (action.timestamp || '') + (action.round_num || 0))
  return (h % 120) + 1
}

// ============== 角色识别：机构 / 媒体 / 普通用户 ==============
// 以前把所有 agent 都换成休闲昵称，导致官方通报被贴上 r/年轻人说
const INSTITUTIONAL_KEYWORDS = [
  '学会', '委员会', '协会', '学术', '官方', '秘书处', '公告',
  '通报', '教育部', '纪委', '部门', '研究院', '学院', '高校',
  '学术道德', '主管', '处置', '决定', '发布【'
]
const MEDIA_KEYWORDS = [
  '媒体', '报道', '记者', '新闻', '央视', '人民日报', '新华',
  '日报', '通讯社', '时报', '编辑部', '中国教育报', '接访'
]

function _detectRole(rawName, sampleText) {
  const corpus = (rawName || '') + ' ' + (sampleText || '')
  if (INSTITUTIONAL_KEYWORDS.some(kw => corpus.includes(kw))) return 'institutional'
  if (MEDIA_KEYWORDS.some(kw => corpus.includes(kw))) return 'media'
  return 'casual'
}

// 子版块按角色分池，避免 学术通报被随机贴到 r/围观瓜田
const SUB_POOLS = {
  institutional: ['学术圈', '高校事', '制度与治理', '院校动态', '公共议题', '教育圈'],
  media: ['媒体报道', '今日热话', '社会热点', '舆情现场'],
  casual: ['校园观察', '围观瓜田', '理性讨论', '年轻人说', '在校生活', '今日热话']
}

function subRedditFor(action) {
  // 优先看当前贴文本身的调性，同一 agent 不同贴可以发在不同子版
  const text = (action.action_args?.content || action.action_args?.original_content || '')
  const role = _detectRole(action.agent_name, text)
  const pool = SUB_POOLS[role]
  const key = (action.agent_name || '') + '|' + (action.action_type || '') + '|' + role
  return pool[_simpleHash(key) % pool.length]
}

// ---- 自然化昵称映射 ----
// 图谱实体名 → 社交媒体风格用户名，确定性哈希选取
// 机构/媒体走独立名池，保证官方贴看起来是官方账号
const INSTITUTIONAL_NAME_POOL = [
  '学术道德委员会', '学术伦理处', '高校联合会', '教育研究院',
  '委员会秘书处', '学术传播部', '官方发布', '院校公告号',
  '学位委员会', '纪委监委', '研究生院', '高教动态'
]
const MEDIA_NAME_POOL = [
  '中青报记者', '人民日报评论', '新华社记者', '教育报编辑',
  '全媒体观察', '新闻手记', '舆情分析师', '财经记者小陈'
]
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

// 按角色从对应的池选名，保证同一 agent 始终只对应一个名字
function _pickFromPool(key, pool, usedSet) {
  let idx = _simpleHash(key) % pool.length
  let attempts = 0
  while (usedSet.has(idx) && attempts < pool.length) {
    idx = (idx + 1) % pool.length
    attempts++
  }
  if (attempts >= pool.length) return null
  usedSet.add(idx)
  return pool[idx]
}
const _institUsed = new Set()
const _mediaUsed = new Set()

function realisticName(raw, action) {
  if (!raw) return '匿名用户'
  const key = String(raw).trim()
  if (_nicknameCache.has(key)) return _nicknameCache.get(key)

  // 根据 agent_name + 当前贴文本识别角色，并选对应名池
  const sampleText = action ? (action.action_args?.content || action.action_args?.original_content || '') : ''
  const role = _detectRole(key, sampleText)

  let nick = null
  if (role === 'institutional') {
    nick = _pickFromPool(key, INSTITUTIONAL_NAME_POOL, _institUsed)
  } else if (role === 'media') {
    nick = _pickFromPool(key, MEDIA_NAME_POOL, _mediaUsed)
  }
  if (!nick) {
    nick = _pickFromPool(key, NICKNAME_POOL, _usedIndices)
  }
  if (!nick) {
    nick = `用户${_poolIndex++}`
  }
  _nicknameCache.set(key, nick)
  return nick
}

// Reddit full-card types (have real text content)
const REDDIT_FULL_TYPES = new Set([
  'CREATE_POST', 'CREATE_COMMENT', 'QUOTE_POST', 'REPOST'
])
const isRedditFullCard = computed(() => {
  if (props.action.platform === 'twitter') return false
  const args = props.action.action_args || {}
  return REDDIT_FULL_TYPES.has(props.action.action_type) && (args.content || args.original_content || args.quote_content)
})

const ACTION_LABELS = {
  CREATE_POST: '发帖',
  QUOTE_POST: '引用',
  REPOST: '转发',
  LIKE_POST: '点赞',
  LIKE_COMMENT: '点赞',
  CREATE_COMMENT: '评论',
  SEARCH_POSTS: '搜索',
  SEARCH_USER: '查人',
  FOLLOW: '关注',
  UPVOTE_POST: '赞同',
  DOWNVOTE_POST: '反对',
  DISLIKE_POST: '踩',
  TREND: '热搜',
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
  if (!name || name === 'None' || name === 'null' || name === 'undefined') return null
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
    DISLIKE_POST: 'vote-down',
    SEARCH_POSTS: 'search',
    SEARCH_USER: 'search',
    FOLLOW: 'follow',
    TREND: 'search',
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
/* ============ 通用 ============ */
.action-card-wrapper { width: 100%; }

.fold-btn {
  background: none; border: none; cursor: pointer;
  color: #1d9bf0; font-size: 12px; font-weight: 600;
  padding: 2px 0; margin-top: 2px;
  transition: color .15s;
}
.fold-btn:hover { color: #60a5fa; text-decoration: underline; }
.fold-btn.reddit-fold { color: #ff6b3a; }
.fold-btn.reddit-fold:hover { color: #ff8c5a; }

/* ============ Twitter 推文卡片 ============ */
.tweet-card {
  display: flex; gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255,255,255,.06);
  transition: background .15s;
  background: rgba(29,155,240,.06);
  border-radius: 8px;
  margin: 6px 8px;
}
.tweet-card:hover { background: rgba(29,155,240,.1); }

.tweet-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  color: #fff; font-size: 15px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.tweet-main { flex: 1; min-width: 0; }
.tweet-header {
  display: flex; align-items: baseline; gap: 5px; flex-wrap: wrap;
  margin-bottom: 2px;
}
.tweet-name { font-size: 13px; font-weight: 700; color: #374151; white-space: nowrap; }
.tweet-handle { font-size: 12px; color: #71767b; white-space: nowrap; }
.tweet-dot { color: #71767b; font-size: 11px; }
.tweet-time { font-size: 11px; color: #71767b; }
.tweet-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px;
  border-radius: 9px; margin-left: auto; letter-spacing: .3px;
}
.tweet-badge.post { background: rgba(29,78,216,.15); color: #60a5fa; }
.tweet-badge.comment { background: rgba(16,185,129,.12); color: #6ee7b7; }
.tweet-badge.like { background: rgba(239,68,68,.12); color: #fca5a5; }
.tweet-badge.quote, .tweet-badge.repost { background: rgba(168,85,247,.12); color: #d8b4fe; }
.tweet-badge.follow { background: rgba(59,130,246,.12); color: #93c5fd; }
.tweet-badge.search { background: rgba(245,158,11,.12); color: #fbbf24; }
.tweet-badge.vote-up { background: rgba(239,68,68,.12); color: #fca5a5; }
.tweet-badge.vote-down { background: rgba(113,147,255,.12); color: #7193ff; }
.tweet-badge.idle { background: rgba(100,116,139,.1); color: #71767b; }

.tweet-body { font-size: 13px; line-height: 1.5; color: #1f2937; margin-bottom: 4px; }
.tweet-text { margin: 0; white-space: pre-wrap; word-break: break-word; color: #1f2937; }
.tweet-action-line { color: #6b7280; font-size: 12px; line-height: 1.4; }
.tweet-action-line .heart { color: #f91880; }
.tweet-action-line.dim { color: #9ca3af; font-style: italic; }
.tweet-action-line b { color: #3b82f6; font-weight: 600; }

.tweet-repost-tag { font-size: 11px; color: #059669; font-weight: 600; margin-bottom: 2px; }
.tweet-quote {
  border: 1px solid rgba(0,0,0,.1); border-radius: 10px;
  padding: 8px 10px; margin-top: 6px;
  background: rgba(0,0,0,.03);
}
.tq-author { color: #3b82f6; font-size: 11px; font-weight: 600; display: block; margin-bottom: 2px; }
.tq-text { color: #4b5563; font-size: 12px; line-height: 1.35; }

.tweet-foot {
  display: flex; gap: 20px; padding-top: 4px;
}
.tf-btn {
  font-size: 13px; color: #6b7280; cursor: pointer;
  transition: color .15s;
}
.tf-btn:hover { color: #1d9bf0; }

/* ============ Reddit 完整帖子卡片 ============ */
.reddit-card {
  display: flex;
  /* 深灰蓝（slate-800 偏暖），不黑不白，与页面背景醒目区分 */
  background: #232a39;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 8px; overflow: hidden;
  transition: border-color .15s, background .15s;
  margin: 6px 8px;
}
.reddit-card:hover {
  border-color: rgba(255,69,0,.35);
  background: #272f3f;
}

.reddit-votes {
  display: flex; flex-direction: column; align-items: center;
  padding: 10px 6px; gap: 2px;
  background: rgba(15, 23, 42, 0.35);
  min-width: 34px;
}
.vote-arrow {
  color: #555; font-size: 13px; cursor: pointer;
  transition: color .15s; line-height: 1;
}
.vote-arrow.up:hover, .vote-arrow.up.active { color: #ff4500; }
.vote-arrow.down:hover, .vote-arrow.down.active { color: #7193ff; }
.vote-score {
  font-size: 11px; font-weight: 700; color: #d7dadc;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.reddit-main { flex: 1; padding: 8px 10px; min-width: 0; }
.reddit-meta {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin-bottom: 4px; font-size: 11.5px;
  line-height: 1.3;
}
.reddit-sub {
  color: #f1f5f9;
  font-weight: 800;
  background: rgba(255, 69, 0, 0.12);
  border: 1px solid rgba(255, 69, 0, 0.25);
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.02em;
}
.reddit-sep { color: #475569; font-size: 11px; }
.reddit-author {
  color: #93c5fd;
  font-weight: 600;
}
.reddit-time {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10.5px;
  font-weight: 700;
}
.reddit-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px;
  border-radius: 9px; margin-left: auto;
}
.reddit-badge.post { background: rgba(255,69,0,.15); color: #ff6b3a; }
.reddit-badge.comment { background: rgba(16,185,129,.12); color: #6ee7b7; }
.reddit-badge.quote, .reddit-badge.repost { background: rgba(168,85,247,.12); color: #d8b4fe; }

.reddit-body { font-size: 13px; line-height: 1.5; color: #d7dadc; margin-bottom: 6px; }
.reddit-text { margin: 0; white-space: pre-wrap; word-break: break-word; }
.reddit-text.comment-style {
  border-left: 2px solid #ff4500; padding-left: 8px;
}
.reddit-repost-tag { font-size: 11px; color: #6ee7b7; font-weight: 600; margin-bottom: 2px; }
.reddit-quote-block {
  border-left: 2px solid rgba(148, 163, 184, 0.3);
  padding: 6px 10px; margin-top: 4px;
  background: rgba(15, 23, 42, 0.3);
  border-radius: 0 4px 4px 0;
}
.rq-author { color: #4a9eff; font-size: 11px; font-weight: 600; display: block; margin-bottom: 2px; }
.rq-text { color: #818384; font-size: 12px; line-height: 1.35; }

.reddit-foot {
  display: flex; gap: 12px; padding-top: 4px; font-size: 11px; color: #818384;
}
.rf-btn { cursor: pointer; transition: color .15s; font-weight: 600; }
.rf-btn:hover { color: #d7dadc; }

/* ============ Reddit mini-card（轻量操作） ============ */
.reddit-mini {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px;
  margin: 3px 8px;
  border-radius: 6px;
  background: #2a3142;
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-left: 3px solid #64748b;
  font-size: 12px; color: #cbd5e1;
  transition: all .15s;
}
.reddit-mini:hover {
  background: #313a4d;
  border-color: rgba(148, 163, 184, 0.2);
}
.reddit-mini.like { border-left-color: #ff4500; }
.reddit-mini.vote-up { border-left-color: #ff4500; }
.reddit-mini.vote-down { border-left-color: #7193ff; }
.reddit-mini.search { border-left-color: #fbbf24; }
.reddit-mini.follow { border-left-color: #3b82f6; }
.reddit-mini.idle { border-left-color: #444; opacity: .7; }

.rm-icon { font-size: 13px; flex-shrink: 0; width: 18px; text-align: center; }
.rm-user {
  color: #93c5fd;
  font-weight: 700;
  white-space: nowrap;
}
.rm-desc {
  color: #cbd5e1;
  flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rm-desc b { color: #93c5fd; font-weight: 700; }
.rm-round {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  margin-left: auto;
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.5);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  letter-spacing: 0.04em;
}
</style>
