# Code AI Review

基于 Python 和 DeepSeek 的 C/C++ AI 代码审查工具。

## 一、功能

- 解析 Git MR 的统一格式 Diff。
- 识别本次修改的文件和代码行。
- 收集修改文件附近的源码及部分本地头文件。
- 调用 DeepSeek API 分析 C/C++ 缺陷。
- 根据固定 Schema 校验模型返回结果。
- 检查发现项的路径和行号。
- 输出 review-result.json，供 CI 读取。

## 二、运行环境

- Python 3.11 或更高版本
- 可用的 DeepSeek API Key
- 可以访问 DeepSeek API 的网络环境

## 三、安装

进入项目根目录：

```bash
python3 -m venv .venv
source .venv/bin/activate

Windows PowerShell 可以使用：
```
python -m venv .venv
.venv\Scripts\Activate.ps1
```

安装项目：
```
python -m pip install --upgrade pip
python -m pip install -e .
```


配置 DeepSeek API Key
macOS/Linux：
export DEEPSEEK_API_KEY="你的_API_Key"

如果在项目根目录执行
source .venv/bin/activate


Windows PowerShell：
$env:DEEPSEEK_API_KEY="你的_API_Key"


可选配置：
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_TIMEOUT_SECONDS="180"
export AI_REVIEW_MAX_CONTEXT_CHARS="80000"


请勿将真实 API Key 提交到 Git 仓库。

执行审查
假设当前目录下有：
- mr.diff：本次 MR 的 Diff 文件
- your-repo：MR 源 Commit 对应的源码目录
运行：
ai-code-review review \
  --diff ./mr.diff \
  --repo-root ./your-repo \
  --output ./review-result.json


也可以指定 Commit SHA：
ai-code-review review \
  --diff ./mr.diff \
  --repo-root ./your-repo \
  --output ./review-result.json \
  --source-sha abc123 \
  --target-sha def456


指定其他 Skill：
ai-code-review review \
  --diff ./mr.diff \
  --repo-root ./your-repo \
  --skill-path ./skills/cpp-ai-code-review/SKILL.md \
  --output ./review-result.json


六、输出结果
review-result.json 包含：
- schema_version：结果格式版本
- review_status：审查状态
- allow_merge：是否可以放行。仅当 review_status 为 completed 且 findings 为空时为 true
- summary：审查摘要
- findings：发现的缺陷列表
- limitations：审查限制
每条 finding 包含：
- rule_id：问题规则标识
- severity：严重程度
- confidence：模型置信度
- file：仓库相对路径
- line：源文件行号
- title：问题标题
- description：问题描述
- evidence：问题证据
- suggestion：修复建议
- introduced_by_change：是否由本次修改引入或暴露