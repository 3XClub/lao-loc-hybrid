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
