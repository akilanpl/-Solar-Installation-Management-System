/* Launch once before the complete suite: environment failures cannot be passed. */
const { createRequire } = require('node:module');
const { spawnSync } = require('node:child_process');
const { writeFileSync, mkdirSync } = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const web = path.join(root, 'apps/web');
const requireWeb = createRequire(path.join(web, 'package.json'));
const suite = process.argv[2];
const output = process.argv[3];
const allowed = new Set(['customer-warranty.spec.ts', 'accessibility.spec.ts']);
const escape = text => String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
async function run() {
  if (!allowed.has(suite) || !output) throw new Error('Expected a reviewed suite and JUnit path');
  try {
    const { chromium } = requireWeb('@playwright/test');
    const browser = await chromium.launch();
    await browser.close();
  } catch (error) {
    mkdirSync(path.dirname(output), { recursive:true });
    writeFileSync(output, `<testsuite name="browser-environment" tests="1" failures="1"><testcase name="chromium_launch_required_for_${escape(suite)}"><failure message="Browser launch blocked; functional pages not executed">${escape(error.message)}</failure></testcase></testsuite>`);
    console.error('Browser environment blocked. No functional page or journey result is claimed.');
    console.error(error.message);
    process.exitCode = 1;
    return;
  }
  const cli = resolveCli();
  const result = spawnSync(process.execPath, [cli,'test',`e2e/release/${suite}`,'--config=playwright.release.config.ts','--reporter=junit'], {
    cwd:web,stdio:'inherit',env:{...process.env,PLAYWRIGHT_JUNIT_OUTPUT_FILE:output},
  });
  process.exitCode = result.status === null ? 1 : result.status;
}
function resolveCli() {
  return path.join(path.dirname(requireWeb.resolve('playwright/package.json')), 'cli.js');
}
module.exports = { resolveCli };
if (require.main === module) run().catch(error=>{ console.error(error.message); process.exitCode=1; });
