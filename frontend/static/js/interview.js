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
  methods: {
    back() {
      this.$emit("back");
    },
  },
  // TODO(阶段三): 实现 总分/等级/维度雷达图/优缺点/建议/逐题复盘
  template: `
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">📊 面试报告</h4>
      <button class="btn btn-outline-secondary btn-sm" @click="back()">← 返回候选人端</button>
    </div>
    <div class="card">
      <div class="card-body text-center text-muted py-5">
        <div class="display-6 mb-2">🚧</div>
        <h5>面试 #{{ interviewId }}</h5>
        <p>结果报告功能将在<b>阶段三</b>实现（总分 / 等级 / 维度雷达图 / 优缺点 / 改进建议）。</p>
      </div>
    </div>
  </div>`,
};
