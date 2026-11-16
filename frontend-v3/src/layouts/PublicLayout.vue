<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

const { theme, toggle } = useTheme()
</script>

<template>
  <div class="login-body">
    <button
      class="icon-btn theme-fab"
      type="button"
      :aria-label="theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'"
      @click="toggle"
    >
      <Sun v-if="theme === 'dark'" :size="16" />
      <Moon v-else :size="16" />
    </button>
    <slot />
  </div>
</template>
