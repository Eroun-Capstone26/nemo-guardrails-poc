from typing import Literal, Optional
from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    action: Literal["respond", "send_email", "grant_permission"] = Field(
        description="The action the agent should take."
    )
    message: str = Field(description="Natural language message to the user.")
    to: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    user: Optional[str] = None
    permission: Optional[str] = None
    reason: Optional[str] = None
