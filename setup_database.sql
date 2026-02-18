-- 自宅在庫管理用テーブル作成
create table household_inventory (
  id uuid default gen_random_uuid() primary key,
  category text not null,       -- カテゴリ (食料品, 日用品 etc)
  name text not null,           -- 商品名
  quantity integer default 1,   -- 数量
  notes text,                   -- 備考
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS (Row Level Security) の設定
-- 今回は個人用で認証を簡略化するため、一時的に全開放します（必要に応じて変更可能）
alter table household_inventory enable row level security;

create policy "Allow all access" on household_inventory
for all using (true) with check (true);
