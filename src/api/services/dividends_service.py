from typing import Optional, Dict, Any
from src.services.blockchain import bittensor_service
from src.celery_worker import stake_based_on_sentiment
from src.db.models import DividendQuery
from src.core.logging import get_logger


logger = get_logger(__name__)

async def fetch_dividend(netuid: Optional[int], hotkey: Optional[str]) -> Dict[str, Any]:
    """Helper function to fetch dividend data with appropriate defaults."""
    # Determine values to use, fetching defaults if needed
    actual_netuid = netuid if netuid is not None else await bittensor_service.get_default_netuid()
    actual_hotkey = hotkey if hotkey is not None else await bittensor_service.get_default_hotkey()
    
    logger.info(f"Fetching dividend for netuid: {actual_netuid}, hotkey: {actual_hotkey}")
    return await bittensor_service.get_tao_dividends(actual_netuid, actual_hotkey)

async def store_dividend_query(result: Dict[str, Any]) -> None:
    """Store dividend query in database."""
    try:
        await DividendQuery.create(
            netuid=result["netuid"],
            hotkey=result["hotkey"],
            dividend=result["dividend"],
            cached=result["cached"]
        )
        logger.info(f"Stored dividend query in database - netuid: {result['netuid']}, hotkey: {result['hotkey']}")
    except Exception as db_error:
        logger.info(f"Error storing dividend query: {str(db_error)}", exc_info=True)

def trigger_sentiment_analysis(netuid: int, hotkey: str) -> bool:
    """Trigger sentiment analysis and return if stake transaction was triggered."""
    stake_based_on_sentiment.delay(
        netuid=netuid,
        hotkey=hotkey
    )
    logger.info(f"Triggered sentiment analysis task  for netuid: {netuid}, hotkey: {hotkey}")
    return True