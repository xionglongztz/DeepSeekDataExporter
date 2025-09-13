# DeepSeek对话导出工具

一个强大的工具，将DeepSeek导出的JSON对话转换为可搜索的Markdown文件。

## ✨ 功能特点

- ✅ 完美处理特殊字符和换行符
- ✅ 保留完整的对话结构
- ✅ 支持思考过程显示
- ✅ 自动生成处理报告
- ✅ 优美的Markdown格式

## 🚀 使用方法

1.在桌面网页端DeepSeek官网中，点击 `系统设置`
2.点击 `数据管理`，点击 `导出所有历史对话`
3. 解压文件，将 `conversations.json` 与 `deepseek_exporter.py` 置于同一目录下
4. 运行 `python deepseek_exporter.py`
5. 查看 `DeepSeek_Conversations/` 目录中的结果

## 📁 文件结构

```text
/DeepSeek_Conversations/会话标题.md
/deepseek_conversion_log.txt # 详细处理日志
/export_report.txt # 统计报告
```

## 💡 提示

- 支持超大规模文件处理（测试过1000+对话）
- 自动处理文件名冲突
- 完整的错误处理和日志记录
- 此代码完全由 `DeepSeek` 编写
