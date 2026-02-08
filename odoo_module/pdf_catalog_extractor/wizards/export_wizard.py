import base64
import csv
import io

from odoo import fields, models, _
from odoo.exceptions import UserError


ODOO_FIELDS = ["name", "default_code", "list_price", "categ_id", "description_sale"]


class CatalogExportWizard(models.TransientModel):
    _name = "pdf.catalog.export.wizard"
    _description = "Export Products to CSV"

    catalog_id = fields.Many2one(
        "pdf.catalog",
        string="Catalog",
        help="Leave empty to export all products",
    )
    filter_mode = fields.Selection(
        [
            ("all", "All Products"),
            ("valid", "Valid Only (no review needed)"),
            ("review", "Needs Review Only"),
            ("missing_price", "Missing Price Only"),
        ],
        string="Filter",
        default="all",
        required=True,
    )
    include_extra_fields = fields.Boolean(
        string="Include Extra Fields (brand, unit)",
        default=True,
    )
    export_file = fields.Binary(string="CSV File", readonly=True)
    export_filename = fields.Char(string="Filename", readonly=True)
    state = fields.Selection(
        [("config", "Configure"), ("done", "Done")],
        default="config",
    )

    def action_export(self):
        """Generate the CSV file."""
        self.ensure_one()

        domain = []
        if self.catalog_id:
            domain.append(("catalog_id", "=", self.catalog_id.id))

        if self.filter_mode == "valid":
            domain.append(("needs_review", "=", False))
        elif self.filter_mode == "review":
            domain.append(("needs_review", "=", True))
        elif self.filter_mode == "missing_price":
            domain.extend(["|", ("list_price", "=", 0), ("list_price", "=", False)])

        products = self.env["pdf.catalog.product"].search(domain, order="id")

        if not products:
            raise UserError(_("No products match the selected filters."))

        # Build CSV
        output = io.StringIO()
        fieldnames = list(ODOO_FIELDS)
        if self.include_extra_fields:
            fieldnames.extend(["brand", "unit"])

        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for p in products:
            row = {
                "name": p.name or "",
                "default_code": p.default_code or "",
                "list_price": str(p.list_price) if p.list_price else "",
                "categ_id": p.categ_name or "",
                "description_sale": p.description_sale or "",
            }
            if self.include_extra_fields:
                row["brand"] = p.brand or ""
                row["unit"] = p.unit or ""
            writer.writerow(row)

        csv_content = output.getvalue()
        csv_bytes = csv_content.encode("utf-8")

        if self.catalog_id:
            fname = self.catalog_id.name.replace(".pdf", "").replace(" ", "_")
            filename = f"{fname}_odoo.csv"
        else:
            filename = "all_products_odoo.csv"

        self.write(
            {
                "export_file": base64.b64encode(csv_bytes),
                "export_filename": filename,
                "state": "done",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
