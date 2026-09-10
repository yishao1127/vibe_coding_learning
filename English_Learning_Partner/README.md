# English Learning Partner

一个仅供个人使用、可安装到多台 Windows 电脑的英语学习桌面工具。

- **翻译模式**：自动识别中文、英文或混合输入并进行工作场景翻译。单词提供英式/美式音标、词性、动词变化、句型/介词搭配、例句和使用提醒；句子或短语提供原文、推荐表达、理由与替代表达。
- **润色模式**：将中文、英文或混合内容整理为简洁、自然、可直接用于邮件或 Teams 的英文表达，并给出其他候选。仅英文润色中的明显语法或表达问题会进入语法复习。
- **复习模式**：分为单词复习、语法复习和全部记录。单词复习包含单词及少于 5 个英文词的可学习短语；可删除所选词汇卡。语法复习按类别合并展示，并可在右侧删除单条问题。

翻译和润色均按 **Enter** 提交，按 **Shift + Enter** 换行。单词卡的英式与美式音标旁均提供离线朗读按钮，使用目标电脑已安装的 Windows 英语语音；若无法朗读，请在 Windows 设置中安装英语（美国）或英语（英国）语音包。所有 AI 能力均调用与 [Knowledge_Forest](../Knowledge_Forest/) 相同的**本机 OpenAI Responses API 兼容服务**，默认地址为 `http://localhost:23333/api/openai/v1`，默认模型为 `gpt-5.4`。学习资料保存到 OneDrive 同步文件夹，可在多台电脑间同步。

## 运行前准备

1. 安装 Python 3.11 或更高版本。
2. 确认本机 OpenAI Responses API 兼容服务已启动，并能访问：

```text
http://localhost:23333/api/openai/v1/responses
```

3. 安装并启动应用：

```powershell
cd Q:\Yi_vibe_coding\vibe_coding_learning\English_Learning_Partner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
english-learning-partner
```

首次打开后，在“设置”中确认本地模型地址和模型名称，并选择 OneDrive 内的资料目录。例如：

```text
C:\Users\shaoyi\OneDrive - Microsoft\EnglishLearningPartner
```

每台电脑均需启动本地模型服务。只要选择同一个 OneDrive 文件夹，查询历史和语法笔记就会自动同步。

## 打包 Windows 安装程序

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pyinstaller packaging\EnglishLearningPartner.spec --noconfirm
```

这会生成目录版 `dist\English Learning Partner\`，并嵌入叶片应用图标。目录版会将 Python 和 Qt DLL 随应用安装到 `Program Files`，避免企业 Application Control 策略拦截单文件 EXE 解压到临时目录的 DLL。使用 [Inno Setup](https://jrsoftware.org/isinfo.php) 编译 `packaging\installer.iss`，即可生成带同一图标、可在其他 Windows 电脑双击安装的 EXE 安装包。

## 测试

```powershell
pytest
```

## 学习资料格式

资料目录包含：

```text
queries/        # 每次查词记录
polishes/       # 每次润色记录
grammar-notes/  # 按语法类别聚合的笔记
```

均为 UTF-8 Markdown 文件，可直接在任意编辑器中阅读和备份。可在“单词复习”或“语法复习”中删除所选记录；删除会同步删除 OneDrive 中对应的 Markdown 文件。