# GitHub OAuth 应用配置指南

本指南将帮助您在 GitHub 上创建 OAuth 应用，并获取 Client ID 和 Client Secret，以便在 GitHuber 应用中使用。

## 快速访问链接

**直接创建 OAuth 应用的链接**：[https://github.com/settings/applications/new](https://github.com/settings/applications/new)

> 注意：您需要先登录 GitHub 账号才能访问此链接。

按照步骤填写即可，如果成功则不需要再观看下方教学。

## 步骤 1: 登录 GitHub

首先，确保您已登录 GitHub 账号。如果没有账号，请先在 [GitHub](https://github.com) 注册。

## 步骤 2: 访问开发者设置

1. 点击右上角的个人头像
2. 在下拉菜单中选择 **Settings**（设置）
3. 在左侧菜单栏的最底部，找到并点击 **Developer settings**（开发者设置）

![开发者设置](https://docs.github.com/assets/cb-34573/mw-1440/images/help/settings/developer-settings.webp)

## 步骤 3: 创建新的 OAuth 应用

1. 在左侧菜单中，点击 **OAuth Apps**
2. 点击右上角的 **New OAuth App** 按钮

![新建OAuth应用](https://docs.github.com/assets/cb-34573/mw-1440/images/help/oauth/oauth-apps-list.webp)

## 步骤 4: 填写应用信息

在创建 OAuth 应用的表单中，填写以下信息：

1. **Application name**（应用名称）: 输入 `GitHuber` 或您喜欢的任何名称
2. **Homepage URL**（主页 URL）: 输入 `http://localhost:8000`
3. **Application description**（应用描述）: 简单描述应用，例如 "GitHub 文件管理工具"
4. **Authorization callback URL**（授权回调 URL）: 输入 `http://localhost:8000/callback`

![填写应用信息](https://docs.github.com/assets/cb-49581/mw-1440/images/help/oauth/oauth-app-create.webp)

5. 点击 **Register application**（注册应用）按钮

## 步骤 5: 获取 Client ID 和 Client Secret

注册成功后，您将看到应用详情页面：

1. 在这个页面上，您可以看到 **Client ID**（客户端 ID）
2. 点击 **Generate a new client secret**（生成新的客户端密钥）按钮
3. 确认操作后，系统会生成并显示 **Client Secret**（客户端密钥）

![获取凭证](https://docs.github.com/assets/cb-33207/mw-1440/images/help/oauth/oauth-client-secret.webp)

> **重要提示**: Client Secret 只会显示一次，请立即复制并保存在安全的地方。如果您忘记了 Client Secret，需要重新生成一个新的。

## 步骤 6: 在 GitHuber 应用中填写凭证

1. 打开 GitHuber 应用
2. 当应用提示输入 OAuth 配置时，粘贴您刚才获取的 **Client ID** 和 **Client Secret**
3. 点击确定保存配置

## 注意事项

- 请保管好您的 Client ID 和 Client Secret，不要分享给他人
- 如果您需要在多台设备上使用 GitHuber，每台设备都需要填写相同的凭证
- 如果您怀疑凭证泄露，请立即在 GitHub 上重新生成 Client Secret
- 授权回调 URL 必须与应用中设置的一致，默认为 `http://localhost:8000/callback`

## 常见问题

### 授权失败怎么办？

- 检查 Client ID 和 Client Secret 是否正确填写
- 确认您的网络连接正常
- 如果您在中国大陆，可能需要使用代理服务

### 需要更改授权范围吗？

- GitHuber 默认请求 `repo` 权限，这足以管理您的仓库
- 无需手动更改授权范围

### 如何撤销授权？

1. 访问 GitHub 设置
2. 进入 **Applications** > **Authorized OAuth Apps**
3. 找到 GitHuber 应用并点击 **Revoke** 按钮

如果您有任何其他问题，请访问 [GitHub 文档](https://docs.github.com/en/developers/apps/building-oauth-apps) 或联系我们获取支持。 