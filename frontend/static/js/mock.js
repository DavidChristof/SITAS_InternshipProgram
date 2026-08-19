/**
 * Mock 数据与 API 兜底（成员C维护）。
 *
 * 用途：成员B 的后端接口尚未全部就绪时，组件统一用 Mock.fetch 系列方法调用，
 *       真实接口请求失败（404/未实现）会自动回落 mock 数据并打印 [TODO联调] 警告。
 *       等接口就绪后，把组件里的 Mock.get(url, mockFn) 改成 API.get(url) 即可。
 *
 * 字段与 backend/app/models/ 下的模型对齐，保证换真接口时字段一致。
 */
const Mock = {
  // ---- 内部状态：本次会话内的可变数据（mock 的增删改查落在这里，刷新页面即重置）----
  _enterprises: [
    { id: 1, name: "示例科技有限公司", industry: "互联网 / 人工智能", description: "一家专注于 AI 产品的科技公司，面向校园招聘后端开发、算法、产品等岗位。", created_at: "2026-08-01 09:00:00" },
    { id: 2, name: "星辰数据科技", industry: "大数据 / 云计算", description: "为企业提供数据中台与云上解决方案，实习生可参与真实项目开发。", created_at: "2026-08-01 09:10:00" },
    { id: 3, name: "云启教育集团", industry: "教育科技", description: "在线教育平台，业务涵盖 K12 与职业培训，技术团队规模大、导师制完善。", created_at: "2026-08-01 09:20:00" },
  ],
  _jobs: [
    { id: 1, enterprise_id: 1, title: "Python 后端开发工程师", description: "负责公司 AI 产品后端服务的设计与开发，包括 REST API、数据服务和 AI 功能接入。", requirements: "熟悉 Python、FastAPI/Django；了解 SQL 与数据库设计；对大模型应用感兴趣；有项目经验者优先。", skills: "Python, FastAPI, SQL, LLM, Redis", created_at: "2026-08-02 10:00:00" },
    { id: 2, enterprise_id: 1, title: "前端开发工程师（Vue）", description: "负责产品前端界面与交互开发，使用 Vue3 与组件化方案，参与产品体验优化。", requirements: "熟悉 Vue3、JavaScript/TypeScript、CSS；理解组件化开发；有前端工程化经验者优先。", skills: "Vue3, JavaScript, TypeScript, CSS", created_at: "2026-08-02 10:05:00" },
    { id: 3, enterprise_id: 1, title: "算法实习生", description: "参与大模型应用相关的算法调研与落地，包括 Prompt 工程、RAG 与效果评估。", requirements: "熟悉 Python、PyTorch；了解 Transformer 与常见 LLM；有论文阅读习惯者优先。", skills: "Python, PyTorch, LLM, RAG", created_at: "2026-08-02 10:10:00" },
    { id: 4, enterprise_id: 2, title: "数据分析师", description: "负责业务数据提取、清洗与可视化分析，支撑运营与产品决策。", requirements: "熟悉 SQL、Python（Pandas）；了解基本统计方法；细心、沟通好。", skills: "Python, SQL, Pandas, Excel", created_at: "2026-08-02 10:15:00" },
    { id: 5, enterprise_id: 3, title: "Java 开发工程师", description: "参与在线教育核心业务系统研发，负责后端服务与接口开发。", requirements: "熟悉 Java、Spring Boot；了解 MySQL；有良好的编码习惯。", skills: "Java, Spring Boot, MySQL", created_at: "2026-08-02 10:20:00" },
  ],
  _candidates: [
    { id: 1, name: "李同学", email: "li@example.com", phone: "13800000001", status: "active", created_at: "2026-08-05 14:00:00" },
    { id: 2, name: "王同学", email: "wang@example.com", phone: "13800000002", status: "active", created_at: "2026-08-05 14:30:00" },
    { id: 3, name: "张同学", email: "zhang@example.com", phone: "13800000003", status: "active", created_at: "2026-08-06 09:00:00" },
    { id: 4, name: "陈同学", email: "chen@example.com", phone: "13800000004", status: "closed", created_at: "2026-08-06 10:00:00" },
  ],
  _interviewers: [
    { id: 1, name: "张老师", role: "teacher", title: "实习指导教师", created_at: "2026-08-01 11:00:00" },
    { id: 2, name: "王经理", role: "hr", title: "HR 经理", created_at: "2026-08-01 11:10:00" },
    { id: 3, name: "刘总监", role: "hr", title: "技术总监", created_at: "2026-08-01 11:20:00" },
  ],
  _questions: [
    { id: 1, job_id: 1, category: "self_intro", question: "请做一个 1 分钟自我介绍，重点突出你的技术栈与项目经历。", expected_points: "教育背景,项目经历,技能,求职动机", sample_answer: "面试官你好，我是 XX 大学软件工程专业应届生，主攻 Python 后端……", difficulty: 1, created_at: "2026-08-03 09:00:00" },
    { id: 2, job_id: 1, category: "technical", question: "请简述 FastAPI 与 Flask 的区别。", expected_points: "异步支持,自动生成 OpenAPI 文档,基于 Pydantic 的类型校验,性能", sample_answer: "FastAPI 基于 ASGI 支持异步、自带 Swagger 文档、用 Pydantic 做请求校验，性能接近 Go；Flask 是同步 WSGI 框架，更轻量但需自行集成文档与校验。", difficulty: 2, created_at: "2026-08-03 09:05:00" },
    { id: 3, job_id: 1, category: "technical", question: "如何设计一个高并发的 REST API 查询接口？", expected_points: "缓存,索引,分页,异步,连接池", sample_answer: "加 Redis 缓存热点数据、数据库加索引并合理分页、用异步处理 IO 密集任务、配置连接池避免连接风暴。", difficulty: 3, created_at: "2026-08-03 09:10:00" },
    { id: 4, job_id: 1, category: "behavioral", question: "请举例说明你在团队项目中遇到分歧时是如何解决的。", expected_points: "STAR 结构,沟通,换位思考,结果", sample_answer: "（情境）小组开发时对技术选型有分歧；（任务）需要尽快确定方案；（行动）我整理两种方案的优劣对比，组织一次短会讨论并投票，保留可回退方案；（结果）达成一致并按时交付。", difficulty: 2, created_at: "2026-08-03 09:15:00" },
    { id: 5, job_id: 2, category: "project", question: "介绍一下你做过的一个前端项目，从需求到上线你负责了哪些部分？", expected_points: "项目背景,个人职责,难点解决,结果量化", sample_answer: "我参与了一个校园二手交易平台的 Web 端开发，负责商品列表与详情页……", difficulty: 2, created_at: "2026-08-03 09:20:00" },
    { id: 6, job_id: null, category: "reverse", question: "关于这个岗位和团队，你有什么想了解的？", expected_points: "主动提问,岗位理解,求职动机", sample_answer: "我想了解团队目前的技术栈与成长路径，以及实习生一般会参与哪些具体任务。", difficulty: 1, created_at: "2026-08-03 09:25:00" },
  ],
  _interviews: [
    { id: 101, candidate_id: 1, job_id: 1, job_title: "Python 后端开发工程师", candidate_name: "李同学", status: "finished", total_score: 82, created_at: "2026-08-10 15:00:00" },
    { id: 102, candidate_id: 1, job_id: 2, job_title: "前端开发工程师（Vue）", candidate_name: "李同学", status: "running", total_score: null, created_at: "2026-08-12 09:30:00" },
    { id: 103, candidate_id: 2, job_id: 3, job_title: "算法实习生", candidate_name: "王同学", status: "pending", total_score: null, created_at: "2026-08-13 11:00:00" },
  ],
  // 本次会话内新创建的面试计划：{ id, job_id, questions[], answers[], round }
  _plans: new Map(),
  _nextInterviewId: 200,

  // 面试题目序列（mock）
  _planQuestions(jobId) {
    const base = [
      { category: "self_intro", question: "请做一个 1 分钟的自我介绍，重点突出你的技术栈与项目经历。" },
      { category: "project", question: "介绍一下你做过的一个最有挑战的项目，你在其中担任什么角色、解决了什么难点？" },
      { category: "technical", question: "请简述 FastAPI 与 Flask 的区别，以及你会如何选择。", jobId },
      { category: "behavioral", question: "请举例说明你在团队项目中遇到分歧时是如何解决的。" },
      { category: "reverse", question: "关于这个岗位和团队，你有什么想了解的？" },
    ];
    // 根据岗位微调技术题
    const map = {
      2: { category: "technical", question: "Vue3 中 ref 和 reactive 有什么区别？你平时怎么选？" },
      3: { category: "technical", question: "请简述 Transformer 结构的基本原理，以及它与 RNN 的差异。" },
      4: { category: "technical", question: "SQL 中 JOIN 有哪几种？它们各自适用于什么场景？" },
      5: { category: "technical", question: "Spring Boot 中一个请求从进入到返回经历了哪些环节？" },
    };
    if (map[jobId]) base[2] = map[jobId];
    return base;
  },

  _ensurePlan(id) {
    if (!this._plans.has(id)) {
      const rec = this._interviews.find((i) => i.id === id) || {};
      this._plans.set(id, {
        id,
        job_id: rec.job_id || 1,
        questions: this._planQuestions(rec.job_id || 1),
        answers: [],
        round: 0,
      });
    }
    return this._plans.get(id);
  },

  _jobName(jobId) {
    const j = this._jobs.find((x) => x.id === jobId);
    return j ? j.title : "未知岗位";
  },

  // ---------- 通用兜底：先真实请求，失败回落 mock ----------
  async fetch(method, url, body, mockFn) {
    try {
      let resp;
      if (method === "GET") resp = await API.get(url);
      else if (method === "POST") resp = await API.post(url, body);
      else if (method === "PUT") resp = await API.put(url, body);
      else if (method === "DELETE") resp = await API.del(url);
      else if (method === "UPLOAD") resp = await API.upload(url, body);
      return API.unwrap(resp);
    } catch (e) {
      console.warn("[TODO联调] " + method + " " + url + " 接口未实现，使用 mock 数据。", e.message);
      return mockFn();
    }
  },
  async get(url, mockFn) { return this.fetch("GET", url, null, mockFn); },
  async post(url, body, mockFn) { return this.fetch("POST", url, body, mockFn); },
  async put(url, body, mockFn) { return this.fetch("PUT", url, body, mockFn); },
  async del(url, mockFn) { return this.fetch("DELETE", url, null, mockFn); },
  async upload(url, fd, mockFn) { return this.fetch("UPLOAD", url, fd, mockFn); },

  // ---------- 候选人端 ----------
  jobs() { return this._jobs.slice(); },

  uploadResume(formData) {
    // TODO 联调: 成员B 的 POST /api/candidate/resume 就绪后，本函数不再被调用。
    const name = (formData && formData.get && formData.get("name")) || "访客候选人";
    const email = (formData && formData.get && formData.get("email")) || "";
    const nextId = Math.max(0, ...this._candidates.map((c) => c.id)) + 1;
    const profile = {
      id: nextId,
      name: name.trim() || "访客候选人",
      email: email,
      phone: "",
      status: "active",
      created_at: "2026-08-17 20:00:00",
      resume_text: "（mock）简历原文已由后端解析，此处为演示数据。",
    };
    this._candidates.unshift(profile);
    return profile;
  },

  createInterview(body) {
    const id = this._nextInterviewId++;
    this._plans.set(id, {
      id,
      job_id: body.job_id,
      questions: this._planQuestions(body.job_id),
      answers: [],
      round: 0,
    });
    return { interview_id: id };
  },

  interviews() {
    // 静态历史 + 本次会话内已开始的面试（合并展示）
    const live = [];
    for (const [id, plan] of this._plans) {
      if (plan.answers.length === 0) continue;
      const finished = plan.answers.length >= plan.questions.length;
      const total = plan.answers.reduce((s, a) => s + a.score, 0) / Math.max(1, plan.answers.length);
      live.push({
        id,
        candidate_id: 1,
        job_id: plan.job_id,
        job_title: this._jobName(plan.job_id),
        candidate_name: "我",
        status: finished ? "finished" : "running",
        total_score: finished ? Math.round(total) : null,
        created_at: "2026-08-17 20:30:00",
      });
    }
    return [...live, ...this._interviews];
  },

  startInterview(id) {
    const plan = this._ensurePlan(id);
    const q = plan.questions[0];
    return { round_no: 1, category: q.category, question: q.question, total_rounds: plan.questions.length };
  },

  // 答案反馈模板（按环节类型）
  _feedback(category, score) {
    const map = {
      self_intro: "自我介绍结构完整，能清晰说明背景与求职动机。建议进一步突出与岗位匹配的量化成果。",
      project: "项目描述较清晰，能体现个人贡献与难点解决。建议补充可量化的效果数据（如性能提升百分比）。",
      technical: "技术回答基本正确，能抓住关键点。建议结合具体场景举例，展示深入理解。",
      behavioral: "回答逻辑清楚、条理分明。可再补充团队协作的具体过程与个人反思。",
      reverse: "提问体现了对岗位和公司的思考，很好。",
    };
    const tip = score >= 85 ? "（表现优秀）" : score >= 70 ? "（表现良好）" : "（仍有提升空间）";
    return (map[category] || "回答有一定内容，建议结合 STAR 结构与岗位要求进一步打磨。") + tip;
  },

  submitAnswer(id, body) {
    const plan = this._ensurePlan(id);
    const round = body.round_no || 1;
    const q = plan.questions[Math.min(round - 1, plan.questions.length - 1)];
    // 评分：结合回答长度给一个较自然的分数
    const len = (body.answer_text || "").length;
    const score = Math.max(60, Math.min(95, Math.round(58 + Math.min(25, len / 3) + Math.random() * 8)));
    plan.answers.push({
      round_no: round,
      category: q.category,
      question: q.question,
      answer_text: body.answer_text || "",
      score: score,
      feedback: this._feedback(q.category, score),
    });
    if (round >= plan.questions.length) {
      return { finished: true, score, feedback: "本轮作答已完成，正在生成报告…" };
    }
    const next = plan.questions[round];
    return {
      score,
      feedback: this._feedback(q.category, score),
      next_round: round + 1,
      next_category: next.category,
      next_question: next.question,
      total_rounds: plan.questions.length,
    };
  },

  /** 语音转写（mock） */
  transcribeAudio(formData) {
    // TODO 联调: 成员B/A 的语音转写接口就绪后，此函数不再被调用
    const round = (formData && formData.get && formData.get("round_no")) || "1";
    return {
      text: "（语音转写结果 mock）这是我通过麦克风录入的第 " + round + " 轮回答。在实际联调中，这里会是 faster-whisper 转写出的真实文本。",
      confidence: 0.9,
    };
  },

  report(id) {
    const plan = this._ensurePlan(id);
    // 未作答（静态历史/中途退出）的面试：合成一份演示答案，保证报告完整
    if (!plan.answers.length) {
      plan.answers = plan.questions.map((q, i) => {
        const score = 70 + ((i * 7) % 26);
        return {
          round_no: i + 1,
          category: q.category,
          question: q.question,
          answer_text:
            "（演示数据）针对「" + q.question.slice(0, 24) + "…」我结合项目经验与岗位要求展开说明，并给出了具体的量化结果。",
          score: score,
          feedback: this._feedback(q.category, score),
        };
      });
    }
    const dims = [
      { name: "专业知识", score: 0 },
      { name: "项目经验", score: 0 },
      { name: "沟通表达", score: 0 },
      { name: "逻辑思维", score: 0 },
      { name: "学习潜力", score: 0 },
    ];
    plan.answers.forEach((a) => {
      if (a.category === "technical") dims[0].score = a.score;
      else if (a.category === "project") dims[1].score = a.score;
      else if (a.category === "self_intro") dims[2].score = a.score;
      else if (a.category === "behavioral") dims[3].score = a.score;
      else dims[4].score = a.score;
    });
    dims.forEach((d) => { if (!d.score) d.score = 75; });
    const total = Math.round(dims.reduce((s, d) => s + d.score, 0) / dims.length);
    const level = total >= 85 ? "优秀" : total >= 70 ? "良好" : "待提升";
    return {
      id,
      job_title: this._jobName(plan.job_id),
      candidate_name: "候选人",
      status: plan.answers.length >= plan.questions.length ? "finished" : "running",
      total_score: total,
      level,
      dimension_scores: dims,
      strengths: [
        "对岗位相关技术栈有基本掌握，能围绕关键词展开说明。",
        "回答结构较为清晰，具备良好的表达与总结能力。",
      ],
      weaknesses: [
        "部分回答缺少具体量化数据支撑，说服力可再加强。",
        "技术深度有待提升，可结合源码与真实场景进一步积累。",
      ],
      suggestions: [
        "面试中多使用 STAR 结构：情境、任务、行动、结果。",
        "针对目标岗位准备 2-3 个高质量项目案例，提前打磨细节。",
        "平时多练习技术题表达，尝试把知识点讲给他人听。",
      ],
      answers: plan.answers.slice(),
      created_at: "2026-08-17 20:30:00",
    };
  },

  // ---------- 后台管理 ----------
  _adminData(resource) {
    const map = {
      enterprise: this._enterprises,
      job: this._jobs,
      candidate: this._candidates,
      interviewer: this._interviewers,
      question: this._questions,
      interview: this._interviews,
    };
    return map[resource] || [];
  },

  adminList(resource, page, size, filters) {
    let all;
    if (resource === "interview") {
      all = this.interviews(); // 面试记录 = 静态历史 + 本次会话内已开始的面试
    } else {
      all = this._adminData(resource);
    }
    // 按筛选条件过滤
    if (filters) {
      if (filters.status) all = all.filter((i) => i.status === filters.status);
      if (filters.job_id) all = all.filter((i) => i.job_id === Number(filters.job_id));
      if (filters.candidate_id) all = all.filter((i) => i.candidate_id === Number(filters.candidate_id));
    }
    const list = all.slice((page - 1) * size, page * size);
    return { list, total: all.length };
  },

  adminCreate(resource, body) {
    const arr = this._adminData(resource);
    const nextId = arr.reduce((m, x) => Math.max(m, x.id), 0) + 1;
    const row = Object.assign({ id: nextId, created_at: "2026-08-17 20:00:00" }, body || {});
    arr.unshift(row);
    return row;
  },

  adminUpdate(resource, id, body) {
    const arr = this._adminData(resource);
    const row = arr.find((x) => x.id === Number(id));
    if (row) Object.assign(row, body || {});
    return row || { id: Number(id) };
  },

  adminDelete(resource, id) {
    const arr = this._adminData(resource);
    const idx = arr.findIndex((x) => x.id === Number(id));
    if (idx >= 0) arr.splice(idx, 1);
    return { deleted: Number(id) };
  },
};
