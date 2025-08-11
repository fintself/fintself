from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal

AccountType = Literal["corriente", "credito", "debito", "prepago"]


class MovementModel(BaseModel):
    """
    Pydantic model to represent a bank movement.
    """

    date: datetime = Field(..., description="Date of the movement.")
    description: str = Field(..., description="Description of the movement.")
    amount: Decimal = Field(
        ...,
        description="Amount of the movement (positive for income, negative for expenses).",
    )
    currency: str = Field(..., description="Currency of the movement (e.g., CLP, USD).")
    transaction_type: Optional[str] = Field(
        None, description="Type of transaction (e.g., 'Debit', 'Credit', 'Transfer')."
    )
    account_id: Optional[str] = Field(
        None, description="Identifier of the source/destination account."
    )
    account_type: Optional[AccountType] = Field(
        None,
        description="Type of account. Must be one of: corriente, credito, debito, prepago.",
    )
    raw_data: Optional[dict] = Field(
        {}, description="Additional raw data from the scraper."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2023-10-26T10:00:00",
                "description": "Compra en Supermercado",
                "amount": "-15000.00",
                "currency": "CLP",
                "transaction_type": "Cargo",
                "account_id": "123456789",
                "account_type": "credito",
                "raw_data": {"original_desc": "COMPRA SUPERMERCADO LIDER"},
            }
        }
