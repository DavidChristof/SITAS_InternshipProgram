/**
 * 后端 API 统一封装（成员C维护）。
 * 所有请求走 fetch 到 /api/*，统一响应格式 {code, message, data}。
 */
const API = {
  base: "",

  async request(method, url, data, isForm = false) {
    const opts = { method, headers: {} };
    if (isForm) {
      opts.body = data; // FormData
    } else if (data !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(data);
    }
    const resp = await fetch(this.base + url, opts);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${url}`);
    return resp.json();
  },

  get(url) {
    return this.request("GET", url);
  },
  post(url, data) {
    return this.request("POST", url, data);
  },
  put(url, data) {
    return this.request("PUT", url, data);
  },
  del(url) {
    return this.request("DELETE", url);
  },
  upload(url, formData) {
    return this.request("POST", url, formData, true);
  },

  /** 统一响应校验：code !== 0 抛错，返回 data。 */
  unwrap(resp) {
    if (resp && resp.code === 0) return resp.data;
    throw new Error((resp && resp.message) || "请求失败");
  },
};
