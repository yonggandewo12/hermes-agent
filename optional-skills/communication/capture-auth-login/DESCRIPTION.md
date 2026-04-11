# Capture Auth Login

交互式登录捕获 skill。给定 URL，自动检测登录跳转，打开浏览器让用户完成登录（含扫码），然后将 Playwright storage_state 自动保存到 `~/.hermes/stats/{域名}.js`，CLI 输出成功信息。

**安装方式：**
```bash
hermes skills install official/communication/capture-auth-login
```

**依赖：** `playwright`（会自动提示安装 Chromium）

**触发词：** `/capture-auth-login <url>`、`帮我登录xxx`、`save login state`、`capture auth`
