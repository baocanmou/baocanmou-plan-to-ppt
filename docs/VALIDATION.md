# 验证范围 / Validation scope

v1.2.0公开包装日期：2026-09-14。沿用v1.1.0已经制作的中文示范，不把补文档说成重新制作了客户项目。

Public distribution date: 2026-09-14. Version 1.2.0 retains the existing v1.1.0 Chinese example; this packaging update is not a new client project.

| 项目 / Item | 结果与范围 / Result and scope |
|---|---|
| 样例 / Sample | 4份虚构资料、27段来源、20条claims、12页 / 4 fictional sources, 27 chunks, 20 claims, 12 slides |
| 工作流回归 / Workflow regressions | 25项既有测试：提取、来源、数值、类别、合计、改稿、方法关系和PPTX篡改 / 25 existing tests for extraction, references, values, labels, sums, revision impact, method links and PPTX tampering |
| 安装回归 / Installation regressions | 3项：保留原文件、符号链接拒绝、扫描目录外备份与回滚、dry-run无写入 / 3 tests covering data preservation, symlink rejection, backups outside discovery, rollback and a non-writing dry run |
| 最终PPTX / Output | 12页、85个原生文字对象、3张表格、1张图表、1个嵌入XLSX、2张图片 / 12 slides, 85 native text objects, 3 tables, 1 chart, 1 embedded XLSX, 2 images |
| 数据负例 / Negative cases | 实际表格15000→15001、图表54→540、删除样本说明均能触发检查 / Tampered table and chart values and a removed disclosure trigger checks |
| PDF | 12页可提取文字；21个Source Han Sans CN嵌入字体子集 / 12 text-extractable pages; 21 embedded Source Han Sans CN font subsets |
| 视觉 / Visual | v1.1制作时完成12页查看；本次复核5张公开预览 / All 12 pages inspected in v1.1 production; five public previews re-inspected for this release |
| 发布检查 / Release checks | 版本、必要文档、相对链接、素材、敏感路径、样例提取与成品检查 / Version, required docs, local links, assets, private paths, sample extraction and output checks |

在仓库根目录运行 `python3 scripts/verify_release.py` 可复查标准库检查和28项测试。`python3 scripts/build_release.py` 生成两个ZIP及SHA256SUMS。CI运行相同发布检查。PDF字体与看图记录是本次人工触发的独立检查，不是CI的自动视觉验收。

Run `python3 scripts/verify_release.py` for the standard-library checks and 28 tests. `python3 scripts/build_release.py` builds two ZIPs and SHA256SUMS. CI uses the same release checks. PDF font inspection and visual review are separate checks, not automated visual acceptance in CI.

## 能证明什么 / What this establishes

检查发现结构缺失、数字错位和一些来源关系错误。它不能判断引用是否真的支持观点、市场定位是否合理、原资料是否真实，也不能证明用户改稿时绝不会出错。历史独立试用中，普通助手也能正确处理基础预算冲突，因此没有充分依据断言本Skill的策划文字一定更好。

Checks detect missing structure, mismatched numbers and some source relationship errors. They do not prove semantic support, positioning quality, source truth or error-free future editing. A historical baseline assistant also handled basic budget conflicts correctly; the trial does not establish superior strategic writing.

## 仍未验证 / Still unverified

- PowerPoint、WPS、Google Slides实际打开、修改、另存 / Native opening, editing and re-saving across these apps.
- Claude Code等其他宿主完整生成链；英文成套PPT和多语言复杂排版 / Full generation in other hosts, a complete English deck and complex multilingual layouts.
- 真实客户、长提案、自带复杂模板、扫描件 / Real client use, long proposals, complex custom templates and scans.
- 节省时间、用户采纳率、传播、获客与商业效果 / Time savings, adoption, reach, lead generation and commercial results.

[历史详细验证记录 / Historical detailed record](../skills/baocanmou-plan-to-ppt/docs/验证说明.md)

本版仅更新示范文件作者与标题元数据，12页内容不变；PDF更新前后逐页渲染哈希相同。Example file author/title metadata were updated; slide content is unchanged, with identical per-page PDF render hashes.

公开PDF另去除了原导出中无效的辅助结构标签；12页文字和渲染哈希不变，重读无渲染警告。本版不声称PDF/UA或无障碍阅读验收。Invalid accessibility structure tags from the original export were removed; text and rendered pixels remain unchanged, and re-rendering reports no warnings. PDF/UA and accessibility behavior are not validated.
