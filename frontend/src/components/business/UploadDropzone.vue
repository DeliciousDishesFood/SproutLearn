<!-- 拖拽上传区：整宽虚线框，hover/拖入转主色浅底，键盘可触发文件选择。 -->
<script setup lang="ts">
import { ref } from 'vue'
import { FileUp, UploadCloud } from 'lucide-vue-next'
import {
  MAX_FILES_PER_REQUEST,
  MAX_TOTAL_UPLOAD_MB,
  UPLOAD_ACCEPT,
  UPLOAD_ALLOWED_EXT,
  UPLOAD_MAX_MB,
} from '@/utils/constants'

withDefaults(
  defineProps<{
    disabled?: boolean
    hint?: string
  }>(),
  {
    disabled: false,
    hint: '',
  },
)

const emit = defineEmits<{
  (event: 'files', files: File[]): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragDepth = ref(0)
const dragActive = ref(false)

function openPicker(): void {
  if (!inputRef.value) return
  inputRef.value.value = ''
  inputRef.value.click()
}

function emitFiles(list: FileList | null): void {
  if (!list) return
  const files = Array.from(list)
  if (files.length > 0) emit('files', files)
}

function onInputChange(event: Event): void {
  emitFiles((event.target as HTMLInputElement).files)
}

function onDragEnter(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value += 1
  dragActive.value = true
}

function onDragOver(event: DragEvent): void {
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (dragDepth.value === 0) dragActive.value = false
}

function onDrop(event: DragEvent): void {
  event.preventDefault()
  dragDepth.value = 0
  dragActive.value = false
  emitFiles(event.dataTransfer?.files ?? null)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openPicker()
  }
}

const extLabel = UPLOAD_ALLOWED_EXT.map((ext) => ext.toUpperCase()).join(' / ')
</script>

<template>
  <div
    class="dropzone"
    :class="{ 'dropzone--active': dragActive, 'dropzone--disabled': disabled }"
    role="button"
    tabindex="0"
    :aria-disabled="disabled"
    aria-label="上传文档：点击选择或拖拽文件到此处"
    @click="disabled ? undefined : openPicker()"
    @keydown="onKeydown"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <input
      ref="inputRef"
      class="dropzone__input"
      type="file"
      multiple
      :accept="UPLOAD_ACCEPT"
      :disabled="disabled"
      @change="onInputChange"
    />

    <span class="dropzone__icon" aria-hidden="true">
      <UploadCloud v-if="!dragActive" :size="25" :stroke-width="1.7" />
      <FileUp v-else :size="25" :stroke-width="1.7" />
    </span>

    <div class="dropzone__copy">
      <p class="dropzone__title">{{ dragActive ? '松开即可加入上传队列' : '拖拽文档到这里' }}</p>
      <p class="dropzone__sub">
        或 <button class="dropzone__link" type="button" :disabled="disabled" @click.stop="openPicker">选择文件</button>
        上传课程资料
      </p>
      <p class="dropzone__hint">
        支持 {{ extLabel }} · 单个文件不超过 {{ UPLOAD_MAX_MB }}MB · 单次最多 {{ MAX_FILES_PER_REQUEST }} 个 ·
        合计不超过 {{ MAX_TOTAL_UPLOAD_MB }}MB
      </p>
      <p v-if="hint" class="dropzone__hint dropzone__hint--extra">{{ hint }}</p>
    </div>
  </div>
</template>

<style scoped>
.dropzone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-4);
  width: 100%;
  min-height: 168px;
  padding: var(--sp-6) var(--sp-5);
  border: 2px dashed var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  transition: border-color 170ms ease-out, background-color 170ms ease-out;
}

.dropzone:hover,
.dropzone:focus-visible {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  outline: none;
}

.dropzone--active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.dropzone--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dropzone__input {
  display: none;
}

.dropzone__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border: 1px solid color-mix(in srgb, var(--color-primary) 22%, transparent);
  border-radius: 999px;
  color: var(--color-primary);
  background: var(--color-surface);
}

.dropzone--active .dropzone__icon {
  color: var(--color-accent);
  background: var(--color-surface);
}

.dropzone__copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dropzone__title {
  font-size: var(--fs-lg);
  font-weight: 600;
}

.dropzone__sub {
  color: var(--color-text-muted);
  font-size: var(--fs-sm);
}

.dropzone__link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.dropzone__link:disabled {
  cursor: not-allowed;
}

.dropzone__hint {
  margin-top: var(--sp-1);
  color: color-mix(in srgb, var(--color-text-muted) 88%, transparent);
  font-size: var(--fs-xs);
  line-height: 1.6;
}

.dropzone__hint--extra {
  color: var(--color-warning);
}

@media (max-width: 720px) {
  .dropzone {
    flex-direction: column;
    gap: var(--sp-3);
    min-height: 190px;
    padding: var(--sp-5) var(--sp-4);
    text-align: center;
  }

  .dropzone__copy {
    align-items: center;
  }
}
</style>
