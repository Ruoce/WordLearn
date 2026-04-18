# Contributing to WordLearn

感谢你对 WordLearn 的关注！欢迎提交 Issue、Pull Request 或建议。

## 参与方式

- 请先阅读 `README.md`，了解项目用途和运行方式。
- 如果你发现 bug，请先在 Issue 中复现问题并提供日志。
- 如果你想新增功能，请先打开 Issue 讨论实现方式。

## 开发准备

1. 克隆仓库：

```bash
git clone https://github.com/yourname/wordlearn.git
cd wordlearn
```

2. 创建虚拟环境并安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

3. 运行本地服务：

```bash
python -m uvicorn api:app --reload
```

## 代码规范

- 尽量保持代码简洁、可读。
- 使用 `wordlearn/` 作为包名，避免与项目根文件混淆。
- 新增模块时请在 `README.md` 中补充说明。

## 提交要求

- 先 Fork 并创建 feature 分支
- 提交信息请简明扼要
- 如果改动较大，请补充说明和测试步骤

## 许可证

本项目使用 MIT 许可证，详见 `LICENSE`。
