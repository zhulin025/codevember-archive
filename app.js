const byId = (id) => document.getElementById(id);
const search = byId('search');
const authors = byId('author');
const themeList = byId('themes');
const results = byId('works');
const about = byId('sources');
const defaultTheme = '01';
const allTheme = 'all';
const freeTheme = 'free';
const themeButtons = new Map();
const cn = [
  '折叠', '破碎', '融化', '缠绕', '苔藓', '行星仪', '空洞', '超立方体', '薄膜', '焦散',
  '锈蚀', '羽毛', '迷宫', '张力', '幻景', '孢子', '海带', '摆锤', '侵蚀', '茧',
  '闪电', '回声', '岩浆', '巢', '面纱', '变形透视', '地洞', '蜂巢', '传送门', '消散',
];
let catalogue;
let selectedTheme = defaultTheme;

function element(tag, classes, text) {
  const node = document.createElement(tag);
  if (classes) node.className = classes;
  if (text != null) node.textContent = text;
  return node;
}

function external(url, className, label) {
  const link = element('a', className, label);
  link.href = url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}

function workCard(work, prompt, eager) {
  const creator = catalogue.creators[work.creator];
  const article = element('article', 'card');
  const picture = external(work.url, 'card-image');
  picture.tabIndex = -1;
  picture.setAttribute('aria-hidden', 'true');
  const fallback = element('span', 'image-fallback', prompt);
  fallback.append(element('small', null, '暂无作品主图'));
  const arrow = element('span', 'card-arrow', '↗');
  picture.append(fallback, arrow);
  if (work.image) {
    const img = element('img');
    img.alt = '';
    img.loading = eager ? 'eager' : 'lazy';
    img.decoding = 'async';
    img.addEventListener('error', () => {
      img.remove();
      fallback.hidden = false;
    });
    fallback.hidden = true;
    img.src = work.image;
    picture.append(img);
  }
  const body = element('div', 'card-text');
  const title = external(work.url, 'card-title', work.title || prompt);
  title.setAttribute('aria-label', `${work.title || prompt} · ${creator.name}（在新标签页打开）`);
  const meta = element('div', 'card-meta');
  const source = external(work.source, null, '来源 ↗');
  source.setAttribute('aria-label', `查看 ${creator.name} 的来源（在新标签页打开）`);
  meta.append(external(creator.url, null, creator.handle ? '@' + creator.handle : creator.name), source);
  body.append(title, meta);
  article.append(picture, body);
  return article;
}

function section({ id, prompt, translation, works }, firstGroup) {
  const block = element('section', 'work-section');
  const head = element('div', 'group-head');
  const heading = element('h3', null, prompt);
  if (id) head.append(element('span', 'number', 'DAY ' + id));
  head.append(heading);
  if (translation) head.append(element('span', 'translation', translation));
  head.append(element('span', 'group-count', `${works.length} 件作品`));
  block.append(head);
  if (works.length) {
    const grid = element('div', 'card-grid');
    grid.append(...works.map((work, index) => workCard(work, prompt, firstGroup && index < 6)));
    block.append(grid);
  } else {
    block.append(element('p', 'empty', search.value || authors.value ? '这个主题下没有符合筛选条件的作品。' : '这个主题暂未收录作品。'));
  }
  return block;
}

function themeFor(work) {
  return work.day ? catalogue.themes[work.day - 1] : { prompt: work.theme };
}

function groupsFor(works) {
  const groups = new Map();
  for (const work of works) {
    const theme = themeFor(work);
    const key = theme.id || theme.prompt;
    if (!groups.has(key)) groups.set(key, { ...theme, works: [] });
    groups.get(key).works.push(work);
  }
  return [...groups.values()];
}

function render() {
  const tokens = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const matching = catalogue.works.filter((work) => {
    if (authors.value && work.creator !== authors.value) return false;
    const creator = catalogue.creators[work.creator];
    const { id, prompt, translation } = themeFor(work);
    const tags = [work.title, creator.name, creator.handle && '@' + creator.handle, prompt, translation, id && 'day ' + id];
    const haystack = tags.filter(Boolean).join(' ').toLocaleLowerCase();
    return tokens.every((token) => haystack.includes(token));
  });

  const totals = new Map([[allTheme, matching.length]]);
  for (const work of matching) {
    const key = work.day ? catalogue.themes[work.day - 1].id : freeTheme;
    totals.set(key, (totals.get(key) || 0) + 1);
  }
  for (const [id, button] of themeButtons) {
    const count = totals.get(id) || 0;
    button.querySelector('.count').textContent = count || '–';
    button.dataset.empty = String(!count);
    if (id === selectedTheme) button.setAttribute('aria-current', 'true');
    else button.removeAttribute('aria-current');
    button.setAttribute('aria-label', `${button.dataset.label}，${count} 件作品`);
  }

  const picked = selectedTheme === allTheme
    ? matching
    : matching.filter((work) => (themeFor(work).id || freeTheme) === selectedTheme);
  const groups = groupsFor(picked);
  const dailyTheme = catalogue.themes.find((item) => item.id === selectedTheme);
  if (!groups.length && dailyTheme) groups.push({ ...dailyTheme, works: [] });
  results.replaceChildren(...(groups.length ? groups.map((group, index) => section(group, index === 0)) : [element('p', 'empty', '没有符合筛选条件的作品。')]));
  byId('announcement').textContent = `显示 ${picked.length} 件作品`;
}

function readLocation() {
  const params = new URLSearchParams(location.search);
  const theme = params.get('day');
  const creator = params.get('author');
  search.value = params.get('q') || '';
  authors.value = creator && catalogue.creators[creator] ? creator : '';
  selectedTheme = themeButtons.has(theme) ? theme : search.value || authors.value ? allTheme : defaultTheme;
}

function saveLocation(push) {
  const url = new URL(location.href);
  url.searchParams.delete('day');
  url.searchParams.delete('q');
  url.searchParams.delete('author');
  if (selectedTheme !== defaultTheme || search.value.trim() || authors.value) url.searchParams.set('day', selectedTheme);
  if (search.value.trim()) url.searchParams.set('q', search.value.trim());
  if (authors.value) url.searchParams.set('author', authors.value);
  if (url.href !== location.href) history[push ? 'pushState' : 'replaceState']({}, '', url);
}

function addTheme(id, number, label) {
  const button = element('button', 'theme-button');
  button.type = 'button';
  button.dataset.label = number && number !== '•' ? `${number} ${label}` : label;
  button.append(element('span', 'number', number), element('span', null, label), element('span', 'count'));
  button.addEventListener('click', () => {
    selectedTheme = id;
    saveLocation(true);
    render();
  });
  themeButtons.set(id, button);
  themeList.append(button);
}

function onFilter() {
  if (selectedTheme === defaultTheme && !new URLSearchParams(location.search).has('day')) selectedTheme = allTheme;
  saveLocation(false);
  render();
}

async function load() {
  const response = await fetch('./data/catalogue.json', { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  catalogue = await response.json();
  catalogue.themes = catalogue.themes.map((prompt, index) => ({
    id: String(index + 1).padStart(2, '0'), prompt, translation: cn[index],
  }));
  const creators = new Set(catalogue.works.map((work) => work.creator));
  const links = [];
  for (const [id, creator] of Object.entries(catalogue.creators).sort((a, b) => a[1].name.localeCompare(b[1].name))) {
    if (!creators.has(id)) continue;
    const option = element('option', null, creator.name);
    option.value = id;
    authors.append(option);
    const item = element('li');
    item.append(external(creator.url, null, creator.name + ' ↗'));
    links.push(item);
  }
  byId('source-list').replaceChildren(...links);
  byId('work-count').textContent = catalogue.works.length;
  byId('author-count').textContent = creators.size;
  if (catalogue.updated) byId('updated').textContent = `收录更新 ${catalogue.updated.replaceAll('-', '.')}`;

  addTheme(allTheme, '•', '全部作品');
  for (const { id, prompt } of catalogue.themes) addTheme(id, id, prompt);
  if (catalogue.works.some((work) => !work.day)) addTheme(freeTheme, '•', '自选主题');
  readLocation();
  render();
  if (selectedTheme !== defaultTheme) {
    const button = themeButtons.get(selectedTheme);
    if (matchMedia('(max-width: 760px)').matches) {
      themeList.scrollLeft = button.offsetLeft - themeList.offsetLeft;
    } else {
      themeList.scrollTop = button.offsetTop - themeList.offsetTop - 74;
    }
  }
  search.addEventListener('input', onFilter);
  authors.addEventListener('change', onFilter);
  window.addEventListener('popstate', () => {
    readLocation();
    render();
  });
}

document.querySelector('.filters').addEventListener('submit', (event) => event.preventDefault());
for (const button of document.querySelectorAll('.sources-trigger')) {
  button.addEventListener('click', () => about.showModal());
}
load().catch((error) => {
  console.error(error);
  results.replaceChildren(element('p', 'empty', '暂时无法读取作品档案，请刷新页面重试。'));
});
