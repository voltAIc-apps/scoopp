<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-brand">
        <router-link to="/">Scoopp</router-link>
      </div>
      <div class="nav-links">
        <router-link to="/history">Historie</router-link>
        <a href="http://192.168.2.93:8001/playground" target="_blank">Playground</a>
        <a href="http://192.168.2.93:8001/docs" target="_blank">API Docs</a>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.navbar {
  background: #1a1a2e;
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand a {
  font-size: 1.5rem;
  font-weight: bold;
  color: white;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
}

.nav-links a {
  color: #ccc;
  text-decoration: none;
  transition: color 0.2s;
}

.nav-links a:hover {
  color: white;
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
