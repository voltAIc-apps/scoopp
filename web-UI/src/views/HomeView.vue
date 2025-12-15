<template>
  <div class="home-view">
    <h1>Scoopp Web-Crawler</h1>
    <p class="subtitle">Web-Inhalte crawlen und als Markdown anzeigen</p>

    <CrawlForm @result="onResult" />

    <div v-if="currentResult" class="result-section">
      <ResultViewer :result="currentResult" />
    </div>

    <CrawlHistory ref="historyRef" @select="onHistorySelect" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import CrawlForm from '../components/CrawlForm.vue'
import ResultViewer from '../components/ResultViewer.vue'
import CrawlHistory from '../components/CrawlHistory.vue'
import { useCrawlStore } from '../stores/crawl'

const store = useCrawlStore()
const historyRef = ref(null)

const currentResult = computed(() => store.currentResult)

function onResult(result) {
  // Result is already stored in the store
  // Scroll to result and refresh history
  setTimeout(() => {
    document.querySelector('.result-section')?.scrollIntoView({ behavior: 'smooth' })
  }, 100)
  // Refresh history after crawl
  historyRef.value?.refresh()
}

function onHistorySelect(item) {
  // Show preview from history item
  if (item.markdown_preview) {
    store.currentResult = {
      crawl_id: item.crawl_id,
      url: item.urls[0],
      markdown: item.markdown_preview + '\n\n[...Vorschau gekuerzt...]',
      success: item.success
    }
  }
}
</script>

<style scoped>
.home-view h1 {
  color: #1a1a2e;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #666;
  margin-bottom: 2rem;
}

.result-section {
  margin-top: 2rem;
}
</style>
