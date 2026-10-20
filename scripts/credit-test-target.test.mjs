import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assertApprovedCreditTarget } from './credit-test-target.mjs';
const projectRef = 'mdxeyhpffhijzcdjjlqe';
const args = ['--project-ref',projectRef,'--allow-writes-to',projectRef,'--approved-run','reviewed-run'];
test('pending approval disables execution even with matching project', () => {
  assert.throws(() => assertApprovedCreditTarget(args,{projectRef,approvedRun:null}), /disabled/);
});
test('wrong run identifier disables execution', () => {
  assert.throws(() => assertApprovedCreditTarget(args,{projectRef,approvedRun:'different-run'}), /disabled/);
});
test('approval does not permit an unrelated project', () => {
  assert.throws(() => assertApprovedCreditTarget(args,{projectRef:'abcdefghijklmnopqrst',approvedRun:'reviewed-run'}), /must match/);
});
test('missing write confirmation is rejected', () => {
  assert.throws(() => assertApprovedCreditTarget(args.filter(x=>x!=='--allow-writes-to'),{projectRef,approvedRun:'reviewed-run'}), /must match/);
});
test('explicit approved run and exact target pass', () => {
  assert.doesNotThrow(() => assertApprovedCreditTarget(args,{projectRef,approvedRun:'reviewed-run'}));
});
