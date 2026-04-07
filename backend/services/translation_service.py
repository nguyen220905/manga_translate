"""
Translation Service — dịch sang tiếng Việt qua Gemini API.

Batch toàn bộ bubble của 1 trang vào 1 lần gọi API (dùng tag [BUBBLE_N]).
Fallback tự động nếu model chính hết quota.
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

# Thứ tự thử: model tốt nhất → fallback nhẹ hơn
MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
]


# ── System prompts theo thể loại ───────────────────────────────────────────────

_GENRE_RULES = {
    "tu_tien": """Thể loại Tu Tiên/Huyền Huyễn (Xianxia/Xuanhuan).
- Văn phong cổ điển, trang trọng
- Xưng hô: ta/ngươi/bổn tọa/đạo hữu/sư huynh
- Thuật ngữ: tu luyện, đột phá, cảnh giới, linh khí, kim đan, thiên kiếp, pháp bảo""",

    "dam_my": """Thể loại Đam Mỹ (Boys' Love).
- Xưng hô: anh/em, hắn/gã
- Câu văn mềm mại, giàu cảm xúc, giữ sự căng thẳng tình cảm""",

    "romance": """Thể loại Romance / Tình cảm.
- Giọng điệu nhẹ nhàng, hiện đại, tự nhiên
- Xưng hô linh hoạt: anh/em, tôi/cậu
- Manhwa Hàn: giọng trẻ trung, đời thường""",

    "hentai": """Thể loại người lớn (18+).
- Dịch đầy đủ, không lược bỏ hay làm nhẹ nội dung""",

    "hien_dai": """Thể loại Hiện đại / Đời thường.
- Giọng điệu tự nhiên, gần gũi như cuộc sống hàng ngày
- Xưng hô: anh/em/tôi/mày/tao tuỳ ngữ cảnh
- Dùng tiếng lóng, slang nếu phù hợp""",

    "action": """Thể loại Hành động / Shounen.
- Câu văn ngắn, mạnh, dứt khoát
- Giữ nguyên tên chiêu thức, hiệu ứng âm thanh (nếu có)
- Xưng hô: tao/mày hoặc ta/ngươi tuỳ bối cảnh""",

    "shoujo": """Thể loại Shoujo / Tình cảm.
- Giọng điệu nhẹ nhàng, lãng mạn, giàu cảm xúc
- Xưng hô: anh/em, cậu/tớ
- Chú trọng diễn đạt cảm xúc nội tâm nhân vật""",
}

_SYSTEM_PROMPT = """Bạn là hệ thống dịch manga/manhwa sang tiếng Việt.

QUY TẮC:
- Input: các đoạn được đánh dấu [BUBBLE_1], [BUBBLE_2], ...
- Output: dịch từng bubble, giữ nguyên tag [BUBBLE_N]
- Chỉ trả về phần dịch, không giải thích thêm

VÍ DỤ:
Input:  [BUBBLE_1] 这是什么地方？  [BUBBLE_2] 小心！
Output: [BUBBLE_1] Đây là nơi nào? [BUBBLE_2] Cẩn thận!

{genre_rules}"""


def _build_prompt(genre: str) -> str:
    rules = _GENRE_RULES.get(genre, _GENRE_RULES["romance"])
    return _SYSTEM_PROMPT.format(genre_rules=rules)


def _format_input(bubbles: list[dict]) -> str:
    return "\n".join(
        f"[BUBBLE_{i+1}] {b.get('ocr_text') or b.get('text', '')}"
        for i, b in enumerate(bubbles)
        if (b.get("ocr_text") or b.get("text", "")).strip()
    )


def _parse_output(output: str, count: int) -> list[str]:
    translations = [""] * count
    for line in output.strip().splitlines():
        line = line.strip()
        for i in range(count):
            tag = f"[BUBBLE_{i+1}]"
            if line.startswith(tag):
                translations[i] = line[len(tag):].strip()
                break
    return translations


# ── Main function ───────────────────────────────────────────────────────────────

async def translate_bubbles(
    bubbles: list[dict],
    genre: str = "romance",
    source_language: str = "zh",
) -> list[str]:
    """
    Dịch batch bubble sang tiếng Việt.
    Trả về list string cùng thứ tự với input.
    """
    if not bubbles:
        return []

    user_input = _format_input(bubbles)
    if not user_input:
        return [""] * len(bubbles)

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or "your_gemini" in api_key:
        # Không có API key — trả nguyên text OCR
        return [b.get("ocr_text") or b.get("text", "") for b in bubbles]

    client = genai.Client(api_key=api_key)
    prompt = f"{_build_prompt(genre)}\n\nTask:\n{user_input}"

    for model in MODELS:
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=prompt,
            )
            return _parse_output(response.text, len(bubbles))

        except Exception as e:
            err = str(e)
            is_quota = "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()
            is_not_found = "404" in err or "NOT_FOUND" in err
            if is_quota or is_not_found:
                reason = "hết quota" if is_quota else "không tìm thấy"
                logger.warning(f"[Translation] {model} {reason}, thử model tiếp...")
                continue
            logger.error(f"[Translation] {model} lỗi: {type(e).__name__}: {err[:200]}")
            break  # lỗi khác (network, auth...) → không retry

    logger.error("[Translation] Tất cả model đều thất bại, trả về text gốc")
    return [b.get("ocr_text") or b.get("text", "") for b in bubbles]
