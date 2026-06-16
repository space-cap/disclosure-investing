# 09. 자동 실행 운영 가이드

이 문서는 공시 수집과 분류를 매일 자동으로 실행하기 위한 Windows 작업 스케줄러 설정 방법입니다.

## 1. 수동 실행 확인

먼저 PowerShell에서 아래 명령이 정상 동작하는지 확인합니다.

```powershell
cd H:\lee\disclosure-investing
.\scripts\run_daily.ps1
```

스크립트는 다음 일을 합니다.

- `uv run disclosure-investing run-daily` 실행
- `logs/run_daily-YYYYMMDD-HHMMSS.log` 로그 저장
- `data/run_daily.lock` 잠금 파일로 중복 실행 방지
- 실행 결과를 SQLite `job_runs` 테이블에 저장

## 2. 작업 스케줄러 등록

처음에는 하루 2회 실행을 추천합니다.

- 장 전: 오전 8:30
- 장 후: 오후 4:10

관리자 권한 PowerShell에서 실행합니다.

```powershell
$project = "H:\lee\disclosure-investing"
$script = Join-Path $project "scripts\run_daily.ps1"
$action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" `
  -WorkingDirectory $project

$morning = New-ScheduledTaskTrigger -Daily -At "08:30"
$afterClose = New-ScheduledTaskTrigger -Daily -At "16:10"

Register-ScheduledTask `
  -TaskName "Disclosure Investing Daily" `
  -Action $action `
  -Trigger @($morning, $afterClose) `
  -Description "DART 공시 자동 수집, 분류, 일일 요약 생성" `
  -RunLevel Limited
```

## 3. 등록 확인

```powershell
Get-ScheduledTask -TaskName "Disclosure Investing Daily"
```

즉시 한 번 실행해 보고 싶으면 아래 명령을 사용합니다.

```powershell
Start-ScheduledTask -TaskName "Disclosure Investing Daily"
```

## 4. 실행 상태 확인

실행 후 Streamlit 화면의 `운영 상태` 탭에서 확인합니다.

```powershell
uv run streamlit run app/streamlit_app.py
```

확인할 항목:

- 마지막 자동 실행 성공/실패
- 수집 건수
- 원문 수집 건수
- 지표 재계산 건수
- AI 분류 건수
- 최근 원문 수집 오류
- 최근 리포트 다운로드

## 5. 스케줄 삭제

```powershell
Unregister-ScheduledTask -TaskName "Disclosure Investing Daily" -Confirm:$false
```

## 6. 장중 감시로 확장할 때

장 전/장 후 실행이 안정되면 장중 30분 주기를 추가합니다.

```powershell
$intraday = New-ScheduledTaskTrigger -Once -At "09:10" `
  -RepetitionInterval (New-TimeSpan -Minutes 30) `
  -RepetitionDuration (New-TimeSpan -Hours 6)
```

장중 감시는 OpenAI 비용과 DART 응답 제한을 보면서 천천히 켜는 것이 좋습니다.
