"""
PDF generation for invoices.
"""

import io
from decimal import Decimal

from django.template.loader import render_to_string

from core.models import BusinessSettings


def generate_invoice_pdf(invoice):
    """Generate a PDF for an invoice using WeasyPrint."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        # Fallback if WeasyPrint not installed or missing system libraries (GTK/Pango on Windows)
        return generate_invoice_pdf_reportlab(invoice)

    settings = BusinessSettings.get_settings()

    html_content = render_to_string('invoicing/invoice_pdf.html', {
        'invoice': invoice,
        'settings': settings,
        'line_items': invoice.line_items.all().order_by('line_type', 'description'),
    })

    pdf_file = io.BytesIO()
    HTML(string=html_content).write_pdf(pdf_file)
    pdf_file.seek(0)

    return pdf_file


def generate_invoice_pdf_reportlab(invoice):
    """Generate a PDF using ReportLab as fallback."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    settings = BusinessSettings.get_settings()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=12
    )

    elements = []

    # Header
    elements.append(Paragraph(settings.business_name, title_style))
    if settings.address:
        elements.append(Paragraph(settings.address.replace('\n', '<br/>'), styles['Normal']))
    if settings.phone:
        elements.append(Paragraph(f"Tel: {settings.phone}", styles['Normal']))
    if settings.email:
        elements.append(Paragraph(f"Email: {settings.email}", styles['Normal']))

    elements.append(Spacer(1, 20*mm))

    # Invoice details
    elements.append(Paragraph(f"<b>INVOICE</b>", styles['Heading2']))
    elements.append(Paragraph(f"Invoice Number: {invoice.invoice_number}", styles['Normal']))
    elements.append(Paragraph(f"Date: {invoice.created_at.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Due Date: {invoice.due_date.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Period: {invoice.period_start.strftime('%d/%m/%Y')} - {invoice.period_end.strftime('%d/%m/%Y')}", styles['Normal']))

    elements.append(Spacer(1, 10*mm))

    # Bill to
    elements.append(Paragraph(f"<b>Bill To:</b>", styles['Normal']))
    elements.append(Paragraph(invoice.owner.name, styles['Normal']))
    if invoice.owner.address:
        elements.append(Paragraph(invoice.owner.address.replace('\n', '<br/>'), styles['Normal']))

    elements.append(Spacer(1, 10*mm))

    # Line items table
    table_data = [['Description', 'Qty', 'Unit Price', 'Total']]

    for item in invoice.line_items.all().order_by('line_type', 'description'):
        table_data.append([
            item.description[:50],
            f"{item.quantity:.2f}",
            f"\u00a3{item.unit_price:.2f}",
            f"\u00a3{item.line_total:.2f}"
        ])

    # Totals
    table_data.append(['', '', 'Subtotal:', f"\u00a3{invoice.subtotal:.2f}"])
    table_data.append(['', '', 'Total:', f"\u00a3{invoice.total:.2f}"])

    table = Table(table_data, colWidths=[100*mm, 20*mm, 25*mm, 25*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -3), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -3), 1, colors.black),
        ('LINEABOVE', (2, -2), (-1, -2), 1, colors.black),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 15*mm))

    # Payment details
    if settings.bank_details:
        elements.append(Paragraph("<b>Payment Details:</b>", styles['Normal']))
        elements.append(Paragraph(settings.bank_details.replace('\n', '<br/>'), styles['Normal']))

    # Notes
    if invoice.notes:
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("<b>Notes:</b>", styles['Normal']))
        elements.append(Paragraph(invoice.notes, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)

    return buffer
