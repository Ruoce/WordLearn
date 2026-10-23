# WordLearn

基于 Python 的单词阅读练习生成器，从 `words.xlsx` 读取单词并生成英文阅读文章和题目。

## 启动

需要 Python 3.11 或更高版本。

```bash
python -m pip install -r requirements.txt
python -m uvicorn api:app --reload
```

浏览器打开 http://127.0.0.1:8000 。

## 网页使用

1. 在“模型与密钥”中选择 DeepSeek、OpenAI、Moonshot / Kimi 或本地 Ollama。
2. 输入所选提供方的 API Key；Ollama 无需密钥，需先启动本地服务。
3. 点击“获取可用模型”，从所选提供方返回的列表中选择支持对话生成的模型。Ollama 会返回本地模型列表；获取失败时可选择手动填写。
4. 选择难度（四级基础、六级进阶、雅思挑战）和题型，点击“生成练习，开始答题”。
5. 生成成功后进入独立答题页，阅读文章并检查答案。点击“返回配置 / 新练习”可回到第一页。失败时留在配置页重试。

支持 CET4、CET6、IELTS，以及仔细阅读、选词填空、段落匹配和判断题。云端模型限流时会显示本地示例。

页面打开后不会自动生成。密钥仅保留在当前页面，刷新或点击“清除密钥”后清除，不写入文件或浏览器存储。生成时通过 POST 请求交给后端，文章和题目使用同一份配置。远程使用时请通过 HTTPS 访问。

项目不再读取 `.env` 或从环境变量选择提供方、密钥、模型。旧 `.env` 文件不会参与生成。

## 命令行使用

```bash
python main.py --file words.xlsx --exam IELTS --provider deepseek
```

云端提供方的密钥在终端中隐藏输入；本地 Ollama 无需输入密钥：

```bash
python main.py --provider ollama --model llama3.1:8b
```

## 项目结构

- `main.py`：命令行入口
- `api.py`：FastAPI 启动入口
- `end.html`：网页界面和密钥输入
- `wordlearn/generator.py`：文章生成和模型接入
- `wordlearn/question_generator.py`：题目生成
- `wordlearn/api.py`：后端接口（`POST /generate`）

`words.xlsx` 默认读取第一列，每行一个单词。

## 上传自己的词表

在第一页选择 `.xlsx` 或 UTF-8 编码的 `.csv` 文件。读取第一张工作表的第一列，每行一个单词，支持可选的“单词 / word / words”表头。没有表头时也会保留第一个单词。空行自动跳过，重复单词合并。

文件最多 5 MB，每次最多 100 个不同单词。上传成功后显示数量和预览，再点击生成即可使用这份词表。文件只在内存中解析，不覆盖项目中的 `words.xlsx`；刷新页面或点击“使用默认词表”即可恢复默认词表。
