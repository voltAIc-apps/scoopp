<template>
  <div class="card crawl-list">
    <div class="list-header">
      <h2>Crawl-Liste</h2>
      <button class="btn btn-secondary" @click="refresh" :disabled="loading">
        {{ loading ? 'Lade...' : 'Aktualisieren' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div v-else-if="loading && crawls.length === 0" class="loading">
      Lade Crawl-Liste...
    </div>

    <div v-else-if="crawls.length === 0" class="empty-state">
      Keine Crawls vorhanden. Starten Sie einen neuen Crawl-Auftrag.
    </div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Crawl-ID</th>
          <th>Aktion</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="crawlId in crawls" :key="crawlId">
          <td>
            <code>{{ crawlId }}</code>
          </td>
          <td>
            <router-link
              :to="{ name: 'result', params: { crawlId } }"
              class="btn btn-primary"
            >
              Anzeigen
            </router-link>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useCrawlStore } from '../stores/crawl'

const store = useCrawlStore()

const crawls = computed(() => store.crawls)
const loading = computed(() => store.loading)
const error = computed(() => store.error)

async function refresh() {
  await store.loadCrawls()
}

onMounted(() => {
  store.loadCrawls()
})
</script>

<style scoped>
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.list-header h2 {
  margin: 0;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}

code {
  background: #f4f4f4;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-family: monospace;
}
</style>
