"""
外交管理器 - Dirty Tricks 核心逻辑
Diplomacy Manager - Corporate Warfare Implementation

实现：
1. Executive Poaching（挖角高管）
2. PR Attack / Smear Campaign（公关攻击）
3. Relation Management（关系管理）
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Tuple, Optional
import random
import json
from datetime import datetime

from backend.models.diplomacy import CompetitorRelation, DiplomaticAction
from backend.models.staff import Staff
from backend.models.company import Company
from backend.models.events import GameEvent
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DiplomacyManager:
    """
    外交管理器 - 处理公司间竞争行为
    """
    
    # 关系影响常数
    POACH_SUCCESS_RELATION_PENALTY = -25.0    # 成功挖角：关系-25
    POACH_FAILURE_RELATION_PENALTY = -10.0    # 失败挖角：关系-10
    PR_ATTACK_RELATION_PENALTY = -15.0        # 公关攻击：关系-15
    PR_ATTACK_BACKFIRE_SELF_DAMAGE = 0.5      # 反噬：自己受0.5倍伤害
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== 关系管理 ====================
    
    def get_or_create_relation(
        self,
        company_id: int,
        target_company_id: int,
        game_id: int
    ) -> CompetitorRelation:
        """
        获取或创建公司间关系记录
        
        Args:
            company_id: 发起方公司ID
            target_company_id: 目标公司ID
            game_id: 游戏ID
            
        Returns:
            CompetitorRelation对象
        """
        relation = self.db.query(CompetitorRelation).filter(
            CompetitorRelation.company_id == company_id,
            CompetitorRelation.target_company_id == target_company_id,
            CompetitorRelation.game_id == game_id
        ).first()
        
        if not relation:
            relation = CompetitorRelation(
                game_id=game_id,
                company_id=company_id,
                target_company_id=target_company_id,
                relation_score=0.0  # 初始中立
            )
            self.db.add(relation)
            self.db.commit()
            logger.info(f"Created new relation: Company {company_id} <-> {target_company_id}")
        
        return relation
    
    def update_relation(
        self,
        company_id: int,
        target_company_id: int,
        game_id: int,
        change: float,
        current_turn: int
    ) -> float:
        """
        更新公司间关系
        
        Args:
            company_id: 发起方
            target_company_id: 目标方
            game_id: 游戏ID
            change: 关系变化值（正或负）
            current_turn: 当前回合
            
        Returns:
            更新后的关系分数
        """
        relation = self.get_or_create_relation(company_id, target_company_id, game_id)
        
        old_score = relation.relation_score
        relation.relation_score += change
        
        # 限制范围 [-100, +100]
        relation.relation_score = max(-100.0, min(100.0, relation.relation_score))
        
        # 更新统计
        relation.last_interaction_turn = current_turn
        if change > 0:
            relation.total_positive_actions += 1
        else:
            relation.total_negative_actions += 1
        
        # 特殊状态检查
        if relation.relation_score <= -80:
            relation.is_embargo = True
        elif relation.relation_score >= 70:
            relation.is_alliance = True
        
        self.db.commit()
        
        logger.info(
            f"Relation updated: Company {company_id} → {target_company_id}: "
            f"{old_score:.1f} → {relation.relation_score:.1f} ({change:+.1f})"
        )
        
        return relation.relation_score
    
    # ==================== Dirty Trick #1: Executive Poaching ====================
    
    def attempt_poach_executive(
        self,
        poaching_company_id: int,
        target_executive_id: int,
        salary_offer: float,
        game_id: int,
        current_turn: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        尝试挖角竞争对手的高管
        
        Success Formula:
            Success Chance = (Salary Offer / Current Salary) × (1 / Loyalty) × Random Factor
            
        Consequences:
        - Success: 高管跳槽，目标公司关系-25，高管忠诚度重置
        - Failure: 目标公司关系-10，被挖高管忠诚度+10（更忠诚）
        
        Args:
            poaching_company_id: 挖角公司ID
            target_executive_id: 目标高管ID
            salary_offer: 提供的薪资
            game_id: 游戏ID
            current_turn: 当前回合
            
        Returns:
            (是否成功, 消息, 详细结果)
        """
        # 1. 获取高管信息
        executive = self.db.query(Staff).filter(Staff.id == target_executive_id).first()
        if not executive:
            return False, "Executive not found", {}
        
        if executive.company_id is None:
            return False, "Executive is not employed", {}
        
        target_company_id = executive.company_id
        
        # 2. 检查是否挖自己人
        if target_company_id == poaching_company_id:
            return False, "Cannot poach your own employees", {}
        
        # 3. 获取挖角公司
        poaching_company = self.db.query(Company).filter(Company.id == poaching_company_id).first()
        if not poaching_company:
            return False, "Poaching company not found", {}
        
        # 4. 计算成功率
        current_salary = executive.salary
        salary_ratio = salary_offer / max(1.0, current_salary)  # 避免除零
        
        # 忠诚度影响（0-100 -> 0.2-2.0倍）
        loyalty_factor = 1.0 / max(0.5, executive.loyalty / 100.0)
        
        # 士气影响（低士气更容易被挖）
        morale_factor = 1.5 - (executive.morale / 100.0)  # 0.5-1.5
        
        # 基础成功率
        base_success_chance = salary_ratio * loyalty_factor * morale_factor * 0.15
        
        # 随机因素 (0.7-1.3)
        random_factor = random.uniform(0.7, 1.3)
        
        final_success_chance = base_success_chance * random_factor
        
        # 上限80%（即使出价很高也有可能失败）
        final_success_chance = min(0.80, final_success_chance)
        
        logger.info(
            f"Poaching attempt: {poaching_company_id} → Executive {target_executive_id} "
            f"(Offer: ${salary_offer:,.0f} vs Current: ${current_salary:,.0f}, "
            f"Success chance: {final_success_chance*100:.1f}%)"
        )
        
        # 5. 判定结果
        roll = random.random()
        success = roll < final_success_chance
        
        # 6. 执行结果
        if success:
            # 成功：高管跳槽
            old_company_id = executive.company_id
            executive.company_id = poaching_company_id
            executive.salary = salary_offer
            executive.loyalty = 50.0  # 忠诚度重置为中等（刚跳槽）
            executive.morale = 75.0   # 士气提升（新环境）
            
            # 关系重创
            new_relation = self.update_relation(
                poaching_company_id,
                target_company_id,
                game_id,
                self.POACH_SUCCESS_RELATION_PENALTY,
                current_turn
            )
            
            # 记录行动
            action = DiplomaticAction(
                game_id=game_id,
                actor_company_id=poaching_company_id,
                target_company_id=target_company_id,
                action_type="POACH_EXECUTIVE",
                action_details=json.dumps({
                    "executive_id": target_executive_id,
                    "executive_name": f"{executive.first_name} {executive.last_name}",
                    "position": executive.position,
                    "old_salary": current_salary,
                    "new_salary": salary_offer
                }),
                success=True,
                outcome_description=f"Successfully poached {executive.first_name} {executive.last_name} ({executive.position})",
                cost_paid=salary_offer * 12,  # 年薪
                relation_change=self.POACH_SUCCESS_RELATION_PENALTY,
                executed_turn=current_turn,
                resolved_turn=current_turn,
                is_public=True,
                discovered_by_target=True
            )
            self.db.add(action)
            
            # 生成事件
            self._generate_poaching_event(
                game_id, poaching_company_id, target_company_id,
                executive, salary_offer, success=True, current_turn=current_turn
            )
            
            self.db.commit()
            
            message = (
                f"✓ Successfully poached {executive.first_name} {executive.last_name} "
                f"({executive.position}) from Company {target_company_id}! "
                f"Relation penalty: {self.POACH_SUCCESS_RELATION_PENALTY:.0f}"
            )
            
            return True, message, {
                "executive_id": target_executive_id,
                "executive_name": f"{executive.first_name} {executive.last_name}",
                "new_salary": salary_offer,
                "relation_impact": self.POACH_SUCCESS_RELATION_PENALTY
            }
        
        else:
            # 失败：高管拒绝，忠诚度提升
            executive.loyalty = min(100.0, executive.loyalty + 10.0)
            
            # 关系受损（但小于成功）
            new_relation = self.update_relation(
                poaching_company_id,
                target_company_id,
                game_id,
                self.POACH_FAILURE_RELATION_PENALTY,
                current_turn
            )
            
            # 记录行动
            action = DiplomaticAction(
                game_id=game_id,
                actor_company_id=poaching_company_id,
                target_company_id=target_company_id,
                action_type="POACH_EXECUTIVE",
                action_details=json.dumps({
                    "executive_id": target_executive_id,
                    "executive_name": f"{executive.first_name} {executive.last_name}",
                    "position": executive.position,
                    "salary_offer": salary_offer,
                    "current_salary": current_salary
                }),
                success=False,
                outcome_description=f"Failed to poach {executive.first_name} {executive.last_name}",
                cost_paid=50000,  # 谈判成本
                relation_change=self.POACH_FAILURE_RELATION_PENALTY,
                executed_turn=current_turn,
                resolved_turn=current_turn,
                is_public=False,  # 失败的挖角通常不公开
                discovered_by_target=True  # 但目标公司知道
            )
            self.db.add(action)
            
            # 生成事件
            self._generate_poaching_event(
                game_id, poaching_company_id, target_company_id,
                executive, salary_offer, success=False, current_turn=current_turn
            )
            
            self.db.commit()
            
            message = (
                f"✗ Failed to poach {executive.first_name} {executive.last_name}. "
                f"Executive remained loyal. Relation penalty: {self.POACH_FAILURE_RELATION_PENALTY:.0f}"
            )
            
            return False, message, {
                "executive_id": target_executive_id,
                "executive_name": f"{executive.first_name} {executive.last_name}",
                "relation_impact": self.POACH_FAILURE_RELATION_PENALTY,
                "executive_loyalty_boost": 10.0
            }
    
    # ==================== Dirty Trick #2: PR Attack ====================
    
    def launch_smear_campaign(
        self,
        attacker_company_id: int,
        target_company_id: int,
        budget: float,
        target_region_id: Optional[int],
        game_id: int,
        current_turn: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        发起公关攻击（抹黑竞争对手）
        
        Effect:
            - Target's Brand Perception reduced in region
            - Small chance of "Backfire" (scandal exposed, damages attacker)
        
        Formula:
            Brand Damage = Budget / 1,000,000 * 5.0  (每百万预算 = 5点品牌伤害)
            Backfire Chance = 10% (固定)
            
        Args:
            attacker_company_id: 攻击方公司ID
            target_company_id: 目标公司ID
            budget: 预算（游戏币）
            target_region_id: 目标区域ID（None=全球）
            game_id: 游戏ID
            current_turn: 当前回合
            
        Returns:
            (是否成功, 消息, 详细结果)
        """
        # 1. 获取公司
        attacker = self.db.query(Company).filter(Company.id == attacker_company_id).first()
        target = self.db.query(Company).filter(Company.id == target_company_id).first()
        
        if not attacker or not target:
            return False, "Company not found", {}
        
        # 2. 检查预算
        if attacker.cash < budget:
            return False, f"Insufficient funds (need ${budget:,.0f}, have ${attacker.cash:,.0f})", {}
        
        # 3. 扣除成本
        attacker.cash -= budget
        
        # 4. 计算伤害
        base_damage = (budget / 1_000_000) * 5.0  # 每百万 = 5点伤害
        
        # 随机波动 (0.8-1.2)
        damage_multiplier = random.uniform(0.8, 1.2)
        actual_damage = base_damage * damage_multiplier
        
        # 5. 检查是否反噬
        backfire_chance = 0.10  # 10%概率
        backfire = random.random() < backfire_chance
        
        if backfire:
            # 反噬：攻击方自己受伤
            self_damage = actual_damage * self.PR_ATTACK_BACKFIRE_SELF_DAMAGE
            
            attacker.brand_prestige = max(0.0, attacker.brand_prestige - self_damage)
            
            # 关系轻微受损
            new_relation = self.update_relation(
                attacker_company_id,
                target_company_id,
                game_id,
                -5.0,  # 轻微惩罚
                current_turn
            )
            
            # 记录行动
            action = DiplomaticAction(
                game_id=game_id,
                actor_company_id=attacker_company_id,
                target_company_id=target_company_id,
                action_type="PR_ATTACK",
                action_details=json.dumps({
                    "budget": budget,
                    "target_region_id": target_region_id,
                    "backfired": True
                }),
                success=False,
                outcome_description=f"PR attack backfired! Attacker's brand damaged by {self_damage:.1f} points",
                cost_paid=budget,
                value_gained=-self_damage,
                relation_change=-5.0,
                executed_turn=current_turn,
                resolved_turn=current_turn,
                is_public=True,  # 反噬通常会曝光
                discovered_by_target=True
            )
            self.db.add(action)
            
            # 生成事件
            self._generate_pr_attack_event(
                game_id, attacker_company_id, target_company_id,
                budget, actual_damage, backfire=True, current_turn=current_turn
            )
            
            self.db.commit()
            
            message = (
                f"✗ PR Attack BACKFIRED! Your smear campaign was exposed. "
                f"Your brand prestige reduced by {self_damage:.1f} points. "
                f"Budget wasted: ${budget:,.0f}"
            )
            
            return False, message, {
                "backfired": True,
                "self_damage": self_damage,
                "budget_wasted": budget,
                "relation_impact": -5.0
            }
        
        else:
            # 成功：目标品牌受损
            target.brand_prestige = max(0.0, target.brand_prestige - actual_damage)
            
            # 关系重创
            new_relation = self.update_relation(
                attacker_company_id,
                target_company_id,
                game_id,
                self.PR_ATTACK_RELATION_PENALTY,
                current_turn
            )
            
            # 记录行动
            action = DiplomaticAction(
                game_id=game_id,
                actor_company_id=attacker_company_id,
                target_company_id=target_company_id,
                action_type="PR_ATTACK",
                action_details=json.dumps({
                    "budget": budget,
                    "target_region_id": target_region_id,
                    "damage_dealt": actual_damage
                }),
                success=True,
                outcome_description=f"Successfully damaged target's brand by {actual_damage:.1f} points",
                cost_paid=budget,
                value_gained=actual_damage,
                relation_change=self.PR_ATTACK_RELATION_PENALTY,
                executed_turn=current_turn,
                resolved_turn=current_turn,
                is_public=False,  # 成功的抹黑通常隐蔽
                discovered_by_target=False  # 可能不知道是谁干的
            )
            self.db.add(action)
            
            # 生成事件
            self._generate_pr_attack_event(
                game_id, attacker_company_id, target_company_id,
                budget, actual_damage, backfire=False, current_turn=current_turn
            )
            
            self.db.commit()
            
            message = (
                f"✓ PR Attack successful! Target's brand prestige reduced by {actual_damage:.1f} points. "
                f"Cost: ${budget:,.0f}. Relation penalty: {self.PR_ATTACK_RELATION_PENALTY:.0f}"
            )
            
            return True, message, {
                "damage_dealt": actual_damage,
                "target_new_prestige": target.brand_prestige,
                "cost": budget,
                "relation_impact": self.PR_ATTACK_RELATION_PENALTY
            }
    
    # ==================== 事件生成 ====================
    
    def _generate_poaching_event(
        self,
        game_id: int,
        poaching_company_id: int,
        target_company_id: int,
        executive: Staff,
        salary_offer: float,
        success: bool,
        current_turn: int
    ):
        """生成挖角事件"""
        if success:
            headline = f"Executive Poached: {executive.first_name} {executive.last_name} Joins Company {poaching_company_id}"
            description = (
                f"{executive.first_name} {executive.last_name}, former {executive.position} "
                f"at Company {target_company_id}, has accepted a position at Company {poaching_company_id} "
                f"for an annual salary of ${salary_offer * 12:,.0f}. "
                f"This aggressive move has severely damaged relations between the two companies."
            )
            severity = "MODERATE"
        else:
            headline = f"Poaching Attempt Failed"
            description = (
                f"Company {poaching_company_id} attempted to poach {executive.first_name} {executive.last_name} "
                f"from Company {target_company_id}, but the executive declined the offer. "
                f"The attempt has strained relations between the companies."
            )
            severity = "MINOR"
        
        event = GameEvent(
            game_id=game_id,
            turn_number=current_turn,
            event_type="COMPANY",
            severity=severity,
            headline=headline,
            description=description,
            affected_company_ids=json.dumps([poaching_company_id, target_company_id]),
            is_player_visible=True
        )
        self.db.add(event)
    
    def _generate_pr_attack_event(
        self,
        game_id: int,
        attacker_company_id: int,
        target_company_id: int,
        budget: float,
        damage: float,
        backfire: bool,
        current_turn: int
    ):
        """生成公关攻击事件"""
        if backfire:
            headline = f"PR Scandal: Company {attacker_company_id} Caught in Smear Campaign"
            description = (
                f"Company {attacker_company_id}'s attempt to damage the reputation of Company {target_company_id} "
                f"has been exposed to the public. The backfired campaign has damaged their own brand credibility "
                f"and exposed unethical business practices. Brand prestige reduced by {damage:.1f} points."
            )
            severity = "MODERATE"
            affected = [attacker_company_id]
        else:
            headline = f"Brand Reputation Damaged"
            description = (
                f"Company {target_company_id} is facing negative publicity, with brand prestige falling by "
                f"{damage:.1f} points. The source of the campaign remains unclear, but industry observers "
                f"suspect competitive interference."
            )
            severity = "MINOR"
            affected = [target_company_id]
        
        event = GameEvent(
            game_id=game_id,
            turn_number=current_turn,
            event_type="COMPANY",
            severity=severity,
            headline=headline,
            description=description,
            affected_company_ids=json.dumps(affected),
            is_player_visible=True
        )
        self.db.add(event)


# 导出
__all__ = ["DiplomacyManager"]

