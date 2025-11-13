from pydantic import BaseModel, Field
from typing import Optional

class TicketData(BaseModel):
    name: str = Field(..., description="Ticket name/title")
    description: Optional[str] = Field(None, description="Ticket description")
    status: Optional[str] = Field(None, description="Ticket status")
    priority: Optional[str] = Field(None, description="Ticket priority")
    type: Optional[str] = Field(None, description="Ticket type")

class Service(BaseModel):
    name: str

class Integration(BaseModel):
    id: str
    name: str

class Organization(BaseModel):
    id: str
    name: str

class Collection(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class TicketSummary(BaseModel):
    id: str
    name: str
    type: str
    status: str