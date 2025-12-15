<template>
  <div class="card result-viewer">
    <div class="result-header">
      <h3>Ergebnis: {{ result.url }}</h3>
      <div class="result-meta">
        <span class="timestamp">{{ formatTime(result.timestamp) }}</span>
      </div>
    </div>

    <div class="result-actions">
      <button class="btn btn-secondary" @click="copyToClipboard">
        {{ copied ? 'Kopiert!' : 'Markdown kopieren' }}
      </button>
      <button class="btn btn-secondary" @click="downloadMarkdown">
        Herunterladen
      </button>
    </div>

    <!-- Single page markdown result -->
    <div v-if="result.markdown" class="markdown-content" v-html="renderedMarkdown"></div>

    <!-- Multi-page crawl results -->
    <div v-else-if="result.results" class="multi-results">
      <div v-for="(item, index) in result.results" :key="index" class="result-item">
        <h4>{{ item.url || `Seite ${index + 1}` }}</h4>
        <div class="markdown-content" v-html="renderMarkdown(item.markdown || item.content || JSON.stringify(item))"></div>
      </div>
    </div>

    <div v-else class="no-content">
      Kein Inhalt verfuegbar
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

const copied = ref(false)

const renderedMarkdown = computed(() => {
  if (!props.result.markdown) return ''
  return md.render(props.result.markdown)
})

function renderMarkdown(content) {
  if (!content) return ''
  return md.render(content)
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('de-DE')
}

function getMarkdownContent() {
  if (props.result.markdown) {
    return props.result.markdown
  }
  if (props.result.results) {
    return props.result.results
      .map(r => `# ${r.url || 'Seite'}\n\n${r.markdown || r.content || ''}`)
      .join('\n\n---\n\n')
  }
  return ''
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(getMarkdownContent())
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    console.error('Kopieren fehlgeschlagen:', e)
  }
}

function downloadMarkdown() {
  const content = getMarkdownContent()
  const blob = new Blob([content], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `crawl-${Date.now()}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #ddd;
}

.result-header h3 {
  margin: 0;
  word-break: break-all;
}

.result-meta {
  color: #666;
  font-size: 0.875rem;
}

.result-actions {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.markdown-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 1rem;
  background: #fafafa;
  border-radius: 4px;
}

.multi-results .result-item {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #ddd;
}

.multi-results .result-item h4 {
  color: #1a1a2e;
  margin-bottom: 1rem;
  word-break: break-all;
}

.no-content {
  text-align: center;
  color: #666;
  padding: 2rem;
}
</style>
