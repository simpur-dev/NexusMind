<template>
  <router-view />
</template>

<script setup>
// 使用 Vue Router 来管理页面
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #0A0A0C;
  background: #FAFAFC;
  min-height: 100vh;
  margin: 0;
  padding: 0;
}

/* 渐变主题滚动条 */
html,
body {
  scrollbar-width: thin;
  scrollbar-color: #887DFF #F2F4F8;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #F2F4F8;
  border-left: 1px solid #E6E8EF;
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #A7F9FF, #887DFF);
  border: 2px solid #F2F4F8;
  border-radius: 999px;
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #887DFF, #FF68D6);
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
