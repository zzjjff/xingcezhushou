import { createRouter, createWebHistory } from 'vue-router'
import QuestionsView from '../views/QuestionsView.vue'

const routes = [
  { path: '/', redirect: '/questions' },
  { path: '/questions', name: 'questions', component: QuestionsView, meta: { title: '题库管理' } },
  { path: '/exam', name: 'exam', component: () => import('../views/ExamView.vue'), meta: { title: '做题' } },
  { path: '/review', name: 'review', component: () => import('../views/ReviewView.vue'), meta: { title: '复盘' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router