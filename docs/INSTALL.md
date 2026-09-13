# 安装与使用 / Installation and use

## 环境 / Requirements

支持 Agent Skills 的助手、文件读写、Python 3.10+。生成实际 PPTX 还需要宿主的演示文稿工具。仅需要逐页内容时可以停在内容阶段。

An assistant with Skills support, file access and Python 3.10+. Actual PPTX generation also requires the host's presentation tools. Outline-only requests can stop before rendering.

- TXT/MD、CSV/TSV、DOCX、PPTX提取及检查使用Python标准库。PDF文本可使用宿主工具，或选装pypdf/PyMuPDF并遵守其许可。扫描件/OCR、XLSX、旧DOC/PPT不是内置解析格式。
- Extraction and checks for TXT/MD, CSV/TSV, DOCX and PPTX use the standard library. PDF text can be read by the host or an optional pypdf/PyMuPDF installation under its license. OCR, XLSX and legacy DOC/PPT are not built-in parsers.
- `render_artifact.mjs` 需要宿主已经提供 `@oai/artifact-tool`。本包不分发该专有SDK，也没有内置PptxGenJS渲染器。
- The optional adapter needs a host-provided `@oai/artifact-tool`. This package distributes no proprietary SDK and includes no PptxGenJS renderer.

## 完整仓库 / Full repository

```bash
git clone https://github.com/yht0912/baocanmou-plan-to-ppt.git
cd baocanmou-plan-to-ppt
python3 scripts/install_skill.py --host codex --dry-run
python3 scripts/install_skill.py --host codex
```

- Codex 默认目录 / default: `~/.agents/skills/baocanmou-plan-to-ppt`
- Claude Code: replace `--host codex` with `--host claude`; default `~/.claude/skills/baocanmou-plan-to-ppt`.
- `--target /absolute/skill/destination` 指定完整目的目录。对符号链接目标，先确认其共享源位置再更新共享源。
- `--target` sets the complete destination directory. If it is a symlink, identify and update the shared source explicitly.

重开会话，按名称或 `$baocanmou-plan-to-ppt` 调用。宿主可能需要自行开启Skills。重新打开不保证所有宿主都会自动发现；以宿主实际发现结果为准。

Reopen the conversation and invoke the Skill by name. Hosts may require enabling Skills; discovery behavior varies.

## 独立 Skill ZIP / Standalone ZIP

从 Releases 下载 `baocanmou-plan-to-ppt-skill-v1.2.0.zip`，解压得到完整同名文件夹，放入上面的技能目录或按宿主导入要求处理。不要只复制SKILL.md；脚本、方法文档与示范需要保留。

Download the standalone ZIP from Releases. Keep the entire extracted folder, including scripts, references and examples. Import it according to the host's requirements. The full plugin ZIP additionally contains root documentation, artwork and release tooling; it is not a claim of one-click marketplace installation.

## 更新、回滚与移除 / Upgrade, rollback and removal

```bash
python3 scripts/install_skill.py --host codex --replace --dry-run
python3 scripts/install_skill.py --host codex --replace
```

替换时先校验暂存副本哈希，再备份旧版。备份在技能扫描目录之外，例如 `~/.agents/skill-backups/`。安装器输出实际备份路径；保留它。若安装失败，安装器尝试恢复原目录。

The installer verifies staged file hashes and backs up the old folder outside Skill discovery, for example in `~/.agents/skill-backups/`. Retain the returned backup path. It attempts to restore the original on a failed replacement.

回滚：关闭正在使用的会话，把新版本移出技能扫描目录，再把实际备份目录移回原目的目录。卸载：仅把本Skill目录移出技能目录，保留工作文件。共享源被多个宿主引用时会影响所有引用它的宿主。

Rollback: close active sessions, move the new folder outside Skill discovery, then move the recorded backup into the original destination. Removal: move only this Skill folder out of discovery; preserve your project files. Changing a shared source affects every host linked to it.

## 自查 / Verify

完整仓库运行 `python3 scripts/verify_release.py`。独立Skill可按其README中的开发者复查命令运行。测试不会生成新提案或证明宿主已经具备PPTX工具。

For the full repository run `python3 scripts/verify_release.py`. The standalone Skill README contains local verification commands. Tests do not generate a new proposal or establish the host's PPTX capability.
