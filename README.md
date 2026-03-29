# 校园开放日 AI 导览（黑客松骨架）

## 目录结构

```
welcome/
├── backend/           # FastAPI：NLU(OpenAI)、导览内容、会话、二维码、机械臂 mock
├── frontend/          # Vite + React：大屏交互 + /m/:token 手机页
├── arm_driver/        # SO101：录制/回放/守护进程；说明见 arm_driver/README.md（中英）
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

**答辩与作品说明（机械臂功能一览、文件分工、与后端如何联动）请阅读：[`arm_driver/README.md`](arm_driver/README.md)（中文 + English）。**

**只有 follower、没有 leader** 也能做指向演示：程序直接下发关节目标（`send_action`）。Leader 用于遥操作与示教录制；无 leader 时可只做 follower 回放。

逻辑动作枚举与 mock：`backend/app/services/arm.py`。路线首向 → 八方位示教回放：`route_arm_direction.py`、`arm_daemon_client.py` 与 `arm_driver/arm_daemon.py`（详见上文 README）。  
可选：**摄像头人脸居中** → `arm_driver/face_track_follower.py`（需安装 `arm_driver/requirements-opencv.txt`；不要与占用串口的 `arm_daemon` 同时运行）。
