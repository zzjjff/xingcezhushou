<template>
  <div class="questions-view">
    <el-card shadow="never" class="panel">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select v-if="isAdmin" v-model="moduleFilter" placeholder="全部模块" clearable style="width:180px" @change="onFilterChange">
            <el-option v-for="m in modules" :key="m" :label="m" :value="m" />
          </el-select>
          <el-button v-if="isAdmin" @click="loadList">刷新</el-button>
          <span v-if="!isAdmin" class="muted-tip">管理员登录后可查看/管理题库</span>
        </div>
        <div class="toolbar-right">
          <el-upload
            :http-request="handleUpload"
            :show-file-list="false"
            accept=".docx,.pdf"
          >
            <el-button type="primary" :loading="uploading">上传题库文件</el-button>
          </el-upload>
        </div>
      </div>

      <!-- 仅管理员可见：题库列表 -->
      <template v-if="isAdmin">
        <el-table :data="list" v-loading="loading" border style="margin-top:16px">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="content" label="题干" min-width="240" show-overflow-tooltip />
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="answer" label="答案" width="70" />
          <el-table-column prop="difficulty" label="难度" width="70" />
          <el-table-column label="掌握度" width="90">
            <template #default="{ row }">
              {{ row.mastery_score != null ? row.mastery_score.toFixed(0) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="source_file" label="来源" width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openEditAnswer(row)">改答案</el-button>
              <el-button text type="danger" @click="handleDelete(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          class="pager"
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="onFilterChange"
          @current-change="loadList"
        />
      </template>
    </el-card>

    <!-- 解析预览弹窗 -->
    <el-dialog v-model="parseResult.visible" title="解析预览" width="900px" :close-on-click-modal="false">
      <div class="parse-head">
        <span>切出 {{ parseResult.items.length }} 题（模式：{{ parseResult.mode }}）</span>
        <el-button type="primary" :loading="importing" @click="handleBatchImport">一键入库</el-button>
      </div>
      <el-table :data="parseResult.items" border max-height="420" style="margin-top:12px">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="module" label="模块" width="130" />
        <el-table-column prop="content" label="题干" min-width="220" show-overflow-tooltip />
        <el-table-column prop="option_a" label="A" min-width="120" show-overflow-tooltip />
        <el-table-column prop="option_b" label="B" min-width="120" show-overflow-tooltip />
        <el-table-column prop="option_c" label="C" min-width="120" show-overflow-tooltip />
        <el-table-column prop="option_d" label="D" min-width="120" show-overflow-tooltip />
        <el-table-column prop="answer" label="答案" width="70">
          <template #default="{ row }">
            <span class="muted">{{ row.answer || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <p class="hint">无答案的题入库时自动占位为 A，找到答案后可在列表点"改答案"录入。</p>
    </el-dialog>

    <!-- 答案录入弹窗 -->
    <el-dialog v-model="editDialog.visible" title="录入答案" width="520px">
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
        <el-input v-model="editDialog.explanation" type="textarea" :rows="4" placeholder="可选，找到解析后录入" />
      </div>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.saving" @click="saveAnswer">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getQuestions, getModules, deleteQuestion, uploadFile, parseQuestions, batchImport, updateQuestion } from '../api'

// 管理员权限：有 token 才显示题库列表/删除/改答案；普通用户仅能上传
const isAdmin = ref(!!localStorage.getItem('admin_token'))

const list = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const moduleFilter = ref('')
const modules = ref([])

const loadList = async () => {
  if (!isAdmin.value) return
  loading.value = true
  try {
    const res = await getQuestions({
      page: page.value,
      page_size: pageSize.value,
      module: moduleFilter.value || undefined
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    if (e.response?.status === 401) {
      // token 失效，降级为普通用户
      isAdmin.value = false
      localStorage.removeItem('admin_token')
    } else {
      ElMessage.error('加载题目列表失败')
    }
  } finally {
    loading.value = false
  }
}

const loadModules = async () => {
  try {
    const res = await getModules()
    modules.value = res.data
  } catch (e) {
    // 模块列表加载失败不阻断主流程
  }
}

const onFilterChange = () => {
  page.value = 1
  loadList()
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该题目？', '提示', { type: 'warning' })
    await deleteQuestion(id)
    ElMessage.success('已删除')
    loadList()
  } catch (e) {
    // 用户取消则忽略
  }
}

// 上传 → 解析 → 预览
const uploading = ref(false)
const importing = ref(false)
const parseResult = ref({ visible: false, mode: '', items: [] })

const handleUpload = async (option) => {
  uploading.value = true
  try {
    const up = await uploadFile(option.file)
    const pr = await parseQuestions(up.data.raw_text)
    parseResult.value = {
      visible: true,
      mode: pr.data.mode,
      items: pr.data.items
    }
    ElMessage.success(`解析完成，切出 ${pr.data.items.length} 题`)
  } catch (e) {
    ElMessage.error('上传/解析失败')
  } finally {
    uploading.value = false
  }
}

const handleBatchImport = async () => {
  importing.value = true
  try {
    const res = await batchImport(parseResult.value.items)
    ElMessage.success(`入库完成：新增 ${res.data.inserted}，跳过重复 ${res.data.skipped}`)
    parseResult.value.visible = false
    if (isAdmin.value) loadList()
    loadModules()
  } catch (e) {
    ElMessage.error('入库失败')
  } finally {
    importing.value = false
  }
}

// 答案录入
const editDialog = ref({ visible: false, id: null, answer: '', explanation: '', saving: false })

const openEditAnswer = (row) => {
  editDialog.value = {
    visible: true,
    id: row.id,
    answer: row.answer || '',
    explanation: row.explanation || '',
    saving: false
  }
}

const saveAnswer = async () => {
  editDialog.value.saving = true
  try {
    await updateQuestion(editDialog.value.id, {
      answer: editDialog.value.answer || null,
      explanation: editDialog.value.explanation || null
    })
    ElMessage.success('已保存')
    editDialog.value.visible = false
    loadList()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    editDialog.value.saving = false
  }
}

onMounted(() => {
  loadModules()
  loadList()
})
</script>

<style scoped>
.questions-view { max-width: 1100px; margin: 0 auto; }
.panel { border-radius: 8px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar-left { display: flex; gap: 8px; align-items: center; }
.pager { margin-top: 16px; justify-content: flex-end; }
.hint { color: #909399; font-size: 12px; margin-top: 8px; }
.muted { color: #c0c4cc; }
.muted-tip { color: #909399; font-size: 14px; }
.parse-head { display: flex; justify-content: space-between; align-items: center; }
.edit-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
.edit-label { width: 48px; color: #606266; line-height: 32px; flex-shrink: 0; }
</style>