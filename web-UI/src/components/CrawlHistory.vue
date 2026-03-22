<template>
  <div id="crawl-history" class="crawl-history">
    <div class="history-header">
      <h3>Letzte Crawls</h3>
      <button @click="refresh" :disabled="loading" class="refresh-btn">
        {{ loading ? 'Laden...' : 'Aktualisieren' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="history.length === 0 && !loading" class="empty">
      Noch keine Crawls vorhanden
    </div>

    <table v-if="history.length > 0" class="history-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Typ</th>
          <th>URL(s)</th>
          <th>Status</th>
          <th>Seiten</th>
          <th>Dauer</th>
          <th>Zeitpunkt</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in history" :key="item.crawl_id" @click="selectCrawl(item)" class="history-row">
          <td class="crawl-id">{{ item.crawl_id }}</td>
          <td>{{ item.request_type }}</td>
          <td class="urls-cell" :title="item.urls.join(', ')">
            {{ truncateUrls(item.urls) }}
          </td>
          <td>
            <span :class="['status', item.success ? 'success' : 'failed']">
              {{ item.success ? 'OK' : 'Fehler' }}
            </span>
          </td>
          <td>{{ item.pages_crawled || '-' }}</td>
          <td>{{ formatDuration(item.processing_time_s) }}</td>
          <td>{{ formatDate(item.created_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted, defineEmits } from 'vue'
import api from '../api/scoopp'

const emit = defineEmits(['select'])

const history = ref([])
const loading = ref(false)
const error = ref(null)

async function refresh() {
  loading.value = true
  error.value = null
  try {
    const res = await api.getHistory(20)
    history.value = res.history || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function selectCrawl(item) {
  emit('select', item)
}

function truncateUrls(urls) {
  if (!urls || urls.length === 0) return '-'
  const first = urls[0].replace(/^https?:\/\//, '').substring(0, 30)
  if (urls.length > 1) {
    return `${first}... (+${urls.length - 1})`
  }
  return first.length < urls[0].length - 8 ? first + '...' : first
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  return `${seconds.toFixed(1)}s`
}

function formatDate(isoStr) {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  return d.toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

defineExpose({ refresh })

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.crawl-history {
  margin-top: 2rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.history-header h3 {
  margin: 0;
  color: #333;
}

.refresh-btn {
  padding: 0.5rem 1rem;
  background: #1a1a2e;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  background: #2a2a4e;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  padding: 1rem;
  background: #fee;
  color: #c00;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.history-table th,
.history-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.history-table th {
  background: #f5f5f5;
  font-weight: 600;
}

.history-row {
  cursor: pointer;
  transition: background 0.15s;
}

.history-row:hover {
  background: #f9f9f9;
}

.crawl-id {
  font-family: monospace;
  font-size: 0.85rem;
}

.urls-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status {
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-size: 0.8rem;
}

.status.success {
  background: #e6f4ea;
  color: #1e7e34;
}

.status.failed {
  background: #fde8e8;
  color: #c53030;
}
</style>
