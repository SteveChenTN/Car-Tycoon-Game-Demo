"""
游戏循环管理器
协调所有系统的回合推进逻辑
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from backend.models.game_state import GameState
from backend.models.company import Company
from backend.models.region import Region
from backend.models.game_manager import EventLog
from backend.models.history import SalesHistory, FinancialHistory
from backend.models.finance import Loan, LoanStatus
from backend.models.engineering import CarTrim
from backend.models.market import MarketingCampaign
from backend.models.production import Factory, Inventory, ProductionLine, FactoryType
from backend.models.supply import SupplierContract, ContractStatus
from backend.core.management.finance import FinanceLogic
from backend.core.management.testing import TestingLogic
from backend.core.management.events import EventLogic
from backend.core.economics.market_simulation import MarketSimulator
from backend.core.economics.used_market import UsedCarMarket
from backend.core.production.production_manager import ProductionManager

logger = logging.getLogger(__name__)


class GameLoopManager:
    """
    游戏主循环管理器

    负责协调回合推进的各个阶段：
    1. 世界更新（经济、地区）
    2. AI公司决策
    3. 玩家输入处理（异步）
    4. 生产解算
    5. 市场解算
    6. 财务结算
    7. 事件触发
    """

    def __init__(self, db: Session):
        """
        初始化游戏循环管理器

        Args:
            db: 数据库会话
        """
        self.db = db

        # 初始化各子系统
        self.finance_logic = FinanceLogic(db)
        self.testing_logic = TestingLogic(db)
        self.event_logic = EventLogic(db)
        self.market_sim = MarketSimulator(db)
        self.production_mgr = ProductionManager(db)
        self.used_car_market = UsedCarMarket(db)  # 新增：二手车市场

        # 事件日志缓存（每回合收集）
        self.turn_event_logs = []

    def _log_event(
        self,
        game_id: int,
        turn: int,
        event_type: str,
        message: str,
        severity: str = "INFO",
        related_company_id: int = None,
        related_region_code: str = None,
        extra_data: dict = None
    ):
        """
        记录事件日志（FM风格ticker）

        Args:
            game_id: 游戏ID
            turn: 回合数
            event_type: 事件类型
            message: 消息内容
            severity: 严重程度
            related_company_id: 关联公司
            related_region_code: 关联地区
            extra_data: 额外数据
        """
        event_log = EventLog(
            game_id=game_id,
            turn_number=turn,
            event_type=event_type,
            message=message,
            severity=severity,
            related_company_id=related_company_id,
            related_region_code=related_region_code,
            extra_data=extra_data
        )

        self.db.add(event_log)
        self.turn_event_logs.append(event_log)

    def advance_turn(self, game_id: int) -> Dict[str, Any]:
        """
        推进一个游戏回合

        这是游戏的核心方法，协调所有系统按顺序执行

        Args:
            game_id: 游戏ID

        Returns:
            回合执行结果摘要
        """
        start_time = datetime.utcnow()

        # 清空事件日志缓存
        self.turn_event_logs = []

        try:
            # 获取游戏状态
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            if not game_state:
                return {"success": False, "error": "Game not found"}

            current_turn = game_state.turn_number

            logger.info(
                f"========== 回合推进开始 ==========\n"
                f"游戏ID: {game_id}\n"
                f"回合: {current_turn} -> {current_turn + 1}\n"
                f"日期: {game_state.get_date_string()}"
            )

            # 记录回合开始
            self._log_event(
                game_id=game_id,
                turn=current_turn + 1,
                event_type="TURN_START",
                message=f"回合 {current_turn + 1} 开始 - {game_state.get_date_string()}",
                severity="INFO"
            )

            turn_summary = {
                "turn": current_turn,
                "phases": {}
            }

            # ========== 阶段 1: 世界更新 ==========
            logger.info("阶段 1: 世界更新")
            world_update = self._phase_world_update(game_id, current_turn)
            turn_summary["phases"]["world_update"] = world_update

            # ========== 阶段 2: AI 公司决策 ==========
            logger.info("阶段 2: AI公司决策")
            ai_decisions = self._phase_ai_decisions(game_id, current_turn)
            turn_summary["phases"]["ai_decisions"] = ai_decisions

            # ========== 阶段 2.5: 合约执行 ==========
            logger.info("阶段 2.5: 供应商合约执行")
            contract_results = self._phase_contract_execution(game_id, current_turn)
            turn_summary["phases"]["contracts"] = contract_results

            # ========== 阶段 3: 生产解算 ==========
            logger.info("阶段 3: 生产解算")
            production_results = self._phase_production(game_id, current_turn)
            turn_summary["phases"]["production"] = production_results

            # ========== 阶段 4: 市场解算 ==========
            logger.info("阶段 4: 市场解算")
            market_results = self._phase_market(game_id, current_turn)
            turn_summary["phases"]["market"] = market_results

            # ========== 阶段 5: 财务结算 ==========
            logger.info("阶段 5: 财务结算")
            financial_results = self._phase_financial(game_id, current_turn)
            turn_summary["phases"]["financial"] = financial_results

            # ========== 阶段 6: 研发项目推进 ==========
            logger.info("阶段 6: 研发项目推进")
            research_results = self._phase_research_projects(game_id, current_turn)
            turn_summary["phases"]["research_projects"] = research_results

            # ========== 阶段 7: 测试项目推进 ==========
            logger.info("阶段 7: 测试项目推进")
            testing_results = self._phase_testing(current_turn)
            turn_summary["phases"]["testing"] = testing_results

            # ========== 阶段 7: 二手车市场更新（新增）==========
            logger.info("阶段 7: 二手车市场更新")
            used_car_results = self._phase_used_car_update(game_id, current_turn)
            turn_summary["phases"]["used_cars"] = used_car_results

            # ========== 阶段 8: 事件触发 ==========
            logger.info("阶段 8: 事件触发")
            event_results = self._phase_events(game_id, current_turn)
            turn_summary["phases"]["events"] = event_results

            # ========== 阶段 9: 历史快照记录（新增）==========
            logger.info("阶段 9: 记录历史快照")
            snapshot_results = self._phase_snapshot(game_id, current_turn)
            turn_summary["phases"]["snapshot"] = snapshot_results

            # ========== 阶段 10: 清理与状态更新 ==========
            logger.info("阶段 10: 回合结束清理")
            cleanup_results = self._phase_cleanup(game_id, current_turn)
            turn_summary["phases"]["cleanup"] = cleanup_results

            # ========== 推进游戏时间 ==========
            game_state.advance_turn()

            # 记录回合结束
            self._log_event(
                game_id=game_id,
                turn=game_state.turn_number,
                event_type="TURN_END",
                message=f"回合 {game_state.turn_number} 结束 - {game_state.get_date_string()}",
                severity="SUCCESS"
            )

            # 提交所有数据库更改（包括事件日志）
            self.db.commit()

            # 计算执行时间
            elapsed = (datetime.utcnow() - start_time).total_seconds()

            turn_summary["success"] = True
            turn_summary["new_turn"] = game_state.turn_number
            turn_summary["new_date"] = game_state.get_date_string()
            turn_summary["execution_time_sec"] = round(elapsed, 2)
            turn_summary["event_count"] = len(self.turn_event_logs)

            logger.info(
                f"========== 回合推进完成 ==========\n"
                f"新回合: {game_state.turn_number}\n"
                f"新日期: {game_state.get_date_string()}\n"
                f"执行时间: {elapsed:.2f}秒\n"
                f"事件数: {len(self.turn_event_logs)}\n"
                f"======================================="
            )

            return turn_summary

        except Exception as e:
            logger.error(f"回合推进失败: {e}", exc_info=True)
            self.db.rollback()
            return {"success": False, "error": str(e)}

    def _phase_world_update(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段1: 世界更新
        更新地区经济指标、资源价格等
        """
        try:
            results = {
                "regions_updated": 0,
                "economic_changes": [],
                "companies_reset": 0
            }

            regions = self.db.query(Region).filter(Region.game_id == game_id).all()

            for region in regions:
                # 模拟GDP增长（简化版）
                old_gdp = region.gdp_per_capita
                gdp_growth_rate = 0.005  # 0.5% per turn (约3-4%年增长)
                region.gdp_per_capita *= (1 + gdp_growth_rate)

                # 记录显著变化
                if gdp_growth_rate > 0.01:  # 超过1%增长
                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="WORLD_UPDATE",
                        message=f"{region.name} 经济繁荣，GDP增长 {gdp_growth_rate*100:.1f}%",
                        severity="INFO",
                        related_region_code=region.code
                    )

                results["regions_updated"] += 1

            self.db.commit()

            return results

        except Exception as e:
            logger.error(f"世界更新失败: {e}")
            return {"error": str(e)}

    def _phase_ai_decisions(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段2: AI公司决策
        执行所有AI公司的决策逻辑
        """
        try:
            from backend.core.ai.ai_strategy import (
                classify_company_size,
                get_or_create_company_personality,
                run_ai_turn_for_company,
            )

            results = {
                "ai_companies": 0,
                "decisions_generated": 0,
                "queued_count": 0,
                "executed_count": 0,
                "failed_count": 0,
                "due_count": 0,
                "decisions_made": [],
                "by_company": {}
            }

            ai_companies = self.db.query(Company).filter(
                Company.game_id == game_id,
                Company.is_ai == True,
                Company.is_bankrupt == False
            ).all()

            for company in ai_companies:
                personality = get_or_create_company_personality(company)
                execution_results = run_ai_turn_for_company(
                    db=self.db,
                    company_id=company.id,
                    game_id=game_id,
                    current_turn=current_turn,
                    personality=personality,
                )
                serialized_results = [execution_result.to_dict() for execution_result in execution_results]
                successful_results = [
                    execution_result
                    for execution_result in execution_results
                    if execution_result.success
                ]
                failed_results = [
                    execution_result
                    for execution_result in execution_results
                    if not execution_result.success
                ]

                company_result = {
                    "company_id": company.id,
                    "company_name": company.name,
                    "size": classify_company_size(company),
                    "generated": len(execution_results),
                    "queued": 0,
                    "executed": len(successful_results),
                    "failed": len(failed_results),
                    "foresight": personality.foresight,
                    "actions": serialized_results,
                }
                results["by_company"][company.id] = company_result
                results["decisions_made"].extend(serialized_results)
                results["decisions_generated"] += len(execution_results)
                results["executed_count"] += len(successful_results)
                results["failed_count"] += len(failed_results)
                results["ai_companies"] += 1

                for execution_result in successful_results:
                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="AI_ACTION",
                        message=execution_result.message,
                        severity="SUCCESS",
                        related_company_id=company.id,
                        extra_data={
                            "size": company_result["size"],
                            "foresight": personality.foresight,
                            "decision_type": execution_result.decision_type,
                            "action": execution_result.action,
                            **execution_result.metadata,
                        },
                    )

            self.db.commit()
            return results

        except Exception as e:
            logger.error(f"AI决策失败: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def _phase_production(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段3: 生产解算
        处理所有工厂的生产（周度）
        """
        try:
            # 首先检查所有retooling中的生产线是否完成
            retooling_completed = self._check_retooling_completion(game_id, current_turn)

            results = self.production_mgr.process_weekly_production(game_id, current_turn)
            results["retooling_completed"] = retooling_completed

            for event in results.get("events", []):
                self._log_event(
                    game_id=game_id,
                    turn=current_turn + 1,
                    event_type=event.get("event_type", "PRODUCTION"),
                    message=event.get("message", "Production event"),
                    severity=event.get("severity", "INFO"),
                    related_company_id=event.get("related_company_id"),
                    extra_data=event.get("extra_data")
                )

            return results

        except Exception as e:
            logger.error(f"生产解算失败: {e}")
            return {"error": str(e)}

    def _check_retooling_completion(self, game_id: int, current_turn: int) -> int:
        """
        检查所有retooling中的生产线是否完成

        Args:
            game_id: 游戏ID
            current_turn: 当前回合数

        Returns:
            完成的生产线数量
        """
        from backend.core.production.retooling import RetoolingCalculator
        from backend.models.production import ProductionLine

        # 获取所有retooling中的生产线
        retooling_lines = self.db.query(ProductionLine).filter(
            ProductionLine.game_id == game_id,
            ProductionLine.status == "RETOOLING"
        ).all()

        completed_count = 0

        for line in retooling_lines:
            if RetoolingCalculator.check_retooling_complete(line, current_turn):
                # 重新配置完成，切换到运行状态
                line.status = "RUNNING"
                # 清理retooling相关字段
                line.retooling_until_turn = None
                line.retooling_start_turn = None
                line.retooling_cost = None

                completed_count += 1

                logger.info(
                    f"Production line {line.id} completed retooling, "
                    f"now producing design {line.current_design_id}"
                )

        if completed_count > 0:
            logger.info(f"Completed {completed_count} retooling operations")
            self.db.commit()

        return completed_count

    def _phase_market(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        try:
            regions = self.db.query(Region).filter(Region.game_id == game_id).all()

            total_sales = 0
            results_by_region = []

            for region in regions:
                market_result = self.market_sim.calculate_monthly_sales(
                    region_id=region.id,
                    current_turn=current_turn,
                    game_id=game_id
                )

                total_sales += market_result.total_sales

                results_by_region.append({
                    "region_id": region.id,
                    "region_code": region.code,
                    "sales": market_result.total_sales,
                    "demand": market_result.total_demand,
                    "used_car_sales": market_result.used_car_sales,
                    "lost_demand": market_result.unmet_demand,
                    "lost_demand_by_reason": market_result.lost_demand_by_reason,
                    "revenue": market_result.total_revenue,
                    "gross_profit": market_result.total_gross_profit
                })

            companies = self.db.query(Company).filter(Company.game_id == game_id).all()
            for company in companies:
                company.market_share_global = (
                    company.monthly_units_sold / total_sales
                    if total_sales > 0 else 0.0
                )

            self.db.flush()

            return {
                "total_sales": total_sales,
                "regions": results_by_region
            }

        except Exception as e:
            logger.error(f"市场解算失败: {e}")
            return {"error": str(e)}

    def _phase_financial(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段5: 财务结算
        处理贷款还款、税务、破产检查等
        """
        try:
            results = {}

            # 1. 处理营销投放摊销
            marketing_results = self._process_marketing_spend(game_id, current_turn)
            results["marketing"] = marketing_results

            # 2. 处理贷款还款
            loan_results = self.finance_logic.process_loan_payments(current_turn)
            results["loan_payments"] = loan_results

            # 3. 每季度计算税务（简化：每12回合）
            if current_turn % 12 == 0:
                tax_results = self._calculate_quarterly_taxes(game_id, current_turn)
                results["taxes"] = tax_results

            # 4. 更新公司信用评级
            companies = self.db.query(Company).filter(
                Company.game_id == game_id,
                Company.is_bankrupt == False
            ).all()

            companies_updated = 0
            bankruptcies = 0

            for company in companies:
                company.update_credit_score()
                companies_updated += 1

                # 检查破产
                if company.is_bankrupt:
                    company.is_bankrupt = True
                    company.bankruptcy_turn = current_turn
                    bankruptcies += 1

                    # 生成破产事件日志
                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="FINANCE",
                        message=f"💥 {company.name} 宣布破产！",
                        severity="CRITICAL",
                        related_company_id=company.id
                    )

                    # 生成破产新闻
                    self.event_logic.generate_news(
                        game_id=game_id,
                        news_type="COMPANY_BANKRUPTCY",
                        subject=company.name,
                        details={}
                    )

            results["credit_updates"] = companies_updated
            results["bankruptcies"] = bankruptcies

            self.db.commit()

            return results

        except Exception as e:
            logger.error(f"财务结算失败: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def _process_marketing_spend(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """Amortize active marketing campaign budgets into this period."""
        active_campaigns = self.db.query(MarketingCampaign).filter(
            MarketingCampaign.game_id == game_id,
            MarketingCampaign.is_active == True,
            MarketingCampaign.start_turn <= current_turn,
            MarketingCampaign.end_turn >= current_turn
        ).all()

        results = {
            "campaigns_charged": 0,
            "total_spend": 0.0,
            "cash_shortfalls": 0
        }

        for campaign in active_campaigns:
            if (campaign.name or "").startswith("AI "):
                continue

            company = self.db.query(Company).filter(Company.id == campaign.company_id).first()
            if not company:
                continue

            duration = max(1, (campaign.end_turn or current_turn) - campaign.start_turn + 1)
            period_spend = float(campaign.budget or 0.0) / duration
            if period_spend <= 0:
                continue

            if company.cash < period_spend:
                campaign.is_active = False
                results["cash_shortfalls"] += 1
                continue

            company.record_cost("marketing", period_spend)
            results["campaigns_charged"] += 1
            results["total_spend"] += period_spend

        return results

    def _phase_research_projects(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段6: 研发项目推进
        使用统一的RDManager处理所有公司的研发项目（引擎、底盘、技术、车辆）

        Args:
            game_id: 游戏ID
            current_turn: 当前回合

        Returns:
            处理结果
        """
        try:
            from backend.logic.rd_manager import RDManager
            from backend.models.company import Company

            # 获取所有公司
            companies = self.db.query(Company).filter(
                Company.game_id == game_id,
                Company.is_bankrupt == False
            ).all()

            total_results = {
                "companies_processed": 0,
                "projects_processed": 0,
                "projects_completed": 0,
                "completed_projects": []
            }

            # 为每个公司处理研发项目
            for company in companies:
                try:
                    # 创建或加载RDManager
                    rd_manager = RDManager(
                        db=self.db,
                        company_id=company.id,
                        game_id=game_id
                    )

                    # 处理每周tick
                    company_results = rd_manager.process_weekly_tick(current_turn)

                    # 保存状态
                    rd_manager.save_state()

                    # 累计结果
                    total_results["companies_processed"] += 1
                    total_results["projects_processed"] += company_results.get("projects_processed", 0)
                    total_results["projects_completed"] += company_results.get("projects_completed", 0)
                    total_results["completed_projects"].extend(company_results.get("completed_projects", []))

                    # 记录完成的项目事件
                    for completed in company_results.get("completed_projects", []):
                        project_type = completed.get("type", "UNKNOWN")
                        dept = completed.get("department", "UNKNOWN")

                        self._log_event(
                            game_id=game_id,
                            turn=current_turn + 1,
                            event_type="ENGINEERING",
                            message=f"✅ {company.name} 完成{project_type}研发（{dept}部门）",
                            severity="SUCCESS",
                            related_company_id=company.id
                        )

                except Exception as e:
                    logger.error(f"处理公司 {company.id} 的研发项目失败: {e}", exc_info=True)
                    continue

            return total_results

        except Exception as e:
            logger.error(f"研发项目推进失败: {e}", exc_info=True)
            return {
                "companies_processed": 0,
                "projects_processed": 0,
                "projects_completed": 0,
                "completed_projects": []
            }

    def _phase_testing(self, current_turn: int) -> Dict[str, Any]:
        """
        阶段6: 测试项目推进
        """
        try:
            results = self.testing_logic.advance_testing_projects(current_turn)
            return results

        except Exception as e:
            logger.error(f"测试推进失败: {e}")
            return {"error": str(e)}

    def _phase_events(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段7: 事件触发
        检查并触发随机事件
        """
        try:
            results = self.event_logic.check_random_events(game_id, current_turn)
            return results

        except Exception as e:
            logger.error(f"事件触发失败: {e}")
            return {"error": str(e)}

    def _phase_cleanup(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段10: 回合结束清理
        清理过期数据、更新统计等
        """
        try:
            results = {
                "expired_events": 0,
                "companies_reset": 0,
                "monthly_reset_due": False
            }

            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            monthly_reset_due = bool(
                game_state and (
                    game_state.simulation_speed == "monthly" or
                    game_state.current_week >= 4
                )
            )
            results["monthly_reset_due"] = monthly_reset_due

            if monthly_reset_due:
                companies = self.db.query(Company).filter(Company.game_id == game_id).all()
                for company in companies:
                    company.reset_monthly_stats()
                    results["companies_reset"] += 1

            return results

        except Exception as e:
            logger.error(f"清理阶段失败: {e}")
            return {"error": str(e)}

    def _phase_contract_execution(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段5.5: 执行供应商合约

        处理所有生效中的合约：
        1. 交付材料
        2. 扣除款项
        3. 检查违约
        """
        try:
            results = {
                "contracts_executed": 0,
                "total_materials_delivered": 0,
                "total_payments": 0.0,
                "breaches": 0,
                "completions": 0,
                "delivery_failures": 0
            }

            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            current_week = game_state.current_week if game_state else 1

            # 获取所有生效中的合约
            active_contracts = self.db.query(SupplierContract).filter(
                SupplierContract.game_id == game_id,
                SupplierContract.status == ContractStatus.ACTIVE.value,
                SupplierContract.start_turn <= current_turn,
                SupplierContract.end_turn >= current_turn
            ).all()

            for contract in active_contracts:
                # 获取公司
                company = self.db.query(Company).filter(
                    Company.id == contract.company_id
                ).first()

                if not company:
                    continue

                delivery_units = self._split_monthly_quantity(
                    contract.monthly_volume_commitment or 0,
                    current_week
                )
                if delivery_units <= 0:
                    continue

                unit_price = float(contract.fixed_price_per_unit or 0.0)
                if contract.volume_discount_rate:
                    unit_price *= (1.0 - contract.volume_discount_rate)
                payment_amount = delivery_units * unit_price

                # 检查公司是否有足够现金
                if company.cash < payment_amount:
                    # 违约！
                    penalty = contract.breach_contract(
                        current_turn=current_turn,
                        reason="现金不足，无法支付合约款项",
                        penalty_rate=0.3
                    )

                    # 扣除罚金（如果有钱）
                    if company.cash >= penalty:
                        company.record_cost("admin", penalty)
                    else:
                        # 连罚金都付不起，全部扣光
                        company.record_cost("admin", company.cash)
                        company.cash = 0

                    # 信用评分大幅下降
                    company.credit_score = max(0, company.credit_score - 15)
                    company.update_credit_score()

                    results["breaches"] += 1

                    # 记录事件
                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="FINANCE",
                        message=f"⚠️ {company.name} 违反供应合约！罚金 {penalty:,.0f}",
                        severity="WARNING",
                        related_company_id=company.id
                    )

                    continue

                target_factory = self._select_contract_delivery_factory(
                    contract, game_id, current_week
                )
                if not target_factory or not contract.material_type:
                    results["delivery_failures"] += 1
                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="SUPPLY",
                        message=f"供应合约 {contract.id} 无可用入库工厂，交付跳过",
                        severity="WARNING",
                        related_company_id=company.id
                    )
                    continue

                company.record_cost("materials", payment_amount)
                inventory = self._get_or_create_inventory(target_factory)
                inventory.add_material(contract.material_type.upper(), delivery_units)
                inventory.total_inventory_value += payment_amount
                contract.record_delivery(delivery_units, unit_price)
                if current_turn >= contract.end_turn:
                    contract.status = ContractStatus.COMPLETED.value

                results["contracts_executed"] += 1
                results["total_materials_delivered"] += delivery_units
                results["total_payments"] += payment_amount

                if contract.status == ContractStatus.COMPLETED.value:
                    results["completions"] += 1

                    self._log_event(
                        game_id=game_id,
                        turn=current_turn + 1,
                        event_type="FINANCE",
                        message=f"✅ {company.name} 完成供应合约 - {contract.material_type}",
                        severity="SUCCESS",
                        related_company_id=company.id
                    )

            self.db.commit()

            return results

        except Exception as e:
            logger.error(f"合约执行失败: {e}")
            self.db.rollback()
            return {"error": str(e)}

    @staticmethod
    def _split_monthly_quantity(monthly_quantity: int, current_week: int) -> int:
        monthly_quantity = max(0, int(monthly_quantity or 0))
        current_week = min(4, max(1, int(current_week or 1)))
        base = monthly_quantity // 4
        remainder = monthly_quantity % 4
        return base + (1 if current_week <= remainder else 0)

    def _get_or_create_inventory(self, factory: Factory) -> Inventory:
        inventory = self.db.query(Inventory).filter(Inventory.factory_id == factory.id).first()
        if inventory:
            return inventory

        inventory = Inventory(
            game_id=factory.game_id,
            factory_id=factory.id,
            raw_materials={},
            finished_components={},
            completed_cars={},
            total_inventory_value=0.0
        )
        self.db.add(inventory)
        self.db.flush()
        return inventory

    def _select_contract_delivery_factory(
        self,
        contract: SupplierContract,
        game_id: int,
        current_week: int
    ) -> Optional[Factory]:
        factories = self.db.query(Factory).filter(
            Factory.game_id == game_id,
            Factory.company_id == contract.company_id,
            Factory.is_operational == True
        ).order_by(Factory.id.asc()).all()
        if not factories:
            return None

        material_type = (contract.material_type or "").upper()
        if not material_type:
            return factories[0]

        best_factory = None
        best_score = None
        for factory in factories:
            weekly_need = self._contract_material_need_for_factory(
                factory, material_type, current_week
            )
            if weekly_need <= 0:
                continue
            inventory = self._get_or_create_inventory(factory)
            available = inventory.get_material_quantity(material_type)
            score = available / weekly_need
            if best_score is None or score < best_score:
                best_score = score
                best_factory = factory

        return best_factory or factories[0]

    def _contract_material_need_for_factory(
        self,
        factory: Factory,
        material_type: str,
        current_week: int
    ) -> float:
        running_lines = self.db.query(ProductionLine).filter(
            ProductionLine.factory_id == factory.id,
            ProductionLine.status == "RUNNING",
            ProductionLine.current_design_id.isnot(None)
        ).all()

        need = 0.0
        for line in running_lines:
            car_trim = line.car_trim
            if not car_trim:
                continue
            quantity = self._split_monthly_quantity(line.monthly_capacity, current_week)
            if quantity <= 0:
                continue
            if factory.factory_type == FactoryType.COMPONENT.value:
                materials = self.production_mgr._sum_materials(
                    self.production_mgr.calculate_engine_material_requirements(car_trim.engine),
                    self.production_mgr.calculate_chassis_material_requirements(car_trim.chassis)
                )
            else:
                materials = self.production_mgr.calculate_car_body_material_requirements(car_trim)
            need += float(materials.get(material_type, 0.0) or 0.0) * quantity

        return need

    def _phase_used_car_update(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段7: 更新二手车市场

        1. 老化现有二手车（折旧）
        2. 将本回合新售车辆加入二手车池
        """
        try:
            # 1. 老化现有库存
            aging_result = self.used_car_market.age_used_car_inventory(game_id)

            # 2. TODO: 从市场销售结果中提取新售车辆
            # 这需要从 _phase_market 的结果中获取
            # 暂时作为占位

            results = {
                "aged_records": aging_result.get("aged_records", 0),
                "removed_records": aging_result.get("removed_records", 0),
                "total_depreciation": aging_result.get("total_depreciation", 0.0),
                "new_used_cars_added": 0  # 待实现
            }

            return results

        except Exception as e:
            logger.error(f"二手车更新失败: {e}")
            return {"error": str(e)}

    def _phase_snapshot(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        阶段9: 记录历史快照

        将本回合的销售和财务数据写入历史表
        """
        try:
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            report_turn = current_turn + 1

            results = {
                "sales_records_created": 0,
                "financial_records_created": 0
            }

            # 获取所有公司
            companies = self.db.query(Company).filter(
                Company.game_id == game_id
            ).all()

            for company in companies:
                inventory_value = self._calculate_inventory_value(company.id, game_id)
                total_liabilities = self._calculate_total_liabilities(company.id)
                total_assets = max(0.0, company.cash) + inventory_value
                company.total_debt = total_liabilities
                company.total_assets = total_assets
                company.refresh_monthly_profit()

                financial_snapshot = self.db.query(FinancialHistory).filter(
                    FinancialHistory.game_id == game_id,
                    FinancialHistory.company_id == company.id,
                    FinancialHistory.turn_number == report_turn
                ).first()

                if not financial_snapshot:
                    financial_snapshot = FinancialHistory(
                        game_id=game_id,
                        company_id=company.id,
                        turn_number=report_turn,
                        year=game_state.current_year,
                        month=game_state.current_month
                    )
                    self.db.add(financial_snapshot)
                    results["financial_records_created"] += 1

                financial_snapshot.year = game_state.current_year
                financial_snapshot.month = game_state.current_month
                financial_snapshot.revenue_vehicles = company.monthly_revenue
                financial_snapshot.revenue_licensing = 0.0
                financial_snapshot.revenue_other = 0.0
                financial_snapshot.cost_manufacturing = company.monthly_cost_manufacturing
                financial_snapshot.cost_materials = company.monthly_cost_materials
                financial_snapshot.cost_labor = company.monthly_cost_labor
                financial_snapshot.cost_rd = company.monthly_cost_rd
                financial_snapshot.cost_marketing = company.monthly_cost_marketing
                financial_snapshot.cost_admin = company.monthly_cost_admin
                financial_snapshot.cost_depreciation = 0.0
                financial_snapshot.cost_interest = company.monthly_interest
                financial_snapshot.cash_end = company.cash
                financial_snapshot.inventory_value = inventory_value
                financial_snapshot.total_assets = total_assets
                financial_snapshot.total_liabilities = total_liabilities
                financial_snapshot.shareholder_equity = total_assets - total_liabilities
                financial_snapshot.units_sold = company.monthly_units_sold
                financial_snapshot.units_produced = company.monthly_units_produced
                financial_snapshot.market_share_global = company.market_share_global
                financial_snapshot.credit_score = company.credit_score
                financial_snapshot.credit_rating = company.credit_rating
                financial_snapshot.calculate_totals()

            # TODO: 记录销售历史（需要从市场模拟结果获取）
            # 这部分应该在 _phase_market 中直接创建 SalesHistory 记录

            self.db.commit()

            return results

        except Exception as e:
            logger.error(f"历史快照记录失败: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def _calculate_inventory_value(self, company_id: int, game_id: int) -> float:
        """Calculate cached inventory value across company factories."""
        factories = self.db.query(Factory).filter(
            Factory.game_id == game_id,
            Factory.company_id == company_id
        ).all()
        factory_ids = [factory.id for factory in factories]
        if not factory_ids:
            return 0.0

        inventories = self.db.query(Inventory).filter(
            Inventory.factory_id.in_(factory_ids)
        ).all()
        return sum(float(inventory.total_inventory_value or 0.0) for inventory in inventories)

    def _calculate_total_liabilities(self, company_id: int) -> float:
        """Calculate active loan principal for the balance sheet."""
        loans = self.db.query(Loan).filter(
            Loan.company_id == company_id,
            Loan.status == LoanStatus.ACTIVE
        ).all()
        return sum(float(loan.remaining_principal or 0.0) for loan in loans)

    def _calculate_quarterly_taxes(self, game_id: int, current_turn: int) -> Dict[str, Any]:
        """
        计算季度税务
        """
        try:
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()

            companies = self.db.query(Company).filter(
                Company.game_id == game_id,
                Company.is_bankrupt == False
            ).all()

            total_taxes = 0.0
            companies_taxed = 0

            for company in companies:
                # 使用季度利润作为应税收入
                if company.quarterly_profit > 0:
                    tax_result = self.finance_logic.calculate_taxes(
                        company_id=company.id,
                        taxable_income=company.quarterly_profit,
                        region_code=company.headquarters_region,
                        tax_year=game_state.current_year,
                        tax_quarter=(game_state.current_month - 1) // 3 + 1
                    )

                    if tax_result.get("success"):
                        total_taxes += tax_result.get("total_tax", 0)
                        companies_taxed += 1

            return {
                "companies_taxed": companies_taxed,
                "total_taxes_collected": total_taxes
            }

        except Exception as e:
            logger.error(f"计算税务失败: {e}")
            return {"error": str(e)}

    def get_game_status(self, game_id: int) -> Dict[str, Any]:
        """
        获取游戏当前状态摘要

        Args:
            game_id: 游戏ID

        Returns:
            状态摘要
        """
        try:
            game_state = self.db.query(GameState).filter(GameState.id == game_id).first()
            if not game_state:
                return {"success": False, "error": "Game not found"}

            companies = self.db.query(Company).filter(Company.game_id == game_id).all()

            return {
                "success": True,
                "turn": game_state.turn_number,
                "date": game_state.get_date_string(),
                "year": game_state.current_year,
                "month": game_state.current_month,
                "week": game_state.current_week,
                "total_companies": len(companies),
                "active_companies": len([c for c in companies if not c.is_bankrupt]),
                "player_companies": len([c for c in companies if c.is_player])
            }

        except Exception as e:
            logger.error(f"获取游戏状态失败: {e}")
            return {"success": False, "error": str(e)}


__all__ = ["GameLoopManager"]
