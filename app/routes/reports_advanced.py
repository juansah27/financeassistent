"""
Advanced reports with PDF export
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from app.db import session, models, crud, crud_extended
from app.auth import auth

router = APIRouter()
from app.templates_utils import create_templates
templates = create_templates("app/templates")

@router.get("/reports/advanced", response_class=HTMLResponse)
async def advanced_reports_page(
    request: Request,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    # Get yearly summary
    now = datetime.now()
    yearly_stats = {}
    for month in range(1, 13):
        stats = crud.get_monthly_stats(db, current_user.id, now.year, month)
        yearly_stats[month] = stats
    
    return templates.TemplateResponse(
        "reports_advanced.html",
        {
            "request": request,
            "user": current_user,
            "yearly_stats": yearly_stats,
            "year": now.year
        }
    )

@router.get("/reports/pdf")
async def export_pdf_report(
    year: int = None,
    db: Session = Depends(session.get_db),
    current_user: models.User = Depends(auth.get_current_user_cookie)
):
    if year is None:
        year = datetime.now().year
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f"Laporan Keuangan Tahun {year}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Summary table
    monthly_data = [['Bulan', 'Pemasukan', 'Pengeluaran', 'Saldo']]
    total_income = 0
    total_expenses = 0
    
    for month in range(1, 13):
        stats = crud.get_monthly_stats(db, current_user.id, year, month)
        month_name = datetime(year, month, 1).strftime("%B")
        monthly_data.append([
            month_name,
            f"Rp {stats['income']:,.0f}",
            f"Rp {stats['expenses']:,.0f}",
            f"Rp {stats['balance']:,.0f}"
        ])
        total_income += stats['income']
        total_expenses += stats['expenses']
    
    monthly_data.append([
        'TOTAL',
        f"Rp {total_income:,.0f}",
        f"Rp {total_expenses:,.0f}",
        f"Rp {total_income - total_expenses:,.0f}"
    ])
    
    table = Table(monthly_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{year}.pdf"}
    )

