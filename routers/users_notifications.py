from typing import Optional
from datetime import datetime
from io import BytesIO
import secrets
import string
import urllib.parse
import base64

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from configs.database import get_db
from models.users import Users
from models.users_notifications import UsersNotifications
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

router = APIRouter(prefix="/users_notifications", tags=["UserNotifications"])


class UsersNotificationsOut(BaseModel):
    id: int
    users_id: Optional[int]
    message_type: Optional[str]
    message_title: Optional[str]
    message_description: Optional[str]
    message_link: Optional[str]
    status: Optional[str]
    read_at: Optional[datetime]
    message_alert_at: Optional[datetime]
    message_alert_expired: Optional[datetime]
    users_fullname: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class UsersNotificationsCreate(BaseModel):
    message_type: Optional[str] = "info"
    message_title: str = Field(..., min_length=1, max_length=255)
    message_description: Optional[str] = None
    message_link: Optional[str] = None
    message_json: Optional[str] = None
    message_alert_at: Optional[datetime] = None
    message_alert_expired: Optional[datetime] = None
    users_id: Optional[int] = None
    code: Optional[str] = None
    seq: Optional[int] = None


class UsersNotificationsUpdate(BaseModel):
    message_title: Optional[str] = None
    message_description: Optional[str] = None
    message_link: Optional[str] = None
    message_json: Optional[str] = None
    message_alert_at: Optional[datetime] = None
    message_alert_expired: Optional[datetime] = None
    status: Optional[str] = None


def generate_notification_code() -> str:
    timestamp = datetime.now().strftime("%y%m")
    random_part = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"N{timestamp}-{random_part}"


def _get_notif_query(db: Session):
    return (
        db.query(UsersNotifications)
        .filter(UsersNotifications.deleted_at == None)
        .order_by(UsersNotifications.id.desc())
    )


def _set_cell_border(cell, border_color: str = "CCCCCC") -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for side in ("top", "left", "bottom", "right"):
        border_el = OxmlElement(f"w:{side}")
        border_el.set(qn("w:val"), "single")
        border_el.set(qn("w:sz"), "4")
        border_el.set(qn("w:color"), border_color)
        tcPr.append(border_el)


def _to_base64_response(buffer: BytesIO, filename: str, content_type: str) -> JSONResponse:
    buffer.seek(0)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return JSONResponse({
        "filename": filename,
        "content_type": content_type,
        "base64": b64,
        "size": len(buffer.getvalue()),
    })


@router.get("/", response_model=list[UsersNotificationsOut])
def list_notifications(
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        query = _get_notif_query(db)
        if page is not None and limit is not None:
            query = query.offset((page - 1) * limit).limit(limit)
        return query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/pdf")
def export_notifications_pdf(db: Session = Depends(get_db)):
    try:
        notifications = _get_notif_query(db).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, spaceAfter=12)

        story = [
            Paragraph("Notifications Report", title_style),
            Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
            Spacer(1, 12),
        ]

        headers = ["ID", "Type", "Title", "Description", "Status", "User", "Alert At", "Created At"]
        data = [headers] + [
            [
                str(n.id),
                n.message_type or "-",
                (n.message_title or "-")[:40],
                (n.message_description or "-")[:45],
                n.status or "-",
                n.users_fullname or "-",
                n.message_alert_at.strftime("%Y-%m-%d") if n.message_alert_at else "-",
                n.created_at.strftime("%Y-%m-%d") if n.created_at else "-",
            ]
            for n in notifications
        ]

        col_widths = [18*mm, 20*mm, 55*mm, 60*mm, 22*mm, 40*mm, 30*mm, 28*mm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1,  0), colors.HexColor("#2E75B6")),
            ("TEXTCOLOR",      (0, 0), (-1,  0), colors.white),
            ("FONTNAME",       (0, 0), (-1,  0), "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1,  0), 9),
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

        filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        return _to_base64_response(buffer, filename, "application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/excel")
def export_notifications_excel(db: Session = Depends(get_db)):
    try:
        notifications = _get_notif_query(db).all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Notifications"

        header_font  = Font(name="Arial", bold=True, color="FFFFFF", size=11)
        header_fill  = PatternFill("solid", fgColor="2E75B6")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin         = Side(style="thin", color="CCCCCC")
        border       = Border(left=thin, right=thin, top=thin, bottom=thin)

        headers    = ["ID", "Type", "Title", "Description", "Status", "User", "Alert At", "Expired At", "Created At"]
        col_widths = [8, 12, 30, 35, 12, 22, 18, 18, 18]

        for col, (header, width) in enumerate(zip(headers, col_widths), start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
            ws.column_dimensions[get_column_letter(col)].width = width

        ws.row_dimensions[1].height = 22

        for row_idx, n in enumerate(notifications, start=2):
            row_data = [
                n.id,
                n.message_type or "",
                n.message_title or "",
                n.message_description or "",
                n.status or "",
                n.users_fullname or "",
                n.message_alert_at.strftime("%Y-%m-%d %H:%M")      if n.message_alert_at      else "",
                n.message_alert_expired.strftime("%Y-%m-%d %H:%M") if n.message_alert_expired else "",
                n.created_at.strftime("%Y-%m-%d %H:%M")            if n.created_at            else "",
            ]
            fill = PatternFill("solid", fgColor="EEF4FB" if row_idx % 2 == 0 else "FFFFFF")

            for col, value in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.font = Font(name="Arial", size=10)
                cell.alignment = Alignment(
                    horizontal="center" if col in (1, 2, 5, 7, 8, 9) else "left",
                    vertical="center",
                )
                cell.border = border
                cell.fill = fill

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}1"

        buffer = BytesIO()
        wb.save(buffer)

        filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return _to_base64_response(buffer, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/word")
def export_notifications_word(db: Session = Depends(get_db)):
    try:
        notifications = _get_notif_query(db).all()

        doc = Document()
        section = doc.sections[0]
        section.orientation = 1
        section.page_width  = Inches(11.69)
        section.page_height = Inches(8.27)
        section.left_margin = section.right_margin  = Inches(0.5)
        section.top_margin  = section.bottom_margin = Inches(0.5)

        title = doc.add_heading("Notifications Report", level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle = doc.add_paragraph(
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Total: {len(notifications)} records"
        )
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        headers       = ["ID", "Type", "Title", "Description", "Status", "User", "Alert At", "Created At"]
        col_widths_in = [0.35, 0.75, 2.2, 2.4, 0.75, 1.5, 1.1, 1.1]

        table = doc.add_table(rows=1, cols=len(headers))
        table.style     = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit   = False

        for i, width in enumerate(col_widths_in):
            for cell in table.columns[i].cells:
                cell.width = Inches(width)

        hdr_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(header)
            run.bold = True
            run.font.size = Pt(10)
            shading = OxmlElement("w:shd")
            shading.set(qn("w:fill"), "2E75B6")
            hdr_cells[i]._tc.get_or_add_tcPr().append(shading)
            _set_cell_border(hdr_cells[i])

        center_cols = {0, 1, 4, 6, 7}
        for n in notifications:
            row_cells  = table.add_row().cells
            fill_color = "EEF4FB" if len(table.rows) % 2 == 0 else "FFFFFF"
            row_data   = [
                str(n.id),
                n.message_type or "-",
                (n.message_title or "-")[:50],
                (n.message_description or "-")[:55],
                n.status or "-",
                n.users_fullname or "-",
                n.message_alert_at.strftime("%Y-%m-%d") if n.message_alert_at else "-",
                n.created_at.strftime("%Y-%m-%d") if n.created_at else "-",
            ]
            for i, text in enumerate(row_data):
                p = row_cells[i].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in center_cols else WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(text)
                run.font.size = Pt(9)
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), fill_color)
                row_cells[i]._tc.get_or_add_tcPr().append(shading)
                _set_cell_border(row_cells[i])

        buffer = BytesIO()
        doc.save(buffer)

        filename = f"notifications_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        return _to_base64_response(buffer, filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{notif_id}", response_model=UsersNotificationsOut)
def get_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        notif = db.query(UsersNotifications).filter(
            UsersNotifications.id == notif_id,
            UsersNotifications.deleted_at == None,
        ).first()
        if not notif:
            raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")
        return notif
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=UsersNotificationsOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    body: UsersNotificationsCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        target_id = body.users_id or current_user.id
        target_user = (
            current_user
            if target_id == current_user.id
            else db.query(Users).filter(Users.id == target_id).first()
        )
        if not target_user and body.users_id is not None:
            raise HTTPException(status_code=400, detail="ไม่พบผู้ใช้เป้าหมาย (users_id ไม่ถูกต้อง)")

        notif = UsersNotifications(
            code=body.code or generate_notification_code(),
            name=body.message_title,
            description=body.message_description or "แจ้งเตือนจากระบบ",
            status="active",
            status_name="Active",
            seq=body.seq,
            users_id=target_id,
            users_fullname=target_user.name if target_user else None,
            message_type=body.message_type,
            message_title=body.message_title,
            message_description=body.message_description,
            message_link=body.message_link,
            message_json=body.message_json,
            message_alert_at=body.message_alert_at,
            message_alert_expired=body.message_alert_expired,
            created_at=datetime.utcnow(),
            created_by=current_user.id,
            created_by_name=current_user.name,
            updated_at=datetime.utcnow(),
        )
        db.add(notif)
        db.flush()
        db.refresh(notif)
        return notif
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{notif_id}", response_model=UsersNotificationsOut)
def update_notification_full(
    notif_id: int,
    body: UsersNotificationsCreate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        notif = db.query(UsersNotifications).filter(
            UsersNotifications.id == notif_id,
            UsersNotifications.deleted_at == None,
        ).first()
        if not notif:
            raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")

        notif.code                  = body.code or notif.code
        notif.seq                   = body.seq if body.seq is not None else notif.seq
        notif.message_type          = body.message_type or notif.message_type
        notif.message_title         = body.message_title
        notif.message_description   = body.message_description
        notif.message_link          = body.message_link
        notif.message_json          = body.message_json
        notif.message_alert_at      = body.message_alert_at
        notif.message_alert_expired = body.message_alert_expired
        notif.status                = "active"
        notif.updated_at            = datetime.utcnow()
        notif.updated_by            = current_user.id
        notif.updated_by_name       = current_user.name

        db.flush()
        db.refresh(notif)
        return notif
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{notif_id}", response_model=UsersNotificationsOut)
def patch_notification(
    notif_id: int,
    body: UsersNotificationsUpdate,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        notif = db.query(UsersNotifications).filter(
            UsersNotifications.id == notif_id,
            UsersNotifications.deleted_at == None,
        ).first()
        if not notif:
            raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")

        updated = False
        if body.message_title is not None:
            notif.message_title = body.message_title; updated = True
        if body.message_description is not None:
            notif.message_description = body.message_description; updated = True
        if body.message_link is not None:
            notif.message_link = body.message_link; updated = True
        if body.message_json is not None:
            notif.message_json = body.message_json; updated = True
        if body.status is not None:
            notif.status = body.status; updated = True
        if body.message_alert_at is not None:
            notif.message_alert_at = body.message_alert_at; updated = True
        if body.message_alert_expired is not None:
            notif.message_alert_expired = body.message_alert_expired; updated = True

        if updated:
            notif.updated_at      = datetime.utcnow()
            notif.updated_by      = current_user.id
            notif.updated_by_name = current_user.name
            db.flush()
            db.refresh(notif)

        return notif
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notif_id}", status_code=status.HTTP_200_OK)
def delete_notification(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(AuthService.get_current_user),
):
    try:
        notif = db.query(UsersNotifications).filter(
            UsersNotifications.id == notif_id,
            UsersNotifications.deleted_at == None,
        ).first()
        if not notif:
            raise HTTPException(status_code=404, detail=f"ไม่พบ notification id={notif_id}")

        db.delete(notif)
        db.flush()
        return {"message": f"ลบ notification id={notif_id} สำเร็จ"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))