import os
import unittest
from http import HTTPStatus

from fastapi.testclient import TestClient
from sqlalchemy import select

from advisor.db.db_models import Base, RawTransaction
from advisor.dependencies import get_session
from main import app
from tests.db_test_helper import DBTestHelper


class TestTransactionsAPI(unittest.IsolatedAsyncioTestCase):

    client = TestClient(app=app)

    async def asyncSetUp(self) -> None:
        self.db_helper = DBTestHelper()

        def override_get_session():
            yield self.db_helper._in_memory_async_session()

        app.dependency_overrides[get_session] = override_get_session

    async def test_bulk_upload_success(self):

        # ARRANGE
        async with self.db_helper.generate_in_memory_async_engine(Base):
            csv_path = os.path.join("tests", "resources", "valid_transactions.csv")
            with open(csv_path, "rb") as f:

                # ACT
                response = self.client.post(
                    "/api/v1/transactions/bulk", files={"file": ("valid_transactions.csv", f, "text/csv")}
                )

            # ASSERT
            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            data = response.json()
            self.assertEqual(data["message"], "Transactions imported successfully")
            self.assertEqual(data["count"], 4)
            self.assertEqual(data["user_id"], 1)

            async with self.db_helper._in_memory_async_session() as session:
                result = await session.execute(select(RawTransaction))
                transactions = result.scalars().all()
                self.assertEqual(len(transactions), 4)

                descriptions = [t.description for t in transactions]
                self.assertIn("Grocery Store", descriptions)
                self.assertIn("Coffee Shop", descriptions)

    async def test_bulk_upload_unsupported_file(self):
        # ARRANGE
        async with self.db_helper.generate_in_memory_async_engine(Base):

            # ACT
            response = self.client.post(
                "/api/v1/transactions/bulk", files={"file": ("test.txt", b"some text", "text/plain")}
            )

            # ASSERT
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
            self.assertIn("Unsupported file type", response.json()["detail"])

    async def test_bulk_upload_invalid_csv(self):
        # ARRANGE
        csv_path = os.path.join("tests", "resources", "invalid_no_required_columns.csv")

        async with self.db_helper.generate_in_memory_async_engine(Base):
            with open(csv_path, "rb") as f:
                # ACT
                response = self.client.post(
                    "/api/v1/transactions/bulk", files={"file": ("invalid_no_required_columns.csv", f, "text/csv")}
                )

            # ASSERT
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
            self.assertIn("No valid transactions found", response.json()["detail"])
