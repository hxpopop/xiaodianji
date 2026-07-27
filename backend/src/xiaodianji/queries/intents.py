from enum import StrEnum


class QueryIntent(StrEnum):
    CUSTOMER_BALANCE = "customer_balance"
    HISTORICAL_QUOTE = "historical_quote"
    DAILY_FLOW = "daily_flow"
    OVERDUE = "overdue"
    PENDING = "pending"
    ANOMALY = "anomaly"
