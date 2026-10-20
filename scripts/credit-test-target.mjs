export function assertApprovedCreditTarget(args, config) {
  const option = name => args.includes(name) ? args[args.indexOf(name) + 1] : undefined;
  if (!config.approvedRun || option('--approved-run') !== config.approvedRun) {
    throw new Error('Integration execution is disabled pending explicit approval and a matching run identifier.');
  }
  if (!/^[a-z]{20}$/.test(config.projectRef ?? '') ||
      option('--project-ref') !== config.projectRef ||
      option('--allow-writes-to') !== config.projectRef) {
    throw new Error('Both project arguments must match the explicitly approved development target.');
  }
}
