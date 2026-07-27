import pytest

from xiaodianji.queries.intents import QueryIntent
from xiaodianji.queries.parser import parse_intent


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("王老板还欠多少钱", QueryIntent.CUSTOMER_BALANCE),
        ("上次给王老板报的插座多少钱", QueryIntent.HISTORICAL_QUOTE),
        ("今天一共卖了多少", QueryIntent.DAILY_FLOW),
        ("哪些账逾期了", QueryIntent.OVERDUE),
        ("有哪些待确认", QueryIntent.PENDING),
        ("最近有哪些异常", QueryIntent.ANOMALY),
    ],
)
def test_supported_questions_map_to_their_fixed_intents(
    question: str,
    intent: QueryIntent,
) -> None:
    # A missing or misordered deterministic rule must not route the question to
    # another query type.
    assert parse_intent(question).intent is intent


def test_unsupported_question_does_not_infer_sql_or_an_amount() -> None:
    # A future broad NLP fallback must not turn an unknown question into a
    # financial conclusion.
    parsed = parse_intent("帮我算算哪种货最赚钱")

    assert parsed.intent is None
    assert parsed.customer_name is None
