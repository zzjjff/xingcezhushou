# 行测智能学习系统

个人行测刷题工具，支持题库录入、智能组卷、做题判分、掌握度追踪、复盘可视化与错题本。

## 功能

- **题库管理**：上传 Word/PDF → 自动切题 → 一键入库（按题干去重）
- **三模式组卷**：培优补弱（按薄弱指数动态出题）/ 全真模拟（130 题、限时 2 小时）/ 按模块练习
- **做题**：每题独立计时、交卷判分、答案纠错
- **掌握度引擎**：答对加分 / 答错扣分 / 连续答对固化 / 惰性衰减（不依赖定时任务）
- **复盘可视化**：雷达图（模块正确率）/ 柱状图（平均耗时）/ 折线图（趋势）/ 错题列表
- **错题本**：按有效分（含衰减）排序、颜色标注、定向复习
- **AI 补全骨架**：填 API key 即可补全答案与解析（OpenAI 兼容格式，无 key 自动降级）

## 技术栈

- 后端：Python 3.9+ / FastAPI / SQLAlchemy / SQLite(WAL)
- 前端：Vue3 / Vite / Element Plus / ECharts / Vue Router

## 启动

后端：

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://127.0.0.1:5173

## 导题说明

1. 启动前后端后，浏览器打开 → 顶部「题库管理」
2. 点「上传题库文件」，选择 `.docx` 或 `.pdf` 题源
3. 系统自动切题，弹出解析预览（题干 / 选项 / 模块）
4. 点「一键入库」，重复题自动去重
5. 无答案的题自动占位为 `A`；找到真答案后，在列表点「改答案」录入

**题源格式要求**（正则切题依赖）：

- 题号单独成行，纯数字（`1`、`2`、…）
- 选项以 `A、` `B、` `C、` `D、` 顿号分隔
- 大模块标题以 `一、` `二、` … 开头（政治理论 / 常识判断 / 言语理解与表达 / 数量关系 / 判断推理 / 资料分析）

切不动的题（如图形推理，题干为图片）会因题干相同被去重，属正常。

## AI 配置（可选）

编辑 `backend/.env`：

```
AI_API_KEY=你的key
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
```

填好重启后端，错题页「AI解析」与批量补全接口即生效（DeepSeek / 智谱 GLM 均可）。

## 数据

- `data/study.db`：SQLite 数据库，含题库 / 掌握度 / 做题记录
- 仓库自带示例题库（行测真题，答案为占位 `A`，需自行录入真答案）
- `.docx` 题源文件不入库（已在 `.gitignore` 排除）

## 项目结构

```
backend/      FastAPI 后端
  routers/    路由（questions / exam）
  services/   服务（解析 / 切题 / 掌握度 / 薄弱指数 / 复盘 / AI）
  models.py   数据模型
  schemas.py  Pydantic 模型
  config.py   AI 配置读取
frontend/     Vue3 前端
  src/views/  四页面（题库 / 做题 / 复盘 / 错题本）
data/         SQLite 数据库
```