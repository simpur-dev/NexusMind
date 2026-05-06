<template>
  <RouterView />
</template>

<script setup>
import { RouterView } from 'vue-router'
</script>

<style>
:root {
  color-scheme: light;
  --nm-text: #0A0A0C;
  --nm-page: #FAFAFC;
  --nm-scroll-track: #F2F4F8;
  --nm-scroll-cool: #A7F9FF;
  --nm-scroll-main: #887DFF;
  --nm-scroll-warm: #FF68D6;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100vh;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--nm-text);
  background: var(--nm-page);
}

html,
body {
  scrollbar-width: thin;
  scrollbar-color: var(--nm-scroll-main) var(--nm-scroll-track);
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--nm-scroll-track);
  border-left: 1px solid #E6E8EF;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--nm-scroll-cool), var(--nm-scroll-main));
  border: 2px solid var(--nm-scroll-track);
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, var(--nm-scroll-main), var(--nm-scroll-warm));
}

button {
  font-family: inherit;
}
</style>
