/**
 * 面试模块组件（成员C实现）。
 *  - InterviewView：AI 面试对话 —— 文字问答、逐题评分反馈、进度提示、语音录音上传。
 *  - ReportView：面试结果报告（总分 / 雷达图 / 优缺点 / 建议），阶段三完善。
 *
 * 面试流程：begin() 启动 → submitAnswer() 逐题提交（展示评分反馈 + 下一题）→ 结束 → 查看报告。
 * 联调说明：接口未实现时用 Mock.post/upload 兜底（mock 会维护同一场面试的题目与答题记录）。
 */
const InterviewView = {
  props: {
    interview: { type: Object, default: null }, // { id, jobId, jobTitle }
  },
  data() {
    return {
      messages: [], // 聊天气泡 [{from:'ai'|'me', text}]
      currentQuestion: null, // 当前题目 {round_no, category, question}
      roundNo: 0,
      totalRounds: 0,
      status: "idle", // idle | loading | running | finished
      answerText: "",
      submitting: false,
      error: "",
      lastResult: null, // 最后一题的 {score, feedback}
      // 录音
      recording: false,
      mediaRecorder: null,
      audioChunks: [],
      transcribing: false,
    };
  },
  computed: {
    jobTitle() {
      return (this.interview && this.interview.jobTitle) || "本场面试";
    },
    progressPercent() {
      if (!this.totalRounds) return 0;
      return Math.min(100, Math.round((this.roundNo / this.totalRounds) * 100));
    },
    categoryLabel() {
      return this.currentQuestion ? this.catName(this.currentQuestion.category) : "";
    },
  },
  created() {
    this.begin();
  },
  methods: {
    /** 环节类型 → 中文名 */
    catName(cat) {
      const map = {
        self_intro: "自我介绍",
        project: "项目经历",
        technical: "专业技能",
        behavioral: "综合素质",
        reverse: "反问环节",
      };
      return map[cat] || cat || "—";
    },
    /** 组装题目气泡文案 */
    formatQuestion(q) {
      return `【${this.catName(q.category)}】\n第 ${q.round_no} 题：${q.question}`;
    },
    pushAi(text) {
      this.messages.push({ from: "ai", text });
      this.scrollBottom();
    },
    pushMe(text) {
      this.messages.push({ from: "me", text });
      this.scrollBottom();
    },
    scrollBottom() {
      this.$nextTick(() => {
        const el = this.$refs.chatBox;
        if (el) el.scrollTop = el.scrollHeight;
      });
    },
    /** 开始面试：调 start 拿第一题 */
    async begin() {
      const id = this.interview && this.interview.id;
      if (!id) {
        this.error = "缺少面试编号，请从候选人端选择岗位开始面试。";
        return;
      }
      this.status = "loading";
      this.error = "";
      this.pushAi("面试即将开始，请认真作答。");
      try {
        // TODO 联调: API.post(`/api/interview/${id}/start`)
        const q = await Mock.post(`/api/interview/${id}/start`, null, () => Mock.startInterview(id));
        this.currentQuestion = q;
        this.roundNo = q.round_no || 1;
        this.totalRounds = q.total_rounds || 0;
        this.status = "running";
        this.pushAi(this.formatQuestion(q));
      } catch (e) {
        this.error = "面试启动失败：" + e.message;
        this.status = "idle";
      }
    },
    /** 提交一题回答：展示评分反馈，有下一题则继续 */
    async submitAnswer() {
      const id = this.interview && this.interview.id;
      const text = this.answerText.trim();
      if (!id || !text || this.submitting || this.status !== "running") return;
      this.pushMe(text);
      this.answerText = "";
      this.submitting = true;
      this.error = "";
      try {
        // TODO 联调: API.post(`/api/interview/${id}/answer`, { round_no, answer_text })
        const r = await Mock.post(
          `/api/interview/${id}/answer`,
          { round_no: this.roundNo, answer_text: text },
          () => Mock.submitAnswer(id, { round_no: this.roundNo, answer_text: text })
        );
        this.lastResult = { score: r.score, feedback: r.feedback };
        if (r.finished) {
          this.pushAi(
            `第 ${this.roundNo} 题作答完成。\n\n评分：${r.score} 分\n反馈：${r.feedback}`
          );
          this.pushAi("🎉 本场面试已结束，正在生成报告…");
          this.status = "finished";
        } else {
          this.pushAi(`第 ${this.roundNo} 题评分：${r.score} 分\n反馈：${r.feedback}`);
          this.roundNo = r.next_round;
          this.currentQuestion = {
            round_no: r.next_round,
            category: r.next_category,
            question: r.next_question,
          };
          this.pushAi(this.formatQuestion(this.currentQuestion));
        }
      } catch (e) {
        this.error = "提交失败：" + e.message;
      } finally {
        this.submitting = false;
      }
    },
    viewReport() {
      this.$emit("view-report", this.interview.id);
    },
    back() {
      this.$emit("back");
    },
    // ===== 语音回答 =====
    async startRecord() {
      if (!navigator.mediaDevices || !window.MediaRecorder) {
        alert("当前浏览器不支持录音，请使用文字回答。");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mr = new MediaRecorder(stream);
        this.audioChunks = [];
        mr.ondataavailable = (e) => {
          if (e.data.size > 0) this.audioChunks.push(e.data);
        };
        mr.onstop = () => {
          stream.getTracks().forEach((t) => t.stop());
          this.uploadAudio(new Blob(this.audioChunks, { type: mr.mimeType || "audio/webm" }));
        };
        this.mediaRecorder = mr;
        this.recording = true;
        mr.start();
      } catch (e) {
        alert("无法获取麦克风：" + e.message + "（请改用文字回答）");
      }
    },
    stopRecord() {
      this.recording = false;
      if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
        this.mediaRecorder.stop();
      }
    },
    /** 录音结束后上传 → 转写 → 填入回答框（失败提示改用文字） */
    async uploadAudio(blob) {
      const id = this.interview && this.interview.id;
      if (!id) return;
      this.transcribing = true;
      try {
        const fd = new FormData();
        fd.append("file", blob, `answer_${this.roundNo}.webm`);
        fd.append("round_no", String(this.roundNo));
        // TODO 联调: 语音转写接口（成员B/A 提供）就绪后替换
        const r = await Mock.upload(`/api/interview/${id}/audio`, fd, () => Mock.transcribeAudio(fd));
        const text = (r && r.text) || "";
        if (text) {
          this.answerText = text;
          alert("✅ 语音已转写为文字，请确认后点击「提交回答」。");
        } else {
          alert("语音识别结果为空，请改用文字回答。");
        }
      } catch (e) {
        alert("语音上传失败：" + e.message + "（请改用文字回答）");
      } finally {
        this.transcribing = false;
      }
    },
  },
  template: `
  <div>
    <div class="d-flex justify-content-between align-items-center mb-1">
      <h4 class="mb-0">💬 AI 面试对话</h4>
      <button class="btn btn-outline-secondary btn-sm" @click="back()">← 返回候选人端</button>
    </div>
    <p class="text-muted small mb-3">🏢 {{ jobTitle }}</p>

    <!-- 缺少面试上下文时的提示 -->
    <div v-if="!interview || !interview.id" class="card">
      <div class="card-body text-center text-muted py-5">
        <div class="display-6 mb-2">🎯</div>
        <h5>尚未选择岗位</h5>
        <p>请从候选人端的岗位大厅选择岗位开始面试。</p>
        <button class="btn btn-primary mt-2" @click="back()">返回候选人端</button>
      </div>
    </div>

    <template v-else>
      <!-- 进度条 -->
      <div class="progress mb-1" style="height: 10px;">
        <div class="progress-bar" role="progressbar" :style="{width: progressPercent + '%'}"
             :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100"></div>
      </div>
      <p class="text-muted small mb-2">第 {{ roundNo }} / {{ totalRounds || '?' }} 题 · 环节：{{ categoryLabel || '—' }}</p>

      <div v-if="error" class="alert alert-danger">{{ error }}</div>

      <!-- 聊天区 -->
      <div class="chat-box" ref="chatBox">
        <div v-for="(m, i) in messages" :key="i" class="d-flex"
             :class="m.from==='me' ? 'justify-content-end' : 'justify-content-start'">
          <div class="msg-bubble" :class="m.from==='ai' ? 'msg-ai' : 'msg-me'">{{ m.text }}</div>
        </div>
        <div v-if="status === 'loading'" class="text-muted small py-2">
          <span class="spinner-border spinner-border-sm me-2" role="status"></span>面试准备中…
        </div>
        <div v-if="transcribing" class="text-muted small py-2">
          <span class="spinner-border spinner-border-sm me-2" role="status"></span>语音转写中…
        </div>
      </div>

      <!-- 输入区（进行中） -->
      <div class="mt-3" v-if="status === 'running'">
        <div class="input-group">
          <textarea v-model="answerText" class="form-control" rows="2" placeholder="输入你的回答…"
                    :disabled="submitting || transcribing"></textarea>
          <button class="btn btn-primary" @click="submitAnswer"
                  :disabled="submitting || transcribing || !answerText.trim()">
            {{ submitting ? '评分中…' : '提交回答' }}
          </button>
          <button class="btn btn-danger" :class="{recording: recording}"
                  @click="recording ? stopRecord() : startRecord()"
                  :disabled="submitting || transcribing">
            {{ recording ? '⏹ 停止录音' : '🎙 语音' }}
          </button>
        </div>
        <p class="text-muted small mt-1">提示：可输入文字或点击「语音」按钮录制回答。</p>
      </div>

      <!-- 面试结束 -->
      <div v-if="status === 'finished'" class="mt-3">
        <div class="card border-success">
          <div class="card-body text-center">
            <h5 class="text-success">🎉 面试已完成</h5>
            <p class="mb-1" v-if="lastResult">
              最后一题评分：<strong>{{ lastResult.score }}</strong> 分<br>
              <span class="text-muted small">{{ lastResult.feedback }}</span>
            </p>
            <p class="text-muted small mb-3">完整报告（总分 / 维度分析 / 优缺点 / 建议）将在结果页展示</p>
            <button class="btn btn-success btn-lg" @click="viewReport()">📊 查看结果报告 →</button>
          </div>
        </div>
      </div>
    </template>
  </div>`,
};

const ReportView = {
  props: {
    interviewId: { type: [Number, String], default: null },
  },
  data() {
    return {
      report: null,
      loading: false,
      error: "",
    };
  },
  created() {
    this.loadReport();
  },
  methods: {
    back() {
      this.$emit("back");
    },
    catName(cat) {
      const map = {
        self_intro: "自我介绍",
        project: "项目经历",
        technical: "专业技能",
        behavioral: "综合素质",
        reverse: "反问环节",
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
    barClass(score) {
      return this.scoreBadge(score);
    },
    levelClass(level) {
      return { 优秀: "bg-success", 良好: "bg-primary", 待提升: "bg-warning" }[level] || "bg-secondary";
    },
    async loadReport() {
      const id = this.interviewId;
      if (id == null) {
        this.error = "缺少面试编号，无法生成报告。";
        return;
      }
      this.loading = true;
      this.error = "";
      try {
        // TODO 联调: API.get(`/api/interview/${id}/report`)
        this.report = await Mock.get(`/api/interview/${id}/report`, () => Mock.report(id));
        this.$nextTick(() => this.drawRadar());
      } catch (e) {
        this.error = "加载报告失败：" + e.message;
      } finally {
        this.loading = false;
      }
    },
    /** 轻量 canvas 雷达图（无三方依赖） */
    drawRadar() {
      const canvas = this.$refs.radarCanvas;
      if (!canvas || !this.report) return;
      const dims = this.report.dimension_scores || [];
      if (dims.length < 3) return;
      const ctx = canvas.getContext("2d");
      const W = canvas.width, H = canvas.height;
      const cx = W / 2, cy = H / 2;
      const R = Math.min(cx, cy) - 40;
      const n = dims.length;
      const LEVELS = 4;
      ctx.clearRect(0, 0, W, H);

      const point = (i, r) => {
        const ang = (Math.PI * 2 * i) / n - Math.PI / 2;
        return [cx + r * Math.cos(ang), cy + r * Math.sin(ang)];
      };

      // 同心网格
      for (let lv = 1; lv <= LEVELS; lv++) {
        const r = (R * lv) / LEVELS;
        ctx.beginPath();
        for (let i = 0; i <= n; i++) {
          const [x, y] = point(i % n, r);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = "#e3e6ea";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 轴线 + 维度标签
      ctx.font = "12px 'Microsoft YaHei', sans-serif";
      ctx.fillStyle = "#495057";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      for (let i = 0; i < n; i++) {
        const [ax, ay] = point(i, R);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(ax, ay);
        ctx.strokeStyle = "#e3e6ea";
        ctx.stroke();
        const [lx, ly] = point(i, R + 18);
        ctx.fillText(dims[i].name, lx, ly);
      }

      // 数据多边形（分数 0-100 映射半径）
      ctx.beginPath();
      for (let i = 0; i <= n; i++) {
        const s = Math.max(0, Math.min(100, dims[i % n].score || 0));
        const [x, y] = point(i % n, (s / 100) * R);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.fillStyle = "rgba(13, 110, 253, 0.22)";
      ctx.fill();
      ctx.strokeStyle = "#0d6efd";
      ctx.lineWidth = 2;
      ctx.stroke();

      // 顶点
      for (let i = 0; i < n; i++) {
        const s = Math.max(0, Math.min(100, dims[i].score || 0));
        const [x, y] = point(i, (s / 100) * R);
        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = "#0d6efd";
        ctx.fill();
      }
    },
  },
  template: `
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">📊 面试报告</h4>
      <button class="btn btn-outline-secondary btn-sm" @click="back()">← 返回候选人端</button>
    </div>

    <div v-if="loading" class="text-center text-muted py-5">
      <div class="spinner-border spinner-border-sm me-2" role="status"></div>报告生成中…
    </div>
    <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

    <template v-else-if="report">
      <!-- 总分概要 -->
      <div class="card mb-3">
        <div class="card-body d-flex align-items-center">
          <div class="me-4 text-center px-3 score-hero">
            <div class="display-4 fw-bold" :class="scoreClass(report.total_score)">{{ report.total_score }}</div>
            <div class="text-muted small">总分</div>
          </div>
          <div>
            <h5 class="mb-2">🏢 {{ report.job_title }}</h5>
            <p class="mb-1">
              <span class="badge" :class="levelClass(report.level)">{{ report.level }}</span>
              <span class="text-muted ms-2 small">候选人：{{ report.candidate_name }}</span>
              <span class="text-muted ms-2 small">时间：{{ report.created_at }}</span>
            </p>
            <p class="text-muted small mb-0">本报告由 AI 面试官根据面试表现自动生成。</p>
          </div>
        </div>
      </div>

      <div class="row">
        <!-- 雷达图 -->
        <div class="col-md-5 mb-3">
          <div class="card h-100">
            <div class="card-body text-center">
              <h6 class="card-title mb-3">能力维度雷达</h6>
              <div class="d-flex justify-content-center">
                <canvas ref="radarCanvas" width="400" height="400" style="max-width:100%;"></canvas>
              </div>
            </div>
          </div>
        </div>
        <!-- 维度进度条 -->
        <div class="col-md-7 mb-3">
          <div class="card h-100">
            <div class="card-body">
              <h6 class="card-title mb-3">各维度得分</h6>
              <div v-for="d in (report.dimension_scores||[])" :key="d.name" class="mb-3">
                <div class="d-flex justify-content-between small mb-1">
                  <span>{{ d.name }}</span>
                  <span class="fw-bold" :class="scoreClass(d.score)">{{ d.score }} 分</span>
                </div>
                <div class="progress" style="height: 8px;">
                  <div class="progress-bar" :class="barClass(d.score)" :style="{width: (d.score||0) + '%'}"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 优缺点 -->
      <div class="row">
        <div class="col-md-6 mb-3">
          <div class="card h-100 border-success">
            <div class="card-header bg-success text-white">💪 优点</div>
            <div class="card-body">
              <ul class="mb-0"><li v-for="(s,i) in (report.strengths||[])" :key="i">{{ s }}</li></ul>
            </div>
          </div>
        </div>
        <div class="col-md-6 mb-3">
          <div class="card h-100 border-warning">
            <div class="card-header bg-warning text-dark">⚠️ 待改进</div>
            <div class="card-body">
              <ul class="mb-0"><li v-for="(s,i) in (report.weaknesses||[])" :key="i">{{ s }}</li></ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 改进建议 -->
      <div class="card mb-3">
        <div class="card-header">📈 改进建议</div>
        <div class="card-body">
          <ol class="mb-0"><li v-for="(s,i) in (report.suggestions||[])" :key="i">{{ s }}</li></ol>
        </div>
      </div>

      <!-- 逐题复盘 -->
      <div class="card">
        <div class="card-header">🗒 逐题复盘（共 {{ (report.answers||[]).length }} 题）</div>
        <div class="card-body">
          <div v-if="!(report.answers||[]).length" class="text-muted text-center py-3">暂无逐题数据</div>
          <div v-for="a in (report.answers||[])" :key="a.round_no" class="border rounded p-2 mb-2">
            <details class="report-details">
              <summary class="fw-bold">
                第 {{ a.round_no }} 题 · {{ catName(a.category) }}
                <span class="ms-2 badge" :class="scoreBadge(a.score)">{{ a.score ?? '—' }} 分</span>
              </summary>
              <div class="mt-2 small">
                <p class="mb-1"><strong>问题：</strong>{{ a.question }}</p>
                <p class="mb-1"><strong>我的回答：</strong>{{ a.answer_text }}</p>
                <p class="mb-0"><strong>反馈：</strong>{{ a.feedback }}</p>
              </div>
            </details>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card">
      <div class="card-body text-center text-muted py-5">未找到该面试的报告。</div>
    </div>
  </div>`,
};
