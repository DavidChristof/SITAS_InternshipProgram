/**
 * HR/教师后台管理组件（成员C实现）。
 * 管理：企业 / 岗位 / 候选人 / 面试官 / 题库 / 面试记录。
 */
const AdminView = {
  data() {
    return {
      tab: "enterprise", // enterprise | job | candidate | interviewer | question | interview
      enterprises: [],
      jobs: [],
      candidates: [],
      interviewers: [],
      questions: [],
      interviews: [],
      error: "",
    };
  },
  created() {
    this.refreshAll();
  },
  methods: {
    async refreshAll() {
      // TODO(成员C): 逐项拉取各管理列表，这里先做岗位/企业示例
      try {
        const resp = await API.get("/api/admin/jobs");
        this.jobs = API.unwrap(resp);
      } catch (e) {
        this.error = e.message;
      }
    },
    async loadTab(tab) {
      this.tab = tab;
      this.error = "";
      const endpoints = {
        enterprise: "/api/admin/enterprises",
        job: "/api/admin/jobs",
        candidate: "/api/admin/candidates",
        interviewer: "/api/admin/interviewers",
        question: "/api/admin/questions",
        interview: "/api/admin/interviews",
      };
      const key = tab;
      try {
        const resp = await API.get(endpoints[key]);
        this[key + "s"] = API.unwrap(resp);
      } catch (e) {
        this.error = "接口未实现：" + e.message;
      }
    },
    // TODO(成员C): 增删改查、题库编辑表单、面试记录查看
  },
  template: `
  <div>
    <h4 class="mb-3">🛠 后台管理</h4>
    <ul class="nav nav-pills mb-3">
      <li class="nav-item" v-for="t in [
        {k:'enterprise', t:'企业'}, {k:'job', t:'岗位'}, {k:'candidate', t:'候选人'},
        {k:'interviewer', t:'面试官'}, {k:'question', t:'题库'}, {k:'interview', t:'面试记录'}]"
        :key="t.k">
        <a class="nav-link" :class="{active: tab===t.k}" href="#" @click.prevent="loadTab(t.k)">{{ t.t }}</a>
      </li>
    </ul>
    <div v-if="error" class="alert alert-warning">{{ error }}</div>

    <div v-if="tab === 'enterprise'">
      <div class="card"><div class="card-body">
        <table class="table"><thead><tr><th>ID</th><th>企业名称</th><th>行业</th><th>简介</th></tr></thead>
        <tbody><tr v-for="e in enterprises" :key="e.id"><td>{{e.id}}</td><td>{{e.name}}</td><td>{{e.industry}}</td><td>{{e.description}}</td></tr></tbody></table>
        <p class="text-muted small">企业管理的增删改查由成员C + 成员B 完成。</p>
      </div></div>
    </div>

    <div v-if="tab === 'job'">
      <div class="card"><div class="card-body">
        <table class="table"><thead><tr><th>ID</th><th>岗位</th><th>技能</th><th>操作</th></tr></thead>
        <tbody><tr v-for="j in jobs" :key="j.id"><td>{{j.id}}</td><td>{{j.title}}</td><td>{{j.skills}}</td><td>编辑/删除</td></tr></tbody></table>
      </div></div>
    </div>

    <div v-if="tab === 'candidate'" class="text-muted">候选人管理（待实现）</div>
    <div v-if="tab === 'interviewer'" class="text-muted">面试官管理（待实现）</div>
    <div v-if="tab === 'question'" class="text-muted">题库管理（待实现）</div>
    <div v-if="tab === 'interview'" class="text-muted">面试记录管理（待实现）</div>
  </div>`,
};
