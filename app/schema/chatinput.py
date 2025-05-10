from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ReviewRequest(BaseModel):
    company_code: str
    max_page: Optional[int]

class ReviewResponse(BaseModel):
    overall_review: Dict[str, Any]
    reviews: List[Dict[str, Any]] 