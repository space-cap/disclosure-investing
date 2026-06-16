# Disclosure Investing

DART API 기반 공시 자동 수집, 분류, 복기 도구입니다.

이 프로젝트는 자동 매매 프로그램이 아닙니다. 공시를 빠르게 걸러보고, 위험 공시와 관심 공시를 사람이 검토하기 쉽게 정리하는 투자 보조 도구입니다.

## Quick Start

```powershell
uv sync
Copy-Item .env.example .env
uv run disclosure-investing init-db
uv run pytest
```

`DART_API_KEY`를 `.env`에 입력한 뒤 오늘 공시를 수집합니다.

```powershell
uv run disclosure-investing fetch-disclosures
uv run disclosure-investing classify-rules
uv run streamlit run app/streamlit_app.py
```

## Documents

개발 계획과 투자 기준 문서는 [docs](./docs) 폴더에 있습니다.
