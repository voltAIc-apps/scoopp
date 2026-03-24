// Scoopp API client
const API_BASE = import.meta.env.VITE_API_URL || 'http://10.0.99.1:8002'
const TOKEN_KEY = 'scoopp_token'
const EMAIL_KEY = 'scoopp_email'

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

function setStoredToken(token, email) {
  localStorage.setItem(TOKEN_KEY, token)
  if (email) localStorage.setItem(EMAIL_KEY, email)
}

function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
}

function getStoredEmail() {
  return localStorage.getItem(EMAIL_KEY)
}

function authHeaders() {
  const token = getStoredToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function handleResponse(response) {
  if (response.status === 401) {
    clearStoredToken()
    window.dispatchEvent(new Event('scoopp:auth-required'))
    throw new Error('Authentication required')
  }
  if (!response.ok) {
    const error = await response.text()
    throw new Error(error)
  }
  return response
}

export const api = {
  async getToken(email) {
    const response = await fetch(`${API_BASE}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    if (!response.ok) {
      const error = await response.text()
      throw new Error(error)
    }
    const data = await response.json()
    setStoredToken(data.access_token, email)
    return data
  },

  async fetchMarkdown(url) {
    const response = await handleResponse(
      await fetch(`${API_BASE}/md`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ url, f: 'fit' })
      })
    )
    return response.text()
  },

  async crawl(urls, maxDepth = null, maxPages = null) {
    const urlArray = Array.isArray(urls) ? urls : [urls]
    const body = { urls: urlArray, browser_config: {}, crawler_config: {} }
    if (maxDepth !== null) body.max_depth = maxDepth
    if (maxPages !== null) body.max_pages = maxPages

    const response = await handleResponse(
      await fetch(`${API_BASE}/crawl`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body)
      })
    )
    return response.json()
  },

  async health() {
    const response = await fetch(`${API_BASE}/health`)
    return response.json()
  },

  async getHistory(limit = 50) {
    const response = await handleResponse(
      await fetch(`${API_BASE}/history?limit=${limit}`, { headers: authHeaders() })
    )
    return response.json()
  },

  async getCrawl(crawlId) {
    const response = await handleResponse(
      await fetch(`${API_BASE}/history/${crawlId}`, { headers: authHeaders() })
    )
    return response.json()
  },

  getStoredToken,
  setStoredToken,
  clearStoredToken,
  getStoredEmail,
}

export default api
