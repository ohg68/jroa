#!/usr/bin/env python3
"""
Standalone test for the PDF Catalog Extractor module.
Runs WITHOUT Odoo - validates services, PDF processing, AI parsing, and CSV export.

Usage:
    cd odoo_module/pdf_catalog_extractor
    python tests/test_standalone.py

    # With AI (requires ANTHROPIC_API_KEY):
    ANTHROPIC_API_KEY="sk-..." python tests/test_standalone.py --with-ai
"""

import argparse
import base64
import csv
import io
import json
import os
import sys
import tempfile
import unittest

# Add parent to path so we can import services directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fitz  # PyMuPDF

from services import pdf_service, ai_service


# =============================================================================
# Helpers
# =============================================================================

def create_test_pdf(products: list[tuple] | None = None, num_pages: int = 1) -> str:
    """Create a test PDF with product data. Returns temp file path."""
    doc = fitz.open()

    if products is None:
        products = [
            ("SKU001", "Taladro Percutor 800W", 89.99, "Tools / Power Tools"),
            ("SKU002", "Sierra Circular 1200W", 129.50, "Tools / Power Tools"),
            ("SKU003", "Amoladora Angular 750W", 64.90, "Tools / Angle Grinders"),
            ("", "Destornillador Electrico", None, "Tools / Screwdrivers"),
            ("SKU005", "Lijadora Orbital 300W", 45.00, "Tools / Sanders"),
        ]

    items_per_page = max(1, len(products) // num_pages)

    for page_idx in range(num_pages):
        page = doc.new_page(width=595, height=842)  # A4
        y = 50

        # Title
        page.insert_text(
            fitz.Point(50, y),
            f"Product Catalog - Page {page_idx + 1}",
            fontsize=16,
            fontname="helv",
        )
        y += 40

        start = page_idx * items_per_page
        end = start + items_per_page if page_idx < num_pages - 1 else len(products)
        page_products = products[start:end]

        for sku, name, price, category in page_products:
            price_str = f"${price:.2f}" if price else "Consultar"
            sku_str = f"[{sku}] " if sku else ""
            line = f"{sku_str}{name} - {price_str} - Category: {category}"
            page.insert_text(fitz.Point(50, y), line, fontsize=10, fontname="helv")
            y += 20

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc.save(path)
    doc.close()
    return path


# =============================================================================
# Test: PDF Service
# =============================================================================

class TestPdfService(unittest.TestCase):
    """Test PDF service functions."""

    def setUp(self):
        self.pdf_path = create_test_pdf()

    def tearDown(self):
        if os.path.exists(self.pdf_path):
            os.unlink(self.pdf_path)

    def test_get_pdf_info(self):
        """get_pdf_info returns correct page count and file size."""
        info = pdf_service.get_pdf_info(self.pdf_path)
        self.assertEqual(info["total_pages"], 1)
        self.assertGreater(info["file_size"], 0)
        print(f"  OK: PDF info - {info['total_pages']} pages, {info['file_size']} bytes")

    def test_get_pdf_info_multipage(self):
        """get_pdf_info handles multi-page PDFs."""
        path = create_test_pdf(num_pages=3)
        try:
            info = pdf_service.get_pdf_info(path)
            self.assertEqual(info["total_pages"], 3)
            print(f"  OK: Multi-page PDF - {info['total_pages']} pages")
        finally:
            os.unlink(path)

    def test_extract_text(self):
        """extract_text_from_pdf extracts text from all pages."""
        pages = pdf_service.extract_text_from_pdf(self.pdf_path)
        self.assertEqual(len(pages), 1)
        text = pages[0]
        self.assertIn("Taladro Percutor", text)
        self.assertIn("Sierra Circular", text)
        self.assertIn("SKU001", text)
        self.assertIn("89.99", text)
        self.assertIn("Destornillador", text)
        print(f"  OK: Text extraction - {len(text)} chars, all products found")

    def test_extract_text_multipage(self):
        """extract_text_from_pdf returns one entry per page."""
        path = create_test_pdf(num_pages=3)
        try:
            pages = pdf_service.extract_text_from_pdf(path)
            self.assertEqual(len(pages), 3)
            # At least one page should have content
            total_text = "".join(pages)
            self.assertGreater(len(total_text), 50)
            print(f"  OK: Multi-page text extraction - {len(pages)} pages, {len(total_text)} total chars")
        finally:
            os.unlink(path)

    def test_extract_pages_as_images(self):
        """extract_pages_as_images returns base64 PNG strings."""
        images = pdf_service.extract_pages_as_images(self.pdf_path)
        self.assertEqual(len(images), 1)
        # Verify it's valid base64
        decoded = base64.b64decode(images[0])
        # PNG magic bytes
        self.assertTrue(decoded[:4] == b"\x89PNG")
        print(f"  OK: Image extraction - {len(images)} images, {len(decoded)} bytes each")

    def test_optimize_pdf(self):
        """optimize_pdf creates a valid optimized PDF."""
        optimized_path = pdf_service.optimize_pdf(self.pdf_path)
        try:
            self.assertTrue(os.path.exists(optimized_path))
            # Optimized file should be a valid PDF
            info = pdf_service.get_pdf_info(optimized_path)
            self.assertEqual(info["total_pages"], 1)
            print(
                f"  OK: PDF optimization - "
                f"original {os.path.getsize(self.pdf_path)} bytes, "
                f"optimized {os.path.getsize(optimized_path)} bytes"
            )
        finally:
            os.unlink(optimized_path)

    def test_empty_pdf(self):
        """Services handle empty PDFs gracefully."""
        doc = fitz.open()
        doc.new_page()
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        doc.save(path)
        doc.close()
        try:
            info = pdf_service.get_pdf_info(path)
            self.assertEqual(info["total_pages"], 1)
            pages = pdf_service.extract_text_from_pdf(path)
            self.assertEqual(len(pages), 1)
            # Empty page should have minimal text
            self.assertEqual(pages[0].strip(), "")
            print("  OK: Empty PDF handled gracefully")
        finally:
            os.unlink(path)


# =============================================================================
# Test: AI Service (response parsing only, no API calls)
# =============================================================================

class TestAiServiceParsing(unittest.TestCase):
    """Test AI response parsing without making actual API calls."""

    def test_parse_clean_json(self):
        """_parse_response handles clean JSON array."""
        raw = '[{"name": "Product A", "list_price": 10.0}]'
        result = ai_service._parse_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Product A")
        print("  OK: Clean JSON parsed")

    def test_parse_markdown_wrapped_json(self):
        """_parse_response handles JSON wrapped in markdown code blocks."""
        raw = '```json\n[{"name": "Product A", "list_price": 10.0}]\n```'
        result = ai_service._parse_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Product A")
        print("  OK: Markdown-wrapped JSON parsed")

    def test_parse_multiple_products(self):
        """_parse_response handles multiple products."""
        raw = json.dumps([
            {"name": "Product A", "default_code": "SKU1", "list_price": 10.0,
             "categ_id": "Cat / Sub", "page_number": 1},
            {"name": "Product B", "default_code": None, "list_price": None,
             "categ_id": "Cat", "page_number": 1},
            {"name": "Product C", "default_code": "SKU3", "list_price": 25.50,
             "categ_id": None, "page_number": 2},
        ])
        result = ai_service._parse_response(raw)
        self.assertEqual(len(result), 3)
        self.assertIsNone(result[1]["list_price"])
        self.assertEqual(result[2]["list_price"], 25.50)
        print("  OK: Multiple products parsed correctly")

    def test_parse_empty_array(self):
        """_parse_response handles empty array."""
        result = ai_service._parse_response("[]")
        self.assertEqual(result, [])
        print("  OK: Empty array parsed")

    def test_parse_invalid_json_raises(self):
        """_parse_response raises on invalid JSON."""
        with self.assertRaises(json.JSONDecodeError):
            ai_service._parse_response("this is not json")
        print("  OK: Invalid JSON raises JSONDecodeError")

    def test_extraction_prompt_content(self):
        """Extraction prompt contains all required Odoo fields."""
        prompt = ai_service.EXTRACTION_PROMPT
        for field in ["name", "default_code", "list_price", "categ_id", "description_sale"]:
            self.assertIn(field, prompt)
        self.assertIn("page_number", prompt)
        self.assertIn("brand", prompt)
        self.assertIn("unit", prompt)
        print("  OK: Prompt contains all required fields")


# =============================================================================
# Test: CSV Export Logic
# =============================================================================

class TestCsvExport(unittest.TestCase):
    """Test CSV generation logic (extracted from export wizard)."""

    ODOO_FIELDS = ["name", "default_code", "list_price", "categ_id", "description_sale"]

    def _generate_csv(self, products: list[dict], include_extra: bool = True) -> str:
        """Replicate the wizard's CSV generation logic."""
        output = io.StringIO()
        fieldnames = list(self.ODOO_FIELDS)
        if include_extra:
            fieldnames.extend(["brand", "unit"])

        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for p in products:
            row = {
                "name": p.get("name", ""),
                "default_code": p.get("default_code", ""),
                "list_price": str(p["list_price"]) if p.get("list_price") else "",
                "categ_id": p.get("categ_name", ""),
                "description_sale": p.get("description_sale", ""),
            }
            if include_extra:
                row["brand"] = p.get("brand", "")
                row["unit"] = p.get("unit", "")
            writer.writerow(row)

        return output.getvalue()

    def test_csv_header(self):
        """CSV has correct Odoo-compatible headers."""
        csv_str = self._generate_csv([])
        reader = csv.reader(io.StringIO(csv_str))
        header = next(reader)
        self.assertEqual(header[:5], self.ODOO_FIELDS)
        print(f"  OK: CSV headers = {header}")

    def test_csv_header_without_extras(self):
        """CSV without extra fields has only Odoo core fields."""
        csv_str = self._generate_csv([], include_extra=False)
        reader = csv.reader(io.StringIO(csv_str))
        header = next(reader)
        self.assertEqual(header, self.ODOO_FIELDS)
        print(f"  OK: CSV headers (no extras) = {header}")

    def test_csv_data_rows(self):
        """CSV data rows contain correct values."""
        products = [
            {
                "name": "Taladro 800W",
                "default_code": "SKU001",
                "list_price": 89.99,
                "categ_name": "Tools / Power Tools",
                "description_sale": "Powerful drill",
                "brand": "Bosch",
                "unit": "unit",
            },
            {
                "name": "Sierra Circular",
                "default_code": "",
                "list_price": None,
                "categ_name": "",
                "description_sale": "",
                "brand": "",
                "unit": "",
            },
        ]
        csv_str = self._generate_csv(products)
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Taladro 800W")
        self.assertEqual(rows[0]["default_code"], "SKU001")
        self.assertEqual(rows[0]["list_price"], "89.99")
        self.assertEqual(rows[0]["categ_id"], "Tools / Power Tools")
        self.assertEqual(rows[0]["brand"], "Bosch")

        # Product with missing data
        self.assertEqual(rows[1]["name"], "Sierra Circular")
        self.assertEqual(rows[1]["list_price"], "")
        print(f"  OK: CSV data - {len(rows)} rows with correct values")

    def test_csv_special_characters(self):
        """CSV handles special characters (commas, quotes)."""
        products = [
            {
                "name": 'Product with "quotes" and, commas',
                "default_code": "SKU-100",
                "list_price": 10.0,
                "categ_name": "Category / Sub, category",
                "description_sale": "Line1\nLine2",
            },
        ]
        csv_str = self._generate_csv(products, include_extra=False)
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        self.assertEqual(rows[0]["name"], 'Product with "quotes" and, commas')
        self.assertEqual(rows[0]["categ_id"], "Category / Sub, category")
        print("  OK: CSV handles special characters correctly")


# =============================================================================
# Test: Review Logic
# =============================================================================

class TestReviewLogic(unittest.TestCase):
    """Test the product review flagging logic (same as in catalog.action_process)."""

    def _check_review(self, raw: dict) -> tuple[bool, list[str]]:
        """Replicate the review logic from catalog.py action_process."""
        price = raw.get("list_price")
        if price is not None:
            try:
                price = float(price)
            except (ValueError, TypeError):
                price = 0.0

        needs_review = False
        review_reasons = []
        if not price or price <= 0:
            needs_review = True
            review_reasons.append("missing_price")
        if not raw.get("default_code"):
            needs_review = True
            review_reasons.append("missing_sku")
        return needs_review, review_reasons

    def test_valid_product(self):
        """Product with price and SKU is valid."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": "SKU1", "list_price": 10.0}
        )
        self.assertFalse(needs)
        self.assertEqual(reasons, [])
        print("  OK: Valid product (price + SKU) -> no review")

    def test_missing_price(self):
        """Product without price needs review."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": "SKU1", "list_price": None}
        )
        self.assertTrue(needs)
        self.assertIn("missing_price", reasons)
        print("  OK: Missing price -> needs review")

    def test_zero_price(self):
        """Product with price 0 needs review."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": "SKU1", "list_price": 0}
        )
        self.assertTrue(needs)
        self.assertIn("missing_price", reasons)
        print("  OK: Zero price -> needs review")

    def test_missing_sku(self):
        """Product without SKU needs review."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": None, "list_price": 10.0}
        )
        self.assertTrue(needs)
        self.assertIn("missing_sku", reasons)
        print("  OK: Missing SKU -> needs review")

    def test_missing_both(self):
        """Product missing both price and SKU has both reasons."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": "", "list_price": None}
        )
        self.assertTrue(needs)
        self.assertIn("missing_price", reasons)
        self.assertIn("missing_sku", reasons)
        print("  OK: Missing both -> two review reasons")

    def test_invalid_price_string(self):
        """Non-numeric price is treated as 0."""
        needs, reasons = self._check_review(
            {"name": "Test", "default_code": "SKU1", "list_price": "invalid"}
        )
        self.assertTrue(needs)
        self.assertIn("missing_price", reasons)
        print("  OK: Invalid price string -> needs review")


# =============================================================================
# Test: Full Pipeline (without AI call)
# =============================================================================

class TestFullPipeline(unittest.TestCase):
    """Test the full extraction pipeline with mocked AI response."""

    def test_pipeline_text_extraction(self):
        """Full pipeline: create PDF -> extract text -> validate products."""
        # 1. Create test PDF
        products_data = [
            ("SKU001", "Taladro Percutor 800W", 89.99, "Tools / Power Tools"),
            ("SKU002", "Sierra Circular 1200W", 129.50, "Tools / Saws"),
            ("", "Destornillador Manual", None, "Tools / Hand Tools"),
        ]
        pdf_path = create_test_pdf(products_data)

        try:
            # 2. Get PDF info
            info = pdf_service.get_pdf_info(pdf_path)
            self.assertEqual(info["total_pages"], 1)

            # 3. Extract text
            pages_text = pdf_service.extract_text_from_pdf(pdf_path)
            self.assertEqual(len(pages_text), 1)
            text = pages_text[0]
            self.assertIn("Taladro Percutor", text)
            self.assertIn("SKU001", text)

            # 4. Simulate AI response (what Claude would return)
            mock_ai_response = json.dumps([
                {
                    "name": "Taladro Percutor 800W",
                    "default_code": "SKU001",
                    "list_price": 89.99,
                    "categ_id": "Tools / Power Tools",
                    "description_sale": "800W power drill",
                    "brand": "Generic",
                    "unit": "unit",
                    "page_number": 1,
                },
                {
                    "name": "Sierra Circular 1200W",
                    "default_code": "SKU002",
                    "list_price": 129.50,
                    "categ_id": "Tools / Saws",
                    "description_sale": "1200W circular saw",
                    "brand": "Generic",
                    "unit": "unit",
                    "page_number": 1,
                },
                {
                    "name": "Destornillador Manual",
                    "default_code": None,
                    "list_price": None,
                    "categ_id": "Tools / Hand Tools",
                    "description_sale": "Manual screwdriver",
                    "brand": None,
                    "unit": "unit",
                    "page_number": 1,
                },
            ])

            # 5. Parse AI response
            parsed = ai_service._parse_response(mock_ai_response)
            self.assertEqual(len(parsed), 3)

            # 6. Validate review logic
            valid_count = 0
            review_count = 0
            for raw in parsed:
                price = raw.get("list_price")
                needs_review = False
                if not price or price <= 0:
                    needs_review = True
                if not raw.get("default_code"):
                    needs_review = True
                if needs_review:
                    review_count += 1
                else:
                    valid_count += 1

            self.assertEqual(valid_count, 2)
            self.assertEqual(review_count, 1)  # Destornillador has no price and no SKU

            print(
                f"  OK: Full pipeline - {len(parsed)} products, "
                f"{valid_count} valid, {review_count} need review"
            )

        finally:
            os.unlink(pdf_path)

    def test_pipeline_optimize_and_reextract(self):
        """Pipeline: create -> optimize -> extract text from optimized."""
        pdf_path = create_test_pdf()
        optimized_path = None

        try:
            # Optimize
            optimized_path = pdf_service.optimize_pdf(pdf_path)
            self.assertTrue(os.path.exists(optimized_path))

            # Extract text from optimized version
            pages_text = pdf_service.extract_text_from_pdf(optimized_path)
            self.assertEqual(len(pages_text), 1)
            self.assertIn("Taladro Percutor", pages_text[0])

            print(
                f"  OK: Optimize + re-extract - "
                f"original {os.path.getsize(pdf_path)}B, "
                f"optimized {os.path.getsize(optimized_path)}B, "
                f"text still readable"
            )

        finally:
            os.unlink(pdf_path)
            if optimized_path and os.path.exists(optimized_path):
                os.unlink(optimized_path)

    def test_pipeline_csv_roundtrip(self):
        """Pipeline: mock products -> CSV -> parse back -> verify."""
        products = [
            {"name": "Product A", "default_code": "A1", "list_price": 10.0,
             "categ_name": "Cat / SubA", "description_sale": "Desc A",
             "brand": "Brand1", "unit": "kg"},
            {"name": "Product B", "default_code": "B2", "list_price": 20.50,
             "categ_name": "Cat / SubB", "description_sale": "Desc B",
             "brand": "Brand2", "unit": "unit"},
        ]

        # Generate CSV
        output = io.StringIO()
        fieldnames = ["name", "default_code", "list_price", "categ_id", "description_sale", "brand", "unit"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for p in products:
            writer.writerow({
                "name": p["name"],
                "default_code": p["default_code"],
                "list_price": str(p["list_price"]),
                "categ_id": p["categ_name"],
                "description_sale": p["description_sale"],
                "brand": p["brand"],
                "unit": p["unit"],
            })

        # Parse back
        csv_content = output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "Product A")
        self.assertEqual(float(rows[0]["list_price"]), 10.0)
        self.assertEqual(rows[1]["categ_id"], "Cat / SubB")

        print(f"  OK: CSV roundtrip - {len(rows)} products preserved correctly")


# =============================================================================
# Test: AI Integration (optional, requires API key)
# =============================================================================

class TestAiIntegration(unittest.TestCase):
    """Test actual AI extraction. Only runs with --with-ai flag."""

    @unittest.skipUnless(
        os.getenv("RUN_AI_TESTS"), "Skipped: set RUN_AI_TESTS=1 or use --with-ai"
    )
    def test_ai_text_extraction(self):
        """AI extracts products from PDF text content."""
        pdf_path = create_test_pdf()
        try:
            pages_text = pdf_service.extract_text_from_pdf(pdf_path)
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.assertTrue(api_key, "ANTHROPIC_API_KEY is required")

            products = ai_service.extract_products(api_key, pages_text=pages_text)
            self.assertGreater(len(products), 0)

            # Check that at least some known products were found
            names = [p.get("name", "").lower() for p in products]
            found_taladro = any("taladro" in n for n in names)
            found_sierra = any("sierra" in n for n in names)
            self.assertTrue(found_taladro, "Should find 'Taladro' product")
            self.assertTrue(found_sierra, "Should find 'Sierra' product")

            # Check structure
            for p in products:
                self.assertIn("name", p)
                self.assertTrue(p["name"])

            print(f"  OK: AI text extraction - {len(products)} products found")
            for p in products:
                price = p.get('list_price')
                price_str = f"${price:.2f}" if price else "N/A"
                print(f"      - {p.get('name', '?')} [{p.get('default_code', '-')}] {price_str}")

        finally:
            os.unlink(pdf_path)

    @unittest.skipUnless(
        os.getenv("RUN_AI_TESTS"), "Skipped: set RUN_AI_TESTS=1 or use --with-ai"
    )
    def test_ai_vision_extraction(self):
        """AI extracts products from PDF page images."""
        pdf_path = create_test_pdf()
        try:
            page_images = pdf_service.extract_pages_as_images(pdf_path)
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.assertTrue(api_key, "ANTHROPIC_API_KEY is required")

            products = ai_service.extract_products(api_key, page_images=page_images)
            self.assertGreater(len(products), 0)

            print(f"  OK: AI vision extraction - {len(products)} products found")
            for p in products:
                price = p.get('list_price')
                price_str = f"${price:.2f}" if price else "N/A"
                print(f"      - {p.get('name', '?')} [{p.get('default_code', '-')}] {price_str}")

        finally:
            os.unlink(pdf_path)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run PDF Catalog Extractor tests")
    parser.add_argument("--with-ai", action="store_true", help="Run AI integration tests (requires ANTHROPIC_API_KEY)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.with_ai:
        os.environ["RUN_AI_TESTS"] = "1"
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("ERROR: --with-ai requires ANTHROPIC_API_KEY environment variable")
            sys.exit(1)

    print("=" * 65)
    print("  PDF CATALOG EXTRACTOR - MODULE TESTS")
    print("=" * 65)

    # Collect test suites
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestPdfService))
    suite.addTests(loader.loadTestsFromTestCase(TestAiServiceParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestCsvExport))
    suite.addTests(loader.loadTestsFromTestCase(TestReviewLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestFullPipeline))
    suite.addTests(loader.loadTestsFromTestCase(TestAiIntegration))

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    print("\n" + "=" * 65)
    if result.wasSuccessful():
        print("  ALL TESTS PASSED")
    else:
        print(f"  FAILURES: {len(result.failures)}  ERRORS: {len(result.errors)}")
    print("=" * 65)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
