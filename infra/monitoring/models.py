"""
Data models for market monitoring
"""
from pydantic import BaseModel


class Price(BaseModel):
    """Price data model"""
    open: float
    close: float
    high: float
    low: float
    volume: int
    time: str


class PriceResponse(BaseModel):
    """API response model for prices"""
    ticker: str
    prices: list[Price]
