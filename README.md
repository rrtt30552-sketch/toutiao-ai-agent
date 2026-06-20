# 今日头条AI内容生成Agent V8.2

「真实数据闭环内容增长系统」

核心原则：禁止任何 AI 预测数据，所有 reward 来自头条导出的真实数据。

## V8.2 核心变更

- ✅ 规则分类器：不消耗 API 即可分类文章（7个类别）
- ✅ 修复 openpyxl 解析失败：优先用 raw XML 解析
- ✅ 时间衰减优化：半衰期 7→30 天，爆款文章不再被压成 0
- ✅ 增长率改线性回归：更稳健，不受单日异常值干扰
- ✅ Thompson Sampling 加 Bayesian Prior：冷启动不再瞎选
- ✅ 标题相似度改分词级 Jaccard：大幅减少误判
- ✅ 统一字段名：内部全部用 reads，不再混用 clicks
- ✅ Prompt Few-shot 示例：AI 输出 JSON 更稳定
- ✅ 桌面 GUI 版：双击即用，支持规则分类按钮

## 使用教程

### 第一步：安装环境

```bash
# 安装 Python 3.10+（如果没有的话）
# 下载地址：https://www.python.org/downloads/

# 安装依赖
pip install -r requirements.txt
```

### 第二步：配置 API Key

```bash
# 复制配置模板
cp .env.example .env

# 用记�本打开 .env，取消注释你想用的那组配置
# 例如使用 MiMo：
# AI_API_KEY=你的密钥
# AI_API_BASE_URL=https://api.xiaomimimo.com/v1
# AI_MODEL=mimo-v2.5
```

### 第三步：导入头条数据

1. 登录 [头条号后台](https://mp.toutiao.com)
2. 点击「内容管理」→「数据分析」
3. 点击「导出数据」，下载 xlsx 文件
4. 把文件放到 `data/imports/` 目录
5. 运行导入：

```bash
python main.py import data/imports/你的文件.xlsx
```

### 第四步：文章分类

```bash
# 规则分类（免费，不消耗 API）
python main.py classify --rule-only
```

### 第五步：生成文章

```bash
# 生成 3 篇文章
python main.py generate --num 3

# 生成的文章在 data/generated/ 目录
```

### 桌面 GUI 版

```bash
# 直接运行
python gui.py

# 或者双击桌面快捷方式（先运行 create_shortcut.bat 创建）
```

### 打包为 exe（可选）

```bash
# 双击 build.bat 自动打包
# 打包好的 exe 在 dist/ 目录
# 记得把 data/ 文件夹和 .env 也复制到 exe 旁边
```

## CLI 命令

| 命令 | 说明 |
|---|---|
| `import <file>` | 导入头条 xlsx 数据 |
| `classify --rule-only` | 规则分类（免费） |
| `classify --ai-only` | AI 分类（消耗 API） |
| `classify` | 规则+AI 混合分类 |
| `generate --num N` | 生成 N 篇文章 |
| `generate --dry-run` | 预览模式 |
| `generate --sync-data` | 仅同步数据 |
| `test` | 测试 AI 连接 |
| `validate` | 校验 CSV 结构 |
| `reward` | 查看 reward 排名 |

## 项目结构

```
toutiao-ai-agent/
├── main.py                  # CLI 入口
├── gui.py                   # GUI 桌面版
├── modules/
│   ├── __init__.py
│   ├── import_xlsx.py       # Excel 导入
│   ├── data_pipeline.py     # CSV 读取+校验
│   ├── reward_calculator.py # Reward 计算
│   ├── feedback_sync.py     # 策略统计+相似度
│   ├── content_ranker.py    # Thompson Sampling
│   ├── strategy_evolver.py  # 策略进化
│   ├── rule_classifier.py   # 规则分类器
│   ├── writer.py            # 文章生成
│   ├── ai_client.py         # AI 调用层
│   ├── logger.py            # 日志系统
│   └── utils.py             # 工具函数
├── scripts/
│   └── sync_csv.py          # CSV 同步脚本
├── tests/
├── data/
│   ├── articles.csv         # 最新快照
│   ├── timeseries.csv       # 时间序列
│   └── imports/             # 放置导入的 xlsx
├── output/                  # 生成的文章
├── .env.example
├── .gitignore
├── requirements.txt
├── build.bat                # 打包 exe
├── create_shortcut.bat      # 创建桌面快捷方式
└── README.md
```

## 支持的 AI 模型

| 模型 | AI_API_BASE_URL | AI_MODEL |
|---|---|---|
| MiMo | https://api.xiaomimimo.com/v1 | mimo-v2.5 |
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| 通义千问 | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-turbo |
| Kimi | https://api.moonshot.cn/v1 | moonshot-v1-8k |
| 智谱GLM | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |

## 注意事项

- 每天从头条号后台导出 xlsx，运行 import 命令导入
- 首次使用请先运行 `classify --rule-only` 给文章分类
- reward 使用时间衰减（30天半衰期），旧数据的 reward 会自然衰减
- 生成的文章会自动检测标题相似度，避免重复内容
