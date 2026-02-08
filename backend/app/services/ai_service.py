import os
import json
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

client = None


def get_client() -> Anthropic:
    global client
    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Set it before starting the server."
            )
        client = Anthropic(api_key=api_key)
    return client


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


def extract_products_from_text(pages_text: list[str]) -> list[dict]:
    """Extract products using text content from PDF pages."""
    combined_text = ""
    for i, text in enumerate(pages_text, 1):
        if text.strip():
            combined_text += f"\n--- PAGE {i} ---\n{text}"

    if not combined_text.strip():
        return []

    # Split into chunks if text is very long (Claude has token limits)
    max_chars = 80000
    chunks = []
    if len(combined_text) > max_chars:
        pages_with_numbers = []
        for i, text in enumerate(pages_text, 1):
            if text.strip():
                pages_with_numbers.append((i, text))

        current_chunk = ""
        for page_num, text in pages_with_numbers:
            page_content = f"\n--- PAGE {page_num} ---\n{text}"
            if len(current_chunk) + len(page_content) > max_chars and current_chunk:
                chunks.append(current_chunk)
                current_chunk = page_content
            else:
                current_chunk += page_content
        if current_chunk:
            chunks.append(current_chunk)
    else:
        chunks = [combined_text]

    all_products = []
    anthropic = get_client()

    for chunk in chunks:
        try:
            message = anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": f"{EXTRACTION_PROMPT}\n\nCATALOG CONTENT:\n{chunk}",
                    }
                ],
            )

            response_text = message.content[0].text.strip()
            # Clean response - remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            products = json.loads(response_text)
            if isinstance(products, list):
                all_products.extend(products)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            continue
        except Exception as e:
            logger.error(f"AI extraction error: {e}")
            raise

    return all_products


def extract_products_from_images(page_images: list[str]) -> list[dict]:
    """Extract products using page images (vision) for scanned/image-heavy PDFs."""
    all_products = []
    anthropic = get_client()

    # Process pages in batches to stay within limits
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
            message = anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": content}],
            )

            response_text = message.content[0].text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            products = json.loads(response_text)
            if isinstance(products, list):
                all_products.extend(products)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            continue
        except Exception as e:
            logger.error(f"AI vision extraction error: {e}")
            raise

    return all_products
