import os
import time
import pickle
import logging
from typing import List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_DIR = os.environ.get("MODEL_DIR", "/app/models")

app = FastAPI(title="RecSys API", version="1.0.0")

model = None
user_enc_classes = None
item_enc_classes = None
items_list = None
user_item_matrix_shape = None

_stats = {
    "total_requests": 0,
    "total_latency": 0.0,
    "start_time": time.time(),
}


def _load_pickle(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)


@app.on_event("startup")
def startup():
    global model, user_enc_classes, item_enc_classes, items_list, user_item_matrix_shape

    model_path = os.path.join(MODEL_DIR, "model.pkl")
    mappings_path = os.path.join(MODEL_DIR, "mappings.pkl")
    items_path = os.path.join(MODEL_DIR, "items.pkl")

    try:
        model = _load_pickle(model_path)
        logger.info("Model loaded from %s", model_path)
    except Exception as e:
        logger.error("Failed to load model: %s", e)
        raise

    try:
        mappings = _load_pickle(mappings_path)
        user_enc_classes = mappings["user_encoder_classes"]
        item_enc_classes = mappings["item_encoder_classes"]
        user_item_matrix_shape = mappings["user_item_matrix_shape"]
        logger.info("Mappings loaded: %d users, %d items", len(user_enc_classes), len(item_enc_classes))
    except Exception as e:
        logger.error("Failed to load mappings: %s", e)
        raise

    try:
        items_list = _load_pickle(items_path)
        logger.info("Items list loaded: %d items", len(items_list))
    except Exception as e:
        logger.error("Failed to load items: %s", e)
        raise


def _get_popular_items(top_n: int) -> List[str]:
    if items_list is None:
        return []
    n = min(top_n, len(items_list))
    return [str(item) for item in items_list[:n]]


@app.get("/health")
def health():
    if model is None or user_enc_classes is None or items_list is None:
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "healthy"}


@app.get("/recommend/{visitorid}")
def recommend(
    visitorid: str,
    top_n: int = Query(default=10, ge=1, le=100),
):
    _stats["total_requests"] += 1
    start = time.time()

    try:
        visitorid_int = int(visitorid)
    except (ValueError, TypeError):
        logger.warning("Invalid visitorid: %s", visitorid)
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid visitorid: {visitorid}"},
        )

    if visitorid_int not in user_enc_classes:
        logger.info("visitorid %s not in mapping, returning popular items", visitorid)
        popular = _get_popular_items(top_n)
        return {
            "visitorid": visitorid,
            "fallback": True,
            "recommendations": popular,
        }

    user_idx = int(np.searchsorted(user_enc_classes, visitorid_int))

    try:
        from scipy.sparse import csr_matrix
        user_items = model.user_items[user_idx]
        recommendations, scores = model.recommend(
            user_idx, user_items, N=top_n, filter_already_liked_items=True
        )
    except Exception as e:
        logger.error("Recommendation failed for visitorid %s: %s", visitorid, e)
        popular = _get_popular_items(top_n)
        return {
            "visitorid": visitorid,
            "fallback": True,
            "recommendations": popular,
        }

    result_items = []
    for idx, score in zip(recommendations, scores):
        if idx < len(item_enc_classes):
            item_id = str(item_enc_classes[idx])
        elif idx < len(items_list):
            item_id = str(items_list[idx])
        else:
            item_id = str(idx)
        result_items.append({"itemid": item_id, "score": float(round(score, 6))})

    latency = time.time() - start
    _stats["total_latency"] += latency

    logger.info(
        "visitorid=%s top_n=%d latency=%.3fs", visitorid, top_n, latency
    )

    return {
        "visitorid": visitorid,
        "fallback": False,
        "recommendations": result_items,
    }


@app.get("/stats")
def stats():
    uptime = time.time() - _stats["start_time"]
    total = _stats["total_requests"]
    avg_latency = _stats["total_latency"] / total if total > 0 else 0.0

    return {
        "total_requests": total,
        "average_latency_seconds": round(avg_latency, 4),
        "uptime_seconds": round(uptime, 2),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
