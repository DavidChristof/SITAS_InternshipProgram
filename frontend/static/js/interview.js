/**
 * 面试模块组件（成员C实现）。
 *  - InterviewView：AI 面试对话（文字 + 录音），阶段二完善。
 *  - ReportView：面试结果报告（总分 / 雷达图 / 优缺点 / 建议），阶段三完善。
 *
 * 阶段一仅提供占位视图，保证「候选人端 → 面试 → 报告」的视图跳转链路可跑通。
 */
const InterviewView = {
  props: {
    interview: { type: Object, default: null }, // { id, jobId, jobTitle }
  },
  data() {
    return {
      messages: [], // 聊天气泡 [{from:'ai'|'me', text}]
      status: "idle", // idle | running | finished
      loading: false,
      error: "",
    };
  },
  computed: {
    jobTitle() {
      return (this.interview && this.interview.jobTitle) || "本场面试";
    },
  },
  methods: {
    back() {
      this.$emit("back");
    },
  },
  // TODO(阶段二): 实现 startInterview / submitAnswer / 录音上传 / 逐题评分反馈 / 进度提示
  template: `
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">💬 AI 面试对话</h4>
      <button class="btn btn-outline-secondary btn-sm" @click="back()">← 返回候选人端</button>
    </div>
    <div class="card">
      <div class="card-body text-center text-muted py-5">
        <div class="display-6 mb-2">🚧</div>
        <h5>{{ jobTitle }}</h5>
        <p>面试对话功能将在<b>阶段二</b>实现（文字面试 → 逐题评分 → 录音 → 报告）。</p>
        <p class="small">当前仅确认视图链路：候选人端 → 面试 → 报告 可正常跳转。</p>
      </div>
    </div>
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
