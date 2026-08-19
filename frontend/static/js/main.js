/**
 * Vue 应用入口（成员C维护）。
 * 顶层视图切换 + 三类用户身份门面（方案A）：
 *   student(学生) / hr(HR教师) / admin(管理员)，身份存 localStorage（sitas_role）。
 *  - 未选身份：显示身份选择首屏
 *  - 学生：仅候选人端；HR：后台（无「面试官管理」）；管理员：后台全部 + 系统管理
 * 视图：candidate(候选人端) / admin(后台) / interview(面试) / report(报告)。
 */
const { createApp } = Vue;

const ROLES = ["student", "hr", "admin"];

const app = createApp({
  data() {
    // 支持 ?view=admin / ?view=interview / ?view=report 深链，便于测试与演示
    const init = new URLSearchParams(window.location.search).get("view") || "candidate";
    return {
      currentView: init, // candidate | admin | interview | report
      role: null, // student | hr | admin
      interviewContext: null, // 当前面试上下文 { id, jobId, jobTitle }
      reportId: null, // 查看报告的面试 id
      candidate: null, // 当前候选人档案
    };
  },
  computed: {
    roleName() {
      return { student: "学生", hr: "HR / 教师", admin: "管理员" }[this.role] || "";
    },
  },
  created() {
    // 恢复上次会话的候选人身份
    try {
      const saved = localStorage.getItem("sitas_candidate");
      if (saved) this.candidate = JSON.parse(saved);
    } catch (e) {
      console.warn("读取候选人缓存失败：", e);
    }
    // 身份：优先 ?role= 参数（便于测试/演示），否则用 localStorage 记忆
    const p = new URLSearchParams(window.location.search);
    const role = p.get("role") || localStorage.getItem("sitas_role");
    if (role && ROLES.includes(role)) {
      this.role = role;
      try {
        localStorage.setItem("sitas_role", role);
      } catch (e) {}
    }
    // 深链：?view=interview&iid=1&jobTitle=xxx 直接进入面试对话
    if (this.currentView === "interview" && p.get("iid")) {
      this.interviewContext = {
        id: Number(p.get("iid")),
        jobId: Number(p.get("jobId") || 1),
        jobTitle: p.get("jobTitle") || "演示岗位",
      };
    }
    // 深链：?view=report&iid=1 直接进入结果报告
    if (this.currentView === "report" && p.get("iid")) {
      this.reportId = Number(p.get("iid"));
    }
    // 已选身份且未显式指定 view 时，进入该身份默认视图
    if (this.role && !p.get("view")) {
      this.currentView = this.roleDefaultView(this.role);
    }
  },
  methods: {
    /** 身份 → 默认视图 */
    roleDefaultView(r) {
      return r === "student" ? "candidate" : "admin";
    },
    /** 选择 / 切换身份 */
    selectRole(r) {
      if (!ROLES.includes(r)) return;
      this.role = r;
      try {
        localStorage.setItem("sitas_role", r);
      } catch (e) {}
      this.currentView = this.roleDefaultView(r);
      window.scrollTo(0, 0);
    },
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
      if (this.role !== "student") return; // 身份门控：仅学生可进候选人端
      this.currentView = "candidate";
      window.scrollTo(0, 0);
    },
    goAdmin() {
      if (this.role !== "hr" && this.role !== "admin") return; // 仅 HR/管理员可进后台
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
    /** 面试/报告返回（回到当前身份的默认视图） */
    backToCandidate() {
      this.interviewContext = null;
      this.reportId = null;
      this.currentView = this.role ? this.roleDefaultView(this.role) : "candidate";
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
