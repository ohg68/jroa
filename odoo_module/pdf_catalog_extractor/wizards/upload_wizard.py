import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class CatalogUploadWizard(models.TransientModel):
    _name = "pdf.catalog.upload.wizard"
    _description = "Upload PDF Catalog Wizard"

    pdf_file = fields.Binary(string="PDF File", required=True)
    pdf_filename = fields.Char(string="Filename")
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
        string="Max Pages",
        default=0,
        help="0 = process all pages",
    )
    auto_process = fields.Boolean(
        string="Process Immediately",
        default=True,
    )

    def action_upload(self):
        """Create catalog and optionally start processing."""
        self.ensure_one()

        if not self.pdf_file:
            raise UserError(_("Please select a PDF file."))

        if not self.pdf_filename or not self.pdf_filename.lower().endswith(".pdf"):
            raise UserError(_("Only PDF files are accepted."))

        # Calculate file size
        raw = base64.b64decode(self.pdf_file)
        file_size_kb = round(len(raw) / 1024, 1)

        catalog = self.env["pdf.catalog"].create(
            {
                "name": self.pdf_filename,
                "pdf_file": self.pdf_file,
                "pdf_filename": self.pdf_filename,
                "file_size": file_size_kb,
                "extraction_mode": self.extraction_mode,
                "max_pages": self.max_pages,
                "state": "pending",
            }
        )

        if self.auto_process:
            catalog.action_process()

        return {
            "type": "ir.actions.act_window",
            "res_model": "pdf.catalog",
            "res_id": catalog.id,
            "view_mode": "form",
        }

    def action_upload_multiple(self):
        """Upload and return to list view."""
        self.action_upload()
        return {
            "type": "ir.actions.act_window",
            "res_model": "pdf.catalog",
            "view_mode": "list,form",
            "target": "current",
        }
