<template>
  <div class="recommendations-section">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 为你推荐 -->
      <el-tab-pane label="为你推荐" name="personalized">
        <div v-loading="personalizedLoading" class="rec-container">
          <template v-if="personalizedItems.length > 0">
            <el-alert v-if="personalizedData.type === 'popular'" title="暂无您的借阅记录，以下为热门图书推荐"
              type="info" :closable="false" show-icon class="rec-tip" />
            <el-alert v-else :title="`基于您偏好的「${(personalizedData.preferred_categories||[]).join('、')}」类别推荐`"
              type="success" :closable="false" show-icon class="rec-tip" />

            <div class="book-grid">
              <el-card v-for="b in personalizedItems" :key="b.book_id" shadow="hover"
                class="book-card" body-style="padding:0" @click="$router.push(`/books/${b.book_id}`)">
                <div class="cover-wrap">
                  <img v-if="b.cover_url" :src="b.cover_url" :alt="b.title" loading="lazy" />
                  <div v-else class="no-cover"><el-icon size="32" color="#ccc"><Reading /></el-icon></div>
                </div>
                <div class="card-info">
                  <h4 class="book-title" :title="b.title">{{ b.title }}</h4>
                  <p class="book-author">{{ b.author || '--' }}</p>
                  <p class="reason-text">{{ b.reason }}</p>
                </div>
              </el-card>
            </div>
          </template>
          <el-empty v-else description="暂无推荐数据" :image-size="100" />
        </div>
      </el-tab-pane>

      <!-- 新书上架 -->
      <el-tab-pane label="新书上架" name="new">
        <div v-loading="newLoading" class="rec-container">
          <template v-if="newBooks.length > 0">
            <el-alert :title="`最近 ${newBooksDays} 天内新入库 ${newBooksCount} 本图书`"
              type="info" :closable="false" show-icon class="rec-tip" />
            <div class="book-grid">
              <el-card v-for="b in newBooks" :key="b.book_id" shadow="hover"
                class="book-card" body-style="padding:0" @click="$router.push(`/books/${b.book_id}`)">
                <div class="cover-wrap">
                  <img v-if="b.cover_url" :src="b.cover_url" :alt="b.title" loading="lazy" />
                  <div v-else class="no-cover"><el-icon size="32" color="#ccc"><Reading /></el-icon></div>
                  <span v-if="b.available_copies !== undefined" class="avail-badge" :class="{ available: b.available_copies > 0 }">
                    {{ b.available_copies > 0 ? '可借' : '借完' }}
                  </span>
                </div>
                <div class="card-info">
                  <h4 class="book-title" :title="b.title">{{ b.title }}</h4>
                  <p class="book-author">{{ b.author || '--' }}</p>
                  <p class="meta-line">{{ b.publisher || '' }} <span v-if="b.isbn">| ISBN: {{ b.isbn }}</span></p>
                  <p class="time-text">入库: {{ b.created_at }}</p>
                </div>
              </el-card>
            </div>
          </template>
          <el-empty v-else description="暂无新书数据" :image-size="100" />
        </div>
      </el-tab-pane>

      <!-- 热门排行 -->
      <el-tab-pane label="热门排行" name="hot">
        <div v-loading="hotLoading" class="rec-container">
          <template v-if="hotBooks.length > 0">
            <el-alert :title="`近 ${periodDays} 天热门借阅 TOP${hotBooks.length}`"
              type="warning" :closable="false" show-icon class="rec-tip" />
            <div class="rank-list">
              <div v-for="(b, idx) in hotBooks" :key="b.book_id" class="rank-item"
                @click="$router.push(`/books/${b.book_id}`)">
                <span class="rank-num" :class="{ top: idx < 3 }">{{ b.rank || idx + 1 }}</span>
                <div class="cover-sm">
                  <img v-if="b.cover_url" :src="b.cover_url" loading="lazy" />
                  <div v-else class="no-cover-sm"></div>
                </div>
                <div class="rank-info">
                  <h4>{{ b.title }}</h4>
                  <p>{{ b.author || '--' }}</p>
                </div>
                <span class="borrow-count">{{ b.borrow_count }}次</span>
              </div>
            </div>
          </template>
          <el-empty v-else description="暂无热门数据" :image-size="100" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Reading } from '@element-plus/icons-vue'
import request from '@/utils/request'

const activeTab = ref('personalized')

// ---- 为你推荐 ----
const personalizedLoading = ref(false)
const personalizedItems = ref([])
const personalizedData = ref({})
async function fetchPersonalized() {
  personalizedLoading.value = true
  try {
    const res = await request.get('/recommendations/personalized', { params: { limit: 8 } })
    personalizedData.value = res.data || {}
    personalizedItems.value = res.data?.items || []
  } catch { /* 静默 */ } finally { personalizedLoading.value = false }
}

// ---- 新书 ----
const newLoading = ref(false)
const newBooks = ref([])
const newBooksDays = ref(30)
const newBooksCount = ref(0)
async function fetchNewBooks() {
  newLoading.value = true
  try {
    const res = await request.get('/recommendations/new-books', { params: { days: 30, limit: 8 } })
    const d = res.data || {}
    newBooks.value = d.items || []
    newBooksDays.value = d.days || 30
    newBooksCount.value = d.total || 0
  } catch { /* 静默 */ } finally { newLoading.value = false }
}

// ---- 热门 ----
const hotLoading = ref(false)
const hotBooks = ref([])
const periodDays = ref(90)
async function fetchHotBooks() {
  hotLoading.value = true
  try {
    const res = await request.get('/recommendations/hot', { params: { days: 90, limit: 10 } })
    const d = res.data || {}
    hotBooks.value = d.items || []
    periodDays.value = d.period_days || 90
  } catch { /* 静默 */ } finally { hotLoading.value = false }
}

onMounted(() => {
  fetchPersonalized()
  fetchNewBooks()
  fetchHotBooks()
})
</script>

<style scoped lang="scss">
.recommendations-section {
  max-width: 1100px; margin: 0 auto;
}
.rec-container { min-height: 300px; }
.rec-tip { margin-bottom: 18px; }

// 图书卡片网格
.book-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 18px; padding: 4px;
}
.book-card {
  cursor: pointer; transition: transform 0.25s, box-shadow 0.25s;
  &:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0,0,0,0.12); }
}
.cover-wrap {
  position: relative; height: 200px; background: #f5f7fa; overflow: hidden;
  img { width: 100%; height: 100%; object-fit: cover; }
  .no-cover { height: 100%; display: flex; align-items: center; justify-content: center; }
  .avail-badge {
    position: absolute; top: 8px; right: 8px; padding: 2px 8px; border-radius: 10px;
    font-size: 11px; color: #fff; background: rgba(220, 223, 230, 0.85);
    &.available { background: rgba(103, 194, 58, 0.85); }
  }
}
.card-info { padding: 12px 14px; }
.book-title { font-size: 14px; font-weight: 600; margin: 0 0 4px; overflow: hidden;
  text-overflow: ellipsis; white-space: nowrap; color: #303133; }
.book-author { font-size: 12px; color: #909399; margin: 0 0 4px; }
.reason-text {
  font-size: 11px; color: #67C23A; margin: 0; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; max-width: 160px;
}
.meta-line { font-size: 11px; color: #c0c4cc; margin: 2px 0; }
.time-text { font-size: 11px; color: #909399; margin: 2px 0 0; }

// 排行榜
.rank-list { padding: 4px; }
.rank-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 8px; border-bottom: 1px solid #f2f3f5;
  cursor: pointer; border-radius: 6px; transition: background 0.2s;
  &:hover { background: #f5f7fa; }
}
.rank-num {
  width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 13px; font-weight: bold; color: #909399;
  background: #f0f2f5; flex-shrink: 0;
  &.top { background: linear-gradient(135deg, #F56C6C, #E6A23C); color: #fff; }
}
.cover-sm {
  width: 42px; height: 56px; border-radius: 4px; overflow: hidden; flex-shrink: 0; background: #eee;
  img { width: 100%; height: 100%; object-fit: cover; }
  .no-cover-sm { width: 100%; height: 100%; }
}
.rank-info { flex: 1; min-width: 0;
  h4 { font-size: 14px; margin: 0 0 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  p { font-size: 12px; color: #909399; margin: 0; }
}
.borrow-count {
  font-size: 13px; color: #E6A23C; font-weight: 600; flex-shrink: 0;
}
</style>
