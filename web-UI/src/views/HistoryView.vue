<template>
  <div class="history-view">
    <h1>Crawl-Historie</h1>
    <p class="subtitle">Alle bisherigen Crawls auf einen Blick</p>

    <CrawlHistory @select="onSelect" />

    <div v-if="selectedItem" class="detail-section">
      <h3>Vorschau: {{ selectedItem.crawl_id }}</h3>
      <div class="detail-meta">
        <span>URL: {{ selectedItem.urls[0] }}</span>
        <span>Typ: {{ selectedItem.request_type }}</span>
        <span>Seiten: {{ selectedItem.pages_crawled || '-' }}</span>
      </div>
      <div class="preview-box">
        <pre>{{ selectedItem.markdown_preview || 'Keine Vorschau verfuegbar' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import CrawlHistory from '../components/CrawlHistory.vue'

const selectedItem = ref(null)

function onSelect(item) {
  selectedItem.value = item
}
</script>

<style scoped>
.history-view h1 {
  color: #1a1a2e;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
}

.detail-section {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.detail-section h3 {
  margin: 0 0 1rem 0;
  font-family: monospace;
}

.detail-meta {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
  font-size: 0.9rem;
  color: #666;
}

.preview-box {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 1rem;
  max-height: 400px;
  overflow: auto;
}

.preview-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.85rem;
}
</style>
