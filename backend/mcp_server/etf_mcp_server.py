"""ETF DB MCP 서버.

MCP(Model Context Protocol) stdio 서버로, ETF DB에 대한 3가지 도구를 제공한다.

  1. etfs_containing_stock  — 요청한 주식종목을 포함하는 ETF들을 구성비율 랭킹으로 출력
  2. stocks_in_same_sector  — 요청한 주식종목과 같은 섹터의 종목들을 출력
  3. stocks_in_same_theme   — 요청한 주식종목과 같은 테마의 종목들을 출력

실행:  python -m backend.mcp_server.etf_mcp_server
(백엔드의 검색Agent가 stdio MCP 클라이언트로 이 서버를 자동 기동/연결한다)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.fastmcp import FastMCP

from backend import database as db

mcp = FastMCP("etf-db")


@mcp.tool()
def etfs_containing_stock(stock: str, limit: int = 20) -> str:
    """요청한 주식종목(이름 또는 코드)을 포함하는 ETF들을 구성비율이 높은 순으로 반환합니다.

    Args:
        stock: 주식 이름 또는 6자리 종목코드 (예: "삼성전자" 또는 "005930")
        limit: 최대 반환 개수
    """
    rows = db.etfs_containing_stock(stock, limit)
    return json.dumps(rows, ensure_ascii=False, default=str)


@mcp.tool()
def stocks_in_same_sector(stock: str, limit: int = 20) -> str:
    """요청한 주식종목과 같은 섹터에 속한 다른 종목들을 반환합니다.

    Args:
        stock: 주식 이름 또는 6자리 종목코드
        limit: 최대 반환 개수
    """
    rows = db.stocks_in_same_sector(stock, limit)
    return json.dumps(rows, ensure_ascii=False, default=str)


@mcp.tool()
def stocks_in_same_theme(stock: str, limit: int = 30) -> str:
    """요청한 주식종목과 같은 테마에 속한 다른 종목들을 반환합니다.

    Args:
        stock: 주식 이름 또는 6자리 종목코드
        limit: 최대 반환 개수
    """
    rows = db.stocks_in_same_theme(stock, limit)
    return json.dumps(rows, ensure_ascii=False, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
