from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
from src.core.security import get_api_key
from src.core.logging import get_logger
from src.schema.tao_dividends import DividendResponse
from src.api.services.dividends_service import fetch_dividend, store_dividend_query, trigger_sentiment_analysis
from src.db.depends import get_database
from databases import Database


router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/tao_dividends/",
    response_model=DividendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get TAO Dividends",
    description="Retrieves TAO dividends for a specified subnet and hotkey. Optionally triggers sentiment analysis and stake/unstake operations.",
    response_description="TAO dividend data and staking status",
    tags=["Dividends"],
    responses={
        status.HTTP_200_OK: {
            "description": "Successfully retrieved dividend data",
            "content": {
                "application/json": {
                    "example": {
                        "netuid": 1,
                        "hotkey": "123456",
                        "dividend": 123456789,
                        "cached": False,
                        "stake_tx_triggered": True
                    }
                }
            }
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Invalid or missing API Key"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Error querying TAO dividends"
        }
    }
)
async def get_tao_dividends(
    netuid: Optional[int] = Query(None, description="Subnet ID", example=18),
    hotkey: Optional[str] = Query(None, description="Account hotkey", example="123456"),
    trade: bool = Query(False, description="Whether to trigger sentiment analysis and stake/unstake based on it"),
    api_key: str = Depends(get_api_key),
    db: Database = Depends(get_database)
):
    """
    Get Tao dividends for a subnet and hotkey.
    
    - **netuid**: Subnet ID (optional, if omitted returns data for all netuids)
    - **hotkey**: Account hotkey (optional, if omitted returns data for all hotkeys on the specified netuid)
    - **trade**: Whether to trigger sentiment analysis and stake/unstake based on it
    
    Returns dividend data and indicates if a stake transaction was triggered.
    """
    try:
        logger.info(f"Tao dividends requested - netuid: {netuid}, hotkey: {hotkey}, trade: {trade}")
        
        # Fetch dividend data
        result = await fetch_dividend(netuid, hotkey)
        
        # Store the query in database
        await store_dividend_query(result)
        
        # trigger sentiment analysis if trade is True
        result["stake_tx_triggered"] = trigger_sentiment_analysis(result["netuid"], result["hotkey"]) if trade else False
        
        logger.info(f"Returning dividend result - netuid: {result['netuid']}, hotkey: {result['hotkey']}")
        return result
        
    except Exception as e:
        logger.error(f"Error querying Tao dividends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying Tao dividends: {str(e)}"
        )