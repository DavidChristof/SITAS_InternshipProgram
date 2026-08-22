/**
 * HR/教师后台管理组件（成员C实现）。
 * 管理：企业 / 岗位 / 候选人 / 面试官 / 题库 / 面试记录。
 *
 * 设计：配置驱动 —— 每个资源在 meta 中声明列(columns)、表单字段(fields)、接口(endpoint)，
 *       通用表格 + 弹窗表单 + 删除确认 + 分页。
 * 进度：阶段一完成 企业/岗位；候选人/面试官/题库（阶段二）、面试记录（阶段四）打开 built 开关即可。
 * 联调：已全部接真实 API（API.get/post/put/del）。
 */
const AdminView = {
  data() {
    return {
      tab: "enterprise",
      error: "",
      // 供岗位/题目表单选择的企业、岗位与候选人列表
      enterprises: [],
      allJobs: [],
      candidates: [],
      // 面试记录筛选条件
      filters: { interview: { status: "", job_id: "", candidate_id: "" } },
      // 面试记录详情弹窗
      detail: null,
      detailRow: null,
      detailLoading: false,
      detailError: "",
      // 各资源的状态
      lists: {}, // lists[resource] = []
      totals: {}, // totals[resource] = number
      pages: {}, // pages[resource] = page
      sizes: {}, // sizes[resource] = size
      loading: {}, // loading[resource] = bool
      // 弹窗表单
      form: {},
      formMode: "add", // add | edit
      editId: null,
      saving: false,
      // 资源配置
      meta: {
        enterprise: {
          label: "企业", endpoint: "/api/admin/enterprises", built: true,
          columns: [
            { key: "name", label: "企业名称" },
            { key: "industry", label: "行业" },
            { key: "description", label: "简介", truncate: true },
            { key: "created_at", label: "创建时间" },
          ],
          fields: [
            { key: "name", label: "企业名称", required: true },
            { key: "industry", label: "所属行业" },
            { key: "description", label: "企业简介", type: "textarea" },
          ],
        },
        job: {
          label: "岗位", endpoint: "/api/admin/jobs", built: true,
          columns: [
            { key: "title", label: "岗位名称" },
            { key: "enterprise_name", label: "所属企业" },
            { key: "skills", label: "技能" },
            { key: "description", label: "岗位描述", truncate: true },
          ],
          fields: [
            { key: "title", label: "岗位名称", required: true },
            {
              key: "enterprise_id", label: "所属企业", type: "select", required: true,
              options: () => this.enterprises.map((e) => ({ value: e.id, label: e.name })),
            },
            { key: "description", label: "岗位描述", type: "textarea" },
            { key: "requirements", label: "任职要求", type: "textarea" },
            { key: "skills", label: "技能关键词（逗号分隔）" },
          ],
        },
        candidate: {
          label: "候选人", endpoint: "/api/admin/candidates", built: true,
          format: { status: { active: "开放", closed: "关闭" } },
          columns: [
            { key: "name", label: "姓名" }, { key: "email", label: "邮箱" },
            { key: "phone", label: "电话" }, { key: "status", label: "状态" },
          ],
          fields: [
            { key: "name", label: "姓名", required: true },
            { key: "email", label: "邮箱" },
            { key: "phone", label: "电话" },
            {
              key: "status", label: "状态", type: "select",
              options: () => [{ value: "active", label: "开放" }, { value: "closed", label: "关闭" }],
            },
          ],
        },
        interviewer: {
          label: "面试官", endpoint: "/api/admin/interviewers", built: true,
          format: { role: { hr: "HR", teacher: "教师", admin: "管理员" } },
          columns: [
            { key: "name", label: "姓名" }, { key: "role", label: "角色" }, { key: "title", label: "职称" },
          ],
          fields: [
            { key: "name", label: "姓名", required: true },
            {
              key: "role", label: "角色", type: "select",
              options: () => [{ value: "hr", label: "HR" }, { value: "teacher", label: "教师" }, { value: "admin", label: "管理员" }],
            },
            { key: "title", label: "职称 / 职位" },
          ],
        },
        question: {
          label: "题库", endpoint: "/api/admin/questions", built: true,
          format: {
            category: { self_intro: "自我介绍", project: "项目经历", technical: "专业技能", behavioral: "综合素质", reverse: "反问环节" },
          },
          columns: [
            { key: "category", label: "环节" }, { key: "question", label: "题目", truncate: true },
            { key: "job_name", label: "关联岗位" }, { key: "difficulty", label: "难度" },
          ],
          fields: [
            {
              key: "job_id", label: "关联岗位（空为通用题）", type: "select",
              options: () => [
                { value: "", label: "（通用题）" },
                ...this.allJobs.map((j) => ({ value: j.id, label: j.title })),
              ],
            },
            {
              key: "category", label: "环节", type: "select",
              options: () => [
                { value: "self_intro", label: "自我介绍" }, { value: "project", label: "项目经历" },
                { value: "technical", label: "专业技能" }, { value: "behavioral", label: "综合素质" },
                { value: "reverse", label: "反问环节" },
              ],
            },
            { key: "question", label: "题目内容", required: true, type: "textarea" },
            { key: "expected_points", label: "评分要点（逗号分隔）" },
            { key: "sample_answer", label: "优秀回答样例", type: "textarea" },
            { key: "difficulty", label: "难度（1-5）", type: "number" },
          ],
        },
        interview: {
          label: "面试记录", endpoint: "/api/admin/interviews", built: true, readonly: true,
          format: { status: { pending: "待开始", running: "进行中", finished: "已完成", abandoned: "已放弃" } },
          columns: [
            { key: "id", label: "ID" }, { key: "candidate_name", label: "候选人" },
            { key: "job_title", label: "岗位" }, { key: "status", label: "状态" },
            { key: "total_score", label: "总分" }, { key: "created_at", label: "时间" },
          ],
          fields: [],
          filters: [
            {
              key: "status", label: "状态",
              options: () => [
                { value: "", label: "全部状态" }, { value: "pending", label: "待开始" },
                { value: "running", label: "进行中" }, { value: "finished", label: "已完成" },
                { value: "abandoned", label: "已放弃" },
              ],
            },
            {
              key: "job_id", label: "岗位",
              options: () => [{ value: "", label: "全部岗位" }, ...this.allJobs.map((j) => ({ value: j.id, label: j.title }))],
            },
            {
              key: "candidate_id", label: "候选人",
              options: () => [{ value: "", label: "全部候选人" }, ...this.candidates.map((c) => ({ value: c.id, label: c.name }))],
            },
          ],
        },
      },
    };
  },
  computed: {
    /** 当前身份（由根组件注入，方案A） */
    role() {
      return this.$root.role;
    },
    /** 按角色过滤后的管理页 tab（方案A C2）：HR 隐藏「面试官」；管理员追加「系统管理」 */
    adminTabs() {
      const base = [
        { k: "enterprise", t: "企业" }, { k: "job", t: "岗位" }, { k: "candidate", t: "候选人" },
        { k: "interviewer", t: "面试官" }, { k: "question", t: "题库" }, { k: "interview", t: "面试记录" },
      ];
      if (this.role === "hr") return base.filter((t) => t.k !== "interviewer");
      if (this.role === "admin") return [...base, { k: "system", t: "系统管理" }];
      return base;
    },
    cur() {
      return this.meta[this.tab] || { built: false, label: "系统管理", columns: [], fields: [] };
    },
    curList() {
      return this.lists[this.tab] || [];
    },
    curTotal() {
      return this.totals[this.tab] || 0;
    },
    curPage() {
      return this.pages[this.tab] || 1;
    },
    curSize() {
      return this.sizes[this.tab] || 10;
    },
    curLoading() {
      return !!this.loading[this.tab];
    },
    // ===== 系统管理页数据概览计数 =====
    enterpriseCount() {
      return (this.lists.enterprise || []).length;
    },
    jobCount() {
      return (this.lists.job || []).length;
    },
    candidateCount() {
      return (this.lists.candidate || []).length;
    },
    questionCount() {
      return (this.lists.question || []).length;
    },
  },
  watch: {
    // 切换身份后若当前 tab 不在新角色允许范围内，回到企业页
    role() {
      const allowed = this.adminTabs.map((t) => t.k);
      if (!allowed.includes(this.tab)) this.loadTab("enterprise");
    },
  },
  created() {
    this.sizes = { enterprise: 10, job: 10, candidate: 10, interviewer: 10, question: 10, interview: 10 };
    this.pages = { enterprise: 1, job: 1, candidate: 1, interviewer: 1, question: 1, interview: 1 };
    // 支持 ?view=admin&tab=candidate 深链，便于测试与演示（system 为虚拟 tab，仅管理员）
    const tab = new URLSearchParams(window.location.search).get("tab");
    if (tab && (tab === "system" || this.meta[tab])) this.tab = tab;
    this.loadReference();
    this.loadTab(this.tab);
  },
  methods: {
    /** 加载表单下拉所需的企业/岗位/候选人列表 */
    async loadReference() {
      // 注意：接口可能返回纯数组或 {list,total}，统一经 normalize() 归一化为数组（与 load() 一致）
      try {
        const r = API.unwrap(await API.get("/api/admin/enterprises?page=1&size=100"));
        this.enterprises = this.normalize("enterprise", r).list;
      } catch (e) {
        this.enterprises = [];
      }
      try {
        const r = API.unwrap(await API.get("/api/admin/jobs?page=1&size=100"));
        this.allJobs = this.normalize("job", r).list;
      } catch (e) {
        this.allJobs = [];
      }
      try {
        const r = API.unwrap(await API.get("/api/admin/candidates?page=1&size=100"));
        this.candidates = this.normalize("candidate", r).list;
      } catch (e) {
        this.candidates = [];
      }
    },
    _enterpriseName(id) {
      const e = this.enterprises.find((x) => x.id === Number(id));
      return e ? e.name : "—";
    },
    _jobName(id) {
      const j = this.allJobs.find((x) => x.id === Number(id));
      return j ? j.title : "（通用题）";
    },
    /** 列表响应归一化：兼容 {list,total} 或 数组 */
    normalize(tab, resp) {
      let list = Array.isArray(resp) ? resp : (resp && resp.list) || [];
      let total = Array.isArray(resp) ? resp.length : (resp && (resp.total ?? list.length)) || list.length;
      if (tab === "job") list = list.map((j) => ({ ...j, enterprise_name: this._enterpriseName(j.enterprise_id) }));
      if (tab === "question") list = list.map((q) => ({ ...q, job_name: this._jobName(q.job_id) }));
      return { list, total };
    },
    async loadTab(tab) {
      if (tab === "system" && this.role !== "admin") tab = "enterprise"; // 系统管理仅管理员可见
      this.tab = tab;
      this.error = "";
      if (tab === "system") {
        // 系统管理页：预加载各资源列表用于数据概览计数
        for (const t of ["enterprise", "job", "candidate", "interviewer", "question", "interview"]) {
          if (!this.lists[t]) await this.load(t, 1);
        }
        return;
      }
      if (this.meta[tab] && this.meta[tab].built && !this.lists[tab]) await this.load(tab, 1);
    },
    async load(tab, page) {
      this.loading[tab] = true;
      this.pages[tab] = page;
      try {
        const size = this.sizes[tab];
        const query = this.buildQuery(tab, page, size);
        const resp = API.unwrap(await API.get(`${this.meta[tab].endpoint}?${query}`));
        const { list, total } = this.normalize(tab, resp);
        this.lists[tab] = list;
        this.totals[tab] = total;
      } catch (e) {
        this.error = "加载失败：" + e.message;
      } finally {
        this.loading[tab] = false;
      }
    },
    /** 拼接分页 + 筛选查询参数 */
    buildQuery(tab, page, size) {
      const params = new URLSearchParams({ page, size });
      const f = this.filters[tab];
      if (f) {
        for (const key of Object.keys(f)) {
          if (f[key] !== "" && f[key] !== null && f[key] !== undefined) params.set(key, f[key]);
        }
      }
      return params.toString();
    },
    /** 筛选条件变化 → 回到第一页重新加载 */
    applyFilters() {
      if (this.filters[this.tab]) this.load(this.tab, 1);
    },
    changeSize(e) {
      this.sizes[this.tab] = Number(e.target.value);
      this.load(this.tab, 1);
    },
    /** 打开新增/编辑弹窗（data-bs-toggle 由按钮上的属性触发显示） */
    openAdd() {
      this.formMode = "add";
      this.editId = null;
      this.form = {};
      this._resetForm();
    },
    openEdit(row) {
      this.formMode = "edit";
      this.editId = row.id;
      this.form = Object.assign({}, row);
      this._resetForm();
    },
    /** 为未填的字段补默认值（保证 v-model 正常） */
    _resetForm() {
      (this.cur.fields || []).forEach((f) => {
        if (this.form[f.key] === undefined || this.form[f.key] === null) {
          this.form[f.key] = f.type === "number" ? "" : "";
        }
      });
    },
    fieldOptions(f) {
      return typeof f.options === "function" ? f.options() : f.options || [];
    },
    cellText(row, col) {
      const v = row[col.key];
      if (v === null || v === undefined) return "—";
      const fmt = this.cur && this.cur.format && this.cur.format[col.key];
      if (fmt && fmt[v] !== undefined) return fmt[v];
      return v;
    },
    async save() {
      if (this.cur.readonly) return; // 只读资源不可增改
      // 校验必填
      for (const f of this.cur.fields || []) {
        if (f.required && (this.form[f.key] === undefined || this.form[f.key] === "")) {
          alert("请填写必填项：" + f.label);
          return;
        }
      }
      this.saving = true;
      this.error = "";
      const tab = this.tab;
      const body = Object.assign({}, this.form);
      // 归一化：可选下拉留空 → null（如通用题 job_id）；数字字段 → Number
      (this.cur.fields || []).forEach((f) => {
        if (body[f.key] === "") {
          if (f.type === "select") body[f.key] = null;
        } else if (f.type === "number" && body[f.key] !== undefined && body[f.key] !== null) {
          body[f.key] = Number(body[f.key]);
        }
      });
      try {
        if (this.formMode === "add") {
          await API.post(this.cur.endpoint, body);
        } else {
          await API.put(`${this.cur.endpoint}/${this.editId}`, body);
        }
        this._closeModal();
        await this.load(tab, this.pages[tab]);
        // 刷新表单下拉引用（新增/编辑企业后，岗位表单「所属企业」下拉才能看到新企业）
        await this.loadReference();
      } catch (e) {
        this.error = "保存失败：" + e.message;
      } finally {
        this.saving = false;
      }
    },
    async del(row) {
      if (this.cur.readonly) return; // 只读资源不可删除
      if (!confirm(`确定删除「${row.name || row.title || row.question || '该记录'}」吗？此操作不可恢复。`)) return;
      const tab = this.tab;
      try {
        await API.del(`${this.cur.endpoint}/${row.id}`);
        await this.load(tab, this.pages[tab]);
        await this.loadReference(); // 删除后同步刷新下拉引用，保持一致
      } catch (e) {
        this.error = "删除失败：" + e.message;
      }
    },
    _closeModal() {
      const el = document.getElementById("crudModal");
      if (el && window.bootstrap) bootstrap.Modal.getInstance(el)?.hide();
    },
    // ===== 详情弹窗共用格式化 =====
    catName(cat) {
      const map = {
        self_intro: "自我介绍", project: "项目经历", technical: "专业技能",
        behavioral: "综合素质", reverse: "反问环节",
      };
      return map[cat] || cat || "—";
    },
    scoreClass(score) {
      if (score == null) return "text-muted";
      return score >= 85 ? "text-success" : score >= 70 ? "text-primary" : "text-warning";
    },
    scoreBadge(score) {
      if (score == null) return "bg-secondary";
      return score >= 85 ? "bg-success" : score >= 70 ? "bg-primary" : "bg-warning";
    },
    levelClass(level) {
      return { 优秀: "bg-success", 良好: "bg-primary", 待提升: "bg-warning" }[level] || "bg-secondary";
    },
    /** 查看面试记录详情（逐题问答 + 报告概要） */
    async viewInterview(row) {
      const el = document.getElementById("interviewDetailModal");
      if (el && window.bootstrap) bootstrap.Modal.getOrCreateInstance(el).show();
      this.detail = null;
      this.detailRow = row;
      this.detailLoading = true;
      this.detailError = "";
      try {
        this.detail = API.unwrap(await API.get(`/api/interview/${row.id}/report`));
      } catch (e) {
        this.detailError = e.message;
      } finally {
        this.detailLoading = false;
      }
    },
  },
  template: `
  <div>
    <h4 class="mb-3">🛠 后台管理</h4>
    <ul class="nav nav-pills mb-3">
      <li class="nav-item" v-for="t in adminTabs" :key="t.k">
        <a class="nav-link" :class="{active: tab===t.k}" href="#" @click.prevent="loadTab(t.k)">{{ t.t }}</a>
      </li>
    </ul>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <!-- ===== 系统管理（管理员专属，方案A C3） ===== -->
    <div v-if="tab === 'system'">
      <div class="card mb-3">
        <div class="card-header">🔐 三类身份入口说明</div>
        <div class="card-body">
          <table class="table table-sm mb-0 align-middle">
            <thead><tr><th>身份</th><th>入口</th><th>功能范围</th></tr></thead>
            <tbody>
              <tr><td>🎓 学生</td><td>候选人端</td><td>简历上传、岗位选择、AI 面试、逐题评分反馈、结果报告、历史记录</td></tr>
              <tr><td>👩‍💼 HR / 教师</td><td>后台（HR 视角）</td><td>企业、岗位、候选人、题库、面试记录管理 + 查看报告（无面试官管理）</td></tr>
              <tr><td>🛡️ 管理员</td><td>后台（管理视角）</td><td>全部管理功能 + 面试官管理 + 系统管理</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-header">📊 数据概览</div>
        <div class="card-body">
          <div class="row text-center g-3">
            <div class="col-3"><div class="fs-3 fw-bold text-primary">{{ enterpriseCount }}</div><div class="text-muted small">企业</div></div>
            <div class="col-3"><div class="fs-3 fw-bold text-success">{{ jobCount }}</div><div class="text-muted small">岗位</div></div>
            <div class="col-3"><div class="fs-3 fw-bold text-warning">{{ candidateCount }}</div><div class="text-muted small">候选人</div></div>
            <div class="col-3"><div class="fs-3 fw-bold text-info">{{ questionCount }}</div><div class="text-muted small">题目</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 已实现资源：通用 CRUD（cur 恒有 built 兜底，无需 &&） ===== -->
    <template v-else-if="cur.built">
      <div class="card">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">{{ cur.label }}管理</h5>
            <button v-if="!cur.readonly" class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#crudModal" @click="openAdd()">
              ＋ 新增{{ cur.label }}
            </button>
          </div>

          <!-- 筛选栏（仅面试记录等有 filters 配置的资源） -->
          <div v-if="cur.filters" class="row g-2 mb-3 align-items-end">
            <div class="col-auto" v-for="f in cur.filters" :key="f.key">
              <label class="form-label small text-muted mb-1">{{ f.label }}</label>
              <select class="form-select form-select-sm" v-model="filters[tab][f.key]" @change="applyFilters()">
                <option v-for="o in fieldOptions(f)" :key="o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
          </div>

          <div v-if="curLoading" class="text-center text-muted py-4">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>加载中…
          </div>

          <div v-else-if="curList.length === 0" class="text-center text-muted py-4">
            {{ cur.readonly ? '暂无面试记录。' : '暂无' + cur.label + '数据，点击右上角新增。' }}
          </div>

          <table v-else class="table table-hover align-middle">
            <thead>
              <tr>
                <th v-for="c in cur.columns" :key="c.key">{{ c.label }}</th>
                <th style="width: 100px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in curList" :key="row.id">
                <td v-for="c in cur.columns" :key="c.key" :class="c.truncate ? 'cell-truncate' : ''" :title="String(cellText(row, c))">
                  {{ cellText(row, c) }}
                </td>
                <td>
                  <template v-if="cur.readonly">
                    <button class="btn btn-sm btn-outline-info" @click="viewInterview(row)">详情</button>
                  </template>
                  <template v-else>
                    <button class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#crudModal" @click="openEdit(row)">编辑</button>
                    <button class="btn btn-sm btn-outline-danger" @click="del(row)">删除</button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 分页 -->
          <div class="d-flex justify-content-between align-items-center text-muted small mt-2">
            <div>
              共 {{ curTotal }} 条
              <select class="form-select form-select-sm d-inline-block w-auto ms-2" :value="curSize" @change="changeSize">
                <option :value="5">5 / 页</option>
                <option :value="10">10 / 页</option>
                <option :value="20">20 / 页</option>
              </select>
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" :disabled="curPage <= 1" @click="load(tab, curPage - 1)">上一页</button>
              <span class="btn btn-outline-secondary disabled">第 {{ curPage }} 页</span>
              <button class="btn btn-outline-secondary" :disabled="curPage * curSize >= curTotal" @click="load(tab, curPage + 1)">下一页</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 新增/编辑弹窗（只读资源如面试记录无此弹窗） -->
      <div v-if="!cur.readonly" class="modal fade" id="crudModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">{{ formMode === 'add' ? '新增' : '编辑' }}{{ cur.label }}</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <template v-for="f in cur.fields" :key="f.key">
                <div class="mb-3">
                  <label class="form-label">
                    {{ f.label }}<span v-if="f.required" class="text-danger"> *</span>
                  </label>
                  <select v-if="f.type === 'select'" class="form-select" v-model="form[f.key]">
                    <option v-if="f.placeholder" value="">{{ f.placeholder }}</option>
                    <option v-for="o in fieldOptions(f)" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <textarea v-else-if="f.type === 'textarea'" class="form-control" rows="3" v-model="form[f.key]"></textarea>
                  <input v-else class="form-control" :type="f.type || 'text'" v-model="form[f.key]" />
                </div>
              </template>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
              <button class="btn btn-primary" @click="save()" :disabled="saving">
                <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>保存
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 面试记录详情弹窗（逐题问答 + 报告概要） -->
      <div v-if="tab === 'interview'" class="modal fade" id="interviewDetailModal" tabindex="-1">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">面试 #{{ detailRow ? detailRow.id : '—' }} 详情</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div v-if="detailLoading" class="text-center text-muted py-4">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>加载中…
              </div>
              <div v-else-if="detailError" class="alert alert-danger">{{ detailError }}</div>
              <template v-else-if="detail">
                <div class="d-flex align-items-center mb-3">
                  <div class="me-3 text-center px-2">
                    <div class="fs-3 fw-bold" :class="scoreClass(detail.total_score)">{{ detail.total_score }}</div>
                    <div class="text-muted small">总分</div>
                  </div>
                  <div>
                    <p class="mb-1"><strong>岗位：</strong>{{ detail.job_title }}</p>
                    <p class="mb-1"><strong>候选人：</strong>{{ detailRow.candidate_name }}</p>
                    <p class="mb-1">
                      <strong>等级：</strong><span class="badge" :class="levelClass(detail.level)">{{ detail.level }}</span>
                    </p>
                    <p class="mb-0 text-muted small"><strong>时间：</strong>{{ detailRow.created_at }}</p>
                  </div>
                </div>
                <hr>
                <h6 class="mb-2">逐题问答</h6>
                <div v-if="!(detail.answers||[]).length" class="text-muted small">暂无答题记录</div>
                <div v-for="a in (detail.answers||[])" :key="a.round_no" class="border rounded p-2 mb-2">
                  <details class="report-details">
                    <summary class="fw-bold">
                      第 {{ a.round_no }} 题 · {{ catName(a.category) }}
                      <span class="ms-2 badge" :class="scoreBadge(a.score)">{{ a.score ?? '—' }} 分</span>
                    </summary>
                    <div class="mt-2 small">
                      <p class="mb-1"><strong>问题：</strong>{{ a.question }}</p>
                      <p class="mb-1"><strong>回答：</strong>{{ a.answer_text }}</p>
                      <p class="mb-0"><strong>反馈：</strong>{{ a.feedback }}</p>
                    </div>
                  </details>
                </div>
              </template>
              <div v-else class="text-muted text-center py-4">暂无数据</div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ===== 未实现资源：占位 ===== -->
    <div v-else class="card">
      <div class="card-body text-center text-muted py-5">
        <div class="display-6 mb-2">🚧</div>
        <h5>{{ cur.label }}管理</h5>
        <p>该模块将在后续阶段完成（成员C 持续推进中，待成员B 接口就绪后联调）。</p>
      </div>
    </div>
  </div>`,
};
