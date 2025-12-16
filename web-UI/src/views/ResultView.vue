<template>
  <div class="result-view">
    <div class="back-link">
      <router-link to="/">&larr; Zurueck zur Startseite</router-link>
    </div>

    <CrawlStatus
      v-if="showStatus"
      :crawl-id="crawlId"
      @completed="onCompleted"
      @failed="onFailed"
    />

    <ResultViewer
      v-if="showResult"
      :crawl-id="crawlId"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import CrawlStatus from '../components/CrawlStatus.vue'
import ResultViewer from '../components/ResultViewer.vue'
import { useCrawlStore } from '../stores/crawl'

const route = useRoute()
const store = useCrawlStore()

const crawlId = computed(() => route.params.crawlId)
const status = ref('checking')
const showResult = ref(false)
const showStatus = ref(true)

async function checkInitialStatus() {
  try {
    const result = await store.getStatus(crawlId.value)
    status.value = result.status

    if (result.status === 'completed') {
      showResult.value = true
      showStatus.value = false
    } else if (result.status === 'failed') {
      showStatus.value = true
      showResult.value = false
    }
  } catch (e) {
    // If status check fails, show status component which will handle errors
    showStatus.value = true
  }
}

function onCompleted() {
  showResult.value = true
  showStatus.value = false
}

function onFailed() {
  showResult.value = false
}

onMounted(() => {
  checkInitialStatus()
})
</script>

<style scoped>
.back-link {
  margin-bottom: 1.5rem;
}

.back-link a {
  color: #4a90d9;
  text-decoration: none;
}

.back-link a:hover {
  text-decoration: underline;
}
</style>
