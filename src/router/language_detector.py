from src.domain.intent import Language

VIETNAMESE_MARKERS = {
    "ă",
    "â",
    "đ",
    "ê",
    "ô",
    "ơ",
    "ư",
    "á",
    "à",
    "ả",
    "ã",
    "ạ",
    "ế",
    "ệ",
}

VIETNAMESE_WORDS = {
    "hom",
    "hôm",
    "qua",
    "cuoc",
    "cuộc",
    "goi",
    "gọi",
    "yeu",
    "yêu",
    "cau",
    "cầu",
    "tong",
    "tổng",
    "dai",
    "đài",
    "theo",
    "thang",
    "tháng",
    "nhan",
    "nhân",
    "vien",
    "viên",
}


def detect_language(text: str) -> Language:
    lowered = text.lower()
    if any(marker in lowered for marker in VIETNAMESE_MARKERS):
        return Language.VI

    tokens = set(lowered.replace(".", " ").replace(",", " ").split())
    if tokens & VIETNAMESE_WORDS:
        return Language.VI
    return Language.EN
