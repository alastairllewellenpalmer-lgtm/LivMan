"""
Email sending functions for notifications.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from core.models import BusinessSettings

logger = logging.getLogger(__name__)


def send_invoice_email(invoice):
    """Send invoice email with PDF attachment."""
    from invoicing.pdf import generate_invoice_pdf

    if not invoice.owner.email:
        return False

    business = BusinessSettings.get_settings()

    subject = f"Invoice {invoice.invoice_number} from {business.business_name}"

    context = {
        'invoice': invoice,
        'business': business,
    }

    html_content = render_to_string('notifications/email/invoice.html', context)

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.owner.email],
    )
    email.content_subtype = 'html'

    # Attach PDF
    pdf_file = generate_invoice_pdf(invoice)
    email.attach(
        f"{invoice.invoice_number}.pdf",
        pdf_file.read(),
        'application/pdf'
    )

    try:
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_vaccination_reminder(vaccination):
    """Send vaccination due reminder email."""
    horse = vaccination.horse
    owner = horse.current_owner

    if not owner or not owner.email:
        return False

    business = BusinessSettings.get_settings()

    subject = f"Vaccination Due: {horse.name} - {vaccination.vaccination_type.name}"

    context = {
        'vaccination': vaccination,
        'horse': horse,
        'owner': owner,
        'business': business,
    }

    html_content = render_to_string('notifications/email/vaccination_reminder.html', context)

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[owner.email],
    )
    email.content_subtype = 'html'

    try:
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_farrier_reminder(farrier_visit):
    """Send farrier due reminder email."""
    horse = farrier_visit.horse
    owner = horse.current_owner

    if not owner or not owner.email:
        return False

    business = BusinessSettings.get_settings()

    subject = f"Farrier Due: {horse.name}"

    context = {
        'visit': farrier_visit,
        'horse': horse,
        'owner': owner,
        'business': business,
    }

    html_content = render_to_string('notifications/email/farrier_reminder.html', context)

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[owner.email],
    )
    email.content_subtype = 'html'

    try:
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_ehv_reminder(breeding_record, month_number):
    """Send EHV vaccination reminder for a pregnant mare."""
    mare = breeding_record.mare
    owner = mare.current_owner

    if not owner or not owner.email:
        return False

    business = BusinessSettings.get_settings()

    ehv_dates = breeding_record.ehv_vaccination_dates
    due_date = ehv_dates.get(month_number)

    subject = f"EHV Vaccination Due: {mare.name} - Month {month_number}"

    context = {
        'breeding_record': breeding_record,
        'mare': mare,
        'owner': owner,
        'business': business,
        'month_number': month_number,
        'due_date': due_date,
    }

    html_content = render_to_string('notifications/email/ehv_reminder.html', context)

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[owner.email],
    )
    email.content_subtype = 'html'

    try:
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send EHV reminder email: {e}")
        return False


def send_invoice_overdue_reminder(invoice):
    """Send overdue invoice reminder email."""
    if not invoice.owner.email:
        return False

    business = BusinessSettings.get_settings()

    subject = f"Payment Reminder: Invoice {invoice.invoice_number}"

    context = {
        'invoice': invoice,
        'business': business,
    }

    html_content = render_to_string('notifications/email/invoice_overdue.html', context)

    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.owner.email],
    )
    email.content_subtype = 'html'

    try:
        email.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
