<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>行测智能学习系统</h1>
      <nav class="app-nav">
        <router-link to="/questions" custom v-slot="{ navigate, isActive }">
          <button :class="['nav-btn', { active: isActive }]" @click="navigate">题库管理</button>
        </router-link>
        <router-link to="/exam" custom v-slot="{ navigate, isActive }">
          <button :class="['nav-btn', { active: isActive }]" @click="navigate">做题</button>
        </router-link>
        <router-link to="/review" custom v-slot="{ navigate, isActive }">
          <button :class="['nav-btn', { active: isActive }]" @click="navigate">复盘</button>
        </router-link>
        <router-link to="/wrong-book" custom v-slot="{ navigate, isActive }">
          <button :class="['nav-btn', { active: isActive }]" @click="navigate">错题本</button>
        </router-link>
        <button v-if="!isAdmin" class="nav-btn nav-login" @click="goLogin">登录</button>
        <button v-else class="nav-btn nav-login" @click="logout">退出管理</button>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const isAdmin = computed(() => !!localStorage.getItem('admin_token'))

const goLogin = () => router.push('/login')
const logout = () => {
  localStorage.removeItem('admin_token')
  // 退出后若在题库管理页，跳到做题页
  if (route.path === '/questions') router.push('/exam')
  location.reload()
}

</script>

<style>
body { margin: 0; }
.app-shell { min-height: 100vh; background: #f5f7fa; }
.app-header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.app-header h1 { margin: 0; font-size: 18px; color: #303133; }
.app-nav { display: flex; gap: 8px; }
.nav-btn {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.nav-btn:hover { color: #409eff; border-color: #c6e2ff; }
.nav-btn.active { color: #fff; background: #409eff; border-color: #409eff; }
.app-main { padding: 24px; }
</style>