from pydantic import BaseModel, Field


class DividendResponse(BaseModel):
    netuid: int = Field(..., description="Subnet ID")
    hotkey: str = Field(..., description="Account hotkey")
    dividend: float = Field(..., description="TAO dividend value")
    cached: bool = Field(..., description="Whether the result was served from cache")
    stake_tx_triggered: bool = Field(..., description="Whether a stake transaction was triggered")
    
    class Config:
        json_schema_extra = {
            "example": {
                "netuid": 18,
                "hotkey": "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",
                "dividend": 123456789,
                "cached": False,
                "stake_tx_triggered": True
            }
        }
