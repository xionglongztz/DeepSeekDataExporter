import os
import markdown
import pdfkit
import argparse
from pathlib import Path
import logging
from datetime import datetime
import sys
import re
from bs4 import BeautifulSoup
import emoji

def setup_logging():
    """设置日志记录"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = log_dir / f'md_to_pdf_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

def clean_font_name(font_name):
    """清理字体名称，移除字重和样式信息"""
    suffixes = [' normal', ' normal italic', ' italic', ' bold', ' bold italic', 
                ' regular', ' light', ' medium', ' heavy', ' black',
                ' Normal', ' Normal Italic', ' Italic', ' Bold', ' Bold Italic',
                ' Regular', ' Light', ' Medium', ' Heavy', ' Black']
    
    cleaned = font_name
    for suffix in suffixes:
        if cleaned.lower().endswith(suffix.lower()):
            cleaned = cleaned[:-len(suffix)]
    
    return cleaned.strip()

def get_font_file_path(fonts_dir, font_name):
    """根据字体名称查找对应的字体文件"""
    font_files = {
        '方正喵呜体': ['方正喵呜体.ttf', '方正喵呜体.otf', 'FZMWFont.ttf', 'FZMWFont.otf'],
        'maple mono cn': ['MapleMonoCN-Regular.ttf', 'MapleMonoCN-Regular.otf', 
                         'MapleMonoCN-Bold.ttf', 'MapleMonoCN-Bold.otf',
                         'MapleMono.ttf', 'MapleMono.otf']
    }
    
    font_name_lower = font_name.lower()
    for font_pattern, possible_files in font_files.items():
        if font_pattern in font_name_lower:
            for filename in possible_files:
                font_path = fonts_dir / filename
                if font_path.exists():
                    return font_path
    
    for ext in ['.ttf', '.otf']:
        for font_file in fonts_dir.glob(f'*{ext}'):
            if font_name_lower in font_file.stem.lower():
                return font_file
    
    return None

def process_emoji_content(html_content):
    """处理HTML中的emoji"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for text_node in soup.find_all(string=True):
        if any(ord(char) > 0xFFFF for char in text_node):
            new_content = []
            for char in text_node:
                if ord(char) > 0xFFFF:
                    span = soup.new_tag('span', **{
                        'class': 'emoji',
                        'style': 'font-family: "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"; font-size: 1.2em;'
                    })
                    span.string = char
                    new_content.append(span)
                else:
                    new_content.append(char)
            
            text_node.replace_with(*new_content)
    
    return str(soup)

def convert_md_to_pdf(md_file, pdf_file, font_config=None, custom_fonts_dir=None):
    """
    将Markdown文件转换为PDF，支持自定义字体
    """
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 启用代码块扩展
        extensions = ['fenced_code', 'codehilite']
        html_content = markdown.markdown(md_content, extensions=extensions)
        html_content = process_emoji_content(html_content)

        # 清理字体名称
        cleaned_font_config = {}
        for key, value in font_config.items():
            cleaned_value = value.replace("'", "").replace('"', '')
            cleaned_value = clean_font_name(cleaned_value)
            cleaned_font_config[key] = f"'{cleaned_value}'"
        
        # 构建字体CSS
        font_css = ""
        if custom_fonts_dir:
            fonts_dir_path = Path(custom_fonts_dir)
            
            miaowu_font_path = get_font_file_path(fonts_dir_path, '方正喵呜体')
            if miaowu_font_path:
                font_url = miaowu_font_path.as_uri()
                font_css += f"""
                @font-face {{
                    font-family: '方正喵呜体';
                    src: url('{font_url}');
                    font-weight: normal;
                    font-style: normal;
                }}
                """
                logging.info(f"找到方正喵呜体字体文件: {miaowu_font_path}")
            
            maple_font_path = get_font_file_path(fonts_dir_path, 'Maple Mono CN')
            if maple_font_path:
                font_url = maple_font_path.as_uri()
                font_css += f"""
                @font-face {{
                    font-family: 'Maple Mono CN';
                    src: url('{font_url}');
                    font-weight: normal;
                    font-style: normal;
                }}
                """
                logging.info(f"找到Maple Mono CN字体文件: {maple_font_path}")
        
        # CSS样式
        css_style = f"""
        {font_css}
        
        @page {{
            size: A4;
            margin: 1in;
        }}
        
        body {{
            font-family: {cleaned_font_config.get('body', "'方正喵呜体', 'Microsoft YaHei', sans-serif")};
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            font-size: 14px;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            font-family: {cleaned_font_config.get('heading', "'方正喵呜体', 'Microsoft YaHei', sans-serif")};
            color: #2c3e50;
            font-weight: bold;
            margin-top: 1.5em;
            margin-bottom: 0.8em;
            line-height: 1.3;
        }}
        
        h1 {{ font-size: 2.2em; border-bottom: 3px solid #3498db; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.8em; border-bottom: 2px solid #3498db; padding-bottom: 0.2em; }}
        h3 {{ font-size: 1.5em; }}
        h4 {{ font-size: 1.3em; color: #e74c3c; }}
        h5 {{ font-size: 1.1em; color: #9b59b6; }}
        h6 {{ font-size: 1em; color: #f39c12; text-transform: uppercase; letter-spacing: 1px; }}
        
        code {{
            font-family: {cleaned_font_config.get('code', "'Maple Mono CN', 'Courier New', monospace")};
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
            font-size: 0.9em;
        }}
        
        pre {{
            font-family: {cleaned_font_config.get('code', "'Maple Mono CN', 'Courier New', monospace")};
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            overflow: auto;
            border: 1px solid #e9ecef;
            line-height: 1.5;
            font-size: 0.9em;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            border: none;
            border-radius: 0;
        }}
        
        .emoji {{
            font-family: "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", sans-serif !important;
            font-size: 1.2em;
        }}
        """
        
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{md_file.stem}</title>
            <style>
                {css_style}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        options = {
            'page-size': 'A4',
            'margin-top': '1in',
            'margin-right': '1in',
            'margin-bottom': '1in',
            'margin-left': '1in',
            'encoding': 'UTF-8',
            'quiet': '',
            'enable-local-file-access': '',
            'dpi': 300,
            'image-quality': 100
        }
        
        pdfkit.from_string(full_html, str(pdf_file), options=options)
        return True, None
        
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='将Markdown文件转换为PDF，支持自定义字体')
    parser.add_argument('--input-dir', default='MarkDowns', 
                       help='输入目录 (默认: MarkDowns)')
    parser.add_argument('--output-dir', default='PDFs',
                       help='输出目录 (默认: PDFs)')
    parser.add_argument('--body-font', default="方正喵呜体", 
                       help='正文字体 (默认: 方正喵呜体)')
    parser.add_argument('--heading-font', default="方正喵呜体",
                       help='标题字体 (默认: 方正喵呜体)')
    parser.add_argument('--code-font', default="Maple Mono CN",
                       help='代码字体 (默认: Maple Mono CN)')
    parser.add_argument('--fonts-dir', default='fonts',
                       help='自定义字体文件目录 (默认: fonts)')
    parser.add_argument('--wkhtmltopdf-path', default=None,
                       help='wkhtmltopdf可执行文件路径')
    parser.add_argument('--no-custom-fonts', action='store_true',
                       help='不使用自定义字体，仅使用系统字体')
    
    args = parser.parse_args()
    
    log_file = setup_logging()
    logging.info("开始Markdown转PDF处理")
    
    font_config = {
        'body': args.body_font,
        'heading': args.heading_font,
        'code': args.code_font
    }
    
    custom_fonts_available = False
    fonts_dir_path = None
    
    if not args.no_custom_fonts:
        fonts_dir_path = Path(args.fonts_dir)
        if fonts_dir_path.exists() and any(fonts_dir_path.glob('*.*')):
            custom_fonts_available = True
    
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logging.error(f"输入目录不存在: {input_dir}")
        return
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    md_files = list(input_dir.glob('**/*.md'))
    if not md_files:
        logging.warning("未找到Markdown文件")
        return
    
    success_count = 0
    for i, md_file in enumerate(md_files, 1):
        relative_path = md_file.relative_to(input_dir)
        pdf_path = output_dir / relative_path.with_suffix('.pdf')
        pdf_path.parent.mkdir(exist_ok=True)
        
        logging.info(f"处理 [{i}/{len(md_files)}]: {md_file.name}")
        
        success, error = convert_md_to_pdf(
            md_file, 
            pdf_path, 
            font_config, 
            str(fonts_dir_path) if custom_fonts_available else None
        )
        
        if success:
            logging.info(f"保存成功: {pdf_path.name}")
            success_count += 1
        else:
            logging.error(f"失败: {error}")
    
    logging.info(f"处理完成! 成功: {success_count}/{len(md_files)}")

if __name__ == "__main__":
    main()
