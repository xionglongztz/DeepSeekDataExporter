import json
import os
import re
from datetime import datetime
import shutil
import collections

def sanitize_filename(title):
    """清理标题中的特殊字符，使其适合作为文件名"""
    sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip()

def parse_timestamp(timestamp_str):
    """解析时间戳字符串"""
    try:
        if '+' in timestamp_str:
            timestamp_str = timestamp_str.split('+')[0]
        return datetime.fromisoformat(timestamp_str)
    except:
        return datetime.now()

def count_messages(mapping):
    """计算对话中的消息数量"""
    count = 0
    for node_id, node in mapping.items():
        if node_id != "root" and node.get("message") and node["message"].get("fragments"):
            count += 1
    return count

def extract_message_content(message_node):
    """从消息节点中提取用户提问和AI回复，忽略工具调用片段（TOOL_SEARCH, TOOL_OPEN等）"""
    if not message_node or not message_node.get("fragments"):
        return {"user_question": "", "ai_thoughts": [], "ai_responses": []}
    
    user_question = ""
    ai_thoughts = []
    ai_responses = []
    
    for fragment in message_node["fragments"]:
        fragment_type = fragment.get("type", "")
        content = fragment.get("content", "").strip()
        
        if fragment_type == "REQUEST":
            user_question = content
        elif fragment_type == "THINK":
            if content:
                ai_thoughts.append(content)
        elif fragment_type == "RESPONSE":
            if content:
                ai_responses.append(content)
        # 显式忽略工具调用类型的片段（无内容，无需处理）
        elif fragment_type in ("TOOL_SEARCH", "TOOL_OPEN"):
            # 直接跳过，不做任何处理
            pass
        # 其他未知类型也忽略（保持向后兼容）
        # else: pass
    
    return {
        "user_question": user_question,
        "ai_thoughts": ai_thoughts,
        "ai_responses": ai_responses
    }

def build_conversation_flow(mapping, log_message=None):
    """构建完整的对话流程，使用深度优先遍历"""
    
    # 如果没有提供日志函数，使用默认的空函数
    if log_message is None:
        def log_message(msg):
            pass
    
    conversation_flow = []
    
    # 收集所有有消息的节点
    for node_id, node in mapping.items():
        if node_id != "root" and node.get("message") and node["message"].get("fragments"):
            message_data = extract_message_content(node["message"])
            
            has_request = any(frag.get("type") == "REQUEST" for frag in node["message"]["fragments"])
            has_response = any(frag.get("type") in ["THINK", "RESPONSE"] for frag in node["message"]["fragments"])
            
            if has_request or has_response:
                conversation_flow.append({
                    "node": node,
                    "message_data": message_data,
                    "is_user": has_request,
                    "is_ai": has_response
                })
    
    log_message(f"    - 收集到 {len(conversation_flow)} 个有效节点")
    
    # 安全的排序逻辑
    def safe_sort_key(item):
        node_id = item['node']['id']
        log_message(f"    - 排序处理节点ID: {node_id}, 类型: {type(node_id)}")
        
        if node_id is None:
            return (0, "")  # None 值排在前面
        
        try:
            numeric_id = int(node_id)
            return (1, numeric_id)  # 数字排在前面
        except (ValueError, TypeError):
            # 如果是字符串，确保不是 None
            return (2, str(node_id) if node_id is not None else "")
    
    # 尝试排序
    try:
        conversation_flow.sort(key=safe_sort_key)
        log_message("    - 节点排序成功")
    except Exception as e:
        log_message(f"    - 节点排序失败: {e}")
        log_message("    - 使用默认顺序")
        # 保持原顺序
    
    return conversation_flow

def generate_markdown(conversation, output_dir, log_message=None):
    """为单个对话生成Markdown文件"""
    
    if log_message is None:
        def log_message(msg):
            pass
    
    def create_anchor(node_id):
        anchor = re.sub(r'[^\w\-_]', '-', node_id)
        return anchor
    
    title = conversation.get("title", "未命名对话")
    conversation_id = conversation.get("id", "未知ID")
    inserted_at = conversation.get("inserted_at", "")
    updated_at = conversation.get("updated_at", "")
    mapping = conversation.get("mapping", {})
    
    log_message(f"  - 开始处理对话 '{title}'")
    log_message(f"  - 对话ID: {conversation_id}")
    log_message(f"  - 映射节点数量: {len(mapping)}")
    
    message_count = count_messages(mapping)
    log_message(f"  - 有效消息数量: {message_count}")
    
    safe_title = sanitize_filename(title)
    filename = f"{safe_title}.md"
    filepath = os.path.join(output_dir, filename)
    
    counter = 1
    original_filepath = filepath
    while os.path.exists(filepath):
        name, ext = os.path.splitext(original_filepath)
        filepath = f"{name}_{counter}{ext}"
        counter += 1
    
    log_message(f"  - 开始构建对话流程")
    conversation_flow = build_conversation_flow(mapping, log_message)
    log_message(f"  - 对话流程构建完成，共 {len(conversation_flow)} 个节点")
    
    md_content = []
    md_content.append(f"# 💬 {title}\n")
    md_content.append("## 📋 会话信息\n")
    md_content.append(f"- **🗂️ ID**: `{conversation_id}`")
    md_content.append(f"- **🕐 创建时间**: {parse_timestamp(inserted_at).strftime('%Y-%m-%d %H:%M:%S')}")
    md_content.append(f"- **🔄 更新时间**: {parse_timestamp(updated_at).strftime('%Y-%m-%d %H:%M:%S')}")
    md_content.append(f"- **💭 消息数量**: {message_count} 条\n")
    md_content.append("---\n")
    
    log_message(f"  - 开始生成Markdown内容")
    for i, item in enumerate(conversation_flow):
        node = item["node"]
        message_data = item["message_data"]
        timestamp = parse_timestamp(node['message']['inserted_at']).strftime('%Y-%m-%d %H:%M:%S')
        model = node.get("message", {}).get("model", "未知模型")
        
        # 用户提问
        if item["is_user"] and message_data["user_question"]:
            md_content.append(f"\n## 👤 用户")
            md_content.append(f"{message_data['user_question']}\n")
            
            # 搜索信息（仅旧格式）
            search_results = []
            for fragment in node.get("message", {}).get("fragments", []):
                if fragment.get("type") == "SEARCH" and fragment.get("results"):
                    search_results = fragment["results"]
                    break
            if search_results:
                md_content.append(f"\n**🌐 网页**(共 {len(search_results)} 个):")
                try:
                    search_results.sort(key=lambda x: x.get("cite_index", 0) or 0)
                except:
                    pass
                for result in search_results:
                    published_at = result.get("published_at")
                    if published_at:
                        try:
                            date_str = datetime.fromtimestamp(published_at).strftime('%Y-%m-%d')
                        except:
                            date_str = "未知日期"
                    else:
                        date_str = "未知日期"
                    site_name = result.get("site_name", "未知网站")
                    title_tmp = result.get("title", "无标题")
                    url = result.get("url", "")
                    snippet = result.get("snippet", "")
                    md_content.append("> **网站**: " + site_name + f" `{date_str}`")
                    md_content.append("> **标题**: " + title_tmp)
                    if url:
                        md_content.append("> **网址**: `" + url + "`")
                    if snippet:
                        md_content.append("> **摘要**:")
                        snippet_lines = snippet.split('\n')
                        for line in snippet_lines:
                            if line.strip():
                                md_content.append(">> " + line)
                    md_content.append(">")
            
            # 附件
            files = node.get("message", {}).get("files", [])
            if files:
                md_content.append("\n**📎 附件**:")
                for file_info in files:
                    file_id = file_info.get('id', '未知ID')
                    file_name = file_info.get('file_name', '未知文件名')
                    file_content = file_info.get('content', '')
                    md_content.append("> 🆔 **文件ID**: `" + file_id + "`")
                    md_content.append("> 📄 **文件名**: `" + file_name + "`")
                    if file_content:
                        md_content.append("> 📋 **文件内容**:")
                        file_extension = os.path.splitext(file_name)[1].lower().lstrip('.')
                        ext_map = {
                            'py': 'python', 'js': 'javascript', 'java': 'java',
                            'cpp': 'cpp', 'c': 'c', 'html': 'html', 'css': 'css',
                            'json': 'json', 'xml': 'xml', 'md': 'markdown',
                            'txt': 'text', 'log': 'text', 'csv': 'csv', 'sql': 'sql',
                            'sh': 'bash', 'bat': 'batch', 'yml': 'yaml', 'yaml': 'yaml',
                            'vb': 'vb.net'
                        }
                        code_lang = ext_map.get(file_extension, 'text')
                        md_content.append(f"> ```{code_lang}")
                        normalized_content = file_content.replace('\r\n', '\n').replace('\r', '\n')
                        for line in normalized_content.split('\n'):
                            md_content.append("> " + line)
                        md_content.append("> ```")
            
            md_content.append(f"\n*🆔 {node['id']} | 🕐 {timestamp}*")
            
            parent_id = node.get('parent')
            children_ids = node.get('children', [])
            if parent_id or children_ids:
                relation_parts = []
                if parent_id and parent_id != "root":
                    parent_anchor = create_anchor(parent_id)
                    relation_parts.append(f"父节点: [{parent_id}](#{parent_anchor})")
                elif parent_id == "root":
                    relation_parts.append(f"父节点: {parent_id}")
                if children_ids:
                    children_links = [f"[{cid}](#{create_anchor(cid)})" for cid in children_ids]
                    relation_parts.append(f"子节点: {', '.join(children_links)}")
                md_content.append(f"\n**🔗 节点关系:** { ' | '.join(relation_parts) }")
            md_content.append("\n---\n")
        
        # AI回复部分（修改重点）
        if item["is_ai"] and (message_data["ai_thoughts"] or message_data["ai_responses"]):
            md_content.append(f"\n## 🤖 回复")
            
            # 搜索信息（仅旧格式）
            search_results = []
            for fragment in node.get("message", {}).get("fragments", []):
                if fragment.get("type") == "SEARCH" and fragment.get("results"):
                    search_results = fragment["results"]
                    break
            if search_results:
                md_content.append(f"\n**🌐 网页**(共 {len(search_results)} 个):")
                try:
                    search_results.sort(key=lambda x: x.get("cite_index", 0) or 0)
                except:
                    pass
                for result in search_results:
                    published_at = result.get("published_at")
                    if published_at:
                        try:
                            date_str = datetime.fromtimestamp(published_at).strftime('%Y-%m-%d')
                        except:
                            date_str = "未知日期"
                    else:
                        date_str = "未知日期"
                    site_name = result.get("site_name", "未知网站")
                    title_tmp = result.get("title", "无标题")
                    url = result.get("url", "")
                    snippet = result.get("snippet", "")
                    md_content.append("> **网站**: " + site_name + f" `{date_str}`")
                    if url:
                        md_content.append("> **标题**: [" + title_tmp + "](" + url + ")")
                    else:
                        md_content.append("> **标题**: " + title_tmp)
                    if snippet:
                        md_content.append("> **摘要**: `" + snippet + "`")
                    md_content.append("\n")
            
            # ========== 核心修改：合并所有思考内容，然后输出回复 ==========
            thoughts = message_data["ai_thoughts"]
            responses = message_data["ai_responses"]
            
            # 输出所有思考内容（合并为一个连续引用块）
            if thoughts:
                md_content.append(f"\n**💭 思考**：")
                for idx, thought in enumerate(thoughts):
                    if idx > 0:
                        md_content.append("")  # 思考片段之间空行（保持引用块连续性）
                    thought_lines = thought.split('\n')
                    for line in thought_lines:
                        md_content.append("> " + line)
                md_content.append("")  # 思考结束后空一行（退出引用块）
            
            # 输出所有回复内容（通常只有一个 RESPONSE）
            if responses:
                for response in responses:
                    md_content.append(f"{response}\n")
            # ============================================================
            
            model = node.get("message", {}).get("model", "未知模型")
            md_content.append(f"\n*🆔 {node['id']} | 🧠 {model} | 🕐 {timestamp}*")
            
            parent_id = node.get('parent')
            children_ids = node.get('children', [])
            if parent_id or children_ids:
                relation_parts = []
                if parent_id and parent_id != "root":
                    parent_anchor = create_anchor(parent_id)
                    relation_parts.append(f"父节点: [{parent_id}](#{parent_anchor})")
                elif parent_id == "root":
                    relation_parts.append(f"父节点: {parent_id}")
                if children_ids:
                    children_links = [f"[{cid}](#{create_anchor(cid)})" for cid in children_ids]
                    relation_parts.append(f"子节点: {', '.join(children_links)}")
                md_content.append(f"\n**🔗 节点关系:** { ' | '.join(relation_parts) }")
            md_content.append("\n---\n")
    
    md_content.append(f"*📄 Markdown文件生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_content.append("*使用DeepSeek导出工具生成*\n")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_content))
    
    try:
        creation_time = parse_timestamp(inserted_at).timestamp()
        os.utime(filepath, (creation_time, creation_time))
    except:
        pass
    
    log_message(f"  - 完成生成Markdown文件: {os.path.basename(filepath)}")
    return filepath

def json_to_markdown_converter(json_file_path):
    """主转换函数"""
    
    # 创建输出目录
    output_dir = "output"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    # 创建日志文件
    log_file = f"conversion_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_content = []
    
    def log_message(message):
        """将消息同时输出到控制台和日志内容"""
        print(message)
        log_content.append(message)
    
    log_message(f"DeepSeek JSON 转 Markdown 转换日志")
    log_message(f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"输入文件: {json_file_path}")
    log_message(f"输出目录: {output_dir}")
    log_message("=" * 50)
    
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            log_message("❌ 错误: JSON数据应该是一个数组")
            return False
        
        # 处理每个对话
        successful_conversions = 0
        total_conversations = len(data)
        
        for i, conversation in enumerate(data):
            try:
                if isinstance(conversation, str) and conversation.startswith("...<"):
                    log_message(f"📝 注意: 检测到截断信息: {conversation}")
                    continue
                
                title = conversation.get("title", f"对话_{i+1}")
                
                log_message(f"正在处理对话 {i+1}/{total_conversations}: {title}")
                log_message(f"对话ID: {conversation.get('id')}")
                
                filepath = generate_markdown(conversation, output_dir, log_message)
                
                log_message(f"✅ 成功转换: {title} -> {os.path.basename(filepath)}")
                successful_conversions += 1
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                log_message(f"❌ 转换失败 - {conversation.get('title', f'对话_{i+1}')}: {str(e)}")
                log_message(f"错误详情:")
                for line in error_details.split('\n'):
                    if line.strip():
                        log_message(f"  {line}")
        
        # 生成总结
        log_message("=" * 50)
        log_message(f"📊 转换总结:")
        log_message(f"   总对话数: {total_conversations}")
        log_message(f"   成功转换: {successful_conversions}")
        log_message(f"   失败数: {total_conversations - successful_conversions}")
        log_message(f"   输出目录: {os.path.abspath(output_dir)}")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_message(f"❌ 致命错误: {str(e)}")
        log_message(f"错误堆栈:")
        for line in error_details.split('\n'):
            if line.strip():
                log_message(f"  {line}")
        return False
    
    # 写入日志文件
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_content))
    
    print(f"转换完成！")
    print(f"日志文件: {log_file}")
    print(f"输出目录: {output_dir}")
    
    return True

# 使用示例
if __name__ == "__main__":
    json_file = "conversations.json"  # 替换为你的实际文件路径
    
    if os.path.exists(json_file):
        success = json_to_markdown_converter(json_file)
        if success:
            print("🎉 所有对话已成功转换为Markdown格式！")
        else:
            print("❌ 转换过程中出现错误，请检查日志文件。")
    else:
        print(f"❌ 文件 {json_file} 不存在，请检查文件路径。")