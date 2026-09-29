-- Supabase SQL Editor에서 한 번만 실행
create table if not exists public.app_state (
  id text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- updated_at 자동 갱신 함수
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists app_state_set_updated_at on public.app_state;
create trigger app_state_set_updated_at
before update on public.app_state
for each row execute procedure public.set_updated_at();

-- 브라우저는 Supabase에 직접 접속하지 않습니다.
-- Render 서버만 service_role key로 접근하므로 RLS를 켜 둡니다.
alter table public.app_state enable row level security;
