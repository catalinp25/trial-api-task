import json, bittensor, asyncio
from typing import Dict, Optional
from bittensor.core.async_subtensor import AsyncSubtensor
from src.core.config import settings
from src.services.redis_cache import cache
from src.core.logging import get_logger


logger = get_logger(__name__)

class BitensorService:
    def __init__(self):
        """Initialize the Bittensor service with network settings"""
        logger.info(f"Initializing BitensorService for network: {settings.BITTENSOR_NETWORK}")
        self._subtensor = None
        self._wallet = None
        self._loop = None
        
    async def _get_subtensor(self):
        """Get or initialize the async subtensor"""
        current_loop = asyncio.get_running_loop()
        
        # If subtensor exists but is bound to a different loop, reset it
        if self._subtensor is not None and self._loop is not current_loop:
            logger.info("Event loop changed, resetting AsyncSubtensor instance")
            await self.reset_connections()
            
        if self._subtensor is None:
            logger.info("Creating new AsyncSubtensor instance")
            self._subtensor = AsyncSubtensor() #network=settings.BITTENSOR_NETWORK)
            self._loop = current_loop
            
        return self._subtensor
    
    async def reset_connections(self):
        """Reset subtensor connection when event loop changes"""
        if self._subtensor:
            try:
                logger.info("Closing existing AsyncSubtensor connection")
                await self._subtensor.close()
            except Exception as e:
                logger.warning(f"Error closing subtensor connection: {str(e)}")
            finally:
                self._subtensor = None
                self._loop = None
    
    async def _get_wallet(self):
        """Get or initialize the bittensor wallet"""
        if self._wallet is None:
            logger.info("Creating new wallet instance")
            
            self._wallet = bittensor.wallet(
                    name=settings.BITTENSOR_WALLET_NAME, 
                    hotkey=settings.BITTENSOR_WALLET_HOTKEY
            )
            
            # If a seed phrase is provided, create wallet with it
            if hasattr(settings, 'WALLET_SEED_PHRASE') and settings.WALLET_SEED_PHRASE:
                logger.info("Creating wallet with mnemonic from configuration")
                self._wallet.regenerate_coldkey(mnemonic=settings.WALLET_SEED_PHRASE, 
                                                overwrite=True, use_password=False)
                
        return self._wallet
    
    async def get_tao_dividends(self, netuid: Optional[int] = None, hotkey: Optional[str] = None) -> Dict:
        """
        Query Tao dividends for a subnet and hotkey.
        
        Args:
            netuid: Subnet ID (optional, defaults to settings.DEFAULT_NETUID)
            hotkey: Account hotkey (optional, defaults to settings.DEFAULT_HOTKEY)
            
        Returns:
            Dict containing dividend data and metadata
        """
        try:
            # Set default values if not provided
            if netuid is None:
                netuid = await self.get_default_netuid()
            if hotkey is None:
                hotkey = await self.get_default_hotkey()
                
            # Generate cache key
            cache_key = cache.generate_key("tao_dividends", netuid, hotkey)
            
            logger.info(f"Cache key for Tao dividends - {cache_key}")

            # Try to get from cache first
            cached_data = await cache.get(cache_key)
            if cached_data:
                logger.info(f"Retrieved cached dividend data for netuid: {netuid}, hotkey: {hotkey}")
                result =  json.loads(cached_data)
                result["cached"] = True
                return result
            
            # Not in cache, query blockchain
            logger.info(f"Querying blockchain for Tao dividends - netuid: {netuid}, hotkey: {hotkey}")
            subtensor = await self._get_subtensor()
            
            result = await subtensor.substrate.query(
                module='SubtensorModule',
                storage_function='TaoDividendsPerSubnet',
                params=[netuid, hotkey]
            )

            dividend = result.value
            
            
            # Format the result
            result = {
                "netuid": netuid,
                "hotkey": hotkey,
                "dividend": dividend,
                "cached": False
            }
            
            # Store in cache for 2 minutes
            await cache.set(cache_key, json.dumps(result), ttl=settings.CACHE_TTL)
            logger.info(f"Storing dividend data in cache - netuid: {netuid}, hotkey: {hotkey}")
            
            return result
            
        except Exception as e:
            # Log the error and re-raise
            logger.error(f"Error querying TaoDividendsPerSubnet: {str(e)}", exc_info=True)
            raise
    
    async def stake(self, amount: float, netuid: int = None, hotkey: str = None) -> str:
        """
        Stake TAO to a hotkey on a subnet.
        
        Args:
            amount: Amount of TAO to stake
            netuid: Subnet ID (optional, defaults to settings.DEFAULT_NETUID)
            hotkey: Account hotkey (optional, defaults to settings.DEFAULT_HOTKEY)
            
        Returns:
            Transaction hash string
        """
        try:
            # Set default values if not provided
            if netuid is None:
                netuid = await self.get_default_netuid()
            if hotkey is None:
                hotkey = await self.get_default_hotkey()
            
            # Ensure amount is positive
            if amount <= 0:
                raise ValueError(f"Stake amount must be positive, got {amount}")
                
            logger.info(f"Staking {amount} TAO to netuid: {netuid}, hotkey: {hotkey}")
            
            # Get subtensor and wallet
            subtensor = await self._get_subtensor()
            wallet = await self._get_wallet()
            
            # Convert amount to Balance type if needed
            amount_balance = bittensor.Balance.from_tao(amount)
            
            # Submit stake transaction
            tx_hash = await subtensor.add_stake(
                wallet=wallet,
                netuid=netuid,
                hotkey_ss58=hotkey,
                amount=abs(amount_balance),
                wait_for_inclusion=True,
                wait_for_finalization=False
            )
            
            logger.info(f"Stake transaction submitted with hash: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            # Log the error and re-raise
            logger.error(f"Error staking TAO: {str(e)}", exc_info=True)
            raise
    
    async def unstake(self, amount: float, netuid: int = None, hotkey: str = None) -> str:
        """
        Unstake TAO from a hotkey on a subnet.
        
        Args:
            amount: Amount of TAO to unstake
            netuid: Subnet ID (optional, defaults to settings.DEFAULT_NETUID)
            hotkey: Account hotkey (optional, defaults to settings.DEFAULT_HOTKEY)
            
        Returns:
            Transaction hash string
        """
        try:
            # Set default values if not provided
            if netuid is None:
                netuid = await self.get_default_netuid()
            if hotkey is None:
                hotkey = await self.get_default_hotkey()
            
            # Ensure amount is positive
            if amount <= 0:
                raise ValueError(f"Unstake amount must be positive, got {amount}")
                
            logger.info(f"Unstaking {amount} TAO from netuid: {netuid}, hotkey: {hotkey}")
            
            # Get subtensor and wallet
            subtensor = await self._get_subtensor()
            wallet = await self._get_wallet()
            
            # Convert amount to Balance type if needed
            amount_balance = bittensor.Balance.from_tao(amount)
            
            # Submit unstake transaction
            tx_hash = await subtensor.unstake(
                wallet=wallet,
                netuid=netuid,
                hotkey_ss58=hotkey,
                amount=abs(amount_balance),
                wait_for_inclusion=True,
                wait_for_finalization=False
            )
            
            logger.info(f"Unstake transaction submitted with hash: {tx_hash}")
            return tx_hash
            
        except Exception as e:
            # Log the error and re-raise
            logger.error(f"Error unstaking TAO: {str(e)}", exc_info=True)
            raise
    
    async def get_default_netuid(self) -> int:
        """Get the default subnet ID from settings"""
        return settings.DEFAULT_NETUID
    
    async def get_default_hotkey(self) -> str:
        """Get the default hotkey from settings"""
        return settings.DEFAULT_HOTKEY
    
    async def close(self):
        """Close the subtensor connection"""
        await self.reset_connections()


# Create a singleton instance
bittensor_service = BitensorService()