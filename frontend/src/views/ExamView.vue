<template>
  <div class="exam-view">
    <!-- 未开始：组卷配置 -->
    <el-card v-if="!started" shadow="never" class="panel">
      <h2>组卷做题</h2>
      <div class="config-row">
        <span class="label">模式</span>
        <el-radio-group v-model="cfg.mode">
          <el-radio-button label="supplement">培优补弱</el-radio-button>
          <el-radio-button label="mock">全真模拟</el-radio-button>
          <el-radio-button label="practice">按模块练习</el-radio-button>
        </el-radio-group>
      </div>
      <div class="config-row" v-if="cfg.mode === 'practice'">
        <span class="label">模块</span>
        <el-select v-model="cfg.module" placeholder="选择模块" style="width:220px">
          <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
        </el-select>
      </div>
      <div class="config-row" v-if="cfg.mode !== 'mock'">
        <span class="label">题量</span>
        <el-input-number v-model="cfg.count" :min="1" :max="50" />
      </div>
      <div class="config-row">
        <el-button type="primary" :loading="starting" @click="onStart">
          {{ cfg.mode === 'mock' ? '开始模拟（130题 / 2小时）' : '开始' }}
        </el-button>
      </div>
      <p class="hint">
        <span v-if="cfg.mode==='supplement'">按薄弱指数分配题量，从掌握度低且未固化的题中抽，重点补弱。</span>
        <span v-else-if="cfg.mode==='mock'">全真模拟：固定130题，限时2小时，按行测通用比例组卷，到时自动交卷。</span>
        <span v-else>指定模块随机抽题。</span>
      </p>
    </el-card>

    <!-- 答题中 -->
    <el-card v-else-if="!submitted" shadow="never" class="panel">
      <div class="exam-head">
        <span>第 {{ idx + 1 }} / {{ questions.length }} 题</span>
        <span class="module-tag">{{ current.module }}</span>
        <span v-if="timeLimit" class="timer-limit" :class="{ overtime: remainTime <= 0 }">
          倒计时 {{ formatTime(remainTime) }}
        </span>
        <span class="timer">本题 {{ currentQuestionTime }}s　累计 {{ totalTime }}s</span>
        <span class="answered-count">已答 {{ answeredCount }} / {{ questions.length }}</span>
      </div>

      <div class="stem">{{ current.content }}</div>

      <div class="options">
        <el-radio-group v-model="answers[current.id]" @change="onAnswer">
          <el-radio
            v-for="opt in optionList(current)"
            :key="opt.key"
            :label="opt.key"
            class="option-item"
          >{{ opt.key }}、{{ opt.text }}</el-radio>
        </el-radio-group>
      </div>

      <div class="exam-foot">
        <el-button :disabled="idx === 0" @click="prev">上一题</el-button>
        <el-button v-if="idx < questions.length - 1" type="primary" @click="next">下一题</el-button>
        <el-button v-else type="success" @click="confirmSubmit">交卷</el-button>
        <el-button text type="info" @click="confirmQuit">退出</el-button>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-card v-else shadow="never" class="panel">
      <h2>答题结果</h2>
      <p v-if="result.accuracy !== null">
        正确 {{ result.correct }} / {{ result.total }}　正确率 {{ (result.accuracy * 100).toFixed(1) }}%
      </p>
      <p v-else class="muted">
        共作答 {{ result.total }} 题。本题库暂无标准答案，正确率待 AI 补全答案后回溯判定。
      </p>
      <el-table :data="result.details" border style="margin-top:12px">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="question_id" label="题号" width="70" />
        <el-table-column prop="user_answer" label="你的答案" width="90" />
        <el-table-column label="正确答案" width="90">
          <template #default="{ row }">{{ row.correct_answer || '—' }}</template>
        </el-table-column>
        <el-table-column label="对错" width="80">
          <template #default="{ row }">
            <span v-if="row.is_correct === null" class="muted">待定</span>
            <span v-else-if="row.is_correct" style="color:#67c23a">对</span>
            <span v-else style="color:#f56c6c">错</span>
          </template>
        </el-table-column>
        <el-table-column prop="time_spent" label="耗时(s)" width="90" />
      </el-table>
      <div class="exam-foot">
        <el-button type="primary" @click="reset">再做一套</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { getModules, startExam, submitExam, generateExam, practiceOne } from '../api'

const modules = ref([])
const started = ref(false)
const submitted = ref(false)
const starting = ref(false)
const questions = ref([])
const idx = ref(0)
const answers = ref({})
const result = ref({ total: 0, correct: null, accuracy: null, details: [] })
const cfg = ref({ mode: 'supplement', module: '', count: 10 })
let timer = null
const route = useRoute()

const startOne = async (qid) => {
  starting.value = true
  try {
    const res = await practiceOne(qid)
    questions.value = res.data.questions
    answers.value = {}
    idx.value = 0
    totalTime.value = 0
    questionTimes.value = {}
    timeLimit.value = 0
    submitted.value = false
    started.value = true
    startTimer()
  } catch (e) {
    ElMessage.error('加载题目失败')
  } finally {
    starting.value = false
  }
}

// 计时：每题独立累计
const questionTimes = ref({})  // { question_id: 该题累计秒数 }
const totalTime = ref(0)       // 整场累计
const timeLimit = ref(0)       // 限时模式总秒数，0=不限
const remainTime = ref(0)      // 剩余秒数

const current = computed(() => questions.value[idx.value])
const answeredCount = computed(() => questions.value.filter(q => answers.value[q.id]).length)
const currentQuestionTime = computed(() => questionTimes.value[current.value?.id] || 0)

const optionList = (q) => {
  const list = []
  if (q.option_a) list.push({ key: 'A', text: q.option_a })
  if (q.option_b) list.push({ key: 'B', text: q.option_b })
  if (q.option_c) list.push({ key: 'C', text: q.option_c })
  if (q.option_d) list.push({ key: 'D', text: q.option_d })
  if (q.option_e) list.push({ key: 'E', text: q.option_e })
  return list
}

const formatTime = (s) => {
  if (s < 0) s = 0
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h, m, sec].map(x => String(x).padStart(2, '0')).join(':')
}

// 计时器：每秒把时间记到"当前题"，切题无需重置（按 idx 累计）
const startTimer = () => {
  stopTimer()
  if (timeLimit.value > 0) remainTime.value = timeLimit.value
  timer = setInterval(() => {
    if (timeLimit.value > 0) {
      remainTime.value--
      if (remainTime.value <= 0) {
        stopTimer()
        ElMessage.warning('时间到，自动交卷')
        autoSubmit()
        return
      }
    }
    totalTime.value++
    const qid = questions.value[idx.value]?.id
    if (qid != null) questionTimes.value[qid] = (questionTimes.value[qid] || 0) + 1
  }, 1000)
}
const stopTimer = () => {
  if (timer) { clearInterval(timer); timer = null }
}

const onStart = async () => {
  if (cfg.value.mode === 'practice' && !cfg.value.module) {
    ElMessage.warning('请选择模块')
    return
  }
  starting.value = true
  try {
    let res
    if (cfg.value.mode === 'practice') {
      res = await startExam(cfg.value.module, cfg.value.count)
    } else {
      res = await generateExam(cfg.value.mode, cfg.value.count)
    }
    questions.value = res.data.questions
    if (questions.value.length === 0) {
      ElMessage.warning('该范围下无题目')
      starting.value = false
      return
    }
    answers.value = {}
    idx.value = 0
    totalTime.value = 0
    questionTimes.value = {}
    timeLimit.value = res.data.total_time_seconds || 0
    submitted.value = false
    started.value = true
    startTimer()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '组卷失败')
  } finally {
    starting.value = false
  }
}

const onAnswer = () => {}

const prev = () => { if (idx.value > 0) idx.value-- }
const next = () => { if (idx.value < questions.value.length - 1) idx.value++ }

// 交卷载荷：每题传各自累计耗时
const buildPayload = () => questions.value.map(q => ({
  question_id: q.id,
  user_answer: answers.value[q.id] || '',
  time_spent: questionTimes.value[q.id] || 0,
}))

const autoSubmit = async () => {
  try {
    const res = await submitExam(buildPayload())
    result.value = res.data
    submitted.value = true
  } catch (e) {
    ElMessage.error('自动交卷失败')
  }
}

const confirmSubmit = async () => {
  const unanswered = questions.value.length - answeredCount.value
  let go = true
  if (unanswered > 0) {
    try {
      await ElMessageBox.confirm(`还有 ${unanswered} 题未作答，确定交卷？`, '提示', { type: 'warning' })
    } catch { go = false }
  }
  if (!go) return
  stopTimer()
  try {
    const res = await submitExam(buildPayload())
    result.value = res.data
    submitted.value = true
    ElMessage.success('已交卷')
  } catch (e) {
    ElMessage.error('交卷失败')
    startTimer()
  }
}

const confirmQuit = async () => {
  try {
    await ElMessageBox.confirm('确定退出本次答题？进度不会保存', '提示', { type: 'warning' })
    stopTimer()
    reset()
  } catch { /* 取消 */ }
}

const reset = () => {
  stopTimer()
  started.value = false
  submitted.value = false
  questions.value = []
  answers.value = {}
  idx.value = 0
  totalTime.value = 0
  questionTimes.value = {}
  timeLimit.value = 0
  remainTime.value = 0
}

onMounted(async () => {
  try { const res = await getModules(); modules.value = res.data } catch { /* 忽略 */ }
  if (route.query.qid) startOne(route.query.qid)
})
onUnmounted(stopTimer)
</script>

<style scoped>
.exam-view { max-width: 900px; margin: 0 auto; }
.panel { border-radius: 8px; }
.config-row { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
.config-row .label { color: #606266; width: 48px; }
.hint { color: #909399; font-size: 12px; margin-top: 16px; }
.exam-head { display: flex; align-items: center; gap: 16px; color: #606266; font-size: 14px; flex-wrap: wrap; }
.module-tag { color: #409eff; }
.timer { color: #e6a23c; }
.timer-limit { color: #e6a23c; font-weight: bold; }
.timer-limit.overtime { color: #f56c6c; }
.answered-count { margin-left: auto; }
.stem { font-size: 16px; line-height: 1.8; margin: 16px 0; color: #303133; white-space: pre-wrap; }
.options { display: flex; flex-direction: column; gap: 10px; }
.option-item { display: flex; align-items: flex-start; margin: 0; }
.option-item :deep(.el-radio__label) { white-space: normal; line-height: 1.6; }
.exam-foot { margin-top: 20px; display: flex; gap: 8px; }
.muted { color: #909399; }
</style>