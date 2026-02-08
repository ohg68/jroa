#!/usr/bin/env python3
"""
Test script to verify AI extraction from a PDF catalog.

Usage:
    export ANTHROPIC_API_KEY="sk-..."
    cd backend
    python test_extraction.py /path/to/catalog.pdf

Options:
    --vision    Force vision-based extraction (for scanned PDFs)
    --text-only Show extracted text without calling AI
    --pages N   Only process first N pages
"""

import sys
import os
import json
import time
import argparse

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services import pdf_service, ai_service


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def print_product_table(products: list[dict]) -> None:
    """Print products as a formatted table."""
    if not products:
        print("\n  No products extracted.")
        return

    # Column widths
    name_w = min(40, max(len("Name"), max(len(p.get("name", "")[:40]) for p in products)))
    sku_w = min(15, max(len("SKU"), max(len(str(p.get("default_code", "") or "")[:15]) for p in products)))
    price_w = 10
    cat_w = min(25, max(len("Category"), max(len(str(p.get("categ_id", "") or "")[:25]) for p in products)))
    brand_w = min(15, max(len("Brand"), max(len(str(p.get("brand", "") or "")[:15]) for p in products)))

    header = (
        f"  {'#':>3}  "
        f"{'Name':<{name_w}}  "
        f"{'SKU':<{sku_w}}  "
        f"{'Price':>{price_w}}  "
        f"{'Category':<{cat_w}}  "
        f"{'Brand':<{brand_w}}  "
        f"{'Pg':>3}  "
        f"Status"
    )
    separator = "  " + "-" * (len(header) - 2)

    print(f"\n{header}")
    print(separator)

    valid = 0
    review = 0

    for i, p in enumerate(products, 1):
        name = (p.get("name") or "")[:name_w]
        sku = (str(p.get("default_code") or "-"))[:sku_w]
        price_val = p.get("list_price")
        price = f"${price_val:.2f}" if price_val is not None else "-"
        cat = (str(p.get("categ_id") or "-"))[:cat_w]
        brand = (str(p.get("brand") or "-"))[:brand_w]
        page = str(p.get("page_number") or "-")

        issues = []
        if price_val is None or (isinstance(price_val, (int, float)) and price_val <= 0):
            issues.append("no_price")
        if not p.get("default_code"):
            issues.append("no_sku")

        if issues:
            status = f"REVIEW ({', '.join(issues)})"
            review += 1
        else:
            status = "OK"
            valid += 1

        print(
            f"  {i:>3}  "
            f"{name:<{name_w}}  "
            f"{sku:<{sku_w}}  "
            f"{price:>{price_w}}  "
            f"{cat:<{cat_w}}  "
            f"{brand:<{brand_w}}  "
            f"{page:>3}  "
            f"{status}"
        )

    print(separator)
    print(f"  Total: {len(products)}  |  Valid: {valid}  |  Need review: {review}")


def main():
    parser = argparse.ArgumentParser(description="Test AI extraction from a PDF catalog")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--vision", action="store_true", help="Force vision-based extraction")
    parser.add_argument("--text-only", action="store_true", help="Show extracted text, don't call AI")
    parser.add_argument("--pages", type=int, default=0, help="Only process first N pages")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of table")
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf_path)
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    if not pdf_path.lower().endswith(".pdf"):
        print("Error: File must be a PDF")
        sys.exit(1)

    # --- PDF Info ---
    info = pdf_service.get_pdf_info(pdf_path)
    print("\n" + "=" * 60)
    print("  PDF CATALOG EXTRACTION TEST")
    print("=" * 60)
    print(f"  File:   {os.path.basename(pdf_path)}")
    print(f"  Size:   {format_size(info['file_size'])}")
    print(f"  Pages:  {info['total_pages']}")

    # --- Text Extraction ---
    print("\n--- Extracting text from PDF... ---")
    pages_text = pdf_service.extract_text_from_pdf(pdf_path)

    if args.pages > 0:
        pages_text = pages_text[: args.pages]
        print(f"  (Limited to first {args.pages} pages)")

    total_chars = sum(len(t) for t in pages_text)
    non_empty_pages = sum(1 for t in pages_text if t.strip())
    print(f"  Text extracted: {total_chars:,} chars from {non_empty_pages}/{len(pages_text)} pages")

    if args.text_only:
        print("\n--- Extracted Text ---")
        for i, text in enumerate(pages_text, 1):
            if text.strip():
                print(f"\n--- PAGE {i} ---")
                print(text[:2000])
                if len(text) > 2000:
                    print(f"  ... ({len(text) - 2000} more chars)")
        return

    # --- Decide extraction method ---
    use_vision = args.vision
    if not use_vision and total_chars < 50:
        print("  Low text content detected - switching to vision extraction")
        use_vision = True

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nError: ANTHROPIC_API_KEY environment variable is required")
        print("  export ANTHROPIC_API_KEY=\"sk-...\"")
        sys.exit(1)

    # --- AI Extraction ---
    method = "vision" if use_vision else "text"
    print(f"\n--- Calling Claude AI ({method} mode)... ---")
    start_time = time.time()

    try:
        if use_vision:
            print("  Rendering pages as images...")
            page_images = pdf_service.extract_pages_as_images(pdf_path)
            if args.pages > 0:
                page_images = page_images[: args.pages]
            print(f"  {len(page_images)} page images ready")
            products = ai_service.extract_products_from_images(page_images)
        else:
            products = ai_service.extract_products_from_text(pages_text)

        elapsed = time.time() - start_time
        print(f"  Completed in {elapsed:.1f}s")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)

    # --- Output ---
    if args.json:
        print("\n--- Raw JSON Output ---")
        print(json.dumps(products, indent=2, ensure_ascii=False))
    else:
        print_product_table(products)

    # --- Odoo CSV Preview ---
    print("\n--- Odoo CSV Preview (first 5 rows) ---")
    print('  "name","default_code","list_price","categ_id","description_sale"')
    for p in products[:5]:
        name = (p.get("name") or "").replace('"', '""')
        sku = (p.get("default_code") or "").replace('"', '""')
        price = str(p.get("list_price") or "")
        cat = (p.get("categ_id") or "").replace('"', '""')
        desc = (p.get("description_sale") or "").replace('"', '""')[:60]
        print(f'  "{name}","{sku}","{price}","{cat}","{desc}"')

    if len(products) > 5:
        print(f"  ... and {len(products) - 5} more rows")

    print()


if __name__ == "__main__":
    main()
