from fastapi import APIRouter, HTTPException
from app.schema.chatinput import ReviewRequest, ReviewResponse
from app.schema.review_model import Model
from app.utils.playwright_utils import fetch_cookies
from app.core.config import settings, logger
from curl_cffi import requests
import json

ReviewRouter = APIRouter()

@ReviewRouter.post("/reviews", response_model=ReviewResponse)
async def get_reviews(request: ReviewRequest):
    if request.max_page <= 0:
        logger.info(f"Rejected request: max_page must be greater than 0, got {request.max_page}.")
        raise HTTPException(status_code=400, detail="max_page must be greater than 0.")
    try:
        # Get cookies (authentication)
        cookies = await fetch_cookies()
        logger.info(f"Cookies collected and Started scraping {request.company_code}")
        
        headers = {
            "User-Agent": settings.User_Agent,
            "next-router-state-tree": settings.next_router_state_tree,
            "rsc": settings.rsc,
        }

        overall_review = {}
        all_reviews = []
        extracted_data = None

        for PAGE in range(1, request.max_page + 1):
            REVIEWS_URL = (
                f"https://www.teamblind.com/company/{request.company_code}/reviews?page={PAGE}"
            )
            logger.info(f"Fetching {REVIEWS_URL}")

            resp = requests.get(
                REVIEWS_URL,
                headers=headers,
                cookies=cookies,
            )

            if resp and resp.text:
                raw_output_string = resp.text
                lines = raw_output_string.splitlines()

                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line.startswith("2:"):
                        extracted_data = stripped_line[2:].strip()
                        break
                if not extracted_data:
                    logger.error("No data found in response for page {PAGE}.")
                    raise HTTPException(status_code=404, detail=f"No data found in response for page {PAGE}.")
            else:
                logger.error("Failed to retrieve content or content is empty for page {PAGE}.")
                raise HTTPException(status_code=502, detail=f"Failed to retrieve content or content is empty for page {PAGE}.")

            try:
                data = json.loads(extracted_data)
            except Exception as e:
                logger.error(f"JSON decode error: {e}")
                raise HTTPException(status_code=500, detail="Failed to parse review data.")

            try:
                overall_review = data[0][3]["children"][0][3]
                reviews = data[0][3]["children"][1][3]["children"][3]["reviews"]["list"]
            except Exception as e:
                logger.error(f"Data structure error: {e}")
                raise HTTPException(status_code=500, detail="Unexpected data structure in review response.")

            if reviews:
                for review in reviews:
                    all_reviews.append(Model(**review).model_dump())
                logger.info(f"Fetched {len(all_reviews)} reviews so far.")
            else:
                logger.info(f"No reviews found on page {PAGE}.")
                break

        return ReviewResponse(
            overall_review=overall_review,
            reviews=all_reviews
        )

    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 