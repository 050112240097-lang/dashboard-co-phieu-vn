# pdf_reporter.py - Báo cáo PDF theo phiên + Nhận định 1 giờ/lần
import os
import re
import glob
import time
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


SESSIONS = {
    'ATO': {
        'name': 'PHIÊN MỞ CỬA (ATO)',
        'time': '09:00 - 09:15',
        'desc': 'Khớp lệnh định kỳ mở cửa - Xác định giá mở cửa',
    },
    'SANG': {
        'name': 'PHIÊN SÁNG',
        'time': '09:15 - 11:30',
        'desc': 'Khớp lệnh liên tục phiên sáng',
    },
    'CHIEU': {
        'name': 'PHIÊN CHIỀU',
        'time': '13:00 - 14:30',
        'desc': 'Khớp lệnh liên tục phiên chiều',
    },
    'ATC': {
        'name': 'PHIÊN ĐÓNG CỬA (ATC)',
        'time': '14:30 - 14:45',
        'desc': 'Khớp lệnh định kỳ đóng cửa - Xác định giá đóng cửa',
    },
}

MARKET_REPORT_INTERVAL = 3600


def get_current_session():
    now = datetime.now().time()
    from datetime import time as dt_time
    if dt_time(9, 0) <= now < dt_time(9, 15):
        return 'ATO'
    elif dt_time(9, 15) <= now < dt_time(11, 30):
        return 'SANG'
    elif dt_time(13, 0) <= now < dt_time(14, 30):
        return 'CHIEU'
    elif dt_time(14, 30) <= now < dt_time(14, 45):
        return 'ATC'
    else:
        return 'DONG_CUA'


def clean_markdown(text):
    if not text:
        return ""
    lines = text.split('\n')
    result = []
    for line in lines:
        s = line.rstrip()
        s = re.sub(r'^#+\s*', '', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
        s = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', s)
        s = re.sub(r'^\s*-\s+', '• ', s)
        s = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', s)
        result.append(s)
    return '\n'.join(result)


def register_vietnamese_font():
    font_paths = [
        ('Arial', 'C:/Windows/Fonts/arial.ttf'),
        ('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'),
        ('Arial-Italic', 'C:/Windows/Fonts/ariali.ttf'),
        ('Arial-BoldItalic', 'C:/Windows/Fonts/arialbi.ttf'),
    ]
    for name, path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                pass
    registered = pdfmetrics.getRegisteredFontNames()
    return {
        'normal': 'Arial' if 'Arial' in registered else 'Helvetica',
        'bold': 'Arial-Bold' if 'Arial-Bold' in registered else 'Helvetica-Bold',
        'italic': 'Arial-Italic' if 'Arial-Italic' in registered else 'Helvetica-Oblique',
    }


def generate_session_report(stocks_data, session_code, ai_report=None):
    session = SESSIONS.get(session_code)
    if not session:
        return None

    fonts = register_vietnamese_font()
    fn, fb, fi = fonts['normal'], fonts['bold'], fonts['italic']

    today = datetime.now().strftime('%d%m%Y')
    filename = f"BaoCao_{session_code}_{today}.pdf"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontName=fb, fontSize=22, leading=26,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=6, alignment=1,
    )
    session_style = ParagraphStyle(
        'Session', parent=styles['Normal'],
        fontName=fb, fontSize=14, leading=18,
        textColor=colors.HexColor('#3B82F6'),
        spaceAfter=4, alignment=1,
    )
    time_style = ParagraphStyle(
        'Time', parent=styles['Normal'],
        fontName=fn, fontSize=11, leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=2, alignment=1,
    )
    h2_style = ParagraphStyle(
        'H2', parent=styles['Heading2'],
        fontName=fb, fontSize=14, leading=18,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=8, spaceBefore=14,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName=fn, fontSize=10, leading=15,
        spaceAfter=6,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontName=fi, fontSize=8, leading=10,
        textColor=colors.HexColor('#94A3B8'), alignment=1,
    )

    story = []

    story.append(Paragraph("BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG", title_style))
    story.append(Paragraph(session['name'], session_style))
    story.append(Paragraph(f"Thời gian: {session['time']}", time_style))
    story.append(Paragraph(session['desc'], time_style))
    story.append(Spacer(1, 0.2*cm))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor('#3B82F6'), spaceAfter=6))
    story.append(Paragraph(
        f"Ngày lập: {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}",
        body_style
    ))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("1. THỐNG KÊ THỊ TRƯỜNG", h2_style))

    up = sum(1 for s in stocks_data if s.get('pct', 0) > 0)
    down = sum(1 for s in stocks_data if s.get('pct', 0) < 0)
    ref = sum(1 for s in stocks_data if s.get('pct', 0) == 0)

    stats_data = [
        ['Chỉ số', 'Giá trị'],
        ['Tổng số mã niêm yết', f"{len(stocks_data):,}"],
        ['Số mã tăng giá', f"{up:,}"],
        ['Số mã giảm giá', f"{down:,}"],
        ['Số mã đứng giá', f"{ref:,}"],
    ]
    stats_table = Table(stats_data, colWidths=[8*cm, 6*cm])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), fb),
        ('FONTNAME', (0, 1), (-1, -1), fn),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("2. TOP 10 CỔ PHIẾU TĂNG/GIẢM MẠNH", h2_style))

    top_up = sorted([s for s in stocks_data if s.get('pct', 0) > 0],
                    key=lambda x: x['pct'], reverse=True)[:10]
    top_down = sorted([s for s in stocks_data if s.get('pct', 0) < 0],
                      key=lambda x: x['pct'])[:10]

    story.append(Paragraph(f"<b>Top 10 cổ phiếu tăng mạnh nhất</b>", body_style))
    up_data = [['STT', 'Mã', 'Giá (VNĐ)', '% Thay đổi', 'Khối lượng']]
    for i, s in enumerate(top_up, 1):
        up_data.append([
            str(i),
            s['symbol'],
            f"{s.get('close', 0):,.0f}",
            f"+{s.get('pct', 0):.2f}%",
            f"{s.get('volume', 0):,}",
        ])
    up_table = Table(up_data, colWidths=[1.2*cm, 2.5*cm, 3.5*cm, 3.2*cm, 3.5*cm])
    up_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), fb),
        ('FONTNAME', (0, 1), (-1, -1), fn),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ECFDF5')]),
    ]))
    story.append(up_table)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(f"<b>Top 10 cổ phiếu giảm mạnh nhất</b>", body_style))
    down_data = [['STT', 'Mã', 'Giá (VNĐ)', '% Thay đổi', 'Khối lượng']]
    for i, s in enumerate(top_down, 1):
        down_data.append([
            str(i),
            s['symbol'],
            f"{s.get('close', 0):,.0f}",
            f"{s.get('pct', 0):.2f}%",
            f"{s.get('volume', 0):,}",
        ])
    down_table = Table(down_data, colWidths=[1.2*cm, 2.5*cm, 3.5*cm, 3.2*cm, 3.5*cm])
    down_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EF4444')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), fb),
        ('FONTNAME', (0, 1), (-1, -1), fn),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF2F2')]),
    ]))
    story.append(down_table)

    if ai_report:
        story.append(PageBreak())
        story.append(Paragraph("3. NHẬN ĐỊNH THỊ TRƯỜNG (AI)", h2_style))
        cleaned = clean_markdown(ai_report)
        for para in cleaned.split('\n\n'):
            para = para.strip()
            if para:
                text_html = para.replace('\n', '<br/>')
                story.append(Paragraph(text_html, body_style))
                story.append(Spacer(1, 0.15*cm))

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#CBD5E1'), spaceAfter=6))
    story.append(Paragraph(
        f"Báo cáo được tạo tự động bởi Dashboard Cổ Phiếu Việt Nam",
        footer_style
    ))
    story.append(Paragraph(
        f"Phiên: {session['name']} - Ngày {datetime.now().strftime('%d/%m/%Y')}",
        footer_style
    ))

    try:
        doc.build(story)
        print(f"  [PDF] Da tao: {filename}")
        return filepath
    except Exception as e:
        print(f"  [PDF] Loi: {str(e)[:150]}")
        return None


def find_recent_market_report(hours=1):
    now = time.time()
    max_age = hours * 3600

    files = glob.glob('NhanDinhThiTruong_*.pdf')
    if not files:
        return None

    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    for f in files:
        age = now - os.path.getmtime(f)
        if age < max_age:
            return f
    return None


def generate_market_report(ai_report, stocks_data):
    if not ai_report:
        return None

    fonts = register_vietnamese_font()
    fn, fb, fi = fonts['normal'], fonts['bold'], fonts['italic']

    today = datetime.now().strftime('%d%m%Y_%H%M')
    filename = f"NhanDinhThiTruong_{today}.pdf"
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        fontName=fb, fontSize=24, leading=28,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=8, alignment=1,
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontName=fi, fontSize=11, leading=14,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=20, alignment=1,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName=fn, fontSize=11, leading=17,
        spaceAfter=8,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontName=fi, fontSize=8, leading=10,
        textColor=colors.HexColor('#94A3B8'), alignment=1,
    )

    story = []

    story.append(Paragraph("NHẬN ĐỊNH THỊ TRƯỜNG", title_style))
    story.append(HRFlowable(width="60%", thickness=1,
                             color=colors.HexColor('#3B82F6'), spaceAfter=8,
                             hAlign='CENTER'))
    story.append(Paragraph(
        f"Báo cáo phân tích thị trường chứng khoán Việt Nam",
        sub_style
    ))
    story.append(Paragraph(
        f"Ngày: {datetime.now().strftime('%d/%m/%Y - %H:%M:%S')}",
        sub_style
    ))

    up = sum(1 for s in stocks_data if s.get('pct', 0) > 0)
    down = sum(1 for s in stocks_data if s.get('pct', 0) < 0)
    ref = sum(1 for s in stocks_data if s.get('pct', 0) == 0)

    quick_stats = [
        ['Tăng giá', 'Giảm giá', 'Đứng giá', 'Tổng số mã'],
        [f"{up:,}", f"{down:,}", f"{ref:,}", f"{len(stocks_data):,}"],
    ]
    quick_table = Table(quick_stats, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
    quick_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), fb),
        ('FONTNAME', (0, 1), (-1, 1), fb),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, 1), 16),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#EF4444')),
        ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor('#F59E0B')),
        ('TEXTCOLOR', (3, 1), (3, 1), colors.HexColor('#1E40AF')),
    ]))
    story.append(quick_table)
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#CBD5E1'), spaceAfter=10))

    cleaned = clean_markdown(ai_report)
    for para in cleaned.split('\n\n'):
        para = para.strip()
        if para:
            text_html = para.replace('\n', '<br/>')
            story.append(Paragraph(text_html, body_style))
            story.append(Spacer(1, 0.15*cm))

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#CBD5E1'), spaceAfter=6))
    story.append(Paragraph(
        f"Báo cáo được tạo tự động bởi Dashboard Cổ Phiếu Việt Nam",
        footer_style
    ))
    story.append(Paragraph(
        f"Nguồn: AI (Groq - Llama 3.3) + Dữ liệu vnstock",
        footer_style
    ))

    try:
        doc.build(story)
        print(f"  [PDF] Da tao: {filename}")
        return filepath
    except Exception as e:
        print(f"  [PDF] Loi: {str(e)[:150]}")
        return None


def generate_all_reports(stocks_data, ai_report=None):
    from datetime import time as dt_time
    now = datetime.now()
    today = now.strftime('%d%m%Y')
    current_time = now.time()

    # Gio ket thuc tung phien
    SESSION_END = {
        'ATO': dt_time(9, 15),
        'SANG': dt_time(11, 30),
        'CHIEU': dt_time(14, 30),
        'ATC': dt_time(14, 45),
    }

    # Buoc 1: Xoa PDF cua phien CHUA ket thuc trong ngay hom nay
    for code, end_time in SESSION_END.items():
        if current_time < end_time:
            fname = f'BaoCao_{code}_{today}.pdf'
            if os.path.exists(fname):
                try:
                    os.remove(fname)
                    print(f"  [PDF] Xoa file cu (phien {code} chua ket thuc): {fname}")
                except Exception:
                    pass

    # Buoc 2: Tao PDF cho cac phien DA ket thuc
    print(f"  [PDF] Gio hien tai: {current_time.strftime('%H:%M')} - tao bao cao cac phien da xong...")
    files = []

    for code in ['ATO', 'SANG', 'CHIEU', 'ATC']:
        end_time = SESSION_END[code]
        if current_time < end_time:
            print(f"  [PDF] Bo qua {code} (chua toi {end_time.strftime('%H:%M')})")
            continue
        path = generate_session_report(stocks_data, code, ai_report)
        if path:
            files.append(path)

    # Buoc 3: Nhan dinh thi truong (1 gio/lan)
    print("  [PDF] Kiem tra file nhan dinh thi truong...")
    recent = find_recent_market_report(hours=1)

    if recent:
        age_min = (time.time() - os.path.getmtime(recent)) / 60
        print(f"  [PDF] Da co nhan dinh cach day {age_min:.0f} phut: {os.path.basename(recent)}")
        print(f"  [PDF] Bo qua tao moi (can 1 gio)")
        files.append(recent)
    else:
        print("  [PDF] Chua co nhan dinh trong 1 gio qua -> tao moi")
        market_path = generate_market_report(ai_report, stocks_data)
        if market_path:
            files.append(market_path)

    print(f"  [PDF] Da xu ly {len(files)} file PDF")
    return files

def generate_daily_report(stocks_data, valuations=None, industries=None, ai_report=None, session=None):
    return generate_all_reports(stocks_data, ai_report)