"""
搜索适配层 —— 抽象基类。
"""

from abc import ABC, abstractmethod


class SearchAdapter(ABC):
    """搜索适配器抽象基类。"""

    @abstractmethod
    def search(self, query: str, timeout: float = 5) -> list[str]:
        """执行搜索，返回结果摘要列表。"""
        ...
