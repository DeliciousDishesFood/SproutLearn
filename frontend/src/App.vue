<!-- 根组件：只承载路由出口与全局 toast。 -->
<script setup lang="ts">
import AppToast from '@/components/base/AppToast.vue'
</script>

<template>
  <router-view />
  <AppToast />
</template>
