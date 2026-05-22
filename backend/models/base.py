"""
数据模型基类和通用Mixin
"""
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declared_attr
from datetime import datetime


class TimestampMixin:
    """时间戳Mixin：自动添加创建/更新时间"""
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime, 
            default=datetime.utcnow,
            nullable=False,
            comment="创建时间"
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
            comment="更新时间"
        )


class BaseModel:
    """
    通用基础模型类
    提供通用字段和方法
    """
    
    def to_dict(self) -> dict:
        """
        将模型转换为字典
        排除私有属性和SQLAlchemy内部属性
        """
        result = {}
        for key in self.__mapper__.c.keys():
            value = getattr(self, key)
            # 处理datetime对象
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    def __repr__(self) -> str:
        """更友好的字符串表示"""
        attrs = ", ".join(
            f"{k}={v!r}" 
            for k, v in self.to_dict().items() 
            if not k.startswith("_")
        )
        return f"<{self.__class__.__name__}({attrs})>"


__all__ = ["TimestampMixin", "BaseModel"]

