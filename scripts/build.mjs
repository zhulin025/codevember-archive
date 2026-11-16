import { copyFile, cp, mkdir, readFile, rm } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const output = new URL('dist/', root);
const data = new URL('data/catalogue.json', root);
const catalogue = JSON.parse(await readFile(data, 'utf8'));

if (!Array.isArray(catalogue.themes) || catalogue.themes.length !== 30 || !Array.isArray(catalogue.works)) {
  throw new Error('Invalid Codevember catalogue');
}

await rm(output, { recursive: true, force: true });
await mkdir(new URL('data/', output), { recursive: true });
await Promise.all([
  ...['index.html', 'app.js', 'styles.css'].map((file) => copyFile(new URL(file, root), new URL(file, output))),
  copyFile(data, new URL('data/catalogue.json', output)),
  cp(new URL('covers/', root), new URL('covers/', output), { recursive: true }),
]);
