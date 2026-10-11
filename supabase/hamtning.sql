-- Morgonkoll: Supabase startar hämtjobbet i GitHub Actions (hamta.yml) enligt schema.
-- GitHubs egna cron hoppar över de flesta körningarna, pg_cron gör det inte.
-- Kör i SQL Editor. Går att köra flera gånger.
--
-- Kräver en GitHub-token i Vault (fine-grained, bara repot morgonkoll, "Actions: Read and write"):
--   select vault.create_secret('github_pat_…', 'github_hamta');
-- Byta token:
--   select vault.update_secret(id, 'github_pat_…') from vault.secrets where name = 'github_hamta';

create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

-- Eget schema som inte exponeras i Data API.
create schema if not exists privat;
revoke all on schema privat from public, anon, authenticated;

-- Körs var 15:e minut. Tiderna är svensk tid, så sommar- och vintertid sköts av sig själv.
create or replace function privat.starta_hamtning()
returns void
language plpgsql
as $$
declare
  nu     timestamp := now() at time zone 'Europe/Stockholm';
  vardag boolean   := extract(isodow from nu) <= 5;
  tim    int       := extract(hour from nu);
  min    int       := extract(minute from nu);
  delar  text;
  token  text;
begin
  -- Allt (lunch, Systembolaget, evenemang m.m.): vardagar 07:15–10:15 varje timme
  -- (menyn byts måndag morgon, så vi hämtar flera gånger), helger 07:30.
  if (vardag and tim between 7 and 10 and min = 15) or (not vardag and tim = 7 and min = 30) then
    delar := '';
  -- Nyheter, börs, trender, Riksbanken (räntebesked 09:30), SHL: var 15:e minut,
  -- vardagar 06:00–22:45 (täcker USA-börsen), helger 08:00–22:45.
  elsif (vardag and tim between 6 and 22) or (not vardag and tim between 8 and 22) then
    delar := 'nyheter bors trender riksbanken shl';
  else
    return;
  end if;

  select decrypted_secret into token from vault.decrypted_secrets where name = 'github_hamta';
  if token is null then
    raise warning 'Vault-hemligheten github_hamta saknas – startar inte hämtningen';
    return;
  end if;

  perform net.http_post(
    url     := 'https://api.github.com/repos/Janne89/morgonkoll/actions/workflows/hamta.yml/dispatches',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || token,
      'Accept', 'application/vnd.github+json',
      'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'morgonkoll-supabase'),
    body    := jsonb_build_object('ref', 'main', 'inputs', jsonb_build_object('delar', delar))
  );
end;
$$;
revoke all on function privat.starta_hamtning() from public, anon, authenticated;

select cron.schedule('hamta', '*/15 * * * *', 'select privat.starta_hamtning()');

-- Felsökning: GitHub svarar 204 när körningen startats (svaren sparas ca 6 h).
--   select created, status_code, content from net._http_response order by created desc limit 10;
--   select start_time, status, return_message from cron.job_run_details order by start_time desc limit 10;
