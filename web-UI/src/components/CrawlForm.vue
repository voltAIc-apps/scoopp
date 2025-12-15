<template>
  <div class="card crawl-form">
    <h2>Web-Crawl starten</h2>

    <form @submit.prevent="handleSubmit">
      <div class="input-group">
        <label for="url">URL *</label>
        <input
          id="url"
          v-model="url"
          type="url"
          placeholder="https://beispiel.de"
          required
        />
      </div>

      <div class="form-row">
        <div class="input-group">
          <label for="depth">Crawl-Tiefe (0-5)</label>
          <input
            id="depth"
            v-model.number="maxDepth"
            type="number"
            min="0"
            max="5"
            placeholder="0 = nur diese Seite"
          />
        </div>

        <div class="input-group">
          <label for="maxPages">Max. Seiten</label>
          <input
            id="maxPages"
            v-model.number="maxPages"
            type="number"
            min="1"
            max="100"
            placeholder="10"
          />
        </div>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ loading ? 'Crawlt...' : 'Crawl starten' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCrawlStore } from '../stores/crawl'

const emit = defineEmits(['result'])

const store = useCrawlStore()

const url = ref('')
const maxDepth = ref(null)
const maxPages = ref(null)

const loading = computed(() => store.loading)
const error = computed(() => store.error)

async function handleSubmit() {
  store.clearError()

  try {
    let result
    if (maxDepth.value && maxDepth.value > 0) {
      // Multi-page crawl with depth
      result = await store.crawlWithDepth(
        url.value,
        maxDepth.value,
        maxPages.value || 10
      )
    } else {
      // Simple single-page markdown fetch
      result = await store.fetchMarkdown(url.value)
    }

    emit('result', result)
  } catch (e) {
    // Error already handled in store
  }
}
</script>

<style scoped>
.crawl-form h2 {
  margin-bottom: 1.5rem;
  color: #1a1a2e;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 600px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
