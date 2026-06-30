<template>
  <div class="login-view">
    <el-card shadow="never" class="login-card">
      <h2>管理员登录</h2>
      <p class="muted-tip">登录后可查看与管理题库。普通用户可直接做题、上传题库。</p>
      <el-input v-model="password" type="password" placeholder="管理员密码" show-password @keyup.enter="onLogin" />
      <el-button type="primary" :loading="loading" @click="onLogin" style="margin-top:12px;width:100%">登录</el-button>
      <p v-if="error" class="err">{{ error }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api'

const router = useRouter()
const password = ref('')
const loading = ref(false)
const error = ref('')

const onLogin = async () => {
  if (!password.value) { error.value = '请输入密码'; return }
  loading.value = true
  error.value = ''
  try {
    const res = await login(password.value)
    localStorage.setItem('admin_token', res.data.token)
    ElMessage.success('登录成功')
    router.push('/questions')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-view { max-width: 380px; margin: 60px auto; }
.login-card { border-radius: 8px; }
.login-card h2 { margin: 0 0 8px; }
.muted-tip { color: #909399; font-size: 12px; margin: 8px 0 16px; }
.err { color: #f56c6c; font-size: 13px; margin-top: 8px; }
</style>