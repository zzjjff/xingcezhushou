<template>
  <div class="wb-view">
    <el-card shadow="never" class="panel">
      <div class="head-row">
        <h2>错题本</h2>
        <div class="toolbar">
          <el-select v-model="moduleFilter" placeholder="全部模块" clearable style="width:180px" @change="load">
            <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
          </el-select>
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
      <p class="hint">按有效分（含时间衰减）升序，红色=亟待复习，绿色=较稳。点"去复习"单独练该题。</p>

      <el-table :data="list" v-loading="loading" border style="margin-top:12px">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="content" label="题干" min-width="240" show-overflow-tooltip />
        <el-table-column label="有效分" width="100">
          <template #default="{ row }">
            <span :class="['score-tag', scoreClass(row.effective_score)]">{{ row.effective_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="原始分" width="90" />
        <el-table-column prop="wrong_count" label="错次" width="70" />
        <el-table-column label="固化" width="70">
          <template #default="{ row }">
            <span v-if="row.is_consolidated" style="color:#67c23a">已固化</span>
            <span v-else class="muted">未</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_practice_at" label="最近练习" width="140" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="goPractice(row.question_id)">去复习</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !list.length" description="暂无错题，去做几题吧" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getWrongBook, getModules } from '../api'

const router = useRouter()
const list = ref([])
const modules = ref([])
const moduleFilter = ref('')
const loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res = await getWrongBook(moduleFilter.value)
    list.value = res.data
  } catch (e) {
    ElMessage.error('加载错题本失败')
  } finally {
    loading.value = false
  }
}

const scoreClass = (eff) => {
  if (eff < 50) return 'score-red'
  if (eff < 70) return 'score-orange'
  return 'score-green'
}

const goPractice = (qid) => {
  router.push({ path: '/exam', query: { qid } })
}

onMounted(async () => {
  try { const res = await getModules(); modules.value = res.data } catch { /* */ }
  load()
})
</script>

<style scoped>
.wb-view { max-width: 1100px; margin: 0 auto; }
.panel { border-radius: 8px; }
.head-row { display: flex; justify-content: space-between; align-items: center; }
.head-row h2 { margin: 0; }
.toolbar { display: flex; gap: 8px; }
.hint { color: #909399; font-size: 12px; margin: 8px 0; }
.muted { color: #c0c4cc; }
.score-tag { font-weight: bold; }
.score-red { color: #f56c6c; }
.score-orange { color: #e6a23c; }
.score-green { color: #67c23a; }
</style>