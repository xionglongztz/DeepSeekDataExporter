"""
ChatGPT对话导出工具
功能：将ChatGPT导出的conversations.json转换为Markdown文件
版本：1.0
"""

import json
import os
import logging
from datetime import datetime
import re

def setup_logging(log_file='chatgpt_conversion_log.txt'):
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("[+] ChatGPT对话导出工具启动")

def sanitize_filename(title):
    """
    安全的文件名清理函数
    """
    if not title or not isinstance(title, str):
        return "untitled_chat"
    
    # 移除非法字符
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    # 移除控制字符和换行符
    title = re.sub(r'[\x00-\x1F\x7F\n\r\t]', '', title)
    # 移除首尾空格和点号
    title = title.strip().strip('.')
    # 限制长度
    if len(title) > 50:
        title = title[:50]
    # 如果标题为空，使用默认名称
    if not title:
        title = f"chatgpt_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return title

def format_timestamp(timestamp):
    """格式化时间戳"""
    try:
        if 'Z' in timestamp:
            timestamp = timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

def extract_message_content(message):
    """提取消息内容"""
    if not message:
        return ""
    
    content = message.get('content', {})
    if not content:
        return ""
    
    # ChatGPT的内容格式：content.parts 是一个数组
    parts = content.get('parts', [])
    if parts and isinstance(parts, list):
        # 合并所有parts的内容
        return "\n".join(str(part) for part in parts if part)
    
    return ""

def build_conversation_tree(mapping):
    """构建对话树结构"""
    # 找到根节点（parent为null的消息）
    root_messages = []
    message_nodes = {}
    
    for msg_id, msg_data in mapping.items():
        if msg_data.get('parent') is None:
            root_messages.append(msg_id)
        message_nodes[msg_id] = msg_data
    
    conversations = []
    
    # 遍历每个根消息构建对话链
    for root_id in root_messages:
        conversation_chain = []
        current_id = root_id
        
        while current_id and current_id in message_nodes:
            node = message_nodes[current_id]
            conversation_chain.append(node)
            
            # 移动到下一个消息（通常只有一个child）
            children = node.get('children', [])
            current_id = children[0] if children else None
        
        if conversation_chain:
            conversations.append(conversation_chain)
    
    return conversations

def parse_chatgpt_conversation(conversation_data, index):
    """解析单个ChatGPT会话"""
    try:
        title = conversation_data.get('title', f'ChatGPT对话_{index}')
        conversation_id = conversation_data.get('id', f'unknown_{index}')
        create_time = conversation_data.get('create_time', '')
        update_time = conversation_data.get('update_time', '')
        mapping = conversation_data.get('mapping', {})
        
        # 格式化时间
        create_str = format_timestamp(create_time)
        update_str = format_timestamp(update_time)
        
        # 构建对话树
        conversation_chains = build_conversation_tree(mapping)
        messages = []
        
        for chain in conversation_chains:
            for node in chain:
                message = node.get('message', {})
                if message:
                    author = message.get('author', {})
                    role = author.get('role', 'unknown')
                    content = extract_message_content(message)
                    
                    if content:  # 只有当有内容时才添加
                        messages.append({
                            'role': role,
                            'content': content,
                            'message_id': node.get('id', '')
                        })
        
        return {
            'title': title,
            'id': conversation_id,
            'create_time': create_str,
            'update_time': update_str,
            'message_count': len(messages),
            'messages': messages,
            'chain_count': len(conversation_chains)
        }
        
    except Exception as e:
        logging.error("[-] 解析会话 %d 时出错: %s", index, e)
        return None

def convert_to_markdown(conversation_data):
    """生成Markdown内容"""
    if not conversation_data:
        return "# 解析失败\n\n该会话数据格式异常"
    
    md_content = []
    
    # 元数据头部
    md_content.append(f"# {conversation_data['title']}\n")
    md_content.append("## 会话信息\n")
    md_content.append(f"- **ID**: `{conversation_data['id']}`")
    md_content.append(f"- **创建时间**: {conversation_data['create_time']}")
    md_content.append(f"- **更新时间**: {conversation_data['update_time']}")
    md_content.append(f"- **消息数量**: {conversation_data['message_count']} 条")
    md_content.append(f"- **对话链数量**: {conversation_data['chain_count']} 条\n")
    
    md_content.append("---\n")
    
    # 对话内容
    for i, message in enumerate(conversation_data['messages'], 1):
        role_display = {
            'user': '👤 用户',
            'assistant': '🤖 ChatGPT',
            'system': '⚙️ 系统',
            'unknown': '❓ 未知'
        }.get(message['role'], f"❓ {message['role']}")
        
        md_content.append(f"## {role_display} - 消息 {i}\n")
        
        if message['content']:
            md_content.append(message['content'] + "\n")
        
        md_content.append("---\n")
    
    # 尾部信息
    md_content.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_content.append("*使用ChatGPT导出工具生成*")
    
    return "\n".join(md_content)

def process_chatgpt_export(input_file="conversations.json", output_dir="ChatGPT_Conversations"):
    """主处理函数"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取数据
    try:
        logging.info("[+] 读取文件: %s", input_file)
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info("[+] 成功读取 %d 个会话", len(data))
    except Exception as e:
        logging.error("[-] 读取失败: %s", e)
        return
    
    # 处理统计
    stats = {
        'total': len(data),
        'success': 0,
        'failed': 0,
        'failed_indices': []
    }
    
    # 处理每个会话
    for i, conversation in enumerate(data, 1):
        try:
            title = conversation.get('title', f'会话_{i}')
            logging.info("[PROCESS] 处理 [%d/%d]: %s", i, stats['total'], title[:40])
            
            parsed_data = parse_chatgpt_conversation(conversation, i)
            if not parsed_data:
                raise ValueError("解析返回空数据")
            
            # 检查是否有实际内容
            if parsed_data['message_count'] == 0:
                logging.warning("[WARN] 会话 %d 没有解析出任何消息内容", i)
                # 但仍然继续处理，可能包含元数据信息
            
            md_content = convert_to_markdown(parsed_data)
            
            # 生成安全文件名
            safe_title = sanitize_filename(parsed_data['title'])
            filename = f"{safe_title}.md"
            filepath = os.path.join(output_dir, filename)
            
            # 处理重复文件
            counter = 1
            while os.path.exists(filepath):
                filename = f"{safe_title}_{counter}.md"
                filepath = os.path.join(output_dir, filename)
                counter += 1
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            stats['success'] += 1
            logging.info("[SUCCESS] 保存成功: %s (消息数: %d)", filename, parsed_data['message_count'])
            
        except Exception as e:
            stats['failed'] += 1
            stats['failed_indices'].append(i)
            logging.error("[-] 处理失败 [%d]: %s", i, e)
    
    # 生成报告
    generate_report(stats, output_dir)

def generate_report(stats, output_dir):
    """生成处理报告"""
    report = [
        "=" * 60,
        "ChatGPT对话导出报告",
        "=" * 60,
        f"总会话数: {stats['total']}",
        f"成功导出: {stats['success']}",
        f"失败数量: {stats['failed']}",
        "",
        "输出目录:",
        f"  {os.path.abspath(output_dir)}",
        "",
        "导出时间:",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    if stats['failed_indices']:
        report.append("失败会话索引:")
        for index in stats['failed_indices']:
            report.append(f"  - 第 {index} 条会话")
    
    report.append("")
    report.append("提示: 专为ChatGPT导出格式设计")
    report.append("=" * 60)
    
    report_text = "\n".join(report)
    print(report_text)
    
    # 保存报告
    with open('chatgpt_export_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)

def debug_first_conversation(input_file="conversations.json"):
    """调试第一个会话的数据结构"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data:
            first_conv = data[0]
            print("=== 第一个会话的调试信息 ===")
            print(f"标题: {first_conv.get('title')}")
            print(f"ID: {first_conv.get('id')}")
            print(f"创建时间: {first_conv.get('create_time')}")
            
            mapping = first_conv.get('mapping', {})
            print(f"消息映射数量: {len(mapping)}")
            
            # 显示前几个消息的结构
            for i, (msg_id, msg_data) in enumerate(list(mapping.items())[:3]):
                print(f"\n--- 消息 {i+1} ({msg_id}) ---")
                print(f"父节点: {msg_data.get('parent')}")
                print(f"子节点: {msg_data.get('children')}")
                
                message = msg_data.get('message', {})
                if message:
                    author = message.get('author', {})
                    print(f"角色: {author.get('role')}")
                    
                    content = message.get('content', {})
                    parts = content.get('parts', [])
                    print(f"内容片段: {parts}")
            
    except Exception as e:
        print(f"调试失败: {e}")

def main():
    """主函数"""
    print("[+] ChatGPT对话导出工具 v1.0")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    
    input_file = "conversations.json"
    output_dir = "ChatGPT_Conversations"
    
    if not os.path.exists(input_file):
        print("[-] 错误: 找不到 conversations.json")
        print("[INFO] 请将ChatGPT导出的conversations.json放在同一目录")
        return
    
    # 可选：调试第一个会话的结构
    debug_choice = input("是否调试第一个会话的结构？(y/N): ").lower()
    if debug_choice == 'y':
        debug_first_conversation(input_file)
        print("\n" + "="*50 + "\n")
    
    print("[+] 开始处理ChatGPT导出数据...")
    process_chatgpt_export(input_file, output_dir)
    print("[+] 处理完成！查看 chatgpt_export_report.txt 获取详细报告")

if __name__ == "__main__":
    main()
