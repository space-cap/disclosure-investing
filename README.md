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
uv run disclosure-investing fetch-documents --limit 10
uv run disclosure-investing classify-ai --limit 10
uv run streamlit run app/streamlit_app.py
```

전체 일일 흐름은 한 번에 실행할 수 있습니다.

```powershell
uv run disclosure-investing run-daily --document-limit 20 --ai-limit 10
```

매일 자동 실행하려면 PowerShell 스크립트를 사용합니다.

```powershell
.\scripts\run_daily.ps1
```

Windows 작업 스케줄러 등록 방법은 [docs/09-automation.md](./docs/09-automation.md)에 정리되어 있습니다.

원문/지표를 반영해 기존 AI 결과를 다시 만들고 싶으면 `--force` 또는 `--force-ai`를 사용합니다.

```powershell
uv run disclosure-investing classify-ai --limit 20 --force
uv run disclosure-investing run-daily --document-limit 20 --ai-limit 20 --force-ai
```

## Documents

개발 계획과 투자 기준 문서는 [docs](./docs) 폴더에 있습니다.
