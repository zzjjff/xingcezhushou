<template>
  <div class="review-view">
    <el-card shadow="never" class="panel">
      <div class="head-row">
        <h2>复盘</h2>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
      <div class="summary" v-if="data">
        <span>总做题 <b>{{ data.summary.total }}</b></span>
        <span>正确 <b>{{ data.summary.correct }}</b></span>
        <span>正确率 <b>{{ (data.summary.accuracy * 100).toFixed(1) }}%</b></span>
      </div>
    </el-card>

    <div class="charts" v-if="data && !empty">
      <el-card shadow="never" class="chart-card">
        <template #header>各模块正确率（雷达）</template>
        <div ref="radarEl" class="chart"></div>
      </el-card>
      <el-card shadow="never" class="chart-card">
        <template #header>各模块平均耗时（秒）</template>
        <div ref="barEl" class="chart"></div>
      </el-card>
      <el-card shadow="never" class="chart-card chart-wide">
        <template #header>近期正确率趋势</template>
        <div ref="lineEl" class="chart"></div>
      </el-card>
    </div>

    <el-card v-if="data && data.wrong_questions.length" shadow="never" class="panel" style="margin-top:16px">
      <template #header>错题列表（最近 {{ data.wrong_questions.length }}）</template>
      <el-table :data="data.wrong_questions" border>
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="content" label="题干" min-width="200" show-overflow-tooltip />
        <el-table-column prop="user_answer" label="你的答案" width="90" />
        <el-table-column prop="correct_answer" label="正确答案" width="90" />
        <el-table-column prop="practiced_at" label="时间" width="140" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="warning" @click="openEditAnswer(row)">答案纠错</el-button>
            <el-button text type="primary" :loading="row._loading" @click="onAiExplain(row)">AI解析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-if="data && empty" description="暂无做题记录，去做几题再来复盘吧" />

    <!-- 答案纠错弹窗 -->
    <el-dialog v-model="editDialog.visible" title="答案纠错" width="520px">
      <div class="edit-row">
        <span class="edit-label">题号</span>
        <span>{{ editDialog.id }}</span>
      </div>
      <div class="edit-row">
        <span class="edit-label">答案</span>
        <el-select v-model="editDialog.answer" placeholder="选择答案" style="width:120px">
          <el-option label="A" value="A" />
          <el-option label="B" value="B" />
          <el-option label="C" value="C" />
          <el-option label="D" value="D" />
          <el-option label="E" value="E" />
        </el-select>
      </div>
      <div class="edit-row">
        <span class="edit-label">解析</span>
        <el-input v-model="editDialog.explanation" type="textarea" :rows="4" placeholder="可选" />
      </div>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="saveAnswer">保存</el-button>
      </template>
    </el-dialog>

    <!-- AI 解析结果弹窗 -->
    <el-dialog v-model="aiDialog.visible" title="AI 解析结果" width="560px">
      <p v-if="aiDialog.mode === 'skipped'" class="muted">{{ aiDialog.message }}</p>
      <div v-else>
        <p><b>答案：</b>{{ aiDialog.answer || '—' }}</p>
        <p><b>解析：</b></p>
        <div class="ai-explanation">{{ aiDialog.explanation || '（空）' }}</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getReview, updateQuestion, aiExplain } from '../api'

const loading = ref(false)
const data = ref(null)
const empty = ref(false)
const radarEl = ref(null)
const barEl = ref(null)
const lineEl = ref(null)
let charts = []

const load = async () => {
  loading.value = true
  try {
    const res = await getReview()
    // 给每行加 _loading 标记（用于 AI 解析按钮）
    res.data.wrong_questions.forEach(r => { r._loading = false })
    data.value = res.data
    empty.value = res.data.summary.total === 0
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error('加载复盘数据失败')
  } finally {
    loading.value = false
  }
}

const renderCharts = () => {
  charts.forEach(c => c.dispose())
  charts = []
  if (!data.value || empty.value) return
  const mods = data.value.modules
  if (!mods.length) return

  if (radarEl.value) {
    const c = echarts.init(radarEl.value)
    c.setOption({
      tooltip: {},
      radar: { indicator: mods.map(m => ({ name: m.module, max: 1 })) },
      series: [{ type: 'radar', data: [{ value: mods.map(m => m.accuracy), name: '正确率', areaStyle: {} }] }],
    })
    charts.push(c)
  }
  if (barEl.value) {
    const c = echarts.init(barEl.value)
    c.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: mods.map(m => m.module), axisLabel: { interval: 0, rotate: 20 } },
      yAxis: { type: 'value', name: '秒' },
      series: [{ type: 'bar', data: mods.map(m => m.avg_time), itemStyle: { color: '#409eff' } }],
    })
    charts.push(c)
  }
  if (lineEl.value) {
    const c = echarts.init(lineEl.value)
    const tr = data.value.trend
    c.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: tr.map(t => t.date) },
      yAxis: { type: 'value', name: '正确率', max: 1, axisLabel: { formatter: v => (v * 100) + '%' } },
      series: [{ type: 'line', data: tr.map(t => t.accuracy), smooth: true, itemStyle: { color: '#67c23a' }, areaStyle: {} }],
    })
    charts.push(c)
  }
}

// 答案纠错（复用 PATCH）
const editDialog = ref({ visible: false, id: null, answer: '', explanation: '', saving: false })
const openEditAnswer = (row) => {
  editDialog.value = { visible: true, id: row.question_id, answer: row.correct_answer || '', explanation: '', saving: false }
}
const saveAnswer = async () => {
  editDialog.value.saving = true
  try {
    await updateQuestion(editDialog.value.id, { answer: editDialog.value.answer || null, explanation: editDialog.value.explanation || null })
    ElMessage.success('答案已更新')
    editDialog.value.visible = false
    load()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    editDialog.value.saving = false
  }
}

// AI 重新解析
const aiDialog = ref({ visible: false, mode: '', answer: '', explanation: '', message: '' })
const onAiExplain = async (row) => {
  row._loading = true
  try {
    const res = await aiExplain(row.question_id)
    const item = res.data.items[0] || {}
    aiDialog.value = {
      visible: true,
      mode: res.data.mode,
      answer: item.answer,
      explanation: item.explanation,
      message: res.data.message,
    }
    if (res.data.mode === 'ai') {
      ElMessage.success('AI 解析完成')
    }
  } catch (e) {
    ElMessage.error('解析失败')
  } finally {
    row._loading = false
  }
}

const onResize = () => charts.forEach(c => c.resize())
onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.review-view { max-width: 1100px; margin: 0 auto; }
.panel { border-radius: 8px; }
.head-row { display: flex; justify-content: space-between; align-items: center; }
.head-row h2 { margin: 0; }
.summary { margin-top: 12px; display: flex; gap: 24px; color: #606266; }
.summary b { color: #409eff; font-size: 16px; margin-left: 4px; }
.charts { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.chart-card { border-radius: 8px; }
.chart-wide { grid-column: 1 / -1; }
.chart { height: 280px; }
.muted { color: #909399; }
.edit-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
.edit-label { width: 48px; color: #606266; line-height: 32px; flex-shrink: 0; }
.ai-explanation { background: #f5f7fa; padding: 12px; border-radius: 6px; line-height: 1.7; white-space: pre-wrap; }
</style>