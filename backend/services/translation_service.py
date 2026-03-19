"""
Translation Service — Genre-aware Vietnamese translation via OpenRouter API.
Batches all bubbles per page into a single API call using [BUBBLE_N] tags.
"""
import os
import httpx
import json
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from backend/ directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)
print(f"[Translation] Loading .env from: {_env_path} (exists={_env_path.exists()})")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.1-8b-instruct:free"

# ── Genre Prompt Templates ─────────────────────────────

GENRE_PROMPTS = {
    "tu_tien": """Bạn là dịch giả chuyên nghiệp thể loại Tu Tiên/Huyền Huyễn (Xianxia/Xuanhuan).

QUY TẮC DỊCH:
- Sử dụng văn phong cổ điển, trang trọng
- Xưng hô: ta/ngươi/bổn tọa/tiểu tử/đạo hữu/sư huynh/sư đệ
- Thuật ngữ cố định:
  • 修炼/修行 = tu luyện
  • 突破 = đột phá
  • 境界 = cảnh giới
  • 丹田 = đan điền
  • 灵气 = linh khí
  • 元婴 = nguyên anh
  • 化神 = hóa thần
  • 金丹 = kim đan
  • 筑基 = trúc cơ
  • 炼气 = luyện khí
  • 天劫 = thiên kiếp
  • 仙人 = tiên nhân
  • 魔族 = ma tộc
  • 功法 = công pháp
  • 法宝 = pháp bảo
- Giữ nguyên tên riêng theo phiên âm Hán-Việt
- Giọng điệu uy nghiêm, có sức nặng""",

    "dam_my": """Bạn là dịch giả chuyên nghiệp thể loại Đam Mỹ (Boys' Love / Danmei).

QUY TẮC DỊCH:
- Xưng hô: anh/em, hắn/gã (ngôi thứ 3)
- Thể hiện cảm xúc tinh tế, lãng mạn
- Giữ sự căng thẳng tình cảm giữa hai nhân vật
- Câu văn mềm mại, giàu cảm xúc
- Thuật ngữ:
  • 攻/受 = công/thụ
  • 双向暗恋 = tương tư ngầm
  • 甜文 = văn ngọt
  • 虐文 = văn ngược
- Dịch tự nhiên, không gượng ép
- Giữ nguyên tên riêng theo phiên âm""",

    "romance": """Bạn là dịch giả chuyên nghiệp thể loại Romance / Tình cảm.

QUY TẮC DỊCH:
- Giọng điệu nhẹ nhàng, hiện đại, tự nhiên
- Xưng hô linh hoạt: anh/em, tôi/cậu tùy ngữ cảnh
- Dịch SFX (hiệu ứng âm thanh): ドキドキ = thình thịch, キュン = rung động
- Xử lý tsundere: giữ sự mâu thuẫn giữa lời nói và cảm xúc
- Câu thoại tự nhiên như đời thường
- Manhwa Hàn: giọng hiện đại, trẻ trung""",

    "hentai": """Bạn là dịch giả thể loại người lớn (18+). Dịch chính xác, không kiểm duyệt.

QUY TẮC DỊCH:
- Dịch đầy đủ nội dung gốc, không lược bỏ hay làm nhẹ
- Sử dụng ngôn ngữ phù hợp với cường độ bản gốc
- Dịch chuẩn SFX và âm thanh
- Giữ nguyên giọng điệu và cảm xúc nhân vật
- Xưng hô phù hợp ngữ cảnh""",
}

BASE_SYSTEM_PROMPT = """Bạn là hệ thống dịch manga/truyện tranh sang tiếng Việt.

ĐỊNH DẠNG:
- Input: Mỗi đoạn text được đánh dấu [BUBBLE_1], [BUBBLE_2], ...
- Output: Dịch từng bubble tương ứng, giữ nguyên tag [BUBBLE_N]
- CHỈ trả về phần dịch, không giải thích

VÍ DỤ INPUT:
[BUBBLE_1] 这是什么地方？
[BUBBLE_2] 小心！有危险！

VÍ DỤ OUTPUT:
[BUBBLE_1] Đây là nơi nào vậy?
[BUBBLE_2] Cẩn thận! Có nguy hiểm!

{genre_rules}
"""


def build_prompt(genre: str) -> str:
    genre_rules = GENRE_PROMPTS.get(genre, GENRE_PROMPTS["romance"])
    return BASE_SYSTEM_PROMPT.format(genre_rules=genre_rules)


def format_bubbles_input(bubbles: list[dict]) -> str:
    """Format bubble texts with [BUBBLE_N] tags for batch translation."""
    lines = []
    for i, b in enumerate(bubbles):
        text = b.get("ocr_text", "") or b.get("text", "")
        if text.strip():
            lines.append(f"[BUBBLE_{i+1}] {text}")
    return "\n".join(lines)


def parse_translation_output(output: str, count: int) -> list[str]:
    """Parse [BUBBLE_N] tagged output back into ordered list."""
    translations = [""] * count
    
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        for i in range(count):
            tag = f"[BUBBLE_{i+1}]"
            if line.startswith(tag):
                translations[i] = line[len(tag):].strip()
                break
    
    return translations


async def translate_bubbles(
    bubbles: list[dict],
    genre: str = "tu_tien",
    source_language: str = "zh",
) -> list[str]:
    """
    Translate a batch of bubble texts to Vietnamese.
    
    Args:
        bubbles: List of {"text": str, ...} dicts
        genre: Genre key for prompt selection
        source_language: Source language code
    
    Returns:
        List of translated strings (same order as input)
    """
    if not bubbles:
        return []
    
    user_input = format_bubbles_input(bubbles)
    if not user_input.strip():
        return [""] * len(bubbles)
    
    system_prompt = build_prompt(genre)
    
    # If no API key, return placeholder translations (just the OCR text)
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return [b.get('ocr_text', b.get('text', '')) for b in bubbles]
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "MangaDich",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            output_text = data["choices"][0]["message"]["content"]
            return parse_translation_output(output_text, len(bubbles))
    
    except httpx.HTTPStatusError as e:
        print(f"Translation HTTP error: {e.response.text}")
        return [f"[Lỗi API] {b.get('ocr_text', b.get('text', ''))}" for b in bubbles]
    except Exception as e:
        print(f"Translation error: {e}")
        # Fallback: return original text with prefix
        return [f"[Lỗi dịch] {b.get('ocr_text', b.get('text', ''))}" for b in bubbles]
