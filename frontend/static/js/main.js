/**
 * Vue 应用入口（成员C维护）。
 * 负责顶层视图切换：candidate(候选人端) / admin(后台) / interview(面试) / report(报告)。
 * 候选人身份通过 localStorage 持久化，供「选岗 → 创建面试」使用。
 */
const { createApp } = Vue;

const app = createApp({
  data() {
    // 支持 ?view=admin / ?view=interview / ?view=report 深链，便于测试与演示
    const init = new URLSearchParams(window.location.search).get("view") || "candidate";
    return {
      currentView: init, // candidate | admin | interview | report
      interviewContext: null, // 当前面试上下文 { id, jobId, jobTitle }
      reportId: null, // 查看报告的面试 id
      candidate: null, // 当前候选人档案
    };
  },
  created() {
    // 恢复上次会话的候选人身份
    try {
      const saved = localStorage.getItem("sitas_candidate");
      if (saved) this.candidate = JSON.parse(saved);
    } catch (e) {
      console.warn("读取候选人缓存失败：", e);
    }
  },
  methods: {
    /** 保存当前候选人并写入 localStorage */
    setCandidate(c) {
      this.candidate = c;
      try {
        localStorage.setItem("sitas_candidate", JSON.stringify(c));
      } catch (e) {
        console.warn("保存候选人缓存失败：", e);
      }
    },
    goCandidate() {
      this.currentView = "candidate";
      window.scrollTo(0, 0);
    },
    goAdmin() {
      this.currentView = "admin";
      window.scrollTo(0, 0);
    },
    /** 进入面试对话视图（由 CandidateView 在创建面试后触发） */
    startInterview(ctx) {
      this.interviewContext = ctx; // { id, jobId, jobTitle }
      this.currentView = "interview";
      window.scrollTo(0, 0);
    },
    /** 进入结果报告视图 */
    viewReport(id) {
      this.reportId = id;
      this.currentView = "report";
      window.scrollTo(0, 0);
    },
    /** 面试/报告返回候选人端 */
    backToCandidate() {
      this.interviewContext = null;
      this.reportId = null;
      this.currentView = "candidate";
      window.scrollTo(0, 0);
    },
  },
  components: {
    CandidateView,
    AdminView,
    InterviewView,
    ReportView,
  },
});

app.mount("#app");
