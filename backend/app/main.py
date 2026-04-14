from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import api, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prediction Mini App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "Prediction Mini App API"}
