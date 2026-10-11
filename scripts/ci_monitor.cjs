#!/usr/bin/env node
// Small observable wrapper; all project CI inspection goes through this entry.
const { spawnSync } = require('node:child_process');
function gh(args) {
  const result = spawnSync('gh', args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return result.stdout.trim();
}
const [command, id] = process.argv.slice(2);
try {
  if (!command || command === '--help') {
    console.log('Usage: node scripts/ci_monitor.cjs runs | watch RUN_ID | log-failed RUN_ID | check-actions');
  } else if (command === 'runs') {
    console.log(gh(['run', 'list', '--limit', '5', '--json', 'databaseId,status,conclusion,headSha,url']));
  } else if (command === 'watch' && /^\d+$/.test(id || '')) {
    const result = spawnSync('gh', ['run', 'watch', id, '--interval', '10', '--exit-status'], { stdio: 'inherit' });
    process.exitCode = result.status || 0;
  } else if (command === 'log-failed' && /^\d+$/.test(id || '')) {
    console.log(gh(['run', 'view', id, '--log-failed']));
  } else if (command === 'check-actions') {
    const actions = {};
    for (const name of ['checkout', 'setup-python']) {
      const tag = gh(['api', `repos/actions/${name}/releases/latest`, '--jq', '.tag_name']);
      const sha = gh(['api', `repos/actions/${name}/git/ref/tags/${tag}`, '--jq', '.object.sha']);
      actions[name] = { tag, sha };
    }
    console.log(JSON.stringify(actions, null, 2));
  } else {
    throw new Error('Unknown command or missing run ID; use --help');
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
