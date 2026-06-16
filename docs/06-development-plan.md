# 06. DART API 기반 공시 자동 분류 프로그램 개발 계획서

## 1. 개발 목적

이 프로그램의 목적은 DART API로 한국 상장사의 공시를 자동 수집하고, 공시를 투자 관점에서 빠르게 분류해 사람이 확인할 수 있게 만드는 것입니다.

이 프로그램은 자동 매매 프로그램이 아닙니다. 목표는 매수와 매도 결정을 대신하는 것이 아니라, 매일 쏟아지는 공시 중에서 볼 만한 공시와 피해야 할 공시를 빠르게 걸러주는 투자 보조 도구를 만드는 것입니다.

## 2. 핵심 원칙

1. 위험 공시를 먼저 거른다.
2. 숫자 계산은 코드가 담당한다.
3. OpenAI API는 해석과 분류 보조에 사용한다.
4. 매수/매도 추천 대신 관심, 보류, 위험, 수동검토로 표시한다.
5. 모든 분류 결과에는 근거와 신뢰도를 남긴다.
6. 판단 기준을 계속 기록하고 개선한다.

## 3. 전체 구조

```text
DART API
  -> 공시 수집기
  -> 원문/메타데이터 저장
  -> 규칙 기반 1차 분류
  -> 숫자 계산
  -> OpenAI API 기반 2차 분류
  -> DB 저장
  -> 웹 화면 / 일일 리포트
```

처음에는 단순한 구조로 시작합니다.

```text
Python + SQLite + Streamlit
```

이후 필요해지면 다음 구조로 확장합니다.

```text
FastAPI + PostgreSQL + React/Next.js + Scheduler
```

## 4. MVP 범위

첫 번째 버전에서 반드시 구현할 기능은 다음입니다.

- DART API 인증키 설정
- 오늘 공시 목록 수집
- 공시 제목, 회사명, 접수번호, 접수일자 저장
- 공시 유형별 1차 분류
- 위험 공시 우선 표시
- OpenAI API를 이용한 공시 요약과 2차 분류
- SQLite 저장
- Streamlit 화면에서 분류별 조회
- 관심 공시 메모 작성

첫 버전에서 제외할 기능은 다음입니다.

- 자동 매매
- 실시간 초단타 대응
- 증권사 주문 API 연동
- 복잡한 백테스트
- 모바일 앱
- 사용자 계정/권한 관리

## 5. 기술 선택

### 5.1 언어

Python을 사용합니다.

이유:

- DART API 연동이 쉽습니다.
- 데이터 수집, 가공, 저장에 적합합니다.
- OpenAI API 연동이 쉽습니다.
- Streamlit으로 빠르게 화면을 만들 수 있습니다.
- 나중에 FastAPI로 확장하기 좋습니다.

### 5.2 데이터베이스

초기에는 SQLite를 사용합니다.

이유:

- 설치와 운영이 간단합니다.
- 개인 투자 보조 도구 MVP에는 충분합니다.
- 파일 하나로 백업할 수 있습니다.

나중에 데이터가 많아지고 여러 기기에서 쓰려면 PostgreSQL로 전환합니다.

### 5.3 화면

초기에는 Streamlit을 사용합니다.

이유:

- 개발 속도가 빠릅니다.
- 데이터 테이블, 필터, 상세 화면을 쉽게 만들 수 있습니다.
- 내부용 투자 보조 도구에 적합합니다.

나중에 정식 웹 서비스 형태가 필요하면 React 또는 Next.js로 전환합니다.

### 5.4 AI 분류

OpenAI API를 사용합니다.

사용 방식:

- Responses API 사용
- Structured Outputs 사용
- 정해진 JSON Schema로만 응답 받기
- 낮은 비용 모델과 고성능 모델을 비교 평가

## 6. 데이터 수집 설계

### 6.1 DART API에서 가져올 정보

기본 공시 목록:

- 회사명
- 종목코드
- 고유번호
- 공시 제목
- 접수번호
- 접수일자
- 제출인
- 시장 구분
- 공시 링크

가능하면 추가로 수집할 정보:

- 공시 원문
- 주요 숫자
- 정정 여부
- 관련 이전 공시
- 보고서 유형

### 6.2 수집 주기

초기 수집 주기:

- 장 전 1회
- 장 중 10분 또는 30분 단위
- 장 후 1회

초기에는 너무 자주 호출하지 않습니다. 먼저 하루 단위로 안정적으로 수집하고, 이후 장중 감시 기능을 붙입니다.

## 7. 분류 체계

### 7.1 1차 대분류

```text
short_term_event: 단기 이벤트 후보
long_term_candidate: 중장기 관심 후보
risk: 위험 공시
manual_review: 수동검토 필요
ignore: 투자 판단 영향 낮음
```

### 7.2 세부 이벤트 유형

단기 이벤트 후보:

- supply_contract: 단일판매ㆍ공급계약
- treasury_stock: 자기주식취득
- stock_retirement: 자기주식소각
- bonus_issue: 무상증자
- dividend: 배당
- earnings_guidance: 실적 전망/잠정실적

중장기 관심 후보:

- facility_investment: 신규시설투자
- regular_report: 정기보고서
- ir_event: 기업설명회
- insider_buying: 임원/주요주주 매수
- major_shareholder_change_positive: 긍정적 지분 변화

위험 공시:

- paid_capital_increase: 유상증자
- convertible_bond: 전환사채
- bond_with_warrant: 신주인수권부사채
- conversion_price_adjustment: 전환가액 조정
- capital_reduction: 감자
- largest_shareholder_change: 최대주주 변경
- audit_opinion_risk: 감사의견 리스크
- delisting_risk: 상장폐지/관리종목
- embezzlement_breach: 횡령ㆍ배임

## 8. 규칙 기반 1차 분류

OpenAI API를 호출하기 전에 제목과 공시 유형으로 먼저 분류합니다.

예시:

```text
제목에 "유상증자결정" 포함 -> risk / paid_capital_increase
제목에 "전환사채권발행결정" 포함 -> risk / convertible_bond
제목에 "단일판매ㆍ공급계약체결" 포함 -> short_term_event / supply_contract
제목에 "자기주식취득결정" 포함 -> short_term_event / treasury_stock
제목에 "신규시설투자" 포함 -> long_term_candidate / facility_investment
제목에 "기업설명회(IR)개최" 포함 -> long_term_candidate / ir_event
```

규칙 기반 분류의 장점은 빠르고 일관적이라는 점입니다. AI 분류는 이 결과를 보정하고 설명을 붙이는 역할로 사용합니다.

## 9. 숫자 계산 설계

숫자 계산은 OpenAI에 맡기지 않고 코드로 처리합니다.

계산할 지표:

```text
계약금액 / 최근 매출액 * 100
자사주 취득 예정금액 / 시가총액 * 100
신규시설투자금액 / 자기자본 * 100
신규 발행 가능 주식 수 / 기존 발행 주식 수 * 100
```

초기에는 DART 공시 안에 있는 숫자를 우선 사용합니다. 시가총액 등 시장 데이터가 필요한 항목은 이후 KRX, 증권 데이터 API, 수동 입력 중 하나로 보완합니다.

## 10. OpenAI API 분류 설계

OpenAI API는 다음 역할만 담당합니다.

- 공시 내용을 짧게 요약
- 규칙 기반 분류가 맞는지 검토
- 위험 요인 정리
- 추가 확인 포인트 제시
- 신뢰도 부여
- 수동검토 필요 여부 판단

OpenAI API가 하지 말아야 할 것:

- 매수 추천
- 매도 추천
- 목표가 제시
- 근거 없는 미래 실적 예측
- 제공되지 않은 정보 추측

### 10.1 출력 JSON 예시

```json
{
  "primary_category": "short_term_event",
  "event_type": "supply_contract",
  "sentiment": "positive",
  "risk_level": "medium",
  "confidence": 0.82,
  "summary": "최근 매출액 대비 의미 있는 공급계약 공시입니다.",
  "reason": "계약금액이 회사 규모 대비 크지만 계약기간과 상대방 정보를 추가 확인해야 합니다.",
  "watch_points": [
    "계약 상대방 신뢰도",
    "계약기간",
    "정정공시 가능성",
    "최근 주가 선반영 여부"
  ],
  "recommended_action": "watch"
}
```

### 10.2 추천 액션

```text
watch: 관심
manual_review: 수동검토
avoid: 회피
ignore: 무시
hold_for_more_data: 추가 정보 대기
```

`buy`, `sell` 같은 표현은 사용하지 않습니다.

## 11. 데이터베이스 초안

### 11.1 disclosures

```text
id
receipt_no
receipt_date
receipt_time
corp_code
corp_name
stock_code
report_name
market
dart_url
is_correction
raw_json
created_at
updated_at
```

### 11.2 classifications

```text
id
disclosure_id
rule_category
rule_event_type
ai_category
ai_event_type
sentiment
risk_level
confidence
summary
reason
watch_points_json
recommended_action
created_at
```

### 11.3 metrics

```text
id
disclosure_id
contract_amount
recent_sales
sales_ratio
treasury_buyback_amount
facility_investment_amount
equity_capital
equity_ratio
new_share_count
existing_share_count
dilution_ratio
created_at
```

### 11.4 notes

```text
id
disclosure_id
user_note
status
created_at
updated_at
```

## 12. 화면 설계

### 12.1 오늘의 공시 화면

표시 항목:

- 접수시간
- 종목명
- 공시 제목
- 1차 분류
- AI 분류
- 위험도
- 신뢰도
- 추천 액션
- 메모 여부

필터:

- 단기 이벤트
- 중장기 관심
- 위험 공시
- 수동검토
- 정정공시

### 12.2 공시 상세 화면

표시 항목:

- 공시 원문 링크
- AI 요약
- 분류 근거
- 계산된 지표
- 위험 요인
- 확인할 포인트
- 사용자 메모
- 관심/제외 상태

### 12.3 일일 요약 화면

표시 항목:

- 오늘 위험 공시 목록
- 오늘 단기 이벤트 후보
- 오늘 중장기 관심 후보
- 수동검토 필요 공시
- 관심종목 신규 공시

## 13. 개발 단계

### 1단계: 프로젝트 뼈대

- Python 프로젝트 생성
- 환경변수 설정
- SQLite 연결
- 기본 폴더 구조 생성

예상 산출물:

- 실행 가능한 기본 CLI
- `.env.example`
- DB 초기화 스크립트

### 2단계: DART API 수집

- DART API 키 설정
- 오늘 공시 목록 수집
- SQLite 저장
- 중복 접수번호 방지

예상 산출물:

- `fetch_disclosures` 명령
- `disclosures` 테이블 저장

### 3단계: 규칙 기반 분류

- 공시 제목 키워드 매핑
- 위험 공시 우선 분류
- 분류 결과 DB 저장

예상 산출물:

- `classify_rules` 명령
- 분류별 조회 가능

### 4단계: OpenAI API 분류

- Structured Outputs 스키마 정의
- OpenAI API 호출
- JSON 검증
- 실패 시 재시도 또는 수동검토 처리

예상 산출물:

- `classify_ai` 명령
- AI 요약과 판단 근거 저장

### 5단계: Streamlit 화면

- 오늘 공시 목록
- 분류별 필터
- 상세 화면
- 메모 기능

예상 산출물:

- 브라우저에서 확인 가능한 MVP 화면

### 6단계: 자동 실행

- 장 전/장 후 자동 수집
- 장중 주기 수집
- 일일 요약 생성

예상 산출물:

- 스케줄러
- 일일 요약 리포트

## 14. 폴더 구조 초안

```text
disclosure-investing/
  docs/
  app/
    main.py
    config.py
    database.py
    dart_client.py
    rule_classifier.py
    ai_classifier.py
    metrics.py
    streamlit_app.py
  data/
    disclosure.db
  scripts/
    init_db.py
    fetch_today.py
    classify_today.py
  tests/
    test_rule_classifier.py
    test_metrics.py
  .env.example
  pyproject.toml
  uv.lock
  README.md
```

## 15. 환경변수

```text
DART_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=
DATABASE_URL=
```

API 키는 코드에 직접 넣지 않습니다. `.env` 파일은 git에 올리지 않는 것을 원칙으로 합니다.

## 16. 테스트 계획

테스트할 항목:

- 같은 접수번호가 중복 저장되지 않는가
- 위험 공시가 우선 분류되는가
- 주요 키워드가 올바른 이벤트 유형으로 분류되는가
- 숫자 계산이 정확한가
- OpenAI 응답 JSON이 스키마와 맞는가
- AI 호출 실패 시 수동검토로 넘어가는가

초기 테스트는 규칙 분류와 숫자 계산부터 작성합니다. AI 응답은 실제 API 호출 테스트와 샘플 JSON 테스트를 분리합니다.

## 17. 운영 리스크

### 17.1 데이터 리스크

DART API 응답 지연, 공시 정정, 누락, 포맷 변경이 있을 수 있습니다.

대응:

- 원본 JSON 저장
- 접수번호 기준 중복 방지
- 정정공시 별도 표시
- 오류 로그 저장

### 17.2 AI 분류 리스크

AI가 공시를 과도하게 긍정적으로 해석하거나, 제공되지 않은 내용을 추측할 수 있습니다.

대응:

- Structured Outputs 사용
- 제공된 정보만 사용하도록 프롬프트 작성
- confidence 낮으면 수동검토
- 매수/매도 표현 금지

### 17.3 투자 판단 리스크

프로그램 결과를 투자 추천으로 오해할 수 있습니다.

대응:

- 화면에 투자 보조 도구임을 명시
- 추천 액션을 watch, avoid, manual_review 정도로 제한
- 사용자가 직접 메모와 최종 판단을 남기도록 설계

## 18. 성공 기준

MVP 성공 기준:

- 하루 공시를 자동 수집할 수 있다.
- 위험 공시를 빠르게 걸러낼 수 있다.
- 단기 이벤트 후보와 중장기 관심 후보를 나눠 볼 수 있다.
- AI 요약과 확인 포인트가 투자 공부에 도움이 된다.
- 사용자가 관심 공시를 메모하고 나중에 복기할 수 있다.

이 기준을 만족하면 다음 단계로 시장 데이터 연동, 관심종목 알림, Slack/메일 리포트, 백테스트 기능을 검토합니다.
