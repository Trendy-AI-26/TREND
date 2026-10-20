// Opt-in live integration tests. Uses disposable records, never existing accounts.
// Requires SUPABASE_ACCESS_TOKEN and explicit --project-ref / --allow-writes-to.
import { randomUUID } from 'node:crypto';
import { writeFileSync, mkdirSync, readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { assertApprovedCreditTarget } from './credit-test-target.mjs';
import { runCreditScenario } from './credit-scenario.mjs';

const args = process.argv.slice(2);
const option = name => args[args.indexOf(name) + 1];
const project = option('--project-ref');
const target = JSON.parse(readFileSync(new URL('./credit-test-target.json', import.meta.url), 'utf8'));
assertApprovedCreditTarget(args, target);
if (!args.includes('--project-ref') || !/^[a-z]{20}$/.test(project ?? '') ||
    !args.includes('--allow-writes-to') || option('--allow-writes-to') !== project) {
  throw new Error('Provide matching --project-ref and --allow-writes-to references.');
}
if (!process.env.SUPABASE_ACCESS_TOKEN) throw new Error('Missing management API token.');
const run = randomUUID();
const label = `credit-${run}`;
const report = { run, project, started_at: new Date().toISOString(), tests: [], fixtures: [] };
mkdirSync('docs', { recursive: true });
const reportPath = `docs/credit-integration-${run}.json`;
const save = () => writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
const literal = value => `'${String(value).replaceAll("'", "''")}'`;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function query(sql, readOnly = false) {
  // Apply a server timeout even to monitoring and cleanup verification queries.
  if (!sql.trimStart().startsWith('BEGIN;')) {
    sql = `BEGIN${readOnly ? ' READ ONLY' : ''}; SET LOCAL statement_timeout='15s'; SET LOCAL lock_timeout='5s'; ${sql}; COMMIT;`;
  }
  const response = await fetch(`https://api.supabase.com/v1/projects/${project}/database/query`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.SUPABASE_ACCESS_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql, read_only: readOnly }),
    signal: AbortSignal.timeout(55000),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(JSON.stringify(data));
  if (!Array.isArray(data)) throw new Error('Unexpected database query response.');
  return data;
}
const transaction = (sql, name = label) => `BEGIN;
 SET LOCAL statement_timeout='40s'; SET LOCAL lock_timeout='25s';
 SET LOCAL application_name=${literal(name)}; ${sql}; COMMIT;`;
const result = promise => promise.then(rows => ({ ok: true, rows }), error => ({ ok: false, error: error.message }));

async function fixture() {
  const f = { user: randomUUID(), brand: randomUUID(), generation: randomUUID(), otherGeneration: randomUUID(), key: randomUUID(), otherKey: randomUUID() };
  report.fixtures.push(f); save(); // Persist cleanup IDs before any network mutation.
  await query(transaction(`
    INSERT INTO auth.users(id,email,raw_user_meta_data)
      VALUES (${literal(f.user)},${literal(`credit-test-${f.user}@example.invalid`)},'{"full_name":"Disposable credit integration test"}');
    INSERT INTO public.brands(id,owner_user_id,name)
      VALUES (${literal(f.brand)},${literal(f.user)},'Disposable credit integration test');
    INSERT INTO public.generations(id,brand_id,user_id,prompt,provider,model,platform_preset,width,height)
      VALUES ${[f.generation, f.otherGeneration].map(id => `(${literal(id)},${literal(f.brand)},${literal(f.user)},'Database test only','openai','test-no-provider-call','instagram_post',1024,1024)`).join(',')};
    INSERT INTO public.credit_accounts(user_id,balance,reserved) VALUES (${literal(f.user)},100,0);
    INSERT INTO public.credit_ledger(user_id,operation,amount,idempotency_key)
      VALUES (${literal(f.user)},'grant',100,${literal(`test-grant-${f.user}`)})`));
  return f;
}
function rpcSql(f, operation, other = false) {
  assert(['reserve', 'commit', 'release'].includes(operation));
  const key = literal(other ? f.otherKey : f.key);
  const generation = literal(other ? f.otherGeneration : f.generation);
  const amount = f.amount === null ? 'NULL' : String(f.amount ?? 10);
  assert(amount === 'NULL' || /^-?\d+$/.test(amount));
  const params = operation === 'reserve' ? `${literal(f.user)},${generation},${amount},${key}` : `${literal(f.user)},${generation},${key},${amount}`;
  return `SET LOCAL ROLE service_role; SELECT public.${operation}_generation_credit(${params}) AS result`;
}
const rpc = (f, operation, other = false, name = label) => query(transaction(rpcSql(f, operation, other), name));
async function state(f) {
  const rows = await query(`SELECT balance,reserved,
    (SELECT jsonb_agg(jsonb_build_object('operation',operation,'amount',amount,'key',idempotency_key) ORDER BY idempotency_key)
     FROM public.credit_ledger WHERE user_id=${literal(f.user)}) AS ledger
    FROM public.credit_accounts WHERE user_id=${literal(f.user)}`, true);
  assert.equal(rows.length, 1);
  return rows[0];
}
function checkState(s, balance, reserved, commits, releases) {
  assert.equal(s.balance, balance, 'balance');
  assert.equal(s.reserved, reserved, 'reserved');
  assert.equal(s.ledger.filter(x => x.operation === 'commit').length, commits, 'commit entries');
  assert.equal(s.ledger.filter(x => x.operation === 'release').length, releases, 'release entries');
}
async function cleanup(f) {
  f.cleanupAttempted = true;
  // The root UUID and exact synthetic email must both match before cascading deletes.
  await query(transaction(`DELETE FROM auth.users WHERE id=${literal(f.user)}
    AND email=${literal(`credit-test-${f.user}@example.invalid`)}`));
  const [remaining] = await query(`SELECT
    (SELECT count(*) FROM auth.users WHERE id=${literal(f.user)}) AS users,
    (SELECT count(*) FROM public.profiles WHERE user_id=${literal(f.user)}) AS profiles,
    (SELECT count(*) FROM public.brands WHERE id=${literal(f.brand)}) AS brands,
    (SELECT count(*) FROM public.generations WHERE id IN (${literal(f.generation)},${literal(f.otherGeneration)})) AS generations,
    (SELECT count(*) FROM public.credit_accounts WHERE user_id=${literal(f.user)}) AS accounts,
    (SELECT count(*) FROM public.credit_ledger WHERE user_id=${literal(f.user)}) AS ledger,
    (SELECT count(*) FROM public.user_generation_quotas WHERE user_id=${literal(f.user)}) AS quotas,
    (SELECT count(*) FROM public.generation_quota_reservations WHERE user_id=${literal(f.user)}) AS quota_reservations,
    (SELECT count(*) FROM public.generation_daily_usage WHERE user_id=${literal(f.user)}) AS daily_usage,
    (SELECT count(*) FROM public.generation_usage WHERE user_id=${literal(f.user)}) AS generation_usage,
    (SELECT count(*) FROM public.usage_events WHERE user_id=${literal(f.user)}) AS usage_events,
    (SELECT count(*) FROM public.idempotency_records WHERE user_id=${literal(f.user)}) AS idempotency_records,
    (SELECT count(*) FROM public.generation_locks WHERE user_id=${literal(f.user)}) AS locks,
    (SELECT count(*) FROM public.subscriptions WHERE user_id=${literal(f.user)}) AS subscriptions`, true);
  f.remaining = remaining;
  assert(Object.values(remaining).every(n => Number(n) === 0), 'Test cleanup incomplete');
  f.cleaned = true; save();
}
async function waitFor(sql, predicate) {
  for (let attempt = 0; attempt < 12; attempt++) {
    const rows = await query(sql, true);
    if (predicate(rows)) return rows;
    await delay(750);
  }
  throw new Error('Concurrency synchronization failed; result is inconclusive.');
}
async function race(f, operations, detail) {
  const blockerName = `${label}-blocker`;
  const workerNames = operations.map((_, i) => `${label}-worker-${i}`);
  let workers = [];
  // Hold only this disposable account row, until both requests are waiting.
  const blocker = result(query(transaction(`SELECT user_id FROM public.credit_accounts
    WHERE user_id=${literal(f.user)} FOR UPDATE; SELECT pg_sleep(35)`, blockerName)));
  try {
    await waitFor(`SELECT pid FROM pg_stat_activity WHERE application_name=${literal(blockerName)} AND wait_event='PgSleep'`, rows => rows.length === 1);
    workers = operations.map((op, i) => result(rpc(f, typeof op === 'string' ? op : op.operation, Boolean(op.other), workerNames[i])));
    detail.waiters = await waitFor(`SELECT application_name,wait_event_type,wait_event
      FROM pg_stat_activity WHERE application_name IN (${workerNames.map(literal).join(',')})
      AND wait_event_type='Lock'`, rows => rows.length === 2);
  } finally {
    // Cancel only our tagged sleeping query; transaction rollback releases its row lock.
    try {
      await query(`SELECT pg_cancel_backend(pid) FROM pg_stat_activity
        WHERE application_name=${literal(blockerName)} AND wait_event='PgSleep' AND pid<>pg_backend_pid()`);
    } finally {
      await blocker;
      detail.outcomes = await Promise.all(workers);
    }
  }
  assert.equal(detail.outcomes.length, 2);
  return detail.outcomes;
}
async function test(name, body) {
  await runCreditScenario(name, body, {
    fixture, state, cleanup, fixtures: report.fixtures,
    record(detail) {
      report.tests.push(detail); save();
      console.log(`${detail.status}: ${name}`);
    },
  });
}

async function creditFingerprint() {
  const [snapshot] = await query(`SELECT
    (SELECT count(*) FROM public.credit_accounts) AS accounts,
    (SELECT md5(COALESCE(string_agg(to_jsonb(c)::text, '' ORDER BY user_id), '')) FROM public.credit_accounts c) AS accounts_hash,
    (SELECT count(*) FROM public.credit_ledger) AS ledger,
    (SELECT md5(COALESCE(string_agg(to_jsonb(l)::text, '' ORDER BY id), '')) FROM public.credit_ledger l) AS ledger_hash`, true);
  return snapshot;
}
async function mustReject(f, operation, expected) {
  const response = await result(rpc(f, operation));
  assert.equal(response.ok, false, 'Invalid request must be rejected');
  assert(response.error.includes(expected), response.error);
}

save();
try {
  report.existing_credit_before = await creditFingerprint(); save();
  for (const op of ['commit', 'release']) {
    await test(`sequential duplicate ${op}`, async (f, d) => {
      await rpc(f, 'reserve'); await rpc(f, op); await rpc(f, op);
      d.observed = await state(f);
      checkState(d.observed, op === 'commit' ? 90 : 100, 0, op === 'commit' ? 1 : 0, op === 'release' ? 1 : 0);
    });
  }
  await test('sequential duplicate reserve: no second mutation', async (f, d) => {
    await rpc(f, 'reserve'); d.retry = await result(rpc(f, 'reserve'));
    d.observed = await state(f); checkState(d.observed, 100, 10, 0, 0);
    assert.equal(d.observed.ledger.filter(x => x.operation === 'reserve').length, 1);
    assert(d.retry.ok, 'Matching reserve retry must return the prior receipt');
  });
  for (const [first, second] of [['commit','release'], ['release','commit']]) {
    await test(`${second} after ${first} rejects`, async (f, d) => {
      await rpc(f, 'reserve'); await rpc(f, first);
      d.outcome = await result(rpc(f, second)); assert.equal(d.outcome.ok, false);
      assert(d.outcome.error.includes(first === 'commit' ? 'ALREADY_COMMITTED' : 'ALREADY_RELEASED'));
      d.observed = await state(f); checkState(d.observed, first === 'commit' ? 90 : 100, 0, first === 'commit' ? 1 : 0, first === 'release' ? 1 : 0);
    });
  }
  for (const op of ['commit', 'release']) {
    await test(`${op} without reservation rejects`, async (f, d) => {
      d.outcome = await result(rpc(f, op)); assert.equal(d.outcome.ok, false);
      assert(d.outcome.error.includes('CREDIT_RESERVATION_NOT_FOUND'));
      checkState(await state(f), 100, 0, 0, 0);
    });
  }
  for (const op of ['reserve','commit','release']) {
    await test(`concurrent duplicate ${op}`, async (f, d) => {
      if (op !== 'reserve') { await rpc(f, 'reserve'); await rpc(f, 'reserve', true); }
      const outcomes = await race(f, [op, op], d);
      d.observed = await state(f);
      checkState(d.observed, op === 'commit' ? 90 : 100, 10, op === 'commit' ? 1 : 0, op === 'release' ? 1 : 0);
      d.balance_safe = true;
      if (op === 'reserve') {
        assert.equal(d.observed.ledger.filter(x => x.operation === 'reserve').length, 1);
        assert(outcomes.every(x => x.ok), 'Matching concurrent reserve retries must both succeed');
      } else {
        assert(outcomes.every(x => x.ok), 'Concurrent identical terminal requests should both return their prior result');
      }
    });
  }
  for (let repeat = 1; repeat <= 3; repeat++) await test(`concurrent commit versus release preserves other reservation (${repeat})`, async (f, d) => {
    await rpc(f, 'reserve'); await rpc(f, 'reserve', true);
    const outcomes = await race(f, repeat % 2 ? ['commit','release'] : ['release','commit'], d);
    d.observed = await state(f);
    assert.equal(d.observed.reserved, 10, 'Other reservation must remain reserved');
    assert.equal(outcomes.filter(x => x.ok).length, 1, 'Only one terminal operation may win');
    const commits = d.observed.ledger.filter(x => x.operation === 'commit').length;
    const releases = d.observed.ledger.filter(x => x.operation === 'release').length;
    assert.equal(commits + releases, 1);
    assert.equal(d.observed.balance, commits ? 90 : 100);
    assert(outcomes.find(x => !x.ok).error.includes(commits ? 'ALREADY_COMMITTED' : 'ALREADY_RELEASED'));
  });

  for (const op of ['reserve','commit','release']) {
    await test(`${op} rejects invalid amounts`, async (f) => {
      if (op !== 'reserve') await rpc(f,'reserve');
      for (const amount of [null,0,-1]) await mustReject({...f,amount},op,'INVALID_CREDIT_AMOUNT');
      checkState(await state(f),100,op === 'reserve' ? 0 : 10,0,0);
    });
  }
  await test('insufficient credits leaves no reservation', async f => {
    await mustReject({...f,amount:101},'reserve','INSUFFICIENT_CREDITS');
    checkState(await state(f),100,0,0,0);
  });
  for (const terminal of ['commit','release']) {
    await test(`mismatched replay rejected before and after ${terminal}`, async f => {
      await rpc(f,'reserve');
      for (const finished of [false,true]) {
        if (finished) await rpc(f,terminal);
        for (const variation of [{amount:11},{generation:f.otherGeneration}]) {
          await mustReject({...f,...variation},'reserve','IDEMPOTENCY_KEY_REUSED');
          await mustReject({...f,...variation},terminal,'CREDIT_RESERVATION_NOT_FOUND');
        }
        checkState(await state(f), finished && terminal === 'commit' ? 90 : 100,
          finished ? 0 : 10, finished && terminal === 'commit' ? 1 : 0,
          finished && terminal === 'release' ? 1 : 0);
      }
      const before = await state(f);
      await rpc(f,'reserve'); // Receipt replay must not reopen a completed reservation.
      assert.deepEqual(await state(f),before);
    });
  }
  await test('cross-user replay cannot consume or replay another account reservation', async f => {
    const foreign = await fixture();
    try {
      await rpc(f,'reserve'); await rpc(f,'commit');
      const impostor = {...f,user:foreign.user};
      await mustReject(impostor,'reserve','IDEMPOTENCY_KEY_REUSED');
      await mustReject(impostor,'commit','CREDIT_RESERVATION_NOT_FOUND');
      await mustReject(impostor,'release','CREDIT_RESERVATION_NOT_FOUND');
      checkState(await state(f),90,0,1,0);
      checkState(await state(foreign),100,0,0,0);
    } finally { await cleanup(foreign); }
  });
  await test('two accounts competing for one global reservation key get a stable conflict', async (f,d) => {
    const foreign = await fixture();
    try {
      d.outcomes = await Promise.all([
        result(rpc(f,'reserve')),
        result(rpc({...foreign,key:f.key},'reserve')),
      ]);
      assert.equal(d.outcomes.filter(x=>x.ok).length,1);
      assert(d.outcomes.find(x=>!x.ok).error.includes('IDEMPOTENCY_KEY_REUSED'));
      checkState(await state(f),100,d.outcomes[0].ok?10:0,0,0);
      checkState(await state(foreign),100,d.outcomes[1].ok?10:0,0,0);
    } finally { await cleanup(foreign); }
  });
  await test('independent reservations on one account can finish concurrently', async (f,d) => {
    await rpc(f,'reserve'); await rpc(f,'reserve',true);
    const outcomes = await race(f,['commit',{operation:'release',other:true}],d);
    assert(outcomes.every(x=>x.ok)); checkState(await state(f),90,0,1,1);
  });
  for (const terminal of ['commit','release']) {
    await test(`reserve another generation concurrently with ${terminal}`, async (f,d) => {
      await rpc(f,'reserve');
      const outcomes = await race(f,[terminal,{operation:'reserve',other:true}],d);
      assert(outcomes.every(x=>x.ok));
      checkState(await state(f),terminal==='commit'?90:100,10,terminal==='commit'?1:0,terminal==='release'?1:0);
    });
  }
  await test('conflicting existing terminal history is rejected without reconciliation', async f => {
    await rpc(f,'reserve'); await rpc(f,'commit');
    // Deliberately inconsistent history only on this disposable fixture.
    await query(transaction(`INSERT INTO public.credit_ledger(user_id,generation_id,operation,amount,idempotency_key)
      VALUES (${literal(f.user)},${literal(f.generation)},'release',10,${literal(f.key+'-release')})`));
    const before = await state(f);
    await mustReject(f,'commit','CREDIT_RESERVATION_STATE_INVALID');
    await mustReject(f,'release','CREDIT_RESERVATION_STATE_INVALID');
    assert.deepEqual(await state(f),before);
  });
} catch (error) { report.fatal_error = error.message; }
finally {
  for (const f of report.fixtures.filter(f => !f.cleaned && !f.cleanupAttempted)) {
    try { await cleanup(f); } catch (error) { f.cleanup_error = error.message; }
  }
  if (report.existing_credit_before) {
    try {
      report.existing_credit_after = await creditFingerprint();
      assert.deepEqual(report.existing_credit_after,report.existing_credit_before);
      report.existing_credit_preserved = true;
    } catch (error) { report.existing_credit_preserved = false; report.preservation_error = error.message; }
  }
  report.finished_at = new Date().toISOString(); save();
  console.log(`Report: ${reportPath}`);
  if (report.fatal_error || report.existing_credit_preserved !== true || report.tests.some(t => t.status !== 'PASS') || report.fixtures.some(f => !f.cleaned)) process.exitCode = 1;
}
