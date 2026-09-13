# 参与贡献 / Contributing

欢迎修复资料提取、来源绑定、数字检查、可编辑性检查和文档问题。品牌判断的改动应提供明确依据，不能只换术语。请优先给出最小脱敏样例、预期结果、实际结果、宿主与版本。

Contributions to extraction, source binding, numerical checks, editability checks and documentation are welcome. Method changes need a clear rationale. Provide a minimal sanitized sample, expected and actual behavior, host and version.

1. Fork后在分支修改 / Fork and make changes on a branch.
2. 保持中英文说明语义一致；标记未验证项 / Keep Chinese and English meanings aligned and disclose untested scope.
3. 运行 `python3 scripts/verify_release.py`；若改渲染器，另行生成并逐页查看真实成品 / Run release checks. Renderer changes also need an actual export and visual inspection.
4. 提交PR并写明问题、改动、验证和限制 / Open a PR describing the problem, change, validation and limits.

不要提交私有客户资料、第三方SDK、字体文件、缓存或凭据。贡献通用代码和文档时，须拥有相应权利，并同意其按本仓库适用MIT许可分发；不因此改变谋术鸣与第三方素材的既有许可范围。理论引用先核对原作者和来源。

Do not submit private client data, third-party SDKs, font files, caches or credentials. You must have rights to contributed generic code and docs and agree to their applicable MIT distribution. This does not change the existing scope for MouShuMing or third-party material. Verify theory attribution and sources.
