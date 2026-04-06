# codex-sdd

`codex-sdd` 是一个面向 Codex CLI 的原生 **double-SDD** 工作流。

double-SDD 指的是：
- Specification-Driven Development（规格驱动开发）
- Subagent-Driven Development（子代理驱动开发）

项目的思想来源于superpowers，只保留了最主要的一条 Happy Path。

这个仓库只面向 Codex，安装后会把 Codex 原生资产写入以下位置：
- 项目级：`.agents/skills/`、`.codex/config.toml`、`.codex/agents/`
- 用户级：`~/.agents/skills/`、`~/.codex/config.toml`、`~/.codex/agents/`

## 工作流

```text
writing-specs -> writing-plans -> subagent-driven-development -> finishing-a-development-branch
```

- `writing-specs`：澄清需求，并产出经过确认的设计规格文档
- `writing-plans`：把规格文档拆解成可执行计划
- `subagent-driven-development`：每次只推进一个实现任务，然后针对同一代码切片并行执行 `spec-code-reviewer` 与 `quality-code-reviewer` 审查
- `finishing-a-development-branch`：负责最终验证以及开发分支收尾

## 安装

前置要求：
- macOS / Linux：`bash`、`python3`
- Windows：`PowerShell`、`Python 3`
- 使用 bootstrap 安装流程时还需要 `git`

项目内安装，适用于 macOS / Linux：

```bash
cd ~/example_sound
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.sh)
codex
```

项目内安装，适用于 Windows PowerShell：

```powershell
cd ~\example_sound
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-project.ps1 | iex
codex
```

项目内卸载：

```bash
./.double-sdd/uninstall
```

```powershell
.\.double-sdd\uninstall.ps1
```

全局安装，适用于 macOS / Linux：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.sh)
codex
```

全局安装，适用于 Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/FYZAFH/codex-sdd/main/scripts/bootstrap-codex-global.ps1 | iex
codex
```

## 仓库结构

- `codex/config.toml`：编排器指令和已注册的子代理配置
- `codex/agents/implementer.toml`：单任务 TDD 实现代理
- `codex/agents/spec-code-reviewer.toml`：针对单个代码切片的规格一致性审查代理
- `codex/agents/quality-code-reviewer.toml`：针对单个代码切片的工程质量审查代理
- `codex/agents/spec-document-reviewer.toml`：规格文档审查代理
- `codex/agents/plan-document-reviewer.toml`：计划文档审查代理
- `codex/skills/*/SKILL.md`：Codex 原生工作流技能
- `scripts/`：安装、卸载、bootstrap 和渲染辅助脚本
- `tests/shared/`：安装与渲染验证脚本

## 验证

```bash
python3 -m py_compile scripts/render-platform-bundle.py scripts/codex_installer.py
bash tests/shared/test-platform-bundle.sh
bash tests/shared/test-codex-install.sh
bash tests/shared/test-codex-project-install.sh
```

## 说明

- Codex 的配置位于 `.codex/config.toml`，而不是 `AGENTS.md`（因为subagent会继承AGENTS.md）
- 已安装的子代理会通过 `[[skills.config]]` 显式禁用技能。由于codex的子代理会默认继承skill，只要存在一个skill未被禁用，使用skill的说明文字就会出现在子代理的系统提示词中分散注意力并且额外消耗token，建议自行修改 agents/ 文件夹中子代理定义文件禁用所有skill。
- 调整子代理的模型请通过取消 agents/ 中的注释并修改字段来进行。

## 许可证

MIT License，详见 [LICENSE](LICENSE)。
