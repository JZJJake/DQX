import json
import logging
from openai import OpenAI

def clean_and_format_text(raw_text, api_key):
    """
    1. Splits raw_text into lines, adding line numbers.
    2. Sends the numbered lines to DeepSeek to identify title and lines to delete.
    3. Removes deleted lines and empty lines.
    4. Appends $END$ after each natural paragraph on a new line.

    Returns:
        title (str): Extracted title, or empty string.
        formatted_text (str): The cleaned text with $END$ markers.
    """
    if not raw_text.strip():
        return "", ""

    # 1. Split into lines, filtering out purely empty lines to save tokens
    lines = raw_text.split('\n')
    numbered_lines = []
    original_lines = {} # map line number to original text
    line_num = 1

    for line in lines:
        stripped = line.strip()
        if stripped: # Only send non-empty lines for analysis
            numbered_lines.append(f"{line_num}: {stripped}")
            original_lines[line_num] = stripped
            line_num += 1

    if not numbered_lines:
        return "", ""

    # Limit the prompt size to avoid token limits if the document is huge
    # In a real production scenario with very large docs, we might need to chunk it.
    # For now, we take up to 2000 lines.
    prompt_text = "\n".join(numbered_lines[:2000])

    system_prompt = """
    你是一个文档分析专家。我会提供一段带有行号的文档文本，你的任务是：
    1. 从中提取出这份文档的正式标题（如果没有明显标题，可以留空）。
    2. 找出所有不属于文档“正式的完整内容”的行，例如页眉、页脚、广告、版权声明等无关信息，给出需要删除的行号范围。不要删除正式内容！

    你必须且只能返回一个合法的 JSON 对象，格式如下：
    {
      "document_title": "提取出的文档标题",
      "delete_line_ranges": [[起始行号1, 结束行号1], [起始行号2, 结束行号2]]
    }

    注意：
    - 如果没有需要删除的行，delete_line_ranges 应该为空数组 []。
    - 如果只有一行需要删除，格式为 [[3, 3]]。
    - 绝不能输出任何 JSON 之外的说明文字。
    """

    title = ""
    lines_to_delete = set()

    if api_key:
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_text}
                ],
                response_format={"type": "json_object"},
                max_tokens=2048,
                temperature=0.0
            )

            content = response.choices[0].message.content
            logging.info(f"DeepSeek response: {content}")
            result = json.loads(content)

            title = result.get("document_title", "").strip()
            ranges = result.get("delete_line_ranges", [])

            for start, end in ranges:
                for i in range(start, end + 1):
                    lines_to_delete.add(i)

        except Exception as e:
            logging.error(f"DeepSeek API error: {e}")
            # We continue even if API fails, the user can manually clean it in GUI
    else:
        logging.warning("No DeepSeek API key provided. Skipping smart filtering.")

    # 3. Clean lines
    cleaned_lines = []
    for num, text in original_lines.items():
        if num not in lines_to_delete:
            cleaned_lines.append(text)

    # If no title was found by API, take first 6 characters of the first valid line
    if not title:
        for line in cleaned_lines:
            if line.strip():
                title = line.strip()[:6]
                break

    # 4. Format with $END$
    formatted_paragraphs = []
    for line in cleaned_lines:
        formatted_paragraphs.append(line)
        formatted_paragraphs.append("$END$")

    formatted_text = "\n".join(formatted_paragraphs)

    return title, formatted_text
