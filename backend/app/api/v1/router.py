from fastapi import APIRouter

from app.api.v1 import auth, blockchain, contact, datasets, federated, predictions, reports, trust, chatbot

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["prediction"])
api_router.include_router(trust.router, prefix="/trust", tags=["trust"])
api_router.include_router(blockchain.router, prefix="/blockchain", tags=["blockchain"])
api_router.include_router(federated.router, prefix="/federated", tags=["federated-learning"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
api_router.include_router(chatbot.router, prefix="", tags=["chatbot"])
