from dataclasses import dataclass
import re

from xiaodianji.queries.intents import QueryIntent


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    intent: QueryIntent | None
    customer_name: str | None = None
    product: str | None = None


def parse_intent(question: str) -> ParsedQuery:
    """Recognize only the six supported, deterministic query forms."""
    normalized = "".join(question.strip().split())
    if not normalized:
        return ParsedQuery(None)
    if "待确认" in normalized:
        return ParsedQuery(QueryIntent.PENDING)
    if "异常" in normalized:
        return ParsedQuery(QueryIntent.ANOMALY)
    if "逾期" in normalized:
        return ParsedQuery(QueryIntent.OVERDUE)
    if "今天" in normalized and any(word in normalized for word in ("卖", "流水", "收了", "进账")):
        return ParsedQuery(QueryIntent.DAILY_FLOW)
    if "报" in normalized and any(word in normalized for word in ("多少钱", "价格", "报价")):
        match = re.search(
            r"(?:上次|之前|最近)?(?:给)?(?P<customer>[\u4e00-\u9fff]{1,20}?)报的(?P<product>[\u4e00-\u9fff0-9]{1,40}?)(?:多少钱|价格|报价)",
            normalized,
        )
        if match:
            return ParsedQuery(
                QueryIntent.HISTORICAL_QUOTE,
                customer_name=match.group("customer"),
                product=match.group("product"),
            )
        return ParsedQuery(QueryIntent.HISTORICAL_QUOTE)
    balance_match = re.search(
        r"(?P<customer>[\u4e00-\u9fff]{1,20}?)(?:还欠|欠款|欠了)",
        normalized,
    )
    if balance_match and any(word in normalized for word in ("多少", "多少钱", "几", "余额")):
        return ParsedQuery(
            QueryIntent.CUSTOMER_BALANCE,
            customer_name=balance_match.group("customer"),
        )
    return ParsedQuery(None)
