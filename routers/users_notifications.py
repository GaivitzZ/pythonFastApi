import base64
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from io import BytesIO

from configs.database import get_db
from models.users_notifications import UsersNotifications
from models.users import Users
from configs.auth import AuthService

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

router = APIRouter(prefix="/users-notifications", tags=["UsersNotifications"])


# ====================== SCHEMAS ======================

class NotificationOut(BaseModel):
    id: int
    code: Optional[str]
    name: Optional[str]
    description: Optional[str]
    status: Optional[str]
    message_type: Optional[str]
    message_title: Optional[str]
    message_description: Optional[str]
    message_link: Optional[str]
    users_id: Optional[int]
    users_fullname: Optional[str]
    read_at: Optional[datetime]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "active"
    message_type: Optional[str] = None
    message_title: Optional[str] = None
    message_description: Optional[str] = None
    message_link: Optional[str] = None
    users_id: Optional[int] = None
    message_alert_at: Optional[datetime] = None
    message_alert_expired: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    message_title: Optional[str] = None
    message_description: Optional[str] = None
    message_link: Optional[str] = None
    read_at: Optional[datetime] = None


# ====================== HELPERS ======================

def _attachment_header(filename: str) -> str:
    encoded = urllib.parse.quote(filename)
    return f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded}'


def set_cell_border(cell, border_color: str = "CCCCCC") -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for side in ("top", "left", "bottom", "right"):
        border_el = OxmlElement(f"w:{side}")
        border_el.set(qn("w:val"), "single")
        border_el.set(qn("w:sz"), "4")
        border_el.set(qn("w:color"), border_color)
        tcPr.append(border_el)


async def _get_notifications(db: AsyncSession):
    result = await db.execute(
        select(UsersNotifications)
        .where(UsersNotifications.deleted_at == None)
        .order_by(UsersNotifications.id.desc())
    )
    return result.scalars().all()


# ====================== EXPORTS ======================
# NOTE: export routes MUST be declared before /{noti_id} to avoid path conflicts

@router.get("/export/pdf", summary="Export notifications เป็น PDF")
async def export_notifications_pdf(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    items = await _get_notifications(db)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm,  bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, spaceAfter=12)

    story = [
        Paragraph("Users Notifications Report", title_style),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 12),
    ]

    headers = ["ID", "Code", "Name", "Type", "Title", "Status", "User", "Read At", "Created At"]
    data = [headers]
    for n in items:
        data.append([
            str(n.id),
            n.code or "-",
            n.name or "-",
            n.message_type or "-",
            n.message_title or "-",
            n.status or "-",
            n.users_fullname or "-",
            n.read_at.strftime("%Y-%m-%d") if n.read_at else "-",
            n.created_at.strftime("%Y-%m-%d") if n.created_at else "-",
        ])

    col_widths = [15*mm, 25*mm, 45*mm, 25*mm, 55*mm, 20*mm, 40*mm, 28*mm, 28*mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#2E75B6")),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  9),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE",       (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF4FB")]),
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)

    raw = buffer.read()
    filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return {
        "filename":  filename,
        "mime_type": "application/pdf",
        "base64":    base64.b64encode(raw).decode(),
        "size":      len(raw),
    }


@router.get("/export/excel", summary="Export notifications เป็น Excel")
async def export_notifications_excel(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    items = await _get_notifications(db)

    wb = Workbook()
    ws = wb.active
    ws.title = "Notifications"

    header_font  = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill  = PatternFill("solid", fgColor="2E75B6")
    center_align = Alignment(horizontal="center", vertical="center")
    thin         = Side(style="thin", color="CCCCCC")
    border       = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers    = ["ID", "Code", "Name", "Type", "Title", "Description", "Status", "User", "Read At", "Created At"]
    col_widths = [8,    14,     28,     16,     28,      35,             12,       25,      18,        18]

    for col, (header, width) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = center_align
        cell.border    = border
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.row_dimensions[1].height = 22

    for row_idx, n in enumerate(items, start=2):
        row_data = [
            n.id,
            n.code or "",
            n.name or "",
            n.message_type or "",
            n.message_title or "",
            n.message_description or "",
            n.status or "",
            n.users_fullname or "",
            n.read_at.strftime("%Y-%m-%d %H:%M") if n.read_at else "",
            n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
        ]
        fill = PatternFill("solid", fgColor="EEF4FB" if row_idx % 2 == 0 else "FFFFFF")
        for col, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.font      = Font(name="Arial", size=10)
            cell.alignment = Alignment(
                horizontal="center" if col in (1, 7, 9, 10) else "left",
                vertical="center",
            )
            cell.border = border
            cell.fill   = fill

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    raw = buffer.read()
    filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return {
        "filename":  filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "base64":    base64.b64encode(raw).decode(),
        "size":      len(raw),
    }


@router.get("/export/word", summary="Export notifications เป็น Word")
async def export_notifications_word(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    items = await _get_notifications(db)

    doc = Document()
    section = doc.sections[0]
    section.orientation   = 1
    section.page_width    = Inches(11.69)
    section.page_height   = Inches(8.27)
    section.left_margin   = section.right_margin  = Inches(0.5)
    section.top_margin    = section.bottom_margin = Inches(0.5)

    title = doc.add_heading("Users Notifications Report", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Total: {len(items)} records"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph()

    headers       = ["ID", "Code", "Name", "Type", "Title", "Status", "User", "Read At", "Created At"]
    col_widths_in = [0.35, 0.8,    1.6,    0.9,    1.8,    0.7,      1.4,    1.1,        1.1]
    num_cols      = len(headers)

    table = doc.add_table(rows=1, cols=num_cols)
    table.style     = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit   = False

    for i, width in enumerate(col_widths_in):
        table.columns[i].width = Inches(width)

    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        p   = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(header)
        run.bold      = True
        run.font.size = Pt(10)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "2E75B6")
        hdr_cells[i]._tc.get_or_add_tcPr().append(shading)
        set_cell_border(hdr_cells[i])

    center_cols = {0, 5, 7, 8}
    for idx, n in enumerate(items):
        row_cells = table.add_row().cells
        row_data  = [
            str(n.id),
            n.code or "-",
            n.name or "-",
            n.message_type or "-",
            n.message_title or "-",
            n.status or "-",
            n.users_fullname or "-",
            n.read_at.strftime("%Y-%m-%d") if n.read_at else "-",
            n.created_at.strftime("%Y-%m-%d") if n.created_at else "-",
        ]
        fill_color = "EEF4FB" if (idx + 1) % 2 == 0 else "FFFFFF"
        for i, text in enumerate(row_data):
            p   = row_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in center_cols else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(text)
            run.font.size = Pt(9)
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), fill_color)
            row_cells[i]._tc.get_or_add_tcPr().append(shading)
            set_cell_border(row_cells[i])

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    raw = buffer.read()
    filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
    return {
        "filename":  filename,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "base64":    base64.b64encode(raw).decode(),
        "size":      len(raw),
    }


# ====================== CRUD ======================

@router.get("/", response_model=list[NotificationOut], summary="รายการ notifications")
async def list_notifications(
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    stmt = (
        select(UsersNotifications)
        .where(UsersNotifications.deleted_at == None)
        .order_by(UsersNotifications.id.desc())
    )
    if page is not None and limit is not None:
        stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{noti_id}", response_model=NotificationOut, summary="ดู notification ตาม ID")
async def get_notification(
    noti_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    result = await db.execute(
        select(UsersNotifications).where(
            UsersNotifications.id == noti_id,
            UsersNotifications.deleted_at == None,
        )
    )
    noti = result.scalar_one_or_none()
    if not noti:
        raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={noti_id}")
    return noti


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED, summary="สร้าง notification")
async def create_notification(
    body: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    noti = UsersNotifications(
        **body.model_dump(),
        created_by=current_user.id,
        created_by_name=current_user.name,
    )
    db.add(noti)
    await db.flush()
    await db.refresh(noti)
    return noti


@router.put("/{noti_id}", response_model=NotificationOut, summary="อัปเดต notification")
async def update_notification(
    noti_id: int,
    body: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    result = await db.execute(
        select(UsersNotifications).where(
            UsersNotifications.id == noti_id,
            UsersNotifications.deleted_at == None,
        )
    )
    noti = result.scalar_one_or_none()
    if not noti:
        raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={noti_id}")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(noti, field, value)

    noti.updated_by      = current_user.id
    noti.updated_by_name = current_user.name

    await db.flush()
    await db.refresh(noti)
    return noti


@router.delete("/{noti_id}", status_code=status.HTTP_200_OK, summary="ลบ notification (soft delete)")
async def delete_notification(
    noti_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    result = await db.execute(
        select(UsersNotifications).where(UsersNotifications.id == noti_id)
    )
    noti = result.scalar_one_or_none()
    if not noti:
        raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={noti_id}")

    noti.deleted_at      = datetime.utcnow()
    noti.deleted_by      = current_user.id
    noti.deleted_by_name = current_user.name

    await db.flush()
    return {"message": f"ลบ notification id={noti_id} สำเร็จ"}