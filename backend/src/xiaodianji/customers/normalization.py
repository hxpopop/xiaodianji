import re
import unicodedata


_TITLE_SUFFIXES = (
    "老板",
    "师傅",
    "先生",
    "女士",
    "大哥",
    "大姐",
    "哥",
    "姐",
    "总",
)


def normalize_customer_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"[\s\W_]+", "", normalized, flags=re.UNICODE)
    for suffix in _TITLE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized

