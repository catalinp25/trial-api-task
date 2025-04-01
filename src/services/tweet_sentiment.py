import aiohttp, re
from typing import  List
from groq import AsyncGroq
from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


class SentimentAnalysisService:
    def __init__(self):
        """Initialize the sentiment analysis service"""
        logger.info("Initializing SentimentAnalysisService")

        self.datura_api_key = settings.DATURA_API_KEY 
        self.groq_client =  AsyncGroq(api_key=settings.GROQ_API_KEY)

    
    def _extract_numeric_value(self, text):
        match = re.search(r'is:\s*(\d+)', text)
        if match:
            return int(match.group(1))
        else:
            return None
        
    async def get_tweets(self, netuid: int) -> List[str]:
        """
        Get recent tweets about a specific Bittensor subnet
        
        Args:
            netuid: Subnet ID to search for
            
        Returns:
            List of tweet texts
        """
        logger.info(f"Fetching tweets for netuid: {netuid}")
        
        # Datura API endpoint for Twitter search
        url = "https://apis.datura.ai/twitter"
        
        # Set up headers with API key
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.datura_api_key
        }
        
        # Query parameters
        payload = {
            "query": f"Bittensor netuid {netuid}",
            "max_results": 10
        }
        
        tweets = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error fetching tweets: {response.status} - {error_text}")
                        raise Exception(f"Error fetching tweets: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    # Extract tweet texts
                    
                    tweets  = [tweet["text"] for tweet in data]
                    
                    logger.info(f"Retrieved {len(tweets)} tweets for netuid {netuid}")
                    return tweets
                    
        except Exception as e:
            logger.error(f"Error in get_tweets: {str(e)}", exc_info=True)
            raise
    
    async def analyze_sentiment(self, tweets: List[str], netuid: int) -> int:
        """
        Analyze sentiment of tweets about a subnet
        
        Args:
            tweets: List of tweets to analyze
            netuid: Subnet ID
            
        Returns:
            Sentiment score from -100 (very negative) to +100 (very positive)
        """
        # If no tweets, return neutral sentiment
        if not tweets:
            logger.info(f"No tweets available for netuid {netuid}, returning neutral sentiment")
            return 0
        
        logger.info(f"Analyzing sentiment for {len(tweets)} tweets about netuid {netuid}")
        

        # Combine tweets into a formatted prompt
        tweets_text = "\n".join([f"- {tweet}" for tweet in tweets])
        
        # Create prompt for sentiment analysis
        prompt = f"""
        Analyze the sentiment of the following tweets about Bittensor subnet {netuid}.
        Provide a sentiment score from -100 (extremely negative) to +100 (extremely positive).
        Return only the numerical score do not include any other text.
        
        Tweets:
        {tweets_text}
        
        Sentiment score:
        """
        

        try:
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=settings.GROQ_MODEL,
            )

            ai_response = chat_completion.choices[0].message.content.strip()
                        
            print(f"AI response: {ai_response}")

            try:
                value = int(ai_response)
                return value
            except Exception as e:
                numeric_value = self._extract_numeric_value(ai_response)
                return numeric_value
            
        except Exception as e:
            logger.error(f"Error in analyze_sentiment: {str(e)}", exc_info=True)
            raise
    
    async def calculate_stake_amount(self, sentiment_score: int) -> float:
        """
        Calculate stake amount based on sentiment score
        
        Args:
            sentiment_score: Sentiment score from -100 to +100
            
        Returns:
            Amount to stake (positive) or unstake (negative)
        """
        # Calculate stake amount as 0.01 TAO per sentiment point
        if sentiment_score is None:
            logger.error("Sentiment score is None, cannot calculate stake amount")
            return 0
        
        stake_amount = 0.01 * sentiment_score
        logger.info(f"Calculated stake amount for sentiment {sentiment_score}: {stake_amount}")
        return stake_amount


# Create a singleton instance
sentiment_service = SentimentAnalysisService()