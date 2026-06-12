"""采集适配器（设计文档第 4 章 / 5.3）。

通过统一的 ReviewIngestor 接口，支持多数据源接入：
新数据源只需实现 base.ReviewIngestor，即可在 1 天内接入（第 17.3 指标）。
"""

from app.services.ingestion.base import RawReview, ReviewIngestor
from app.services.ingestion.registry import get_ingestor

__all__ = ["RawReview", "ReviewIngestor", "get_ingestor"]
