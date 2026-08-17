/**
 * HR/教师后台管理组件（成员C实现）。
 * 管理：企业 / 岗位 / 候选人 / 面试官 / 题库 / 面试记录。
 *
 * 设计：配置驱动 —— 每个资源在 meta 中声明列(columns)、表单字段(fields)、接口(endpoint)，
 *       通用表格 + 弹窗表单 + 删除确认 + 分页。
 * 进度：阶段一完成 企业/岗位；候选人/面试官/题库（阶段二）、面试记录（阶段四）打开 built 开关即可。
 * 联调：统一用 Mock.get/post/put/del(url, mockFn) 兜底，接口就绪后改为 API.xxx。
 */
const AdminView = {
  data() {
    return {
      tab: "enterprise",
      error: "",
      // 供岗位/题目表单选择的企业与岗位列表
      enterprises: [],
      allJobs: [],
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
          label: "候选人", endpoint: "/api/admin/candidates", built: false,
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
          label: "面试官", endpoint: "/api/admin/interviewers", built: false,
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
          label: "题库", endpoint: "/api/admin/questions", built: false,
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
          label: "面试记录", endpoint: "/api/admin/interviews", built: false,
          columns: [
            { key: "id", label: "ID" }, { key: "candidate_name", label: "候选人" },
            { key: "job_title", label: "岗位" }, { key: "status", label: "状态" },
            { key: "total_score", label: "总分" }, { key: "created_at", label: "时间" },
          ],
          fields: [],
        },
      },
    };
  },
  computed: {
    cur() {
      return this.meta[this.tab];
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
  },
  created() {
    this.sizes = { enterprise: 10, job: 10, candidate: 10, interviewer: 10, question: 10, interview: 10 };
    this.pages = { enterprise: 1, job: 1, candidate: 1, interviewer: 1, question: 1, interview: 1 };
    this.loadReference();
    this.loadTab(this.tab);
  },
  methods: {
    /** 加载表单下拉所需的企业/岗位列表 */
    async loadReference() {
      try {
        this.enterprises = await Mock.get("/api/admin/enterprises?page=1&size=100", () => Mock.adminList("enterprise", 1, 100).list);
      } catch (e) {
        this.enterprises = [];
      }
      try {
        this.allJobs = await Mock.get("/api/admin/jobs?page=1&size=100", () => Mock.adminList("job", 1, 100).list);
      } catch (e) {
        this.allJobs = [];
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
      this.tab = tab;
      this.error = "";
      if (this.meta[tab].built && !this.lists[tab]) await this.load(tab, 1);
    },
    async load(tab, page) {
      this.loading[tab] = true;
      this.pages[tab] = page;
      try {
        const size = this.sizes[tab];
        const resp = await Mock.get(
          `${this.meta[tab].endpoint}?page=${page}&size=${size}`,
          () => Mock.adminList(tab, page, size)
        );
        const { list, total } = this.normalize(tab, resp);
        this.lists[tab] = list;
        this.totals[tab] = total;
      } catch (e) {
        this.error = "加载失败：" + e.message;
      } finally {
        this.loading[tab] = false;
      }
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
      if (col.key === "total_score" && v === null) return "—";
      return v;
    },
    async save() {
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
      try {
        if (this.formMode === "add") {
          // TODO 联调: API.post(this.cur.endpoint, body)
          await Mock.post(this.cur.endpoint, body, () => Mock.adminCreate(tab, body));
        } else {
          // TODO 联调: API.put(this.cur.endpoint + '/' + this.editId, body)
          await Mock.put(`${this.cur.endpoint}/${this.editId}`, body, () => Mock.adminUpdate(tab, this.editId, body));
        }
        this._closeModal();
        await this.load(tab, this.pages[tab]);
      } catch (e) {
        this.error = "保存失败：" + e.message;
      } finally {
        this.saving = false;
      }
    },
    async del(row) {
      if (!confirm(`确定删除「${row.name || row.title || row.question || '该记录'}」吗？此操作不可恢复。`)) return;
      const tab = this.tab;
      try {
        // TODO 联调: API.del(this.cur.endpoint + '/' + row.id)
        await Mock.del(`${this.cur.endpoint}/${row.id}`, () => Mock.adminDelete(tab, row.id));
        await this.load(tab, this.pages[tab]);
      } catch (e) {
        this.error = "删除失败：" + e.message;
      }
    },
    _closeModal() {
      const el = document.getElementById("crudModal");
      if (el && window.bootstrap) bootstrap.Modal.getInstance(el)?.hide();
    },
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
    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <!-- ===== 已实现资源：通用 CRUD ===== -->
    <div v-if="cur.built">
      <div class="card">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">{{ cur.label }}管理</h5>
            <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#crudModal" @click="openAdd()">
              ＋ 新增{{ cur.label }}
            </button>
          </div>

          <div v-if="curLoading" class="text-center text-muted py-4">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>加载中…
          </div>

          <div v-else-if="curList.length === 0" class="text-center text-muted py-4">
            暂无{{ cur.label }}数据，点击右上角新增。
          </div>

          <table v-else class="table table-hover align-middle">
            <thead>
              <tr>
                <th v-for="c in cur.columns" :key="c.key">{{ c.label }}</th>
                <th style="width: 140px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in curList" :key="row.id">
                <td v-for="c in cur.columns" :key="c.key" :class="c.truncate ? 'cell-truncate' : ''" :title="String(cellText(row, c))">
                  {{ cellText(row, c) }}
                </td>
                <td>
                  <button class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#crudModal" @click="openEdit(row)">编辑</button>
                  <button class="btn btn-sm btn-outline-danger" @click="del(row)">删除</button>
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

      <!-- 新增/编辑弹窗 -->
      <div class="modal fade" id="crudModal" tabindex="-1">
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
    </div>

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
