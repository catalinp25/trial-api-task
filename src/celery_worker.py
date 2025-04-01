from celery import Celery
from src.core.config import settings
from src.core.logging import get_logger
from src.services.tweet_sentiment import sentiment_service
from src.services.blockchain import bittensor_service
from src.db.models import StakeTransaction
from src.db.depends import db
import asyncio


logger = get_logger(__name__)

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


@celery_app.task
def stake_based_on_sentiment(netuid: int, hotkey: str):
    """
    analyze sentiment and stake/unstake TAO.
    """
    logger.info(f"Starting sentiment analysis task for netuid: {netuid}, hotkey: {hotkey}")
    
    async def _process():
        try:
            await bittensor_service.reset_connections()
            
            # Get tweets about this subnet
            logger.info(f"Retrieving tweets for netuid: {netuid}")
            tweets = await sentiment_service.get_tweets(netuid)
            
            # Analyze sentiment
            logger.info(f"Analyzing sentiment for {len(tweets)} tweets")
            sentiment_score = await sentiment_service.analyze_sentiment(tweets, netuid)
            logger.info(f"Sentiment score for netuid {netuid}: {sentiment_score}")
            
            # Calculate stake amount
            stake_amount = await sentiment_service.calculate_stake_amount(sentiment_score)
            logger.info(f"Calculated stake amount: {stake_amount}")
            
            if sentiment_score is None:
                sentiment_score = 0
            
            # Record transaction details
            tx_details = {
                "netuid": netuid,
                "hotkey": hotkey,
                "sentiment_score": sentiment_score,
                "amount": abs(stake_amount),
                "action": "stake" if stake_amount > 0 else "unstake",
                "status": "pending"
            }
            
            # Stake or unstake
            tx_hash = None

            if stake_amount > 0 and stake_amount != 0 and sentiment_score != 0:
                logger.info(f"Positive sentiment ({sentiment_score}), staking {stake_amount} TAO")
                tx_hash = await bittensor_service.stake(abs(stake_amount), netuid, hotkey)
            elif stake_amount < 0 and stake_amount != 0 and sentiment_score != 0:
                logger.info(f"Negative sentiment ({sentiment_score}), unstaking {abs(stake_amount)} TAO")
                tx_hash = await bittensor_service.unstake(abs(stake_amount), netuid, hotkey)
            else:
                #  no action
                logger.info("Neutral sentiment, no staking action needed")
                tx_details["status"] = "skipped"
            
            # Update transaction details
            if tx_hash:
                tx_details["tx_hash"] = tx_hash
                tx_details["status"] = "completed"
                logger.info(f"Transaction completed with hash: {tx_hash}")
            
            # Store in database
            logger.info("Storing transaction details in database")
            await db.connect()
            await StakeTransaction.create(**tx_details)
            await db.disconnect()
            
            return {
                "success": True,
                "sentiment_score": sentiment_score,
                "stake_amount": stake_amount,
                "tx_hash": tx_hash
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment-based staking: {str(e)}", exc_info=True)
            # Store error in database
            tx_details = {
                "netuid": netuid,
                "hotkey": hotkey,
                "sentiment_score": 0,
                "amount": 0,
                "action": "error",
                "status": "failed",
                "error": str(e)
            }
            
            try:
                logger.info("Storing error details in database")
                await db.connect()
                await StakeTransaction.create(**tx_details)
                await db.disconnect()
            except Exception as db_error:
                logger.error(f"Error storing transaction: {str(db_error)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_process())
    finally:
        loop.close()