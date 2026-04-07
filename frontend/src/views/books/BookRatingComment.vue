<template>
  <div class="book-rating-comment" v-if="bookId">
    <!-- 评分区域 -->
    <el-card shadow="never" class="rating-card">
      <template #header>
        <div class="section-header">
          <span>图书评分</span>
          <span v-if="ratingData.total_ratings > 0" class="avg-display">
            <span class="avg-num">{{ ratingData.average_rating }}</span>
            <el-rate v-model="ratingData.average_rating" disabled :max="5"
              :colors="['#F7BA2A', '#F7BA2A', '#FF9900']" style="display:inline;vertical-align:middle;margin-left:6px" />
            <span class="total-text">({{ ratingData.total_ratings }}人评价)</span>
          </span>
        </div>
      </template>

      <!-- 评分分布条 -->
      <div v-if="ratingData.distribution" class="distribution-bars">
        <div v-for="i in 5" :key="i" class="dist-row">
          <span class="star-label">{{ 6 - i }}星</span>
          <el-progress :percentage="getDistPercent(6 - i)"
            :stroke-width="8" :show-text="false" color="#E6A23C" />
          <span class="count">{{ ratingData.distribution[6 - i] || 0 }}</span>
        </div>
      </div>

      <!-- 我的评分 -->
      <div class="my-rating">
        <template v-if="!isLogin">
          <span>请先登录后评分</span>
        </template>
        <template v-else>
          <span>我的评分：</span>
          <el-rate v-model="myRate" allow-half :max="5"
            :colors="['#F7BA2A', '#F7BA2A', '#FF9900']"
            @change="handleRateChange"
            :disabled="rateLoading" />
        </template>
      </div>
    </el-card>

    <!-- 评论区域 -->
    <el-card shadow="never" class="comment-card">
      <template #header>
        <div class="section-header">
          <span>读者评论 ({{ commentTotal }})</span>
          <el-button type="primary" size="small" @click="showCommentDialog = true"
            v-if="isLogin">
            写评论
          </el-button>
        </div>
      </template>

      <!-- 评论列表 -->
      <div v-if="commentList.length === 0 && !commentLoading" class="empty-state">
        <el-empty description="暂无评论，快来发表第一条吧~" :image-size="80" />
      </div>
      <div v-else class="comment-list" v-loading="commentLoading">
        <div v-for="c in commentList" :key="c.comment_id" class="comment-item">
          <div class="comment-meta">
            <span class="user-name">{{ c.username || '匿名' }}</span>
            <span class="comment-time">{{ c.created_at }}</span>
          </div>
          <p class="comment-content">{{ c.content }}</p>
          <div v-if="c.admin_reply" class="admin-reply">
            <el-tag size="small" type="info">馆方回复</el-tag>
            {{ c.admin_reply }}
          </div>
        </div>
      </div>

      <div class="pagination-wrapper" v-if="commentTotal > commentPageSize">
        <el-pagination v-model:current-page="commentPage" :total="commentTotal"
          :page-size="commentPageSize" layout="prev, pager, next"
          small @current-change="fetchComments" />
      </div>
    </el-card>

    <!-- 发表评论对话框 -->
    <el-dialog v-model="showCommentDialog" title="发表评论" width="500px"
      :close-on-click-modal="false">
      <el-alert title="请文明发言，评论需经管理员审核后公开显示"
        type="warning" :closable="false" show-icon style="margin-bottom:16px" />
      <el-input v-model="newComment" type="textarea" :rows="4" maxlength="1000"
        show-word-limit placeholder="分享您的阅读感受..." />
      <template #footer>
        <el-button @click="showCommentDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitComment">发表</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const props = defineProps({
  bookId: { type: [Number, String], required: true },
})

const isLogin = computed(() => !!localStorage.getItem('access_token'))

// ============ 评分 ============
const rateLoading = ref(false)
const myRate = ref(0)
const ratingData = ref({ total_ratings: 0, average_rating: 0, distribution: {}, my_rating: null })

async function fetchRatings() {
  try {
    const res = await request.get(`/books/${props.bookId}/ratings`)
    const d = res.data || {}
    ratingData.value = {
      total_ratings: d.total_ratings || 0,
      average_rating: d.average_rating || 0,
      distribution: d.distribution || {},
      my_rating: d.my_rating,
    }
    if (d.my_rating != null) myRate.value = d.my_rating
  } catch {
    /* 静默 */
  }
}

function getDistPercent(star) {
  const total = ratingData.value.total_ratings || 1
  return Math.round(((ratingData.value.distribution?.[star] || 0) / total) * 100)
}

async function handleRateChange(val) {
  if (!val) return
  rateLoading.value = true
  try {
    await request.post(`/books/${props.bookId}/ratings`, { book_id: Number(props.bookId), rating: val })
    ElMessage.success(val > 3 ? '感谢好评！' : '感谢您的评价')
    fetchRatings()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '评分失败')
    // 回滚
    fetchRatings()
  } finally {
    rateLoading.value = false
  }
}

// ============ 评论 ============
const commentLoading = ref(false)
const submitLoading = ref(false)
const showCommentDialog = ref(false)
const newComment = ref('')
const commentList = ref([])
const commentPage = ref(1)
const commentTotal = ref(0)
const commentPageSize = 20

async function fetchComments() {
  commentLoading.value = true
  try {
    const res = await request.get(`/books/${props.bookId}/comments`, {
      params: { page: commentPage.value, size: commentPageSize }
    })
    const d = res.data || {}
    commentList.value = d.items || []
    commentTotal.value = d.total || 0
  } catch {
    /* 静默 */
  } finally {
    commentLoading.value = false
  }
}

async function submitComment() {
  const text = newComment.value.trim()
  if (text.length < 2) {
    ElMessage.warning('评论内容至少需要2个字符')
    return
  }
  submitLoading.value = true
  try {
    await request.post(`/books/${props.bookId}/comments`, {
      book_id: Number(props.bookId),
      content: text,
    })
    ElMessage.success('评论已提交，审核通过后将展示')
    showCommentDialog.value = false
    newComment.value = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitLoading.value = false
  }
}

// ============ 初始化 ============
watch(() => props.bookId, () => {
  if (props.bookId) {
    fetchRatings()
    fetchComments()
  }
}, { immediate: true })
</script>

<style scoped lang="scss">
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.avg-display {
  .avg-num { font-size: 24px; font-weight: bold; color: #F7BA2A; margin-right: 4px; }
  .total-text { color: #909399; font-size: 13px; margin-left: 8px; }
}
.rating-card, .comment-card { margin-bottom: 16px; }

// 评分分布
.distribution-bars { padding: 12px 0; }
.dist-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 6px;
  .star-label { width: 30px; font-size: 13px; color: #606266; }
  .count { width: 28px; font-size: 13px; color: #909399; text-align: right; }
}
.my-rating {
  display: flex; align-items: center; gap: 10px;
  margin-top: 16px; padding-top: 14px; border-top: 1px solid #ebeef5;
  font-size: 14px;
}

// 评论列表
.comment-list { min-height: 120px; }
.comment-item {
  padding: 14px 0; border-bottom: 1px solid #f0f2f5;
  &:last-child { border-bottom: none; }
}
.comment-meta {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;
  .user-name { font-weight: 600; color: #409EFF; font-size: 13px; }
  .comment-time { color: #c0c4cc; font-size: 12px; }
}
.comment-content { line-height: 1.6; color: #303133; font-size: 14px; margin: 0; word-break: break-all; }
.admin-reply {
  margin-top: 10px; padding: 10px 12px; background: #f5f7fa; border-radius: 6px;
  font-size: 13px; color: #606266; line-height: 1.5;
}
.empty-state { padding: 20px 0; }
.pagination-wrapper { margin-top: 16px; display: flex; justify-content: center; }
</style>
