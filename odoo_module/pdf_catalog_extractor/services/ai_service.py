import json
import logging

from anthropic import Anthropic

_logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a product data extraction specialist. Analyze the following product catalog content and extract ALL products found.

For each product, extract:
- **name**: Product name/title (required)
- **default_code**: SKU, reference code, or product code (if available)
- **list_price**: Price as a number (without currency symbols). If multiple prices exist, use the main/retail price
- **categ_id**: Product category or classification (e.g., "Tools / Power Tools", "Electronics / Cables")
- **description_sale**: Brief product description for sales
- **brand**: Brand or manufacturer name (if available)
- **unit**: Unit of measure (e.g., "unit", "kg", "m", "box")
- **page_number**: The page number where this product was found

IMPORTANT RULES:
1. Extract ALL products, even if some data is missing
2. Set list_price to null if no price is found
3. Use "/" as separator for category hierarchy (Odoo format)
4. Be thorough - don't skip products
5. If a product lacks critical data, still include it

Return ONLY a valid JSON array of objects. No markdown, no explanation. Example:
[
  {
    "name": "Product Name",
    "default_code": "SKU123",
    "list_price": 29.99,
    "categ_id": "Category / Subcategory",
    "description_sale": "Brief description",
    "brand": "BrandName",
    "unit": "unit",
    "page_number": 1
  }
]"""


def _parse_response(response_text: str) -> list[dict]:
    """Clean and parse the AI response JSON."""
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


def extract_products(
    api_key: str,
    pages_text: list[str] | None = None,
    page_images: list[str] | None = None,
) -> list[dict]:
    """Extract products using text or vision mode.

    Provide either pages_text (list of text per page) or
    page_images (list of base64 PNG strings).
    """
    client = Anthropic(api_key=api_key)
    all_products = []

    if page_images:
        # Vision mode: process in batches of 5
        batch_size = 5
        for i in range(0, len(page_images), batch_size):
            batch = page_images[i : i + batch_size]
            content = []
            for j, img_b64 in enumerate(batch):
                page_num = i + j + 1
                content.append({"type": "text", "text": f"Page {page_num}:"})
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_b64,
                        },
                    }
                )
            content.append({"type": "text", "text": EXTRACTION_PROMPT})

            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": content}],
                )
                products = _parse_response(message.content[0].text)
                if isinstance(products, list):
                    all_products.extend(products)
            except json.JSONDecodeError as e:
                _logger.error("Failed to parse AI vision response: %s", e)
                continue

    elif pages_text:
        # Text mode: combine pages and chunk if needed
        combined = ""
        for i, text in enumerate(pages_text, 1):
            if text.strip():
                combined += f"\n--- PAGE {i} ---\n{text}"

        if not combined.strip():
            return []

        max_chars = 80000
        chunks = []
        if len(combined) > max_chars:
            pages_with_numbers = [
                (i, text)
                for i, text in enumerate(pages_text, 1)
                if text.strip()
            ]
            current_chunk = ""
            for page_num, text in pages_with_numbers:
                page_content = f"\n--- PAGE {page_num} ---\n{text}"
                if (
                    len(current_chunk) + len(page_content) > max_chars
                    and current_chunk
                ):
                    chunks.append(current_chunk)
                    current_chunk = page_content
                else:
                    current_chunk += page_content
            if current_chunk:
                chunks.append(current_chunk)
        else:
            chunks = [combined]

        for chunk in chunks:
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": f"{EXTRACTION_PROMPT}\n\nCATALOG CONTENT:\n{chunk}",
                        }
                    ],
                )
                products = _parse_response(message.content[0].text)
                if isinstance(products, list):
                    all_products.extend(products)
            except json.JSONDecodeError as e:
                _logger.error("Failed to parse AI text response: %s", e)
                continue

    return all_products
