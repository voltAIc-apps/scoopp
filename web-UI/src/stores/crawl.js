import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/scoopp'

export const useCrawlStore = defineStore('crawl', () => {
  const currentResult = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Fetch markdown for single URL (simple mode)
  async function fetchMarkdown(url) {
    loading.value = true
    error.value = null
    currentResult.value = null

    try {
      const markdown = await api.fetchMarkdown(url)
      currentResult.value = {
        url: url,
        markdown: markdown,
        timestamp: new Date().toISOString()
      }
      return currentResult.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  // Crawl with depth (multi-page mode)
  async function crawlWithDepth(url, maxDepth, maxPages) {
    loading.value = true
    error.value = null
    currentResult.value = null

    try {
      const result = await api.crawl(url, maxDepth, maxPages)
      currentResult.value = {
        url: url,
        results: result,
        timestamp: new Date().toISOString()
      }
      return currentResult.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearResult() {
    currentResult.value = null
  }

  return {
    currentResult,
    loading,
    error,
    fetchMarkdown,
    crawlWithDepth,
    clearError,
    clearResult
  }
})
