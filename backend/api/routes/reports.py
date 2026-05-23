"""
报告API路由
提供月报、财务历史和现金变化解释。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging

from backend.core.dependencies import get_db_optional
from backend.models import GameState, Company, EventLog
from backend.models.history import FinancialHistory
from backend.models.production import Factory, ProductionLine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


class CostBreakdown(BaseModel):
    manufacturing: float = 0.0
    materials: float = 0.0
    labor: float = 0.0
    rd: float = 0.0
    marketing: float = 0.0
    admin: float = 0.0
    depreciation: float = 0.0
    interest: float = 0.0
    total: float = 0.0


class BalanceSheetSnapshot(BaseModel):
    cash: float
    inventory: float
    total_assets: float
    total_liabilities: float
    shareholder_equity: float


class CashFlowLine(BaseModel):
    label: str
    amount: float
    kind: str


class CashFlowBridge(BaseModel):
    starting_cash: float
    ending_cash: float
    cash_change: float
    net_income: float
    debt_principal_change: float
    other_cash_flow: float
    lines: List[CashFlowLine]


class MonthlyFinancials(BaseModel):
    revenue: float
    costs: float
    gross_profit: float
    operating_profit: float
    net_profit: float
    cash_balance: float
    cost_breakdown: CostBreakdown
    balance_sheet: BalanceSheetSnapshot
    cash_flow: CashFlowBridge


class MonthlyProduction(BaseModel):
    cars_built: int
    components_produced: int
    utilization_rate: float


class MonthlyAlert(BaseModel):
    type: str
    message: str


class MonthlyReport(BaseModel):
    turn_number: int
    year: int
    month: int
    unit: str
    financials: MonthlyFinancials
    production: MonthlyProduction
    alerts: List[MonthlyAlert]


def _require_db(db: Optional[Session]) -> Session:
    if db is None:
        raise HTTPException(status_code=404, detail="游戏未加载，请先创建或加载存档")
    return db


def _get_game(db: Session, game_id: int) -> GameState:
    game = db.query(GameState).filter(GameState.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail=f"游戏 {game_id} 不存在")
    return game


def _get_player_company(db: Session, game_id: int) -> Company:
    company = db.query(Company).filter(
        Company.game_id == game_id,
        Company.is_player == True
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="未找到玩家公司")
    return company


def _number(value: Optional[float]) -> float:
    return float(value or 0.0)


def _total_revenue(record: FinancialHistory) -> float:
    return (
        _number(record.revenue_vehicles) +
        _number(record.revenue_licensing) +
        _number(record.revenue_other)
    )


def _total_costs(record: FinancialHistory) -> float:
    return (
        _number(record.cost_manufacturing) +
        _number(record.cost_materials) +
        _number(record.cost_labor) +
        _number(record.cost_rd) +
        _number(record.cost_marketing) +
        _number(record.cost_admin) +
        _number(record.cost_depreciation) +
        _number(record.cost_interest)
    )


def _cost_breakdown(record: FinancialHistory) -> CostBreakdown:
    return CostBreakdown(
        manufacturing=_number(record.cost_manufacturing),
        materials=_number(record.cost_materials),
        labor=_number(record.cost_labor),
        rd=_number(record.cost_rd),
        marketing=_number(record.cost_marketing),
        admin=_number(record.cost_admin),
        depreciation=_number(record.cost_depreciation),
        interest=_number(record.cost_interest),
        total=_total_costs(record),
    )


def _previous_snapshot(
    db: Session,
    game_id: int,
    company_id: int,
    turn_number: int
) -> Optional[FinancialHistory]:
    return db.query(FinancialHistory).filter(
        FinancialHistory.game_id == game_id,
        FinancialHistory.company_id == company_id,
        FinancialHistory.turn_number < turn_number
    ).order_by(FinancialHistory.turn_number.desc()).first()


def _cash_flow_bridge(
    db: Session,
    record: FinancialHistory,
    previous: Optional[FinancialHistory] = None
) -> CashFlowBridge:
    if previous is None:
        previous = _previous_snapshot(db, record.game_id, record.company_id, record.turn_number)

    cash_end = _number(record.cash_end)
    net_income = _number(record.net_income)
    total_liabilities = _number(record.total_liabilities)
    starting_cash = _number(previous.cash_end) if previous else cash_end - net_income
    previous_liabilities = _number(previous.total_liabilities) if previous else total_liabilities
    cash_change = cash_end - starting_cash
    debt_principal_change = total_liabilities - previous_liabilities
    other_cash_flow = cash_change - net_income - debt_principal_change

    lines = [
        CashFlowLine(label="经营净利润", amount=net_income, kind="operating"),
        CashFlowLine(label="债务净流入/偿还", amount=debt_principal_change, kind="financing"),
        CashFlowLine(label="库存、资本支出及其他", amount=other_cash_flow, kind="other"),
    ]

    return CashFlowBridge(
        starting_cash=starting_cash,
        ending_cash=cash_end,
        cash_change=cash_change,
        net_income=net_income,
        debt_principal_change=debt_principal_change,
        other_cash_flow=other_cash_flow,
        lines=lines,
    )


def _production_summary(db: Session, company: Company, record: FinancialHistory) -> MonthlyProduction:
    factories = db.query(Factory).filter(
        Factory.company_id == company.id,
        Factory.is_operational == True
    ).all()
    factory_ids = [factory.id for factory in factories]

    production_lines: List[ProductionLine] = []
    if factory_ids:
        production_lines = db.query(ProductionLine).filter(
            ProductionLine.factory_id.in_(factory_ids),
            ProductionLine.status == "RUNNING"
        ).all()

    total_capacity = sum(line.monthly_capacity for line in production_lines)
    if total_capacity <= 0:
        total_capacity = sum(
            factory.capacity_units_per_month
            for factory in factories
            if factory.factory_type == "ASSEMBLY"
        )

    utilization_rate = 0.0
    if total_capacity > 0:
        utilization_rate = min(1.0, _number(record.units_produced) / total_capacity)

    return MonthlyProduction(
        cars_built=int(record.units_produced or 0),
        components_produced=0,
        utilization_rate=utilization_rate,
    )


def _alerts(
    db: Session,
    game_id: int,
    record: FinancialHistory,
    utilization_rate: float
) -> List[MonthlyAlert]:
    alerts: List[MonthlyAlert] = []

    cash_end = _number(record.cash_end)
    net_income = _number(record.net_income)

    if cash_end < 1_000_000:
        alerts.append(MonthlyAlert(
            type="critical",
            message=f"现金严重不足，期末余额 ${cash_end:,.0f}，建议融资或削减支出"
        ))
    elif cash_end < 5_000_000:
        alerts.append(MonthlyAlert(
            type="warning",
            message=f"现金余额偏低：${cash_end:,.0f}，请关注下月现金流"
        ))

    if net_income < 0:
        alerts.append(MonthlyAlert(
            type="warning",
            message=f"本期亏损 ${abs(net_income):,.0f}，主要成本需复盘"
        ))

    if utilization_rate > 0 and utilization_rate < 0.5:
        alerts.append(MonthlyAlert(
            type="info",
            message=f"产能利用率偏低 ({utilization_rate * 100:.0f}%)"
        ))
    elif utilization_rate > 0.95:
        alerts.append(MonthlyAlert(
            type="success",
            message=f"产线接近满负荷 ({utilization_rate * 100:.0f}%)"
        ))

    recent_events = db.query(EventLog).filter(
        EventLog.game_id == game_id,
        EventLog.turn_number == record.turn_number
    ).order_by(EventLog.id.desc()).limit(3).all()

    for event in recent_events:
        severity = (event.severity or "info").lower()
        if severity in {"warning", "critical", "error"}:
            alerts.append(MonthlyAlert(
                type="critical" if severity in {"critical", "error"} else "warning",
                message=event.message[:120]
            ))

    if not alerts:
        alerts.append(MonthlyAlert(type="success", message="本期运营正常，财务闭环已生成快照"))

    return alerts


def _record_to_monthly_report(db: Session, company: Company, record: FinancialHistory) -> MonthlyReport:
    costs = _total_costs(record)
    production = _production_summary(db, company, record)

    return MonthlyReport(
        turn_number=record.turn_number,
        year=record.year,
        month=record.month,
        unit="game_currency",
        financials=MonthlyFinancials(
            revenue=_total_revenue(record),
            costs=costs,
            gross_profit=_number(record.gross_profit),
            operating_profit=_number(record.operating_profit),
            net_profit=_number(record.net_income),
            cash_balance=_number(record.cash_end),
            cost_breakdown=_cost_breakdown(record),
            balance_sheet=BalanceSheetSnapshot(
                cash=_number(record.cash_end),
                inventory=_number(record.inventory_value),
                total_assets=_number(record.total_assets),
                total_liabilities=_number(record.total_liabilities),
                shareholder_equity=_number(record.shareholder_equity),
            ),
            cash_flow=_cash_flow_bridge(db, record),
        ),
        production=production,
        alerts=_alerts(db, record.game_id, record, production.utilization_rate),
    )


def _latest_snapshot(db: Session, game_id: int, company_id: int) -> Optional[FinancialHistory]:
    return db.query(FinancialHistory).filter(
        FinancialHistory.game_id == game_id,
        FinancialHistory.company_id == company_id
    ).order_by(FinancialHistory.turn_number.desc()).first()


@router.get("/latest", response_model=MonthlyReport)
async def get_latest_monthly_report(
    game_id: int = Query(..., description="游戏ID"),
    db: Session = Depends(get_db_optional)
) -> MonthlyReport:
    db = _require_db(db)
    _get_game(db, game_id)
    company = _get_player_company(db, game_id)
    record = _latest_snapshot(db, game_id, company.id)
    if not record:
        raise HTTPException(status_code=404, detail="尚未生成月度财务快照")
    return _record_to_monthly_report(db, company, record)


@router.get("/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    game_id: int = Query(..., description="游戏ID"),
    turn_number: int = Query(..., description="回合数"),
    db: Session = Depends(get_db_optional)
) -> MonthlyReport:
    db = _require_db(db)
    _get_game(db, game_id)
    company = _get_player_company(db, game_id)
    record = db.query(FinancialHistory).filter(
        FinancialHistory.game_id == game_id,
        FinancialHistory.company_id == company.id,
        FinancialHistory.turn_number == turn_number
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"回合 {turn_number} 尚无月报")
    return _record_to_monthly_report(db, company, record)


@router.get("/financial", response_model=Dict[str, Any])
async def get_financial_report_page(
    game_id: int = Query(..., description="游戏ID"),
    company_id: int = Query(..., description="公司ID"),
    limit: int = Query(24, ge=1, le=120, description="历史记录数"),
    db: Session = Depends(get_db_optional)
) -> Dict[str, Any]:
    db = _require_db(db)
    _get_game(db, game_id)
    company = db.query(Company).filter(
        Company.game_id == game_id,
        Company.id == company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    records = db.query(FinancialHistory).filter(
        FinancialHistory.game_id == game_id,
        FinancialHistory.company_id == company_id
    ).order_by(FinancialHistory.turn_number.desc()).limit(limit).all()
    records = list(reversed(records))

    history = []
    previous: Optional[FinancialHistory] = None
    for record in records:
        bridge = _cash_flow_bridge(db, record, previous)
        history.append({
            "turn": record.turn_number,
            "year": record.year,
            "month": record.month,
            "revenue": _total_revenue(record),
            "expenses": _total_costs(record),
            "net_income": _number(record.net_income),
            "cash": _number(record.cash_end),
            "cash_change": bridge.cash_change,
            "units_sold": int(record.units_sold or 0),
        })
        previous = record

    latest = records[-1] if records else None
    pl_statement = None
    cash_flow = None
    balance_sheet = None
    cost_breakdown = None
    if latest:
        cost_breakdown = _cost_breakdown(latest).dict()
        cash_flow = _cash_flow_bridge(db, latest).dict()
        balance_sheet = {
            "cash": _number(latest.cash_end),
            "inventory": _number(latest.inventory_value),
            "total_assets": _number(latest.total_assets),
            "total_liabilities": _number(latest.total_liabilities),
            "shareholder_equity": _number(latest.shareholder_equity),
        }
        pl_statement = {
            "revenue": _total_revenue(latest),
            "cogs": (
                _number(latest.cost_manufacturing) +
                _number(latest.cost_materials) +
                _number(latest.cost_labor)
            ),
            "gross_profit": _number(latest.gross_profit),
            "rd_cost": _number(latest.cost_rd),
            "marketing_cost": _number(latest.cost_marketing),
            "admin_cost": _number(latest.cost_admin),
            "operating_income": _number(latest.operating_profit),
            "interest": _number(latest.cost_interest),
            "tax": 0.0,
            "net_income": _number(latest.net_income),
        }

    same_turn_records = []
    if latest:
        same_turn_records = db.query(FinancialHistory).filter(
            FinancialHistory.game_id == game_id,
            FinancialHistory.turn_number == latest.turn_number
        ).all()

    palette = ["#06b6d4", "#f59e0b", "#10b981", "#a855f7", "#64748b"]
    market_share = []
    for index, record in enumerate(same_turn_records[:5]):
        company_name = db.query(Company.name).filter(Company.id == record.company_id).scalar() or f"Company {record.company_id}"
        market_share.append({
            "company": company_name,
            "share": round((record.market_share_global or 0.0) * 100, 2),
            "color": palette[index % len(palette)],
        })

    return {
        "success": True,
        "unit": "game_currency",
        "history": history,
        "pl_statement": pl_statement,
        "cash_flow": cash_flow,
        "balance_sheet": balance_sheet,
        "cost_breakdown": cost_breakdown,
        "market_share": market_share,
    }
