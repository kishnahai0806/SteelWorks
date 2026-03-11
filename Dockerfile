FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 8501

CMD ["sh", "-c", "poetry run streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT}"]
