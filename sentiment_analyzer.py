# sentiment_analyzer.py - Phan tich sentiment tin tuc tieng Viet (rule-based)
import re
import unicodedata


# ============================================================
# TU DIEN SENTIMENT TIENG VIET
# ============================================================
# Tu khoa TICH CUC (diem +1 moi tu)
POSITIVE_WORDS = {
    # Tang truong
    'tăng', 'tăng mạnh', 'tăng trưởng', 'tăng vọt', 'tăng mạnh mẽ', 'bứt phá',
    'tăng tốc', 'khởi sắc', 'bùng nổ', 'đột phá', 'phục hồi', 'hồi phục',
    'tăng vượt', 'lập đỉnh', 'đỉnh cao', 'cao nhất', 'kỷ lục', 'đạt đỉnh',
    # Loi nhuan
    'lợi nhuận', 'lãi', 'lãi lớn', 'lãi đậm', 'lợi nhuận cao', 'sinh lời',
    'doanh thu tăng', 'lợi nhuận tăng', 'vượt kế hoạch', 'vượt chỉ tiêu',
    'đạt kế hoạch', 'hoàn thành kế hoạch', 'vượt mục tiêu',
    # Khuyen nghi
    'mua', 'mua vào', 'khuyến nghị mua', 'tích cực', 'lạc quan', 'khả quan',
    'đáng đầu tư', 'tiềm năng', 'hấp dẫn', 'rẻ', 'định giá thấp',
    'giá mục tiêu tăng', 'nâng giá mục tiêu', 'nâng khuyến nghị',
    # Dong tien
    'mua ròng', 'dòng tiền vào', 'dòng tiền tích cực', 'khối ngoại mua',
    'dòng tiền mạnh', 'thanh khoản cao', 'giao dịch sôi động',
    # Co phieu
    'cổ tức', 'chia cổ tức', 'chia thưởng', 'trả cổ tức cao',
    'phát hành thêm', 'tăng vốn', 'mở rộng', 'mở rộng sản xuất',
    # Khac
    'thành công', 'tốt', 'hiệu quả', 'vượt trội', 'dẫn đầu', 'top đầu',
    'hứa hẹn', 'triển vọng', 'khởi sắc', 'thuận lợi', 'ủng hộ',
}

# Tu khoa TIEU CUC (diem -1 moi tu)
NEGATIVE_WORDS = {
    # Giam
    'giảm', 'giảm mạnh', 'giảm sâu', 'lao dốc', 'sụt giảm', 'suy giảm',
    'suy yếu', 'đi xuống', 'xuống dốc', 'rớt giá', 'sụp đổ', 'bán tháo',
    'giảm vượt', 'đáy', 'thấp nhất', 'chạm đáy',
    # Loi nhuan
    'lỗ', 'thua lỗ', 'lỗ lớn', 'lỗ đậm', 'lợi nhuận giảm', 'doanh thu giảm',
    'không đạt kế hoạch', 'dưới kế hoạch', 'không hoàn thành',
    'thất bại', 'sai lầm', 'thua', 'suy thoái',
    # Khuyen nghi
    'bán', 'bán ra', 'khuyến nghị bán', 'tiêu cực', 'bi quan', 'kém khả quan',
    'không đáng đầu tư', 'đắt', 'định giá cao', 'rủi ro cao',
    'giá mục tiêu giảm', 'hạ giá mục tiêu', 'hạ khuyến nghị',
    # Dong tien
    'bán ròng', 'dòng tiền ra', 'dòng tiền tiêu cực', 'khối ngoại bán',
    'dòng tiền yếu', 'thanh khoản thấp', 'giao dịch ảm đạm', 'ế ẩm',
    # Rui ro
    'rủi ro', 'cảnh báo', 'lo ngại', 'lo lắng', 'bất ổn', 'khó khăn',
    'thách thức', 'biến động mạnh', 'biến động', 'điều chỉnh',
    # Khac
    'phá sản', 'nợ xấu', 'nợ đọng', 'vi phạm', 'xử phạt', 'khởi tố',
    'điều tra', 'truy tố', 'hủy niêm yết', 'đình chỉ', 'tạm ngừng',
    'thu hồi', 'chậm trễ', 'trì trệ', 'bế tắc', 'ảm đạm', 'èo uột',
}

# Cum tang cuong (nhan he so)
INTENSIFIERS = {
    'rất', 'cực', 'vô cùng', 'hết sức', 'cực kỳ', 'siêu',
    'mạnh', 'mạnh mẽ', 'dữ dội', 'khủng khiếp', 'lịch sử',
}

# Phu dinh (dao nguoc sentiment)
NEGATIONS = {'không', 'chẳng', 'chưa', 'chả', 'chớ', 'đừng'}


def _remove_accents(s):
    """Bo dau tieng Viet de so khop linh hoat."""
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def _tokenize(text):
    """Tach tu, giu cum tu co dau cach."""
    text = text.lower()
    # Tach theo ky tu khong phai chu
    tokens = re.findall(r'\b[\wàáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]+\b', text)
    return tokens


def analyze_sentiment(text, title_only=False):
    """
    Phan tich sentiment cua 1 doan text.
    Tra ve dict:
      - score: diem (am = tieu cuc, duong = tich cuc)
      - label: 'positive' / 'neutral' / 'negative'
      - positive_hits: list tu tich cuc tim thay
      - negative_hits: list tu tieu cuc tim thay
    """
    if not text:
        return {'score': 0, 'label': 'neutral', 'positive_hits': [], 'negative_hits': []}

    text_lower = text.lower()
    # Bo dau de so khop linh hoat (VD: "tăng" vs "tang")
    text_no_accent = _remove_accents(text_lower)

    score = 0
    pos_hits = []
    neg_hits = []

    # Kiem tra tung tu tich cuc
    for word in POSITIVE_WORDS:
        word_no_accent = _remove_accents(word)
        # Tim ca 2 dang: co dau va khong dau
        if word in text_lower or word_no_accent in text_no_accent:
            score += 1
            pos_hits.append(word)

    # Kiem tra tung tu tieu cuc
    for word in NEGATIVE_WORDS:
        word_no_accent = _remove_accents(word)
        if word in text_lower or word_no_accent in text_no_accent:
            score -= 1
            neg_hits.append(word)

    # Xu ly phu dinh: "không tăng" -> khong phai tich cuc
    for neg in NEGATIONS:
        # Tim pattern "khong <positive_word>" -> giam 2 diem
        for word in POSITIVE_WORDS:
            pattern = r'\b' + re.escape(neg) + r'\s+\w*\s*' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                score -= 2  # Dao nguoc + trung phat
                if word in pos_hits:
                    pos_hits.remove(word)

        for word in NEGATIVE_WORDS:
            pattern = r'\b' + re.escape(neg) + r'\s+\w*\s*' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                score += 1  # "khong giam" = tich cuc nhe

    # Xac dinh label
    if score >= 2:
        label = 'positive'
    elif score <= -2:
        label = 'negative'
    else:
        label = 'neutral'

    return {
        'score': score,
        'label': label,
        'positive_hits': pos_hits[:5],
        'negative_hits': neg_hits[:5],
    }


def sentiment_summary(items):
    """
    Tong hop sentiment cua 1 list bai viet.
    items: list dict co field 'title' va 'description' (optional)
    Tra ve dict:
      - total, positive, negative, neutral
      - avg_score
    """
    total = len(items)
    if total == 0:
        return {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0, 'avg_score': 0}

    pos = neg = neu = 0
    total_score = 0
    for item in items:
        title = item.get('title', '')
        desc = item.get('description', '')
        text = title + ' ' + desc
        result = analyze_sentiment(text)
        total_score += result['score']
        if result['label'] == 'positive':
            pos += 1
        elif result['label'] == 'negative':
            neg += 1
        else:
            neu += 1

    return {
        'total': total,
        'positive': pos,
        'negative': neg,
        'neutral': neu,
        'avg_score': round(total_score / total, 2),
    }


# ============================================================
# TEST
# ============================================================
if __name__ == '__main__':
    tests = [
        "FPT tăng mạnh 5% sau khi công bố lợi nhuận kỷ lục",
        "Cổ phiếu HPG lao dốc, khối ngoại bán ròng 500 tỷ",
        "Thị trường chứng khoán đi ngang, thanh khoản thấp",
        "PNJ được khuyến nghị mua với giá mục tiêu 95.000",
        "VCB bị hạ khuyến nghị xuống trung lập, rủi ro nợ xấu tăng",
        "VN-Index không tăng dù có tin tốt",
    ]
    for t in tests:
        r = analyze_sentiment(t)
        print(f"[{r['label']:>8}] score={r['score']:>3} | {t[:60]}")