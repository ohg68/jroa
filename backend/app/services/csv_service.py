import csv
import io
from app.models import Product


ODOO_FIELDS = ["name", "default_code", "list_price", "categ_id", "description_sale"]


def products_to_csv(products: list[Product], include_extra_fields: bool = True) -> str:
    """Convert products to CSV string compatible with Odoo import."""
    output = io.StringIO()

    fields = list(ODOO_FIELDS)
    if include_extra_fields:
        fields.extend(["brand", "unit"])

    writer = csv.DictWriter(output, fieldnames=fields, quoting=csv.QUOTE_ALL)
    writer.writeheader()

    for product in products:
        row = {
            "name": product.name or "",
            "default_code": product.default_code or "",
            "list_price": str(product.list_price) if product.list_price is not None else "",
            "categ_id": product.categ_id or "",
            "description_sale": product.description_sale or "",
        }
        if include_extra_fields:
            row["brand"] = product.brand or ""
            row["unit"] = product.unit or ""
        writer.writerow(row)

    return output.getvalue()
