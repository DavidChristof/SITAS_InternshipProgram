/**
 * 候选人端组件（成员C实现）。
 * 页面：面试大厅（岗位列表） / 简历上传 / 历史记录。
 *
 * 联调说明：
 *   jobs/interviews/resume/interview 已接真实 API（API.xxx）；候选人身份由根组件维护（localStorage），
 *   上传简历后获得 candidate_id 才能开始面试。语音转写接口推迟（联调 #5），暂保留 Mock。
 */
const CandidateView = {
  data() {
    return {
      page: "hall", // hall | upload | history
      jobs: [],
      loading: false,
      error: "",
      // 简历上传表单
      resumeForm: {
        name: "",
        email: "",
        file: null,
      },
      uploading: false,
      uploadResult: null, // 解析出的候选人档案
      // 历史记录
      history: [],
      historyLoading: false,
      // 正在创建面试的岗位 id
      startingId: null,
    };
  },
  computed: {
    // 当前候选人（由根组件注入）
    candidate() {
      return this.$root.candidate;
    },
  },
  created() {
    this.loadJobs();
    this.loadHistory();
  },
  methods: {
    /** 面试状态 → bootstrap 徽章样式 */
    statusClass(status) {
      const map = { pending: "bg-secondary", running: "bg-primary", finished: "bg-success" };
      return map[status] || "bg-secondary";
    },
    /** 得分 → 徽章颜色 */
    scoreBadge(score) {
      if (score == null) return "bg-secondary";
      return score >= 85 ? "bg-success" : score >= 70 ? "bg-primary" : "bg-warning";
    },
    /** 兼容列表接口两种返回形态：纯数组 / {list,total} */
    toList(r) {
      return Array.isArray(r) ? r : ((r && r.list) || []);
    },
    async loadJobs() {
      this.loading = true;
      this.error = "";
      try {
        const r = API.unwrap(await API.get("/api/candidate/jobs"));
        this.jobs = this.toList(r);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    async loadHistory() {
      this.historyLoading = true;
      const cid = this.candidate && this.candidate.id;
      if (!cid) {
        // 未上传简历尚无候选人身份，后端 /interviews 要求 candidate_id 必填
        this.historyLoading = false;
        return;
      }
      try {
        const r = API.unwrap(await API.get(`/api/candidate/interviews?candidate_id=${cid}`));
        this.history = this.toList(r);
      } catch (e) {
        this.history = [];
        this.error = "加载历史记录失败：" + e.message;
      } finally {
        this.historyLoading = false;
      }
    },
    goPage(p) {
      this.page = p;
      if (p === "history") this.loadHistory();
    },
    onFileChange(e) {
      this.resumeForm.file = e.target.files[0] || null;
    },
    /** 上传简历 → 解析 → 保存候选人身份 → 展示结果 */
    async uploadResume() {
      if (!this.resumeForm.file) {
        alert("请先选择简历文件（PDF / DOCX / TXT）");
        return;
      }
      this.uploading = true;
      this.error = "";
      const fd = new FormData();
      fd.append("name", this.resumeForm.name);
      fd.append("email", this.resumeForm.email);
      fd.append("file", this.resumeForm.file);
      try {
        const profile = API.unwrap(await API.upload("/api/candidate/resume", fd));
        this.uploadResult = profile;
        this.$root.setCandidate(profile); // 保存候选人身份，供选岗面试使用
        alert("简历上传并解析成功！");
      } catch (e) {
        this.error = "上传失败：" + e.message;
      } finally {
        this.uploading = false;
      }
    },
    /** 开始面试：需先有候选人身份，创建面试后跳转对话视图 */
    async startInterview(job) {
      if (!this.candidate) {
        alert("请先在上传简历页提交简历，获得候选人身份后再开始面试。");
        this.page = "upload";
        return;
      }
      this.startingId = job.id;
      this.error = "";
      try {
        const resp = API.unwrap(
          await API.post("/api/candidate/interview", { candidate_id: this.candidate.id, job_id: job.id })
        );
        const interviewId = resp.interview_id;
        this.$emit("start-interview", { id: interviewId, jobId: job.id, jobTitle: job.title });
      } catch (e) {
        this.error = "创建面试失败：" + e.message;
      } finally {
        this.startingId = null;
      }
    },
    /** 查看历史报告（仅已完成） */
    viewReport(id) {
      this.$emit("view-report", id);
    },
  },
  template: `
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">🎯 候选人端</h4>
      <div class="text-muted">
        <template v-if="candidate">
          <span class="badge bg-success me-1">已就绪</span>
          你好，<strong>{{ candidate.name }}</strong>
        </template>
        <template v-else>
          <span class="badge bg-warning text-dark me-1">未上传简历</span>
          上传简历后即可开始面试
        </template>
      </div>
    </div>

    <ul class="nav nav-pills mb-3">
      <li class="nav-item"><a class="nav-link" :class="{active: page==='hall'}" href="#" @click.prevent="goPage('hall')">岗位大厅</a></li>
      <li class="nav-item"><a class="nav-link" :class="{active: page==='upload'}" href="#" @click.prevent="goPage('upload')">上传简历</a></li>
      <li class="nav-item"><a class="nav-link" :class="{active: page==='history'}" href="#" @click.prevent="goPage('history')">历史记录</a></li>
    </ul>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <!-- ===== 岗位大厅 ===== -->
    <div v-if="page === 'hall'">
      <div v-if="loading" class="text-center text-muted py-4">
        <div class="spinner-border spinner-border-sm me-2" role="status"></div>岗位加载中…
      </div>
      <div v-else-if="jobs.length === 0" class="text-center text-muted py-4">
        暂无岗位，请稍后刷新。
      </div>
      <div v-else class="row">
        <div class="col-md-4 mb-3" v-for="job in jobs" :key="job.id">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{{ job.title }}</h5>
              <p class="card-text text-muted small mb-2">
                <span v-if="job.enterprise_name" class="me-2">🏢 {{ job.enterprise_name }}</span>
              </p>
              <p class="card-text text-muted" style="min-height: 2.4rem;">{{ job.description }}</p>
              <div>
                <span class="badge bg-secondary me-1 mb-1" v-for="s in (job.skills||'').split(',').filter(Boolean)" :key="s">{{ s }}</span>
              </div>
            </div>
            <div class="card-footer bg-white">
              <button class="btn btn-primary btn-sm w-100" @click="startInterview(job)" :disabled="startingId === job.id">
                <span v-if="startingId === job.id" class="spinner-border spinner-border-sm me-1"></span>
                开始面试
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 简历上传 ===== -->
    <div v-if="page === 'upload'" class="row">
      <div class="col-md-6">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">上传简历</h5>
            <form @submit.prevent="uploadResume">
              <div class="mb-3">
                <label class="form-label">姓名</label>
                <input class="form-control" v-model="resumeForm.name" placeholder="请输入姓名" />
              </div>
              <div class="mb-3">
                <label class="form-label">邮箱</label>
                <input class="form-control" v-model="resumeForm.email" type="email" placeholder="用于接收面试通知" />
              </div>
              <div class="mb-3">
                <label class="form-label">简历文件（PDF / DOCX / TXT）</label>
                <input class="form-control" type="file" accept=".pdf,.docx,.doc,.txt" @change="onFileChange" />
              </div>
              <button class="btn btn-primary w-100" type="submit" :disabled="uploading">
                <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
                {{ uploading ? '解析中…' : '上传并解析' }}
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-md-6" v-if="uploadResult">
        <div class="card border-success">
          <div class="card-header bg-success text-white">✅ 解析结果（候选人档案）</div>
          <div class="card-body">
            <p class="mb-1"><strong>姓名：</strong>{{ uploadResult.name }}</p>
            <p class="mb-1"><strong>邮箱：</strong>{{ uploadResult.email || '—' }}</p>
            <p class="mb-1"><strong>电话：</strong>{{ uploadResult.phone || '—' }}</p>
            <p class="mb-1"><strong>状态：</strong><span class="badge bg-success">{{ uploadResult.status }}</span></p>
            <p class="text-muted small mb-0">{{ uploadResult.resume_text }}</p>
            <button class="btn btn-outline-success btn-sm mt-3" @click="page='hall'">去大厅选岗面试 →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 历史记录 ===== -->
    <div v-if="page === 'history'">
      <div v-if="historyLoading" class="text-center text-muted py-4">
        <div class="spinner-border spinner-border-sm me-2" role="status"></div>加载中…
      </div>
      <div v-else-if="history.length === 0" class="text-center text-muted py-4">
        暂无面试记录，去大厅开始一场面试吧。
      </div>
      <table v-else class="table table-hover bg-white align-middle">
        <thead><tr><th>#</th><th>岗位</th><th>状态</th><th>总分</th><th>时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td>{{ h.id }}</td>
            <td>{{ h.job_title }}</td>
            <td><span class="badge" :class="statusClass(h.status)">{{ h.status }}</span></td>
            <td>
              <span v-if="h.total_score != null" class="badge" :class="scoreBadge(h.total_score)">{{ h.total_score }}</span>
              <span v-else class="text-muted">—</span>
            </td>
            <td>{{ h.created_at }}</td>
            <td>
              <button v-if="h.status === 'finished'" class="btn btn-sm btn-outline-primary" @click="viewReport(h.id)">查看报告</button>
              <button v-else class="btn btn-sm btn-outline-secondary" disabled>进行中</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>`,
};
