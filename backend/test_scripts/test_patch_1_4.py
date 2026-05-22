"""
Patch 1.4 功能测试脚本
测试所有新功能：历史记录、二手车、合约、Logit模型
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import *
from backend.core.economics.market_math import MultinomialLogitModel as MultinomialLogit
from backend.core.economics.used_market import UsedCarMarket as UsedMarketLogic
from backend.utils.logger import get_logger
import random

logger = get_logger(__name__)


def test_multinomial_logit():
    """测试Multinomial Logit模型"""
    logger.info("\n" + "="*60)
    logger.info("测试 1: Multinomial Logit 模型")
    logger.info("="*60)
    
    # 初始化模型
    logit = MultinomialLogit(beta_params={
        'price': -0.0001,
        'performance': 0.05,
        'brand': 0.02
    })
    
    # 测试车辆选项
    options = [
        {
            'id': 1,
            'attributes': {'price': 25000, 'performance': 80, 'brand': 70}
        },
        {
            'id': 2,
            'attributes': {'price': 30000, 'performance': 90, 'brand': 85}
        },
        {
            'id': 3,
            'attributes': {'price': 20000, 'performance': 60, 'brand': 50}
        }
    ]
    
    # 计算概率
    probs = logit.calculate_probabilities(options)
    
    logger.info("车辆选项:")
    for i, opt in enumerate(options):
        logger.info(f"  选项{opt['id']}: 价格${opt['attributes']['price']:,}, "
                   f"性能{opt['attributes']['performance']}, 品牌{opt['attributes']['brand']}")
        logger.info(f"    → 选择概率: {probs[i]*100:.2f}%")
    
    assert len(probs) == len(options), "概率数量应等于选项数量"
    assert abs(sum(probs) - 1.0) < 0.01, "概率之和应为1"
    logger.info("✓ Logit模型测试通过")


def test_sales_history():
    """测试销售历史记录"""
    logger.info("\n" + "="*60)
    logger.info("测试 2: 销售历史记录")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # 创建测试记录
        sales_record = SalesHistory(
            game_id=1,
            turn_number=100,
            region_id=1,
            car_trim_id=1,
            quantity=150,
            revenue=3750000.0
        )
        db.add(sales_record)
        db.commit()
        
        # 查询验证
        records = db.query(SalesHistory).filter(
            SalesHistory.game_id == 1,
            SalesHistory.turn_number == 100
        ).all()
        
        logger.info(f"创建销售记录: 回合{sales_record.turn_number}, 数量{sales_record.quantity}, 收入${sales_record.revenue:,.0f}")
        logger.info(f"查询结果: 找到{len(records)}条记录")
        
        assert len(records) > 0, "应能查询到销售记录"
        logger.info("✓ 销售历史记录测试通过")
        
        # 清理
        db.delete(sales_record)
        db.commit()
        
    finally:
        db.close()


def test_financial_history():
    """测试财务历史记录"""
    logger.info("\n" + "="*60)
    logger.info("测试 3: 财务历史记录")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # 创建测试记录
        financial_record = FinancialHistory(
            game_id=1,
            turn_number=100,
            company_id=1,
            revenue=5000000.0,
            expense=3500000.0,
            net_profit=1500000.0,
            cash_balance=10000000.0
        )
        db.add(financial_record)
        db.commit()
        
        # 查询验证
        records = db.query(FinancialHistory).filter(
            FinancialHistory.game_id == 1,
            FinancialHistory.company_id == 1
        ).all()
        
        logger.info(f"创建财务记录: 收入${financial_record.revenue:,.0f}, "
                   f"费用${financial_record.expense:,.0f}, 利润${financial_record.net_profit:,.0f}")
        logger.info(f"查询结果: 找到{len(records)}条记录")
        
        assert len(records) > 0, "应能查询到财务记录"
        logger.info("✓ 财务历史记录测试通过")
        
        # 清理
        db.delete(financial_record)
        db.commit()
        
    finally:
        db.close()


def test_used_car_inventory():
    """测试二手车库存"""
    logger.info("\n" + "="*60)
    logger.info("测试 4: 二手车库存")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # 创建测试记录
        used_car = UsedCarInventory(
            game_id=1,
            region_id=1,
            car_trim_id=1,
            condition_score=85,
            quantity=50,
            base_price=18000.0
        )
        db.add(used_car)
        db.commit()
        
        # 查询验证
        inventory = db.query(UsedCarInventory).filter(
            UsedCarInventory.game_id == 1,
            UsedCarInventory.region_id == 1
        ).all()
        
        logger.info(f"创建二手车库存: 数量{used_car.quantity}, 状况{used_car.condition_score}/100, 价格${used_car.base_price:,.0f}")
        logger.info(f"查询结果: 找到{len(inventory)}条记录")
        
        assert len(inventory) > 0, "应能查询到二手车库存"
        logger.info("✓ 二手车库存测试通过")
        
        # 清理
        db.delete(used_car)
        db.commit()
        
    finally:
        db.close()


def test_supplier_contract():
    """测试供应商合约"""
    logger.info("\n" + "="*60)
    logger.info("测试 5: 供应商合约")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # 创建测试合约
        contract = SupplierContract(
            game_id=1,
            company_id=1,
            supplier_id=1,
            material_type="STEEL",
            lock_price=500.0,
            duration_months=12,
            monthly_quantity=10000,
            start_turn=100,
            end_turn=112,
            is_active=True
        )
        db.add(contract)
        db.commit()
        
        # 查询验证
        contracts = db.query(SupplierContract).filter(
            SupplierContract.game_id == 1,
            SupplierContract.company_id == 1,
            SupplierContract.is_active == True
        ).all()
        
        logger.info(f"创建供应商合约: 材料{contract.material_type}, 锁定价格${contract.lock_price}, "
                   f"数量{contract.monthly_quantity}/月, 期限{contract.duration_months}月")
        logger.info(f"查询结果: 找到{len(contracts)}个活跃合约")
        
        assert len(contracts) > 0, "应能查询到活跃合约"
        logger.info("✓ 供应商合约测试通过")
        
        # 清理
        db.delete(contract)
        db.commit()
        
    finally:
        db.close()


def test_region_used_car_flags():
    """测试地区二手车进出口标志"""
    logger.info("\n" + "="*60)
    logger.info("测试 6: 地区二手车进出口标志")
    logger.info("="*60)
    
    db = SessionLocal()
    try:
        # 查询地区
        region = db.query(Region).first()
        
        if region:
            logger.info(f"地区: {region.name}")
            logger.info(f"  允许二手车出口: {region.allow_used_export}")
            logger.info(f"  允许二手车进口: {region.allow_used_import}")
            
            # 测试修改
            original_export = region.allow_used_export
            region.allow_used_export = not original_export
            db.commit()
            
            db.refresh(region)
            assert region.allow_used_export == (not original_export), "标志应已更改"
            
            # 恢复
            region.allow_used_export = original_export
            db.commit()
            
            logger.info("✓ 地区二手车标志测试通过")
        else:
            logger.warning("⚠ 没有找到地区数据，跳过测试")
    
    finally:
        db.close()


def run_all_tests():
    """运行所有测试"""
    logger.info("\n" + "="*80)
    logger.info("开始 Patch 1.4 功能测试")
    logger.info("="*80)
    
    tests = [
        ("Multinomial Logit模型", test_multinomial_logit),
        ("销售历史记录", test_sales_history),
        ("财务历史记录", test_financial_history),
        ("二手车库存", test_used_car_inventory),
        ("供应商合约", test_supplier_contract),
        ("地区二手车标志", test_region_used_car_flags),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"✗ {test_name}测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    logger.info("\n" + "="*80)
    logger.info(f"测试完成: {passed}通过, {failed}失败")
    logger.info("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
