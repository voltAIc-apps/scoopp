<template>
  <div class="card crawl-status">
    <div class="status-header">
      <h3>Crawl #{{ crawlId }}</h3>
      <span :class="['status-badge', `status-${status}`]">
        {{ statusLabel }}
      </span>
    </div>

    <div v-if="status === 'in_progress'" class="progress-info">
      <div class="spinner"></div>
      <p>Crawl laeuft... ({{ pollingCount }} Abfragen)</p>
    </div>

    <div v-if="status === 'completed'" class="success-info">
      <p>Crawl erfolgreich abgeschlossen.</p>
      <router-link
        :to="{ name: 'result', params: { crawlId } }"
        class="btn btn-primary"
      >
        Ergebnis anzeigen
      </router-link>
    </div>

    <div v-if="status === 'failed'" class="error-info">
      <p>Crawl fehlgeschlagen.</p>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useCrawlStore } from '../stores/crawl'

const props = defineProps({
  crawlId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['completed', 'failed'])

const store = useCrawlStore()

const status = ref('in_progress')
const error = ref(null)
const pollingCount = ref(0)
let pollInterval = null

const statusLabel = computed(() => {
  const labels = {
    'in_progress': 'In Bearbeitung',
    'completed': 'Abgeschlossen',
    'failed': 'Fehlgeschlagen'
  }
  return labels[status.value] || status.value
})

async function checkStatus() {
  try {
    pollingCount.value++
    const result = await store.getStatus(props.crawlId)
    status.value = result.status

    if (result.status === 'completed') {
      stopPolling()
      emit('completed', result)
    } else if (result.status === 'failed') {
      stopPolling()
      emit('failed', result)
    }
  } catch (e) {
    error.value = e.message
    stopPolling()
  }
}

function startPolling() {
  checkStatus()
  const POLL_MS = parseInt(import.meta.env.VITE_POLL_INTERVAL || '2000')
  pollInterval = setInterval(checkStatus, POLL_MS)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

watch(() => props.crawlId, () => {
  status.value = 'in_progress'
  pollingCount.value = 0
  error.value = null
  stopPolling()
  startPolling()
})
</script>

<style scoped>
.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.status-header h3 {
  margin: 0;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #666;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.success-info {
  color: #155724;
}

.success-info p {
  margin-bottom: 1rem;
}

.error-info {
  color: #721c24;
}
</style>
