from fastapi import FastAPI
from config import settings
from api.routes import auth, projects, credits, health, literature, agents, citation
from api.middleware import setup_cors, setup_rate_limiting

app = FastAPI(title=settings.PROJECT_NAME)

# Middleware registration order matters: the last middleware added becomes the
# outermost layer. Rate limiting is added first (so it can short-circuit 429s)
# and CORS last (so browsers still receive CORS headers on throttled responses).
setup_rate_limiting(app)
setup_cors(app)

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(credits.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(literature.router, prefix=settings.API_V1_STR)
app.include_router(agents.router, prefix=settings.API_V1_STR)
app.include_router(citation.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "Backend is running"}