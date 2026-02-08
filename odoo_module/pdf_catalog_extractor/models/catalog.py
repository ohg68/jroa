import base64
import logging
import os
import tempfile

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PdfCatalog(models.Model):
    _name = "pdf.catalog"
    _description = "PDF Product Catalog"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Filename",
        required=True,
        tracking=True,
    )
    pdf_file = fields.Binary(
        string="PDF File",
        attachment=True,
        required=True,
    )
    pdf_filename = fields.Char(string="PDF Filename")
    optimized_file = fields.Binary(
        string="Optimized PDF",
        attachment=True,
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("processed", "Processed"),
            ("error", "Error"),
        ],
        string="Status",
        default="pending",
        tracking=True,
        required=True,
    )
    total_pages = fields.Integer(string="Total Pages", readonly=True)
    file_size = fields.Float(string="File Size (KB)", readonly=True)
    optimized_size = fields.Float(string="Optimized Size (KB)", readonly=True)
    error_message = fields.Text(string="Error Message", readonly=True)
    processed_date = fields.Datetime(string="Processed Date", readonly=True)

    # AI config
    extraction_mode = fields.Selection(
        [
            ("auto", "Auto (text, fallback to vision)"),
            ("text", "Text Only"),
            ("vision", "Vision Only"),
        ],
        string="Extraction Mode",
        default="auto",
    )
    max_pages = fields.Integer(
        string="Max Pages to Process",
        default=0,
        help="0 = all pages",
    )

    # Product lines
    product_line_ids = fields.One2many(
        "pdf.catalog.product",
        "catalog_id",
        string="Extracted Products",
    )

    # Computed metrics
    total_products = fields.Integer(
        compute="_compute_metrics",
        string="Total Products",
        store=True,
    )
    valid_products = fields.Integer(
        compute="_compute_metrics",
        string="Valid Products",
        store=True,
    )
    review_products = fields.Integer(
        compute="_compute_metrics",
        string="Need Review",
        store=True,
    )

    @api.depends("product_line_ids", "product_line_ids.needs_review")
    def _compute_metrics(self):
        for record in self:
            lines = record.product_line_ids
            record.total_products = len(lines)
            record.valid_products = len(lines.filtered(lambda l: not l.needs_review))
            record.review_products = len(lines.filtered(lambda l: l.needs_review))

    # -------------------------------------------------------------------------
    # PDF helpers
    # -------------------------------------------------------------------------

    def _get_pdf_as_tempfile(self, use_optimized=False):
        """Write the binary PDF to a temp file and return its path."""
        data = self.optimized_file if (use_optimized and self.optimized_file) else self.pdf_file
        if not data:
            raise UserError(_("No PDF file attached."))
        raw = base64.b64decode(data)
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.write(fd, raw)
        os.close(fd)
        return path

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_process(self):
        """Extract products from the PDF using AI."""
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_("Please upload a PDF file first."))

        self.write({"state": "processing", "error_message": False})

        try:
            from ..services import pdf_service, ai_service

            path = self._get_pdf_as_tempfile(use_optimized=True)

            try:
                # Get PDF info
                info = pdf_service.get_pdf_info(path)
                self.total_pages = info["total_pages"]
                self.file_size = round(info["file_size"] / 1024, 1)

                # Determine extraction method
                pages_text = pdf_service.extract_text_from_pdf(path)

                if self.max_pages > 0:
                    pages_text = pages_text[: self.max_pages]

                total_text = "".join(pages_text).strip()
                use_vision = self.extraction_mode == "vision"

                if self.extraction_mode == "auto" and len(total_text) < 50:
                    use_vision = True

                if self.extraction_mode == "text":
                    use_vision = False

                # Get API key from system parameters
                api_key = self.env["ir.config_parameter"].sudo().get_param(
                    "pdf_catalog_extractor.anthropic_api_key", ""
                )
                if not api_key:
                    raise UserError(
                        _(
                            "Anthropic API key not configured. "
                            "Go to Settings > Technical > Parameters > System Parameters "
                            'and set "pdf_catalog_extractor.anthropic_api_key".'
                        )
                    )

                # Extract
                if use_vision:
                    page_images = pdf_service.extract_pages_as_images(path)
                    if self.max_pages > 0:
                        page_images = page_images[: self.max_pages]
                    raw_products = ai_service.extract_products(
                        api_key, page_images=page_images
                    )
                else:
                    raw_products = ai_service.extract_products(
                        api_key, pages_text=pages_text
                    )

                # Delete existing lines and create new ones
                self.product_line_ids.unlink()

                line_vals = []
                for raw in raw_products:
                    name = (raw.get("name") or "").strip()
                    if not name:
                        continue

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

                    line_vals.append(
                        {
                            "catalog_id": self.id,
                            "name": name,
                            "default_code": raw.get("default_code") or False,
                            "list_price": price or 0.0,
                            "categ_name": raw.get("categ_id") or False,
                            "description_sale": raw.get("description_sale") or False,
                            "brand": raw.get("brand") or False,
                            "unit": raw.get("unit") or False,
                            "needs_review": needs_review,
                            "review_reason": ", ".join(review_reasons)
                            if review_reasons
                            else False,
                            "page_number": raw.get("page_number") or 0,
                        }
                    )

                self.env["pdf.catalog.product"].create(line_vals)

                self.write(
                    {
                        "state": "processed",
                        "processed_date": fields.Datetime.now(),
                        "error_message": False,
                    }
                )

                _logger.info(
                    "Catalog %s: extracted %d products", self.name, len(line_vals)
                )

            finally:
                os.unlink(path)

        except UserError:
            raise
        except Exception as e:
            self.write({"state": "error", "error_message": str(e)[:500]})
            _logger.exception("Catalog %s processing error", self.name)
            raise UserError(_("Processing failed: %s") % str(e))

    def action_reprocess(self):
        """Reprocess the catalog."""
        self.ensure_one()
        self.action_process()

    def action_optimize_pdf(self):
        """Optimize PDF to reduce file size."""
        self.ensure_one()
        if not self.pdf_file:
            raise UserError(_("No PDF file to optimize."))

        from ..services import pdf_service

        path = self._get_pdf_as_tempfile()
        try:
            optimized_path = pdf_service.optimize_pdf(path)
            with open(optimized_path, "rb") as f:
                optimized_data = base64.b64encode(f.read())
            optimized_kb = round(os.path.getsize(optimized_path) / 1024, 1)
            os.unlink(optimized_path)

            self.write(
                {
                    "optimized_file": optimized_data,
                    "optimized_size": optimized_kb,
                }
            )
        finally:
            os.unlink(path)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("PDF Optimized"),
                "message": _(
                    "Original: %(orig).1f KB → Optimized: %(opt).1f KB",
                    orig=self.file_size,
                    opt=self.optimized_size,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_import_to_odoo(self):
        """Import validated products into product.template."""
        self.ensure_one()
        valid_lines = self.product_line_ids.filtered(lambda l: not l.needs_review)
        if not valid_lines:
            raise UserError(_("No valid products to import."))

        created = self.env["product.template"]
        for line in valid_lines:
            if line.imported:
                continue

            vals = {
                "name": line.name,
                "default_code": line.default_code or False,
                "list_price": line.list_price,
                "description_sale": line.description_sale or False,
                "type": "consu",
            }

            # Try to find/create category
            if line.categ_name:
                categ = self._find_or_create_category(line.categ_name)
                if categ:
                    vals["categ_id"] = categ.id

            product = self.env["product.template"].create(vals)
            line.write({"imported": True, "odoo_product_id": product.id})
            created |= product

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Products Imported"),
                "message": _("%d products created in Odoo.", len(created)),
                "type": "success",
                "sticky": False,
            },
        }

    def _find_or_create_category(self, categ_path):
        """Find or create a product category from a path like 'Tools / Power Tools'."""
        if not categ_path:
            return False

        parts = [p.strip() for p in categ_path.split("/") if p.strip()]
        if not parts:
            return False

        parent = False
        Category = self.env["product.category"]

        for part in parts:
            domain = [("name", "=", part)]
            if parent:
                domain.append(("parent_id", "=", parent.id))
            else:
                domain.append(("parent_id", "=", False))

            categ = Category.search(domain, limit=1)
            if not categ:
                vals = {"name": part}
                if parent:
                    vals["parent_id"] = parent.id
                categ = Category.create(vals)
            parent = categ

        return parent

    def action_reset_to_pending(self):
        """Reset status back to pending."""
        self.write({"state": "pending", "error_message": False})

    def action_delete_products(self):
        """Delete all extracted products from this catalog."""
        self.product_line_ids.unlink()

    def action_view_products(self):
        """Open products list view for this catalog."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Products - %s", self.name),
            "res_model": "pdf.catalog.product",
            "view_mode": "list,form",
            "domain": [("catalog_id", "=", self.id)],
            "context": {"default_catalog_id": self.id},
        }

    def action_view_review_products(self):
        """Open products needing review."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Products Needing Review - %s", self.name),
            "res_model": "pdf.catalog.product",
            "view_mode": "list,form",
            "domain": [
                ("catalog_id", "=", self.id),
                ("needs_review", "=", True),
            ],
            "context": {"default_catalog_id": self.id},
        }
