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
  color: #000000;
  

  background:  radial-gradient(circle, #1e88e5, #00a1f3, #00b9fb, #00cfff, #00e5ff);
  min-height: 100vh; /* 让背景铺满整个屏幕 */
  margin: 0;
  padding: 0;
}

/* 滚动条：与导航栏浅蓝系 #73A8B9 / #E6F2F7 / #F8FAFC 一致 */
html,
body {
  scrollbar-width: thin;
  scrollbar-color: #73a8b9 #e6f2f7;
}

::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}

::-webkit-scrollbar-track {
  background: #e6f2f7;
  border-left: 1px solid rgba(115, 168, 185, 0.12);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #8ebdcb, #73a8b9);
  border: 2px solid #e6f2f7;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(248, 250, 252, 0.5);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #73a8b9, #5c9eaf);
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
