<template>
  <div class="login-container">
    <div class="login-card">
      <h1>Scoopp</h1>
      <p class="subtitle">Enter your email to access the crawler</p>
      <form @submit.prevent="handleLogin">
        <input
          v-model="emailInput"
          type="email"
          placeholder="you@example.com"
          required
          :disabled="auth.loginLoading"
          class="email-input"
        />
        <button type="submit" :disabled="auth.loginLoading" class="login-btn">
          {{ auth.loginLoading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>
      <p v-if="auth.loginError" class="error">{{ auth.loginError }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const emailInput = ref('')

async function handleLogin() {
  try {
    await auth.login(emailInput.value)
    router.push('/')
  } catch {
    // error is shown via auth.loginError
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.login-card {
  background: #16213e;
  padding: 2.5rem;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-card h1 {
  color: white;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #8899aa;
  margin-bottom: 1.5rem;
}

.email-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #2a3a5c;
  border-radius: 8px;
  background: #0f1729;
  color: white;
  font-size: 1rem;
  margin-bottom: 1rem;
  box-sizing: border-box;
}

.email-input:focus {
  outline: none;
  border-color: #4a6fa5;
}

.login-btn {
  width: 100%;
  padding: 0.75rem;
  background: #4a6fa5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}

.login-btn:hover:not(:disabled) {
  background: #5a8fc5;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #e74c3c;
  margin-top: 1rem;
  font-size: 0.9rem;
}
</style>
