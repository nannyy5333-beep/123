
import io, csv
from typing import List, Dict, Any, Iterable
import pandas as pd

def to_csv_bytes(rows: Iterable[Dict[str, Any]]) -> bytes:
    rows = list(rows)
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue().encode("utf-8")

def to_xlsx_bytes(rows: Iterable[Dict[str, Any]]) -> bytes:
    rows = list(rows)
    if not rows:
        # create empty sheet
        df = pd.DataFrame([])
    else:
        df = pd.DataFrame(rows)
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="data")
    return bio.getvalue()


def export_all_zip(datasets: dict) -> bytes:
    """
    datasets: {"products_csv":[{...},...], "orders_xlsx":[{...},...]}
    Names ending with _csv / _xlsx decide the format per sheet/file.
    Returns zip bytes containing files for each dataset.
    """
    import io, zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        for name, rows in datasets.items():
            if name.endswith("_csv"):
                data = to_csv_bytes(rows)
                z.writestr(name.replace("_csv","") + ".csv", data)
            elif name.endswith("_xlsx"):
                data = to_xlsx_bytes(rows)
                z.writestr(name.replace("_xlsx","") + ".xlsx", data)
            else:
                # default CSV
                data = to_csv_bytes(rows)
                z.writestr(name + ".csv", data)
    return bio.getvalue()


def pricelist_pdf_bytes(rows):
    """
    Generate simple A4 PDF price list with columns: Name | Category | Subcategory | Price | Stock
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Прайс-лист", styles["Title"]))
    story.append(Spacer(1, 6*mm))

    table_data = [["Товар", "Категория", "Подкатегория", "Цена", "Остаток"]]
    for r in rows:
        table_data.append([
            str(r.get("name") or ""),
            str(r.get("category") or ""),
            str(r.get("subcategory_name") or ""),
            f'{float(r.get("price") or 0):.2f}',
            str(r.get("stock") or 0)
        ])

    tbl = Table(table_data, repeatRows=1, colWidths=[70*mm, 30*mm, 40*mm, 20*mm, 20*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (-2,1), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey])
    ]))
    story.append(tbl)
    doc.build(story)
    return buf.getvalue()
