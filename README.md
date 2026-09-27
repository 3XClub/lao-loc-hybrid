
# Lao-LOC+ Hybrid Strict Web App

사용 목적:
- 매일 베트남 시간 오전 08:00에 SOXL 최신 일봉을 가져와 중계표 생성
- 사용자는 실제 체결가/수량만 입력
- Layer Ledger, 현금, 전체 평단, Layer별 손익, 전체 계좌 손익 자동 갱신
- 모든 중계표와 체결 기록을 SQLite에 영구 저장

## 현재 전략 규칙 (v0.1)

- 시작 운용금: $10,000 (웹에서 DB reset 또는 settings 수정 가능)
- 1 Line: 초기 운용금 / 13
- Flat Buy1: `Close × 1.07 - 0.04`
- Flat Buy2: `Close × 0.999`
- 보유 중 Buy1: 최근 체결 Layer와 Close/Anchor 비율에 따라 기존 역추적 factor 적용
- 보유 중 Buy2: `min(Close × 0.999, 최근 Layer 매수가 - 0.02)`
- Sell 기본: 최근 Layer부터 LIFO, Layer 매수가 × 1.0015
- Profit-Layer First: 비용까지 포함해 해당 Layer가 순이익일 때 정상 매도
- Hybrid Strict: `ADX(14) >= 25` AND `20거래일 수익률 <= -20%`이면 손실 Layer Exit 허용
- 매수/매도 비용: 각각 0.02%
- 체결: LOC 방식. 실제 체결은 사용자가 직접 입력하며 앱은 임의로 체결 처리하지 않음.

주의:
이 앱은 지금까지 역추적된 Lao/P 규칙을 구현한 연구/운용 도구입니다. 원 저자의 비공개 규칙을 100% 재현한다고 보장하지 않습니다.

## 실행

Python 3.11+ 권장.

```bash
pip install -r requirements.txt
python app.py
```

브라우저:
`http://localhost:8000`

## 환경변수

- `APP_TIMEZONE=Asia/Ho_Chi_Minh`
- `DATABASE_PATH=/path/to/persistent/lao_loc.db`
- `PORT=8000`
- `DISABLE_SCHEDULER=1` : 내부 08:00 스케줄러를 끄고 싶을 때
- `SOXL_CSV_PATH=/path/to/SOXL.csv` : Yahoo Finance 대신 CSV를 사용할 때

## 서버 배포

`Procfile`은 gunicorn 1 worker로 설정되어 있습니다.
DB를 영구 보존하려면 호스팅 서비스의 Persistent Disk/Volume에 `DATABASE_PATH`를 지정해야 합니다.

Render / Railway / Fly.io / 개인 VPS 등에 올릴 수 있습니다.
서버가 24시간 켜져 있어야 내부 APScheduler가 매일 08:00 중계표를 자동 생성합니다.

실전 운용 전에는 소액/수동 체결로 충분히 검증하십시오.
