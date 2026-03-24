import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/scoopp'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(api.getStoredToken())
  const email = ref(api.getStoredEmail())
  const loginError = ref(null)
  const loginLoading = ref(false)

  const isAuthenticated = computed(() => !!token.value)

  async function login(emailInput) {
    loginLoading.value = true
    loginError.value = null
    try {
      const data = await api.getToken(emailInput)
      token.value = data.access_token
      email.value = emailInput
    } catch (e) {
      loginError.value = e.message
      throw e
    } finally {
      loginLoading.value = false
    }
  }

  function logout() {
    api.clearStoredToken()
    token.value = null
    email.value = null
  }

  function onAuthRequired() {
    token.value = null
    email.value = null
  }

  return { token, email, loginError, loginLoading, isAuthenticated, login, logout, onAuthRequired }
})
