from typing import Dict, Type

from advisor.ingestion.base_parser import BaseParser
from advisor.ingestion.csv_parser import CSVParser
from advisor.utils.file_utils import extract_file_extension


class ParserFactory:
    _parsers: Dict[str, Type[BaseParser]] = {".csv": CSVParser}

    @classmethod
    def get_parser(cls, filename: str) -> BaseParser:
        file_extension = "." + extract_file_extension(filename)
        parser_cls = cls._parsers.get(file_extension)
        if not parser_cls:
            raise ValueError(f"No parser found for extension: {file_extension}")
        return parser_cls()
