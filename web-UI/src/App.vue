<template>
  <div id="app" class="app">
    <nav class="navbar">
      <div class="nav-brand">
        <router-link to="/">Scoopp</router-link>
      </div>
      <div class="nav-links">
        <template v-if="auth.isAuthenticated">
          <router-link to="/history">Historie</router-link>
          <a href="/api/docs" target="_blank">API Docs</a>
          <span class="nav-email">{{ auth.email }}</span>
          <button class="logout-btn" @click="handleLogout">Logout</button>
        </template>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function onAuthRequired() {
  auth.onAuthRequired()
  router.push('/login')
}

onMounted(() => window.addEventListener('scoopp:auth-required', onAuthRequired))
onUnmounted(() => window.removeEventListener('scoopp:auth-required', onAuthRequired))
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: #1a1a2e;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand a {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.nav-links a {
  color: #ccc;
  text-decoration: none;
  transition: color 0.2s;
}

.nav-links a:hover {
  color: white;
}

.nav-email {
  color: #8899aa;
  font-size: 0.85rem;
}

.logout-btn {
  background: transparent;
  border: 1px solid #555;
  color: #ccc;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.logout-btn:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
