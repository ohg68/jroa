from odoo import api, fields, models, _


class PdfCatalogProduct(models.Model):
    _name = "pdf.catalog.product"
    _description = "Extracted Product from PDF Catalog"
    _order = "page_number, id"

    catalog_id = fields.Many2one(
        "pdf.catalog",
        string="Catalog",
        required=True,
        ondelete="cascade",
        index=True,
    )
    catalog_state = fields.Selection(
        related="catalog_id.state",
        string="Catalog Status",
        store=True,
    )

    # Odoo-compatible fields
    name = fields.Char(string="Product Name", required=True)
    default_code = fields.Char(string="Internal Reference / SKU")
    list_price = fields.Float(string="Sales Price", digits=(12, 2))
    categ_name = fields.Char(
        string="Category",
        help="Category path in Odoo format: 'Parent / Child'",
    )
    description_sale = fields.Text(string="Sales Description")

    # Extra extracted fields
    brand = fields.Char(string="Brand")
    unit = fields.Char(string="Unit of Measure")
    page_number = fields.Integer(string="Page")

    # Validation
    needs_review = fields.Boolean(
        string="Needs Review",
        default=False,
        index=True,
    )
    review_reason = fields.Char(string="Review Reason")

    # Import tracking
    imported = fields.Boolean(string="Imported to Odoo", default=False, index=True)
    odoo_product_id = fields.Many2one(
        "product.template",
        string="Odoo Product",
        readonly=True,
    )

    # UI colors
    color = fields.Integer(compute="_compute_color")

    @api.depends("needs_review", "imported")
    def _compute_color(self):
        for record in self:
            if record.imported:
                record.color = 10  # green
            elif record.needs_review:
                record.color = 3  # yellow
            else:
                record.color = 0  # default

    @api.onchange("list_price", "default_code")
    def _onchange_validate(self):
        """Recalculate review status when key fields change."""
        reasons = []
        if not self.list_price or self.list_price <= 0:
            reasons.append("missing_price")
        if not self.default_code:
            reasons.append("missing_sku")
        self.needs_review = bool(reasons)
        self.review_reason = ", ".join(reasons) if reasons else False

    def action_mark_valid(self):
        """Manually mark as valid (dismiss review flag)."""
        self.write({"needs_review": False, "review_reason": False})

    def action_mark_review(self):
        """Manually flag for review."""
        self.write({"needs_review": True, "review_reason": "manual_review"})

    def action_import_single(self):
        """Import this single product into Odoo."""
        self.ensure_one()
        if self.imported:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Already Imported"),
                    "message": _("This product was already imported."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        vals = {
            "name": self.name,
            "default_code": self.default_code or False,
            "list_price": self.list_price,
            "description_sale": self.description_sale or False,
            "type": "consu",
        }

        if self.categ_name:
            categ = self.catalog_id._find_or_create_category(self.categ_name)
            if categ:
                vals["categ_id"] = categ.id

        product = self.env["product.template"].create(vals)
        self.write({"imported": True, "odoo_product_id": product.id})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Product Created"),
                "message": _("'%s' has been created in Odoo.", self.name),
                "type": "success",
                "sticky": False,
            },
        }

    def action_open_odoo_product(self):
        """Open the linked Odoo product."""
        self.ensure_one()
        if not self.odoo_product_id:
            return
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "res_id": self.odoo_product_id.id,
            "view_mode": "form",
        }
