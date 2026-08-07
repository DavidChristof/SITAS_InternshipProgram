/**
 * Vue 应用入口（成员C维护）。
 * 注册候选人与后台两个全局组件，控制当前视图切换。
 */
const { createApp } = Vue;

const app = createApp({
  data() {
    return {
      currentView: "candidate", // candidate | admin
    };
  },
  components: {
    CandidateView,
    AdminView,
  },
});

app.mount("#app");
