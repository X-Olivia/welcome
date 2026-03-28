# 校园开放日 AI 导览（黑客松骨架）

## 目录结构

```
welcome/
├── backend/           # FastAPI：NLU(OpenAI)、导览内容、会话、二维码、机械臂 mock
├── frontend/          # Vite + React：大屏交互 + /m/:token 手机页
├── arm_driver/        # SO101 串口测试脚本
├── camera/            # 摄像头追踪 + SO101（Haar / YOLO-Pose，见 camera/README.md）
└── README.md
```

## 后端

**请在 conda 环境 `lerobot` 中运行**（与 SO-ARM101 / LeRobot 工具链一致）：

```bash
# 若为非交互 shell，先初始化 conda（任选其一，按你本机 conda 安装方式）
# eval "$(conda shell.bash hook)"
# source ~/miniconda3/etc/profile.d/conda.sh

conda activate lerobot
cd backend
pip install -r requirements.txt
cp .env.example .env        # 填入 OPENAI_API_KEY；现场扫码填局域网 IP 到 PUBLIC_BASE_URL
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

或在仓库根目录执行（自动 `conda activate lerobot`）：

```bash
chmod +x backend/run_dev.sh
./backend/run_dev.sh
```

**注意**：若本终端曾 `source backend/.venv/bin/activate`，请先执行 `deactivate`，再 `conda activate lerobot`，否则 `python` 可能仍指向 `.venv`。

若尚未创建该环境：`conda create -n lerobot python=3.10 -y` 再 `conda activate lerobot` 后安装依赖。

不使用 conda 时，仍可用 `python3 -m venv .venv` + `source .venv/bin/activate` 代替。

- API：`POST /api/guide`，`GET /api/session/{token}`，`GET /api/health`
- 无 `OPENAI_API_KEY` 时使用关键词占位 NLU，便于离线开发
- `ARM_MOCK=true`（默认）时机械臂仅打日志；真机在 `app/services/arm.py` 扩展

## 前端

需安装 Node.js/npm 后：

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

开发时 Vite 将 `/api` 代理到 `http://127.0.0.1:8000`。手机扫码请把 `.env` 里 `PUBLIC_BASE_URL` 设为 `http://<电脑局域网IP>:5173`。

可选：新建 `frontend/.env` 写入 `VITE_API_BASE=http://<电脑IP>:8000`（若前后端不同源）。

## SO-ARM101 / LeRobot

**只有 follower、没有 leader** 也能做本项目的指向演示：由程序直接下发关节目标（`send_action`）即可。Leader 主要用于官方文档里的遥操作、双机录制等流程；没有 leader 时不必接第二块板，可忽略相关说明。

关节角或示教名填在 `backend/app/services/arm.py` 的 `HARDCODED_PRESETS`；或通过 `arm_driver` 独立进程接收动作枚举再调用 `lerobot`。
