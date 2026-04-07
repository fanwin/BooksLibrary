<template>
  <div class="placeholder page-container">
    <el-card>
      <template #header>
        <span>{{ title }}</span>
      </template>
      <el-empty :description="`${title}模块开发中...`" />
    </el-card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => route.meta.title || '页面')
</script>
