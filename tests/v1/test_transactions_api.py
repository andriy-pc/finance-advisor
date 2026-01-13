import os
import unittest
from http import HTTPStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import ASGITransport, AsyncClient

from advisor.db.db_models import Base, User, RawTransaction
from advisor.dependencies import get_session
from main import app

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

class TestTransactionsAPI(unittest.IsolatedAsyncioTestCase):
    engine = None
    session_factory = None

    async def asyncSetUp(self):
        # Create engine and tables if not exists (per-test class level simulation)
        if TestTransactionsAPI.engine is None:
            TestTransactionsAPI.engine = create_async_engine(
                TEST_DATABASE_URL,
                connect_args={"check_same_thread": False},
                echo=False
            )
            
            async with TestTransactionsAPI.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
                # Seed a test user (id=1) since it's hardcoded in the API
                await conn.execute(
                    User.__table__.insert().values(
                        id=1,
                        email="test@example.com",
                        first_name="Test",
                        last_name="User",
                        default_currency="USD"
                    )
                )
            
            TestTransactionsAPI.session_factory = async_sessionmaker(
                TestTransactionsAPI.engine, expire_on_commit=False, class_=AsyncSession
            )

        # Create a new session for each test
        self.db_session = TestTransactionsAPI.session_factory()
        
        # Override get_session dependency
        def override_get_session():
            yield self.db_session

        app.dependency_overrides[get_session] = override_get_session
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def asyncTearDown(self):
        # Clean up RawTransaction table after each test
        if self.db_session:
            await self.db_session.execute(Base.metadata.tables["RAW_TRANSACTION"].delete())
            await self.db_session.commit()
            await self.db_session.close()
        
        if hasattr(self, 'client'):
            await self.client.aclose()
        
        app.dependency_overrides.clear()

    @classmethod
    def tearDownClass(cls):
        # Sync cleanup if necessary, but engine dispose is async
        import asyncio
        if cls.engine:
            # This is a bit tricky in unittest, but engine will be closed eventually
            pass

    async def test_bulk_upload_success(self):
        # Path to valid CSV
        csv_path = os.path.join("tests", "resources", "valid_transactions.csv")
        
        with open(csv_path, "rb") as f:
            response = await self.client.post(
                "/api/v1/transactions/bulk",
                files={"file": ("valid_transactions.csv", f, "text/csv")}
            )
        
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        data = response.json()
        self.assertEqual(data["message"], "Transactions imported successfully")
        self.assertEqual(data["count"], 4)
        self.assertEqual(data["user_id"], 1)
        
        # Verify DB state
        result = await self.db_session.execute(select(RawTransaction))
        transactions = result.scalars().all()
        self.assertEqual(len(transactions), 4)
        
        # Verify some content
        descriptions = [t.description for t in transactions]
        self.assertIn("Grocery Store", descriptions)
        self.assertIn("Coffee Shop", descriptions)

    async def test_bulk_upload_unsupported_file(self):
        response = await self.client.post(
            "/api/v1/transactions/bulk",
            files={"file": ("test.txt", b"some text", "text/plain")}
        )
        
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Unsupported file type", response.json()["detail"])

    async def test_bulk_upload_invalid_csv(self):
        # Use invalid CSV that is missing required columns
        csv_path = os.path.join("tests", "resources", "invalid_no_required_columns.csv")
        
        with open(csv_path, "rb") as f:
            response = await self.client.post(
                "/api/v1/transactions/bulk",
                files={"file": ("invalid_no_required_columns.csv", f, "text/csv")}
            )
        
        # Based on the API implementation, it raises 400 if no valid transactions found
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("No valid transactions found", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
