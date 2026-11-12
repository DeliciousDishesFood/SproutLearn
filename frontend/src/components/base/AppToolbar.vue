<!-- 工具栏：左侧搜索/筛选、中间扩展、右侧主动作的统一换行与间距。 -->
<template>
  <div class="app-toolbar">
    <div v-if="$slots.left" class="app-toolbar__group app-toolbar__group--left">
      <slot name="left" />
    </div>
    <div v-if="$slots.default" class="app-toolbar__group app-toolbar__group--center">
      <slot />
    </div>
    <div v-if="$slots.right" class="app-toolbar__group app-toolbar__group--right">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
.app-toolbar {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.app-toolbar__group {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex-wrap: wrap;
}

.app-toolbar__group--center {
  min-width: 0;
  flex: 1 1 auto;
}

.app-toolbar__group--right {
  margin-left: auto;
  flex-shrink: 0;
}

@media (max-width: 720px) {
  .app-toolbar__group--right {
    margin-left: 0;
  }
}
</style>
