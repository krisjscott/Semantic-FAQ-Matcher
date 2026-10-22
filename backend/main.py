import os
from collections import Counter
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .evaluation import Evaluator
from .matcher import FAQMatcher, MODEL_NAME 
from .repository import CSVFAQRepository, FAQ
from .schemas import EvaluationRequest, MatchRequest, MatchResponse

ROOT = Path(__file__).resolve().parent


def create_app(matcher: FAQMatcher | None = None, data_dir: Path | None = None) -> FastAPI:
    faq_path = Path(os.getenv('FAQ_DATA_PATH', str(ROOT / 'semantic_faq_dataset.csv')))
    test_path = data_dir or Path(os.getenv('FAQ_TEST_DATA_DIR', str(ROOT / 'data')))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.matcher = matcher or FAQMatcher(CSVFAQRepository(faq_path))
        app.state.evaluator = Evaluator(app.state.matcher, test_path)
        app.state.dataset_sha256 = sha256(faq_path.read_bytes()).hexdigest()
        yield

    app = FastAPI(title='Semantic FAQ Matcher', version='1.0.0', lifespan=lifespan)
    app.add_middleware(CORSMiddleware,
                       allow_origins=os.getenv('FAQ_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(','),
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.get('/api/health')
    def health(request: Request):
        return {'status': 'ready', 'model': MODEL_NAME, 'faq_count': len(request.app.state.matcher.faqs)}

    @app.get('/api/metadata')
    def metadata(request: Request):
        faqs = request.app.state.matcher.faqs
        return dict(model=MODEL_NAME, faq_count=len(faqs),
                    categories=[{'name': name, 'count': count} for name, count in sorted(Counter(f.category for f in faqs).items())],
                    default_threshold=0.45, semantic_weight=0.85, keyword_weight=0.15,
                    dataset_sha256=request.app.state.dataset_sha256,
                    datasets=request.app.state.evaluator.inventory())

    @app.get('/api/faqs', response_model=list[FAQ])
    def faqs(request: Request, search: str = Query('', max_length=200), category: str | None = None):
        return [f for f in request.app.state.matcher.faqs
                if (not category or f.category == category)
                and search.casefold() in f'{f.faq_id} {f.question} {f.answer}'.casefold()]

    @app.get('/api/dataset/download')
    def download():
        return FileResponse(faq_path, media_type='text/csv', filename='semantic_faq_dataset.csv')

    @app.post('/api/match', response_model=MatchResponse)
    def match(body: MatchRequest, request: Request):
        return request.app.state.matcher.find_answer(body.query, body.threshold)

    @app.post('/api/evaluate')
    def evaluate(body: EvaluationRequest, request: Request):
        try:
            return request.app.state.evaluator.run(body.threshold)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return app


app = create_app()

