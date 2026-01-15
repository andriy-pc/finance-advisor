from abc import ABC, abstractmethod
from typing import BinaryIO, List

from advisor.db.db_models import RawTransaction


class BaseParser(ABC):

    @abstractmethod
    def parse_transactions(self, file_content: BinaryIO, filename: str, user_id: int) -> List[RawTransaction]:
        """Parses a file and returns a list of RawTransaction models."""
        pass
