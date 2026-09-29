# Lao-LOC+ v0.9 Cloud Auto-Save

이 버전은 체결/Layer/중계표 상태를 Supabase에 자동 저장합니다.
일일 수동 백업은 필요 없습니다.

## 1. Supabase
1. https://supabase.com 에서 무료 프로젝트 생성
2. SQL Editor 열기
3. `SUPABASE_SETUP.sql` 전체를 붙여넣고 Run

## 2. Supabase 키 확인
Supabase에서 아래 두 값을 확인:
- Project URL
- Secret key (`sb_secret_...`)

Secret key는 절대로 GitHub, 브라우저 코드, 채팅에 공개하지 마세요.

## 3. Render Environment Variables
Render → lao-loc-hybrid → Environment 에 추가:

SUPABASE_URL = (Supabase Project URL)
SUPABASE_SECRET_KEY = (Supabase Secret key, sb_secret_...)
APP_STATE_ID = main

참고: 예전 `service_role` 키도 코드가 호환하지만, 새 설정에서는 Secret key를 권장합니다.

저장 후 Render에서 최신 버전을 재배포합니다.

## 결과
- 체결 입력 → 자동 클라우드 저장
- 시작금 변경 → 자동 클라우드 저장
- Layer 변경 → 자동 클라우드 저장
- 중계표 기록 → 자동 클라우드 저장
- 다른 PC/브라우저에서도 같은 웹주소를 열면 동일 기록 로드
- 브라우저 삭제/Render 재배포/Render sleep에도 DB 기록 유지
- 백업 버튼은 비상용으로만 남겨둠

## 무료 플랜 참고
Supabase Free는 현재 500MB DB를 제공합니다. 이 앱의 텍스트 기록 규모에서는 매우 넉넉합니다.
Free 프로젝트는 1주 동안 비활성 상태면 pause될 수 있습니다.


## 4. Render 보안 환경변수도 추가
공개 웹주소이므로 아래 2개를 추가해 앱 로그인을 보호합니다.

APP_PASSWORD = 본인이 정할 웹앱 로그인 비밀번호
FLASK_SECRET_KEY = 충분히 긴 랜덤 문자열

예:
APP_PASSWORD = (본인이 기억할 비밀번호)
FLASK_SECRET_KEY = 32자 이상 랜덤 문자열

중요:
- 이 값들도 GitHub에 절대 올리지 않습니다.
- Render Environment에만 넣습니다.
- FLASK_SECRET_KEY는 기억할 필요 없습니다. 한 번 저장하면 됩니다.

최종 Render 환경변수 5개:
SUPABASE_URL
SUPABASE_SECRET_KEY
APP_STATE_ID
APP_PASSWORD
FLASK_SECRET_KEY
