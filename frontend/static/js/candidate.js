/**
 * 候选人端组件（成员C实现）。
 * 页面：面试大厅 / 简历上传 / 岗位选择 / 历史记录。
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
      uploadResult: null,
      // 历史记录
      history: [],
    };
  },
  created() {
    this.loadJobs();
    this.loadHistory();
  },
  methods: {
    async loadJobs() {
      this.loading = true;
      this.error = "";
      try {
        const resp = await API.get("/api/candidate/jobs");
        this.jobs = API.unwrap(resp);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
    async loadHistory() {
      try {
        const resp = await API.get("/api/candidate/interviews");
        this.history = API.unwrap(resp);
      } catch (e) {
        this.history = [];
      }
    },
    onFileChange(e) {
      this.resumeForm.file = e.target.files[0] || null;
    },
    async uploadResume() {
      // TODO(成员C): 实现简历上传 → 后端解析 → 进入岗位选择/面试
      const fd = new FormData();
      fd.append("name", this.resumeForm.name);
      fd.append("email", this.resumeForm.email);
      if (this.resumeForm.file) fd.append("file", this.resumeForm.file);
      try {
        const resp = await API.upload("/api/candidate/resume", fd);
        this.uploadResult = API.unwrap(resp);
        alert("简历上传并解析成功！");
      } catch (e) {
        alert("上传失败：" + e.message);
      }
    },
    startInterview(job) {
      // TODO(成员C): 进入面试对话页（InterviewView），携带 job 信息
      alert(`开始面试岗位：${job.title}（功能开发中）`);
    },
  },
  template: `
  <div>
    <h4 class="mb-3">🎯 候选人端 · 面试大厅</h4>

    <ul class="nav nav-pills mb-3">
      <li class="nav-item"><a class="nav-link" :class="{active: page==='hall'}" href="#" @click.prevent="page='hall'">岗位大厅</a></li>
      <li class="nav-item"><a class="nav-link" :class="{active: page==='upload'}" href="#" @click.prevent="page='upload'">上传简历</a></li>
      <li class="nav-item"><a class="nav-link" :class="{active: page==='history'}" href="#" @click.prevent="page='history'">历史记录</a></li>
    </ul>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <!-- 岗位大厅 -->
    <div v-if="page === 'hall'">
      <div class="row">
        <div class="col-md-4 mb-3" v-for="job in jobs" :key="job.id">
          <div class="card h-100">
            <div class="card-body">
              <h5 class="card-title">{{ job.title }}</h5>
              <p class="card-text text-muted">{{ job.description }}</p>
              <span class="badge bg-secondary me-1" v-for="s in (job.skills||'').split(',')" :key="s">{{ s }}</span>
            </div>
            <div class="card-footer bg-white">
              <button class="btn btn-primary btn-sm" @click="startInterview(job)">开始面试</button>
            </div>
          </div>
        </div>
      </div>
      <p v-if="!loading && jobs.length === 0" class="text-muted">暂无岗位，请稍后刷新。</p>
    </div>

    <!-- 简历上传 -->
    <div v-if="page === 'upload'" class="col-md-6">
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">上传简历</h5>
          <form @submit.prevent="uploadResume">
            <div class="mb-3">
              <label class="form-label">姓名</label>
              <input class="form-control" v-model="resumeForm.name" required />
            </div>
            <div class="mb-3">
              <label class="form-label">邮箱</label>
              <input class="form-control" v-model="resumeForm.email" type="email" />
            </div>
            <div class="mb-3">
              <label class="form-label">简历文件（PDF / DOCX / TXT）</label>
              <input class="form-control" type="file" accept=".pdf,.docx,.doc,.txt" @change="onFileChange" />
            </div>
            <button class="btn btn-primary" type="submit">上传并解析</button>
          </form>
        </div>
      </div>
    </div>

    <!-- 历史记录 -->
    <div v-if="page === 'history'">
      <table class="table table-hover bg-white">
        <thead><tr><th>#</th><th>岗位</th><th>状态</th><th>总分</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td>{{ h.id }}</td>
            <td>{{ h.job_title }}</td>
            <td>{{ h.status }}</td>
            <td>{{ h.total_score }}</td>
            <td><button class="btn btn-sm btn-outline-primary" @click="$emit('view-report', h.id)">查看报告</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>`,
};
