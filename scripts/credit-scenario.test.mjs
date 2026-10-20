import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { runCreditScenario } from './credit-scenario.mjs';

for (const failure of ['assertion', 'timeout', 'setup', 'execution', 'snapshot', 'cleanup']) {
  test(`${failure} aborts after own bounded cleanup; no later scenario starts`, async () => {
    const events = [];
    const prior = { cleaned: true };
    const fixtures = [prior];
    const hooks = {
      fixtures,
      async fixture() {
        events.push('setup'); const f = {}; fixtures.push(f);
        if (failure === 'setup') throw new Error('setup failed');
        return f;
      },
      async state() { if (failure === 'snapshot') throw new Error('snapshot failed'); },
      async cleanup(f) {
        assert.notEqual(f, prior); events.push('cleanup');
        if (failure === 'cleanup') throw new Error('cleanup failed');
        f.cleaned = true;
      },
      record(d) { assert.equal(d.status, 'FAIL'); events.push('record'); },
    };
    await assert.rejects(async () => {
      await runCreditScenario('first', async () => {
        if (failure === 'assertion') assert.fail('deliberate assertion');
        if (failure === 'timeout') throw new DOMException('timed out', 'TimeoutError');
        if (failure === 'execution') throw new Error('execution failed');
      }, hooks);
      events.push('later scenario');
    }, /suite stopped/);
    assert.deepEqual(events, ['setup', 'cleanup', 'record']);
    assert.equal(fixtures[1].cleanupAttempted, true);
  });
}
test('secondary fixture from failed setup is cleaned once before abort', async () => {
  const fixtures = []; let cleanups = 0;
  const hooks = { fixtures, async fixture() { const f={}; fixtures.push(f); return f; },
    async state() {}, async cleanup(f) { cleanups++; f.cleaned=true; }, record() {} };
  await assert.rejects(runCreditScenario('secondary', async () => {
    fixtures.push({}); throw new Error('secondary setup failed');
  }, hooks));
  assert.equal(cleanups, 2); assert(fixtures.every(f => f.cleaned));
});
test('failed lifecycle produces a nonzero process exit and prevents later code', () => {
  const child = spawnSync(process.execPath, ['--input-type=module', '-e', `
    import { runCreditScenario } from ${JSON.stringify(new URL('./credit-scenario.mjs', import.meta.url).href)};
    const fixtures=[];
    await runCreditScenario('failure', async()=>{throw new Error('assertion');}, {
      fixtures, async fixture(){const f={}; fixtures.push(f); return f;},
      async state(){}, async cleanup(f){f.cleaned=true; console.log('cleaned');}, record(){}
    });
    console.log('LATER');
  `], { encoding:'utf8', timeout:5000 });
  assert.equal(child.error, undefined); assert.notEqual(child.status,0);
  assert.match(child.stdout,/cleaned/); assert.doesNotMatch(child.stdout,/LATER/);
});
