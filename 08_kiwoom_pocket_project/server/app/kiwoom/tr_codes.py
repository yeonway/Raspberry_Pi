TOKEN_ISSUE = "au10001"

ACCOUNT_NUMBERS = "kt00001"
ACCOUNT_BALANCE = "kt00003"
ACCOUNT_PORTFOLIO = "kt00004"

STOCK_QUOTE = "ka10001"
STOCK_ORDERBOOK = "ka10004"
STOCK_DAY_CHART = "ka10081"
STOCK_MINUTE_CHART = "ka10080"

CONDITION_LIST = "ka10171"
CONDITION_RUN = "ka10172"

MOCK_BUY_ORDER = "kt10000"
MOCK_SELL_ORDER = "kt10001"

ENDPOINTS = {
    ACCOUNT_NUMBERS: "/api/dostk/acnt",
    ACCOUNT_BALANCE: "/api/dostk/acnt",
    ACCOUNT_PORTFOLIO: "/api/dostk/acnt",
    STOCK_QUOTE: "/api/dostk/stkinfo",
    STOCK_ORDERBOOK: "/api/dostk/mrkcond",
    STOCK_DAY_CHART: "/api/dostk/chart",
    STOCK_MINUTE_CHART: "/api/dostk/chart",
    CONDITION_LIST: "/api/dostk/stkinfo",
    CONDITION_RUN: "/api/dostk/stkinfo",
    MOCK_BUY_ORDER: "/api/dostk/ordr",
    MOCK_SELL_ORDER: "/api/dostk/ordr",
}
