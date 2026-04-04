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

/* 滚动条样式 */
html,
body {
  scrollbar-width: thin;
  scrollbar-color: rgba(131, 231, 255, 0.72) rgba(8, 20, 36, 0.88);
}

::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

::-webkit-scrollbar-track {
  background: linear-gradient(180deg, rgba(6, 17, 31, 0.96), rgba(10, 26, 46, 0.92));
  border-left: 1px solid rgba(126, 236, 255, 0.08);
}

::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(174, 245, 255, 0.92), rgba(83, 203, 255, 0.88) 34%, rgba(33, 110, 214, 0.92) 100%);
  border: 2px solid rgba(7, 20, 36, 0.96);
  border-radius: 999px;
  box-shadow:
    inset 0 0 0 1px rgba(229, 252, 255, 0.18),
    0 0 16px rgba(90, 205, 255, 0.22);
}

::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(216, 252, 255, 0.96), rgba(109, 221, 255, 0.92) 34%, rgba(47, 127, 228, 0.96) 100%);
  box-shadow:
    inset 0 0 0 1px rgba(240, 253, 255, 0.22),
    0 0 20px rgba(102, 214, 255, 0.3);
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}
</style>
