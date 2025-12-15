// Scoopp API client - adapted for demo branch API
const API_BASE = import.meta.env.VITE_API_URL || 'http://192.168.2.93:8001'

export const api = {
  // Fetch markdown for a single URL (simple, synchronous)
  async fetchMarkdown(url) {
    const response = await fetch(`${API_BASE}/md`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        f: 'fit'  // Filter type: fit (default), raw, bm25, llm
      })
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Fehler: ${error}`)
    }

    return response.text()
  },

  // Crawl URL(s) with optional depth (for multi-page crawls)
  async crawl(urls, maxDepth = null, maxPages = null) {
    const urlArray = Array.isArray(urls) ? urls : [urls]

    const body = {
      urls: urlArray,
      browser_config: {},
      crawler_config: {}
    }

    if (maxDepth !== null) {
      body.max_depth = maxDepth
    }
    if (maxPages !== null) {
      body.max_pages = maxPages
    }

    const response = await fetch(`${API_BASE}/crawl`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Fehler beim Crawlen: ${error}`)
    }

    return response.json()
  },

  // Health check
  async health() {
    const response = await fetch(`${API_BASE}/health`)
    return response.json()
  },

  // Get crawl history
  async getHistory(limit = 50) {
    const response = await fetch(`${API_BASE}/history?limit=${limit}`)
    if (!response.ok) {
      throw new Error('Fehler beim Laden der Historie')
    }
    return response.json()
  },

  // Get single crawl details
  async getCrawl(crawlId) {
    const response = await fetch(`${API_BASE}/history/${crawlId}`)
    if (!response.ok) {
      throw new Error(`Crawl ${crawlId} nicht gefunden`)
    }
    return response.json()
  }
}

export default api
