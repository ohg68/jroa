{
    "name": "PDF Catalog Extractor",
    "version": "19.0.1.0.0",
    "category": "Inventory/Products",
    "summary": "Extract products from PDF catalogs using AI and import them into Odoo",
    "description": """
PDF Catalog Extractor
=====================

Extracts product data from PDF catalogs using Claude AI (Anthropic)
and creates or updates products in Odoo.

Features:
- Upload PDF product catalogs
- AI-powered extraction (text + vision for scanned PDFs)
- Dashboard with processing metrics
- Editable extracted products before import
- Filter products needing review (missing price, SKU, etc.)
- Export extracted data to CSV (Odoo-compatible)
- Import validated products directly into Odoo
- PDF optimization (reduce file size)
- Reprocess catalogs
    """,
    "author": "PDF Catalog Extractor",
    "license": "LGPL-3",
    "depends": ["base", "product", "mail"],
    "data": [
        "security/security.xml",
#         "security/ir.model.access.csv",
        "data/sequences.xml",
        "wizards/upload_wizard_views.xml",
        "wizards/export_wizard_views.xml",
        "views/catalog_views.xml",
        "views/catalog_product_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "external_dependencies": {
        "python": ["anthropic", "PyMuPDF"],
    },
}
