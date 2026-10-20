// Local lifecycle control shared by the live runner and offline safety tests.
// cleanup/state implementations retain their existing server and HTTP timeouts.
export async function runCreditScenario(name, body, hooks) {
  const detail = { name };
  const firstFixture = hooks.fixtures.length;
  let fixture;
  try {
    fixture = await hooks.fixture();
    await body(fixture, detail);
    detail.status = 'PASS';
  } catch (error) {
    detail.status = 'FAIL';
    detail.error = error.message;
  } finally {
    if (fixture) {
      try { detail.final_state = await hooks.state(fixture); }
      catch (error) { detail.snapshot_error = error.message; detail.status = 'FAIL'; }
    }
    // Includes partially created setup fixtures and secondary cross-user fixtures.
    // Never clean fixtures belonging to another scenario or retry failed cleanup.
    for (const own of hooks.fixtures.slice(firstFixture)) {
      if (own.cleaned || own.cleanupAttempted) continue;
      own.cleanupAttempted = true;
      try { await hooks.cleanup(own); }
      catch (error) {
        own.cleanup_error = error.message;
        detail.cleanup_error = error.message;
        detail.status = 'FAIL';
      }
    }
    if (hooks.fixtures.slice(firstFixture).some(f => !f.cleaned)) {
      detail.status = 'FAIL';
      detail.cleanup_error ??= 'Scenario cleanup could not be verified';
    }
    hooks.record(detail);
  }
  if (detail.status !== 'PASS') throw new Error(`Scenario failed; suite stopped: ${name}`);
}
