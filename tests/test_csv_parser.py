import io
import unittest
from datetime import date
from decimal import Decimal

from advisor.ingestion.csv_parser import CSVParser


class TestCSVParser(unittest.TestCase):
    def test_parse_valid_csv(self):
        csv_content = """Date,Amount,Description
2023-01-01,100.50,Grocery Store
2023-01-02,20.00,Coffee Shop"""

        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        parser = CSVParser()
        transactions = parser.parse_transactions(file_obj, "test.csv", user_id=1)

        self.assertEqual(len(transactions), 2)

        t1 = transactions[0]
        self.assertEqual(t1.date, date(2023, 1, 1))
        self.assertEqual(t1.amount, Decimal("100.50"))
        self.assertEqual(t1.description, "Grocery Store")

        t2 = transactions[1]
        self.assertEqual(t2.amount, Decimal("20.00"))

    def test_parse_ignoring_invalid_row(self):
        csv_content = """Date,Amount,Description
2023-01-01,,Invalid Amount
2023-01-02,50.00,Valid Row"""

        file_obj = io.BytesIO(csv_content.encode("utf-8"))
        parser = CSVParser()
        transactions = parser.parse_transactions(file_obj, "test.csv", user_id=1)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].description, "Valid Row")


