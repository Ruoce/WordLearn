# WordLearn

一个基于 Python 的单词阅读练习生成器，支持从 `words.xlsx` 读取单词，并生成阅读文章和对应题目。现在可以直接调用本地 Ollama 模型。

## 功能

- 从 Excel 词表读取单词
- 生成英文阅读文章
- 支持 `IELTS`、`CET4`、`CET6`
- 支持 `careful_reading`、`banked_cloze`、`paragraph_matching`、`tfng`
- 支持 `OpenAI`、`Moonshot`、`Ollama`
- 模型调用失败时可回退到本地示例内容

## 项目结构

- `main.py`：命令行入口
- `api.py`：FastAPI 启动入口
- `end.html`：前端页面
- `.env.example`：环境变量示例
- `wordlearn/generator.py`：文章生成和模型接入
- `wordlearn/question_generator.py`：题目生成
- `wordlearn/api.py`：后端接口

## 安装依赖

```bash
python -m pip install -r requirements.txt
```

## 使用本地 Ollama

### 1. 确认 Ollama 已启动

默认接口地址是：

```text
http://127.0.0.1:11434/v1
```

如果你还没启动 Ollama，可以先在另一个终端确认本地模型：

```bash
ollama list
```

当前这台机器上已经存在这些模型：

- `llama3.1:8b`
- `deepseek-coder:6.7b`

### 2. 配置 `.env`

复制 `.env.example` 为 `.env`，然后填写：

```env
WORDLEARN_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=llama3.1:8b
OLLAMA_API_KEY=ollama
```

说明：

- `WORDLEARN_PROVIDER=ollama` 会强制项目优先使用本地 Ollama
- `OLLAMA_MODEL` 填你本机 `ollama list` 能看到的模型名
- `OLLAMA_API_KEY` 对 Ollama 来说通常只是占位值，保留 `ollama` 即可

### 3. 命令行运行

```bash
python main.py --file words.xlsx --exam IELTS
```

如果你想临时切换模型，也可以直接传：

```bash
python main.py --file words.xlsx --exam IELTS --model llama3.1:8b
```

## Web 模式

启动后端：

```bash
python -m uvicorn api:app --reload
```

浏览器打开：

```text
http://127.0.0.1:8000
```

只要 `.env` 里配置的是 Ollama，网页生成时也会自动走本地模型。

## 其他提供方

如果你想切回云端模型，可以把 `.env` 改成下面任一种。

OpenAI：

```env
WORDLEARN_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
```

Moonshot：

```env
WORDLEARN_PROVIDER=moonshot
MOONSHOT_API_KEY=your_moonshot_api_key_here
```

## 词表格式

`words.xlsx` 默认读取第一列，每行一个单词。

## 说明

- 项目现在会在创建模型客户端前自动读取 `.env`
- 如果同时保留其他 API Key，只要 `WORDLEARN_PROVIDER=ollama`，仍会优先使用本地 Ollama
