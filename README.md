# Lao-LOC+ Hybrid Strict FREE Refresh v0.5

- Render Free Web Service용
- 오전 8시 스케줄러 없음
- 페이지 접속/새로고침 시 최신 SOXL 종가로 중계표 자동 생성
- 무료 서버 sleep 시 첫 접속이 약 1분 느릴 수 있음
- 체결/Layer/중계표 기록은 브라우저 localStorage에 저장
- 백업/복원 JSON 버튼 제공
- 같은 브라우저/PC에서는 기록 유지
- 브라우저 데이터 삭제 또는 다른 PC에서는 자동 동기화되지 않으므로 정기 백업 권장


## v0.5 추가
- 웹 상단에서 운용 시작금을 직접 변경 가능
- 1 Line = 시작금 / 13 자동 계산
- Buy1/Buy2 수량 = INT(1 Line 예산 / Target 가격)으로 자동 변경
- 매도수량은 실제 Layer 잔여수량 기준
- 거래 전 시작금 변경: 현금도 새 시작금으로 재설정
- 거래 후 시작금 변경: 차액을 입금/출금으로 반영하고 이후 Line 크기 변경


## v0.6 FIX
- Render/Yahoo 시세 호출이 실패해도 중계표가 빈 화면이 되지 않도록 수정
- 2026-09-25까지 SOXL 백업 일봉 내장
- live yfinance 데이터가 들어오면 백업 데이터와 자동 병합
- API 오류는 항상 JSON으로 반환
- 브라우저가 빈 응답/HTML 에러 응답을 안전하게 처리
- 화면에 '실시간 시세' 또는 '내장 백업 시세' 표시

## v0.7 ROBUST
시세 연결 순서:
1. Yahoo direct chart JSON
2. yfinance
3. 내장 SOXL fallback (2026-09-25까지)

따라서 Render에서 yfinance가 막혀도 direct Yahoo가 먼저 시도됩니다.


## v0.8 TARGET PROFIT FIX
- 매도 주문 활성화는 현재 종가가 아니라 Sell Target 체결 시 수수료 포함 순손익으로 판단
- 현재가가 소폭 마이너스여도 Target 체결 기준 순이익이면 정상 익절 주문 활성
- 중계표 손익 열은 Target 체결 손익 기준
