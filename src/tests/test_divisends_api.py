import pytest, json, asyncio
import sys
import os
# Add project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from main import app  # Import the FastAPI app
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status
from src.services.blockchain import bittensor_service
from src.services.tweet_sentiment import sentiment_service
from src.services.redis_cache import cache
from src.celery_worker import stake_based_on_sentiment
from src.db.models import db, DividendQuery, StakeTransaction


# TestClient for synchronous tests
client = TestClient(app)

# Valid API key for testing
TEST_API_KEY = "YourSecretApiKey"
HEADERS = {"X-API-Key": TEST_API_KEY}

# Test data
TEST_NETUID = 18
TEST_HOTKEY = "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v"
TEST_DIVIDEND = 123456789
TEST_TWEETS = ["Great progress on Bittensor netuid 18!", "Very impressed with the subnet's performance"]
TEST_SENTIMENT_SCORE = 75
TEST_STAKE_AMOUNT = 0.75  # 0.01 * sentiment score


@pytest.fixture
def mock_db_connect():
    """Mock database connection and disconnect"""
    async def mock_connect():
        return True
    
    async def mock_disconnect():
        return True
    
    with patch.object(db, "connect", mock_connect), \
         patch.object(db, "disconnect", mock_disconnect):
        yield


@pytest.fixture
def mock_dividend_query_create():
    """Mock DividendQuery.create"""
    async def mock_create(**kwargs):
        return 1
    
    with patch.object(DividendQuery, "create", mock_create):
        yield


@pytest.fixture
def mock_cache():
    """Mock Redis cache"""
    async def mock_get(key):
        return None
    
    async def mock_set(key, value, ttl=None):
        return True
    
    with patch.object(cache, "get", mock_get), \
         patch.object(cache, "set", mock_set), \
         patch.object(cache, "generate_key", MagicMock(return_value="test_key")):
        yield


@pytest.fixture
def mock_bittensor_service():
    """Mock bittensor service with predefined responses"""
    mock_dividend_response = {
        "netuid": TEST_NETUID,
        "hotkey": TEST_HOTKEY,
        "dividend": TEST_DIVIDEND,
        "cached": False
    }
    
    async def mock_get_tao_dividends(netuid=None, hotkey=None):
        return mock_dividend_response
    
    async def mock_get_default_netuid():
        return TEST_NETUID
    
    async def mock_get_default_hotkey():
        return TEST_HOTKEY
    
    with patch.object(bittensor_service, "get_tao_dividends", mock_get_tao_dividends), \
         patch.object(bittensor_service, "get_default_netuid", mock_get_default_netuid), \
         patch.object(bittensor_service, "get_default_hotkey", mock_get_default_hotkey):
        yield


@pytest.fixture
def mock_sentiment_service():
    """Mock sentiment service for testing"""
    async def mock_get_tweets(netuid):
        return TEST_TWEETS
    
    async def mock_analyze_sentiment(tweets, netuid):
        return TEST_SENTIMENT_SCORE
    
    async def mock_calculate_stake_amount(sentiment_score):
        return TEST_STAKE_AMOUNT
    
    with patch.object(sentiment_service, "get_tweets", mock_get_tweets), \
         patch.object(sentiment_service, "analyze_sentiment", mock_analyze_sentiment), \
         patch.object(sentiment_service, "calculate_stake_amount", mock_calculate_stake_amount):
        yield


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution"""
    with patch.object(stake_based_on_sentiment, "delay", MagicMock(return_value=MagicMock(id="task-id"))):
        yield


class TestDividendsAPI:
    """Test cases for the /tao_dividends endpoint"""
    
    def test_missing_api_key(self):
        """Test that requests without API key are rejected"""
        response = client.get("/api/v1/tao_dividends")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or missing API Key" in response.json().get("detail")
    
    def test_invalid_api_key(self):
        """Test that requests with invalid API key are rejected"""
        response = client.get("/api/v1/tao_dividends", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or missing API Key" in response.json().get("detail")
    
    def test_tao_dividends_default_params(self, mock_db_connect, mock_dividend_query_create, 
                                         mock_cache, mock_bittensor_service, mock_celery_task):
        """Test endpoint without specifying parameters (should use defaults)"""
        response = client.get("/api/v1/tao_dividends", headers=HEADERS)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["netuid"] == TEST_NETUID
        assert data["hotkey"] == TEST_HOTKEY
        assert data["dividend"] == TEST_DIVIDEND
        assert data["cached"] is False
        assert data["stake_tx_triggered"] is False  # trade=False by default
    
    def test_tao_dividends_specified_params(self, mock_db_connect, mock_dividend_query_create, 
                                           mock_cache, mock_bittensor_service, mock_celery_task):
        """Test endpoint with specific netuid and hotkey"""
        response = client.get(
            f"/api/v1/tao_dividends?netuid={TEST_NETUID}&hotkey={TEST_HOTKEY}", 
            headers=HEADERS
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["netuid"] == TEST_NETUID
        assert data["hotkey"] == TEST_HOTKEY
        assert data["dividend"] == TEST_DIVIDEND
        assert data["cached"] is False
        assert data["stake_tx_triggered"] is False
    
    def test_tao_dividends_with_trade(self, mock_db_connect, mock_dividend_query_create, 
                                     mock_cache, mock_bittensor_service, mock_celery_task):
        """Test endpoint with trade=True to trigger sentiment analysis and staking"""
        response = client.get(
            f"/api/v1/tao_dividends?netuid={TEST_NETUID}&hotkey={TEST_HOTKEY}&trade=true", 
            headers=HEADERS
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["netuid"] == TEST_NETUID
        assert data["hotkey"] == TEST_HOTKEY
        assert data["dividend"] == TEST_DIVIDEND
        assert data["cached"] is False
        assert data["stake_tx_triggered"] is True
        
        # Verify Celery task was called with correct parameters
        stake_based_on_sentiment.delay.assert_called_once_with(
            netuid=TEST_NETUID, 
            hotkey=TEST_HOTKEY
        )
    
    def test_only_netuid_specified(self, mock_db_connect, mock_dividend_query_create, 
                                  mock_cache, mock_bittensor_service, mock_celery_task):
        """Test endpoint with only netuid specified"""
        response = client.get(
            f"/api/v1/tao_dividends?netuid={TEST_NETUID}", 
            headers=HEADERS
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["netuid"] == TEST_NETUID
        assert "hotkey" in data
        assert data["dividend"] == TEST_DIVIDEND
    
    def test_only_hotkey_specified(self, mock_db_connect, mock_dividend_query_create, 
                                  mock_cache, mock_bittensor_service, mock_celery_task):
        """Test endpoint with only hotkey specified"""
        response = client.get(
            f"/api/v1/tao_dividends?hotkey={TEST_HOTKEY}", 
            headers=HEADERS
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "netuid" in data
        assert data["hotkey"] == TEST_HOTKEY
        assert data["dividend"] == TEST_DIVIDEND


@pytest.mark.asyncio
class TestConcurrency:
    """Test concurrent access to the API endpoint"""
    
    async def test_concurrent_requests(self, mock_db_connect, mock_dividend_query_create, 
                                      mock_cache, mock_bittensor_service, mock_celery_task):
        """Test the API can handle many concurrent requests"""
        import aiohttp
        
        async with aiohttp.AsyncClient(app=app, base_url="http://test") as ac:
            # Make 50 concurrent requests to simulate high load
            tasks = []
            for _ in range(50):
                tasks.append(
                    ac.get(
                        "/api/v1/tao_dividends", 
                        headers=HEADERS
                    )
                )
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks)
            
            # Check all responses were successful
            for response in responses:
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["netuid"] == TEST_NETUID
                assert data["hotkey"] == TEST_HOTKEY
                assert data["dividend"] == TEST_DIVIDEND


@pytest.mark.asyncio
class TestWorkerTask:
    """Test cases for the Celery worker task"""
    
    @pytest.fixture
    def mock_stake_transaction_create(self):
        """Mock StakeTransaction.create"""
        async def mock_create(**kwargs):
            return 1
        
        with patch.object(StakeTransaction, "create", mock_create):
            yield
    
    async def test_stake_based_on_sentiment(self, mock_db_connect, mock_sentiment_service,
                                           mock_stake_transaction_create):
        """Test the sentiment analysis and staking background task"""
        with patch.object(bittensor_service, "stake", AsyncMock(return_value="tx_hash_123")):
            # Execute the task directly (not through Celery)
            result = await stake_based_on_sentiment._process()
            
            # Verify the result
            assert result["success"] is True
            assert result["sentiment_score"] == TEST_SENTIMENT_SCORE
            assert result["stake_amount"] == TEST_STAKE_AMOUNT
            assert result["tx_hash"] == "tx_hash_123"
            
            # Verify stake was called with correct parameters
            bittensor_service.stake.assert_called_once_with(
                TEST_STAKE_AMOUNT, 
                TEST_NETUID, 
                TEST_HOTKEY
            )
    
    async def test_unstake_based_on_sentiment(self, mock_db_connect, mock_stake_transaction_create):
        """Test unstaking based on negative sentiment"""
        # Mock negative sentiment
        async def mock_get_tweets(netuid):
            return ["Disappointed with Bittensor netuid performance"]
        
        async def mock_analyze_sentiment(tweets, netuid):
            return -60
        
        async def mock_calculate_stake_amount(sentiment_score):
            return -0.6  # 0.01 * -60
        
        with patch.object(sentiment_service, "get_tweets", mock_get_tweets), \
             patch.object(sentiment_service, "analyze_sentiment", mock_analyze_sentiment), \
             patch.object(sentiment_service, "calculate_stake_amount", mock_calculate_stake_amount), \
             patch.object(bittensor_service, "unstake", AsyncMock(return_value="tx_hash_456")):
            
            # Execute the task directly
            result = await stake_based_on_sentiment._process()
            
            # Verify the result
            assert result["success"] is True
            assert result["sentiment_score"] == -60
            assert result["stake_amount"] == -0.6
            assert result["tx_hash"] == "tx_hash_456"
            
            # Verify unstake was called with correct parameters (amount should be positive)
            bittensor_service.unstake.assert_called_once_with(
                0.6,  # Absolute value of stake amount
                TEST_NETUID, 
                TEST_HOTKEY
            )
            
    async def test_error_handling(self, mock_db_connect, mock_stake_transaction_create):
        """Test error handling in the worker task"""
        # Mock services to raise an exception
        async def mock_get_tweets(netuid):
            raise Exception("Twitter API error")
        
        with patch.object(sentiment_service, "get_tweets", mock_get_tweets):
            # Execute the task directly
            result = await stake_based_on_sentiment._process()
            
            # Verify error is returned
            assert result["success"] is False
            assert "error" in result
            assert "Twitter API error" in result["error"]