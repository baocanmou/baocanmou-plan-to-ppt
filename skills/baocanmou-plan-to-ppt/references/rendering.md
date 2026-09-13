# 视觉与运行环境

## 先查可用能力

本 Skill 是供 AI 助手执行的专业工作流，Python 脚本负责提取与检查，不会自己调用大模型。无需提供包参谋 API Key，也不会上传资料。

资料脚本与 PPTX 检查器需要 Python 3.10+；MD/TXT/CSV/TSV/DOCX/PPTX 使用标准库，PDF 文本提取可选 PyMuPDF 或 pypdf。图片/OCR/XLSX/旧 DOC 文件可用宿主读取，保留出处；不要宣称脚本已原生支持。

PPTX 生成使用当前宿主可用的能力：

- Codex 中如果有官方演示文稿能力，读取它的规范，使用其运行环境、导出与验证流程。随包提供的 `scripts/render_artifact.mjs` 是可选适配器，需要宿主提供 `@oai/artifact-tool`，并不是可公开 npm 安装的依赖。
- 其他助手使用已有的 PPTX 工具或公开生成库（如 PptxGenJS），由助手依据 plan.json 创建原生元素；本版本没有内置或声称测试了这些运行环境。
- 不具备任何 PPTX 生成工具时，明确说明缺口；仅有大纲和 HTML 不能算完成。

公开包不包含专有 SDK、宿主运行文件或独立字体文件；示范PDF嵌入字体的许可见NOTICE。API、图像生成、字体与模板的可用性/费用取决于用户环境；实际生成前说明新增依赖，不要求安装整套无关工具。

## 设计决策

沿用用户指定模板、比例、字体和品牌资产。只有文本来源的旧 PPT 不自动成为视觉模板。无指定设计时选择与行业、听众和场合匹配的色彩与字体，并检查是否可用。

控制整套节奏：封面/主张、证据、比较、场景图、执行表可以形成变化。每页保留主次；密集内容拆分或精简，先不靠缩小字体解决。留白服务阅读，不使用巨大空区凑高级感。

优先原生文字与数据。真实产品图、授权素材或标明用途的生成图承担视觉内容，不拿完整幻灯片截图冒充可编辑 PPT。图像生成不能改坏原 Logo、产品标签或事实性证据。

## 可选适配器

在已具备官方 Artifact Tool 的宿主中：

```bash
node scripts/render_artifact.mjs --plan /path/plan.json --out /path/draft.pptx --preview /path/previews
```

宿主须使 `@oai/artifact-tool` 可导入，或通过 `BCM_ARTIFACT_MODULE` 指定模块绝对路径。适配器不会搜索用户的隐藏目录，不会自动下载 SDK。参数文件里的相对图片路径以 plan.json 所在目录解析；图片必须存在。

适配器提供 cover、statement、editorial、quote、image、table、chart、closing、framework 作为可运行起点。framework 用于价值观中心指引三模块的原生文字示意，含 center.heading、center.text 与三项 columns。layout 不在名单中时明确报错，由助手扩展或换宿主生成，不静默退回统一模板。用户指定的设计始终优先，可以自编排版并保留 plan.json 契约。

适配器导出的是草稿。使用宿主要求的最终化流程，再调用 pptxcheck；所有页面逐页渲染检查之后，才报告视觉检查范围。可选 PDF 导出由宿主完成。PDF 字体、PowerPoint 实际打开、Google Slides 导入各自独立验收。
