# plan.json：内容与来源契约

JSON 使用 UTF-8。这是 AI 的工作文件，不是要求客户填写的表单。渲染器可增加布局字段；保留以下基本含义。

```json
{
  "schema_version": "1.0",
  "project": {"title":"上市方案", "audience":"品牌负责人", "purpose":"确定试行范围", "slide_count":1},
  "claims": [{
    "id":"F01", "kind":"source", "text":"预算上限6万元",
    "sources":[{"chunk_id":"填写intake真实返回的ID", "quote":"预算上限6万元"}]
  }],
  "conflicts": [],
  "slides": [{
    "id":"S01", "title":"试行范围", "purpose":"确认预算和地域", "layout":"statement",
    "claim_ids":["F01"], "lead":"预算上限6万元", "body":["优先完成小范围验证"],
    "required_text":["预算上限6万元"], "notes":"保留相关来源定位与讲述要点"
  }]
}
```

示例中来源 ID 仅解释格式，实际运行必须使用 intake 的返回值。

## 事实账本

- `source`：材料中的说法，引用真实 chunk 和逐字摘录；仍需判断来源是否可靠。
- `proposal`：本次提出的建议、目标、创意，不声称已发生。影响决策时在页面写清“建议/目标/试行”等。
- `calculation`：据资料计算，记录 sources 与 `calculation: {operation, values, result}`。operation 支持 sum、difference、ratio；单位换算、加权等需另行计算并保留说明。
- `unknown`：缺资料或冲突未解。引用此事实的页面必须有 `disclosure`。

`conflicts` 每项包含 `id`、涉及的 `claim_ids`、`resolution`（采用哪项及依据；未解决留空）。不是最新文件就自动胜出。

## 页面数据

- `title`、`purpose`、`layout`、`claim_ids` 是工作所需字段。
- `required_text` 指必须保留且可编辑的正文；最终 PPTX 会与它核对。
- `disclosure` 是必须可见的限定语，不能仅放备注。
- `table.rows` 是完整二维数组，含表头。可用 `totals: [{column:1, rows:[1,2], expected:60000}]` 声明求和关系，行列从0开始。
- `chart` 包含 `type`、`unit`、`categories`、`series:[{name, values}]`；具体数值与类别将在最终 PPTX 缓存中核对。
- 每个图表数据点和表格中的数字单元格必须有 `bindings`，避免“有引用但数字已错”。图表项为 `{series:0,index:0,value:54,label:"工作日下午",claim_id:"F01",chunk_id:"真实ID",quote:"工作日下午54人"}`；表格项将 series/index 换成 row/column。坐标从0开始，表头是row=0；binding.value 与原始单元格内容一致（例如"29元"）。
- source 类型绑定的引用需包含该数值；图表还需包含对应类别文字。calculation 类型绑定需等于计算结果。proposal 类型绑定可以没有引用，但页面必须有可见 disclosure。表格第1周等排期数字也按提议绑定。
- 图表可声明 `totals:[{series:0,expected:120}]` 核对合计。不得通过修改绑定、引用或总量去掩盖错误数字；原始来源的真实性仍须人工核对。
- `notes` 可包含讲述补充与来源。内部验证日志不进入备注。
- `image` 包含相对 `path`、`alt`、`source`、`fit`。原 Logo 使用 contain；示意插画与真实照片分清。

不要为了通过脚本把所有断言标成 proposal，也不要遗漏图表背后的事实映射。脚本不是事实核查模型，不会自动判断引用是否真正支持语义。

## 稳定标识与改稿

slide.id 和 claim.id 是稳定标识，调整页面顺序时不重新编号已有 ID。更换来源后用 impact.py 查直接受影响页；新增事实、缺失事实、定位与预算的连带变化由 AI 再复核。

每项 binding 必填 `label`：图表是该点类别，表格是该行首列文字。检查器会对照显示标签，防止类别换序后数值错位。使用能明确对应这一类别和数值的最短完整原文，宽泛引用仍需人工确认语义。

## 谋术鸣应用记录（v1.1新增，可选）

品牌方案使用模型时填写 `methodology`；非品牌任务与旧计划可省略。不是要求用户填写的表单。

- `id: "moushuming"`，`content_version: "4.0"`。
- `mode`：`full` 表示具备全案前置材料；`partial` 表示按已知范围形成局部方案；`hypothesis` 表示带缺口的工作假设/演示。模式不代表客户认可。
- `inputs`：`assessment_claim_ids`、`source_card_claim_ids`、`founder_claim_ids`。full 模式三者均须引用真实 source 事实；其余模式如实留缺口。
- `center`：`value_claim_ids`、`mission_claim_ids`、`vision_claim_ids`、`slide_ids`。缺失的愿景用 unknown 事实并在对应页显示待确认，不能拿使命冒充愿景。
- `mao[]`：每项含 `id, claim_ids, slide_ids, category, difference, proof`，后三项对应定位三问；不足之处写待验证并关联 unknown 事实。
- `shu[]`：每项含 `id, mao_id, claim_ids, slide_ids, task, perception, scene`。指向一条定位判断，说明设计任务、期望认知与使用场景。
- `ming[]`：每项含 `id, mao_id, shu_ids, claim_ids, slide_ids, audience, channel, content, rhythm, feedback`。所用设计与传播自身指向同一定位。

局部任务仍说明未涉及模块的缺口，可用关联 unknown 事实的简短记录；不生成用户没要的设计或传播正文。只有使用模型才填写这一部分，禁止为了过检查将经营周报硬改成品牌全案。

方法记录引用的事实须实际出现在其声明页面的 `claim_ids` 中；脚本检查这种承接关系，商业合理性由人判断。完整可运行示例见 `examples/plan.json`。需要在成品核对署名时，在相应页面的 `required_text` 声明完整署名。
