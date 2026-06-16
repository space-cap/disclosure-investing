# 08. OpenAI 공시 분류 스키마

OpenAI API는 공시를 투자 추천으로 판단하지 않고, 검토 우선순위를 구조화해서 반환합니다.

## 실행 명령

```powershell
uv run disclosure-investing classify-ai --limit 10
```

`--limit`은 한 번에 AI 분류할 공시 수입니다. 비용과 속도 관리를 위해 처음에는 3~10건 정도로 실행합니다.

## 출력 필드

```json
{
  "primary_category": "risk",
  "event_type": "paid_capital_increase",
  "sentiment": "negative",
  "risk_level": "high",
  "confidence": 0.98,
  "summary": "유상증자 관련 정정 공시입니다.",
  "reason": "유상증자는 기존 주주의 지분 희석 가능성이 있어 위험 공시로 우선 검토해야 합니다.",
  "watch_points": [
    "발행 주식 수",
    "자금 사용 목적",
    "최대주주 참여 여부"
  ],
  "recommended_action": "avoid"
}
```

## 대분류

- `short_term_event`: 단기 이벤트 후보
- `long_term_candidate`: 중장기 관심 후보
- `risk`: 위험 공시
- `manual_review`: 수동검토 필요
- `ignore`: 투자 판단 영향 낮음

## 추천 액션

- `watch`: 관심
- `manual_review`: 수동검토
- `avoid`: 회피
- `ignore`: 무시
- `hold_for_more_data`: 추가 정보 대기

## 운영 원칙

- `buy`, `sell` 같은 매수/매도 표현은 사용하지 않습니다.
- 제공된 공시 메타데이터와 규칙 분류만 사용합니다.
- 제공되지 않은 정보는 추측하지 않습니다.
- 위험 공시는 보수적으로 분류합니다.
- 신뢰도가 낮거나 정보가 부족하면 수동검토로 보냅니다.

