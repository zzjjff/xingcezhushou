import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

export default api

// 题库相关接口（对应后端 routers/questions.py）
export const getQuestions = (params) => api.get('/questions', { params })
export const getModules = () => api.get('/questions/modules/list')
export const deleteQuestion = (id) => api.delete(`/questions/${id}`)
export const uploadFile = (file) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/questions/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
// 解析纯文本为结构化题目（不入库）
export const parseQuestions = (rawText) => api.post('/questions/parse', { raw_text: rawText })
// 批量入库（按 content 去重）
export const batchImport = (questions) => api.post('/questions/batch', questions)

// 做题相关接口
export const startExam = (module, count) => api.post('/exam/start', { module: module || null, count })
export const submitExam = (answers) => api.post('/exam/submit', { answers })


// 更新题目（答案录入）
export const updateQuestion = (id, data) => api.patch(`/questions/${id}`, data)


// 组卷（双模式：mock 模拟 / supplement 培优补弱）
export const generateExam = (mode, count) => api.post('/exam/generate', { mode, count })


// 复盘统计
export const getReview = () => api.get('/exam/review')


// 单题 AI 补全答案/解析
export const aiExplain = (id) => api.post(`/questions/${id}/ai_explain`)


// 定向复习单题
export const practiceOne = (qid) => api.post('/exam/practice_one', null, { params: { question_id: qid } })

// 错题本
export const getWrongBook = (module) => api.get('/exam/wrong_book', { params: module ? { module } : {} })

