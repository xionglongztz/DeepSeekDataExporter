"""
DeepSeek对话导出工具 - 终极版
功能：将DeepSeek导出的conversations.json转换为Markdown文件
作者：DeepSeek & 热心用户
版本：2.0
"""

import json
import os
import logging
from datetime import datetime
import re

def setup_logging(log_file='deepseek_conversion_log.txt'):
    """设置详细的日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("🚀 DeepSeek对话导出工具启动")

def sanitize_filename(title):
    """
    安全的文件名清理函数
    处理所有非法字符：<>:"/\\|?*和换行符等
    """
    if not title or not isinstance(title, str):
        return "untitled"
    
    # 移除所有非法字符
    title = re.sub(r'[<>:"/\\|?*\n\r\t]', '', title)
    # 移除首尾空格和点号
    title = title.strip().strip('.')
    # 限制长度
    if len(title) > 50:
        title = title[:50]
    # 如果标题为空，使用默认名称
    if not title:
        title = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return title

def parse_conversation(conversation):
    """解析单个会话的完整信息"""
    try:
        title = conversation.get('title', '无标题对话')
        conversation_id = conversation.get('id', 'unknown')
        inserted_at = conversation.get('inserted_at', '')
        updated_at = conversation.get('updated_at', '')
        
        # 解析时间
        def format_time(timestamp):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return timestamp
        
        inserted_str = format_time(inserted_at)
        updated_str = format_time(updated_at)
        
        mapping = conversation.get('mapping', {})
        messages = []
        current_id = mapping.get('root', {}).get('children', [])[0] if mapping.get('root') else None
        
        # 遍历所有消息节点
        while current_id and current_id in mapping:
            node = mapping[current_id]
            message = node.get('message')
            
            if message:
                fragments = message.get('fragments', [])
                request_content = ""
                think_content = ""
                response_content = ""
                model = message.get('model', 'unknown')
                files = message.get('files', [])
                
                for fragment in fragments:
                    frag_type = fragment.get('type')
                    frag_content = fragment.get('content', '')
                    
                    if frag_type == 'REQUEST':
                        request_content += frag_content + "\n"
                    elif frag_type == 'THINK':
                        think_content += frag_content + "\n"
                    elif frag_type == 'RESPONSE':
                        response_content += frag_content + "\n"
                
                messages.append({
                    'model': model,
                    'files': files,
                    'request': request_content.strip(),
                    'think': think_content.strip(),
                    'response': response_content.strip(),
                    'timestamp': message.get('inserted_at', '')
                })
            
            # 移动到下一个消息
            children = node.get('children', [])
            current_id = children[0] if children else None
        
        return {
            'title': title,
            'id': conversation_id,
            'inserted_at': inserted_str,
            'updated_at': updated_str,
            'message_count': len(messages),
            'messages': messages
        }
        
    except Exception as e:
        logging.error(f"解析会话时出错: {e}")
        return None

def convert_to_markdown(conversation_data):
    """生成格式优美的Markdown内容"""
    if not conversation_data:
        return "# 解析失败\n\n该会话数据格式异常"
    
    md_content = []
    
    # 元数据头部
    md_content.append(f"# 💬 {conversation_data['title']}\n")
    md_content.append("## 📋 会话信息\n")
    md_content.append(f"- **🗂️ ID**: `{conversation_data['id']}`")
    md_content.append(f"- **🕐 创建时间**: {conversation_data['inserted_at']}")
    md_content.append(f"- **🔄 更新时间**: {conversation_data['updated_at']}")
    md_content.append(f"- **💭 消息数量**: {conversation_data['message_count']} 条\n")
    
    md_content.append("---\n")
    
    # 对话内容
    for i, message in enumerate(conversation_data['messages'], 1):
        md_content.append(f"## 🔄 第 {i} 轮对话\n")
        
        if message['request']:
            md_content.append("### 👤 用户提问\n")
            md_content.append(f"{message['request']}\n")
        
        if message['think'] or message['response']:
            md_content.append("### 🤖 DeepSeek回复\n")
            md_content.append(f"**🧠 模型**: `{message['model']}`\n")
            
            if message['files']:
                md_content.append(f"**📎 文件**: {len(message['files'])} 个附件\n")
            
            if message['think']:
                md_content.append("#### 💭 思考过程\n")
                md_content.append(f"{message['think']}\n")
            
            if message['response']:
                md_content.append("#### 📝 回复内容\n")
                md_content.append(f"{message['response']}\n")
        
        md_content.append("---\n")
    
    # 尾部信息
    md_content.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_content.append("*使用DeepSeek导出工具生成*")
    
    return "\n".join(md_content)

def process_deepseek_export(input_file="conversations.json", output_dir="DeepSeek_Conversations"):
    """主处理函数"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取数据
    try:
        logging.info(f"📖 读取文件: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logging.info(f"✅ 成功读取 {len(data)} 个会话")
    except Exception as e:
        logging.error(f"❌ 读取失败: {e}")
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
            logging.info(f"🔄 处理 [{i}/{stats['total']}]: {title[:30]}...")
            
            parsed_data = parse_conversation(conversation)
            if not parsed_data:
                raise ValueError("解析返回空数据")
            
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
            logging.info(f"✅ 保存成功: {filename}")
            
        except Exception as e:
            stats['failed'] += 1
            stats['failed_indices'].append(i)
            logging.error(f"❌ 处理失败 [{i}]: {e}")
    
    # 生成报告
    generate_report(stats, output_dir)

def generate_report(stats, output_dir):
    """生成处理报告"""
    report = [
        "=" * 60,
        "📊 DeepSeek对话导出报告",
        "=" * 60,
        f"总会话数: {stats['total']}",
        f"成功导出: {stats['success']} ✅",
        f"失败数量: {stats['failed']} ❌",
        "",
        "📁 输出目录:",
        f"  {os.path.abspath(output_dir)}",
        "",
        "🕐 导出时间:",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    if stats['failed_indices']:
        report.append("❌ 失败会话索引:")
        for index in stats['failed_indices']:
            report.append(f"  - 第 {index} 条会话")
    
    report.append("")
    report.append("💡 提示: 失败通常是由于标题包含特殊字符")
    report.append("=" * 60)
    
    report_text = "\n".join(report)
    print(report_text)
    
    # 保存报告
    with open('export_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)

def main():
    """主函数"""
    print("🎯 DeepSeek对话导出工具 v2.0")
    print("📝 作者: DeepSeek & 热心用户")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    
    input_file = "conversations.json"
    output_dir = "DeepSeek_Conversations"
    
    if not os.path.exists(input_file):
        print(f"❌ 错误: 找不到 {input_file}")
        print("💡 请将DeepSeek导出的conversations.json放在同一目录")
        return
    
    print("🔄 开始处理...")
    process_deepseek_export(input_file, output_dir)
    print("🎉 处理完成！查看 export_report.txt 获取详细报告")

if __name__ == "__main__":
    main()
