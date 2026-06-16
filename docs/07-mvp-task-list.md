# 07. MVP 개발 체크리스트

## 완료

- [x] 프로젝트 기본 폴더 생성
- [x] uv 프로젝트 설정
- [x] `pyproject.toml` 작성
- [x] `.env.example` 작성
- [x] SQLite DB 스키마 작성
- [x] DB 초기화 CLI 작성
- [x] DART 공시 목록 수집 클라이언트 작성
- [x] DART 원문 문서 수집 CLI 작성
- [x] 공급계약 등 핵심 지표 추출 모듈 작성
- [x] 규칙 기반 공시 분류 모듈 작성
- [x] OpenAI Structured Outputs 분류 모듈 작성
- [x] AI 분류 CLI 작성
- [x] AI 강제 재분류 옵션 추가
- [x] 일괄 실행 `run-daily` 추가
- [x] 일일 요약 리포트 생성 추가
- [x] 지표 계산 모듈 작성
- [x] 실행 이력 `job_runs` 테이블 추가
- [x] `run-daily` 실행 결과 저장
- [x] 자동 실행 PowerShell 스크립트 추가
- [x] Windows 작업 스케줄러 운영 문서 추가
- [x] Streamlit 기본 목록 화면 작성
- [x] Streamlit 목록에 AI 분류 컬럼 추가
- [x] 상세 화면에 핵심 숫자 표시
- [x] Streamlit 운영 상태 탭 추가
- [x] 규칙 분류 테스트 작성
- [x] AI 분류 스키마 테스트 작성
- [x] 지표 계산 테스트 작성

## 다음 작업

- [x] `.env` 파일 생성 후 `DART_API_KEY` 입력
- [x] 실제 DART API로 오늘 공시 수집 테스트
- [x] 수집된 공시를 규칙 기반으로 분류
- [x] OpenAI API 2차 분류 테스트
- [x] Streamlit 화면에서 AI 분류 결과 확인
- [x] 공시 상세 화면 추가
- [x] 사용자 메모 저장 기능 추가
- [x] 장 전/장 후 일일 요약 리포트 추가
- [x] Streamlit 화면에서 일일 요약 리포트 보기
- [x] Streamlit 화면에서 자동 실행 상태 보기

## 실행 명령

```powershell
uv sync
uv run disclosure-investing init-db
uv run disclosure-investing fetch-disclosures
uv run disclosure-investing classify-rules
uv run disclosure-investing fetch-documents --limit 10
uv run disclosure-investing classify-ai --limit 10
uv run disclosure-investing classify-ai --limit 10 --force
uv run disclosure-investing run-daily --document-limit 20 --ai-limit 10
uv run disclosure-investing daily-report
uv run streamlit run app/streamlit_app.py
.\scripts\run_daily.ps1
uv run pytest
```
