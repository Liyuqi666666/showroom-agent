# 机器人展厅助手

本地 Python 工具 + LangChain 模型接入练习。实现状态查询、模拟导航、本地产品资料检索。
`main.py` 是原来的离线菜单；`agent.py` 通过百炼 API 调用千问模型，支持自然语言和工具调用。
尚未连接真实机器人、向量检索或 HTTP 服务。
所有产品均为虚构练习数据，超时是可控故障注入。

## 先运行模型版

安装 Python 3.11 或更新版本，将仓库克隆到本地后，在 Windows PowerShell 中执行：

```powershell
cd showroom-agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

把 `.env.example` 复制为 `.env`（已有时不要覆盖），填写自己的新密钥、北京地域的完整 OpenAI 兼容地址和模型 ID。
`.env` 已被 `.gitignore` 排除，不应发到聊天或 GitHub。若泄露密钥，应在百炼控制台删除并重新创建。

```powershell
# 仅检查配置格式，不联网，不产生模型费用
.\.venv\Scripts\python.exe agent.py --check

# 以下命令会调用付费 API
# 先验证一句你好
.\.venv\Scripts\python.exe agent.py --smoke

# 自然语言对话：可以多轮追问，输入 exit 退出
.\.venv\Scripts\python.exe agent.py

# 单次完整任务
.\.venv\Scripts\python.exe agent.py --ask "带我去机器人展区，并介绍这里的产品"

# 模拟故障，观察模型能否如实说明失败
.\.venv\Scripts\python.exe agent.py --scenario busy --ask "带我去机器人展区"
.\.venv\Scripts\python.exe agent.py --scenario timeout --ask "带我去工业展区"
```

终端中 `[调用工具]` 表示模型提出的函数名称和参数，`[工具结果]` 是本地 Python 函数的真实返回。
最后的“助手”才是模型根据返回结果生成的回答。工具仍在本地模拟运行，只有模型请求需要联网。

### 新文件做什么

| 文件 | 作用 |
| --- | --- |
| `.env` | 本地密钥、接口地址和模型名称，不上传 |
| `.env.example` | 可以公开的配置模板，不含密钥 |
| `model_config.py` | 读取配置，创建 LangChain 模型连接，转换错误提示 |
| `agent.py` | 系统提示词、注册工具、模型与工具循环、对话入口 |
| `tests/test_agent.py` | 模型替身测试，不联网、不计费 |

本版使用 LangChain 的 `ChatOpenAI`、`StructuredTool`、消息类型和 `bind_tools`，循环在 `agent.py` 中显式编写，方便学习。
模型只给出工具名和参数；Python 从三个函数的白名单中执行，`reset_robot` 不开放给模型。
为适配千问的兼容接口，使用 Chat Completions 并关闭思考模式，不传递专属思考字段。

### 试用限制与错误处理

每次模型请求最多输出 600 Token、不自动重试、网络超时为 25 秒；每轮最多 6 次模型请求和 8 次工具调用。
一次交互会话最多 6 轮，单次输入最多 2000 字符。这些限制用于约束用量，不是人民币消费上限；实际费用以百炼账单为准。
运行期间机器人状态保存在内存，退出重启会重置；模型请求失败时已经执行的动作不会回滚。
终端显示 Token 用量，出错时用量可能不完整。程序不启用 LangSmith 云端追踪，也不保存完整对话日志。

- 401：检查密钥是否有效、密钥与地址是否属于同一地域。
- 403：检查权限、账户状态以及“免费额度用完即停”。
- 404：检查模型 ID 和接口地址。
- 429：检查限流和配额，不要连续重复执行。
- 导航 TIMEOUT：结果未知，需要确认状态，不能直接重发导航。

模型是否追问、是否准确引用来源，还需用真实模型评测；单元测试只保证循环及工具层的工程行为。
本项目是学习用原型，未提供生产级权限控制、并发调度或回答事实校验。

参考：[LangChain 工具调用](https://docs.langchain.com/oss/python/langchain/models)、[百炼 Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)。

### 本机验证记录（2026-10-30）

36 个本地测试通过（25 个原工具测试 + 11 个 Agent/配置测试），测试过程不调用模型。
以下另外使用当前配置的 `qwen3.8-flash` 进行真实 API 验证，产生了少量按量用量：

| 场景 | 实际观察 |
| --- | --- |
| 连接测试 | 返回“你好！” |
| 带路并介绍机器人展区 | 依次调用状态、导航、检索，最终介绍引用 `knowledge/products.json#guide_robot_a` |
| busy | 只查询状态，说明忙碌，没有导航 |
| timeout | 执行结果标记未知，模型要求确认，没有重试导航 |
| “带我去那里”后补充“互动展区” | 先追问展区，补充后查询状态并导航 |
| 水下探测器 | 检索无结果，明确说明未找到，没有编造产品资料 |

部分场景的完整回复和工具轨迹在本地 `logs/live_validation.json`，不含密钥，已被 Git 忽略。
这是一次小规模验证，不代表统计意义上的任务成功率。

## 从哪里开始读

1. `knowledge/products.json`：看看产品资料长什么样。
2. `robot_tools.py`：重点看三个工具函数的输入、校验、输出。
3. `main.py`：看看程序怎样调用工具。
4. `tests/test_tools.py`：看看如何验证成功和失败情况。

## 在 VS Code 中运行

打开此项目文件夹，选择“终端 → 新建终端”。终端应位于项目根目录。
使用 Python 3.11 或更新版本。离线菜单无需第三方依赖，Agent 入口需安装上面的依赖。

本项目已在 Windows / Python 3.12.14 上验证。虚拟环境不随仓库上传，新环境需自行创建：

```powershell
python -m venv .venv
```

按 Ctrl+Shift+P，执行 Python: Select Interpreter，选择 `.venv\Scripts\python.exe`。
下面的命令直接使用虚拟环境解释器，无需先激活：

```powershell
# 交互菜单：输入数字选择操作
.\.venv\Scripts\python.exe main.py

# 自动演示：状态查询 → 导航 → 状态查询 → 资料检索
.\.venv\Scripts\python.exe main.py --demo

# 演示忙碌、失败和超时
.\.venv\Scripts\python.exe main.py --demo --scenario busy
.\.venv\Scripts\python.exe main.py --demo --scenario navigation_failure
.\.venv\Scripts\python.exe main.py --demo --scenario timeout

# 运行所有本地测试（当前 36 个，均不联网）
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

安装 Microsoft 的 Python/Python Debugger 扩展后，也可以按 F5 选择菜单或自动演示。

## 三个函数

| 函数 | 输入 | 结果 |
| --- | --- | --- |
| `get_robot_status()` | 无 | 状态、位置、电量、位置是否已确认 |
| `navigate_to(area)` | 三个合法展区之一 | 导航结果；成功更新位置 |
| `search_product_info(query)` | 产品名、别名、展区或功能关键词 | 资料列表、来源定位；未找到返回空列表 |

统一返回 `success`、`code`、`message`、`data` 和 `simulation`。
调用者应检查 `success` 和 `code`，不要只看自然语言消息。
资料来源示例：`knowledge/products.json#guide_robot_a`，表示该文件中对应 id 的记录。

## 状态和模拟场景

- normal：正常状态，成功导航后位置改变。
- busy：忙碌，拒绝导航。
- offline：离线，拒绝导航。
- navigation_failure：路线不可达，保留原位置。
- timeout：结果未知，标记位置未确认；阻止自动重复导航。

`reset_robot(scenario)` 仅用于测试和演示。重启程序也会重置环境。
状态保存在单进程内存中，这个版本没有并发、多机器人或持久化功能。
模拟超时不会实际发出网络请求或等待；在真实系统中，需要查询动作结果以消除未知状态。

## 建议动手练习

1. 运行自动演示，观察导航前后位置。
2. 在菜单中选择 busy 场景，再尝试导航。
3. 搜索“导览机器人A”“工业展区”“语音讲解”和“水下探测器”。
4. 给产品资料新增一项功能，重新运行检索。
5. 在工具函数处打断点，观察参数和返回值。

## 后续开发顺序

1. 用 `agent.py` 实测正常任务、目的地追问和各类故障，记录真实模型结果。
2. 增加自动化的端到端任务评测与失败分类。
3. 将检索拆到 `retrieval.py`，加入文档分块、向量检索和基于来源的生成。
4. 增加 FastAPI 接口、日志和端到端场景评测。

当前 25 个测试验证的是工具层行为，不代表 Agent 任务完成率或真实机器人的可靠性。

已验证：25 个工具层测试通过；5 种场景的命令行演示与交互菜单流程通过。
