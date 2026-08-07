/**
 * 面试对话组件（成员C实现）。
 * 功能：进度提示 / 文字面试 / 语音录音上传 / 逐题评分反馈 / 报告展示。
 */
const InterviewView = {
  data() {
    return {
      interviewId: null,
      currentQuestion: null,
      roundNo: 0,
      messages: [], // [{from:'ai'|'me', text}]
      answerText: "",
      status: "idle", // idle | running | finished
      report: null,
      recording: false,
      mediaRecorder: null,
      audioChunks: [],
    };
  },
  methods: {
    async startInterview() {
      // TODO(成员C): 调用 POST /api/interview/{id}/start 获取第一题
    },
    async submitAnswer() {
      // TODO(成员C): 调用 POST /api/interview/{id}/answer 提交，展示评分与下一题
    },
    startRecord() {
      // TODO(成员C): 用 MediaRecorder 录音，结束后上传 /api/interview/... 语音
      const self = this;
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          const mr = new MediaRecorder(stream);
          mr.ondataavailable = (e) => self.audioChunks.push(e.data);
          mr.onstop = () => self.uploadAudio(new Blob(self.audioChunks, { type: "audio/webm" }));
          self.mediaRecorder = mr;
          self.recording = true;
          self.audioChunks = [];
          mr.start();
        })
        .catch((e) => alert("无法获取麦克风：" + e.message));
    },
    stopRecord() {
      this.recording = false;
      if (this.mediaRecorder) this.mediaRecorder.stop();
    },
    uploadAudio(blob) {
      // TODO(成员C): 上传音频 → 后端转写 → 作为回答提交
      alert("语音上传转写功能开发中，请先使用文字回答。");
    },
  },
  template: `
  <div>
    <h4 class="mb-3">💬 AI 面试对话</h4>
    <div class="chat-box" ref="chatBox">
      <div v-for="(m, i) in messages" :key="i" class="d-flex" :class="m.from==='me' ? 'justify-content-end' : 'justify-content-start'">
        <div class="msg-bubble" :class="m.from==='ai' ? 'msg-ai' : 'msg-me'">{{ m.text }}</div>
      </div>
    </div>
    <div class="mt-3">
      <div class="input-group">
        <textarea v-model="answerText" class="form-control" rows="2" placeholder="输入你的回答…" :disabled="status !== 'running'"></textarea>
        <button class="btn btn-primary" @click="submitAnswer" :disabled="status !== 'running'">提交回答</button>
        <button class="btn btn-danger" :class="{recording: recording}" @click="recording ? stopRecord() : startRecord()">
          {{ recording ? '停止录音' : '🎙 语音回答' }}
        </button>
      </div>
      <p class="text-muted small mt-1">第 {{ roundNo }} 轮 · 面试状态：{{ status }}</p>
    </div>
  </div>`,
};
