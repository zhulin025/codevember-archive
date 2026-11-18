#!/usr/bin/env python3
"""Refresh the gallery from creator pages and verified individual submissions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
from functools import lru_cache
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'catalogue.json'
ENTRIES = ROOT / 'entries.json'
GITHUB = 'https://github.com/'
RAW = 'https://raw.githubusercontent.com/'
MIRROR = 'https://teapawt.org/'
X = 'https://x.com/'
THEMES = json.loads((ROOT / 'themes.json').read_text())
if len(THEMES) != 30 or len(set(THEMES)) != 30:
    raise ValueError('Expected 30 distinct daily themes')
DAY_RANGE = range(1, 31)

CREATORS = {
    'mrdoob': ('mrdoob', 'mrdoob', 'https://mrdoob.github.io/codevember-2026/'),
    'spite': ('Jaume Sánchez Elias', 'thespite', 'https://spite.github.io/codevember-2026/'),
    'adam': ('Adam Chernick', 'ajc_builds', 'https://adamwebsite.com/codevember/'),
    'akella': ('akella', 'akella', 'https://akella.github.io/codevember-2026/'),
    'theo': ('Theo Tillberg', 'theo_t', 'https://ttillberg.github.io/codevember-2026/'),
    'vipin': ('Vipin Pathak', 'curllmooha', 'https://codevember-26.vercel.app/'),
    'andrew': ('Andrew Voirol', 'AI_Andrew', GITHUB + 'AndrewVoirol/codevember-2026'),
    'drschizzo': ('drschizzo', 'drschizzo', 'https://drschizzo.github.io/Codevember/'),
    'frida': ('Frida Wiig', 'aqua_ne0n', 'https://codevember.vercel.app/'),
    'lars': ('Lars Berg', 'laserberg', X + 'laserberg'),
    'gregory': ('Grégory Daviet', 'grgrdvrt', 'https://grgrdvrt.com/works/codevember-2026/'),
    'greg': ('Greg Christian', 'gregpuzzles1', GITHUB + 'gregpuzzles1/codevember-2026'),
    'aki': ('Aleksandar Aki Rodić', 'akirodic', 'https://akirodic.com/p/codevember2026/'),
    'tino': ('Tino Tibaldo', 'tinotibaldo', X + 'tinotibaldo'),
    'shoreless': ('shoreless', 'shoreless', 'https://shoreless.github.io/codevember/'),
    'loktar': ('Loktar', 'loktar00', 'https://loktar00.github.io/codevember/'),
    'niyati': ('Niyati', 'Niyati82', GITHUB + 'Niyati82/codevember-2026'),
    'eric': ('Eric Levin', 'ericrius1', 'https://www.ericlevin.dev/codevember/'),
    'felix': ('Félix Martínez', 'Sirokos', 'https://codevember-2026.felixmartinez.dev/'),
    'pwd': ('Frank Reitberger', '_pwd_', X + '_pwd_'),
    'tiago': ('Tiago Canzian', 'tgcnzn', X + 'tgcnzn'),
    'henk': ('Henk Beemsterboer', 'hpbeem', X + 'hpbeem'),
    'magpie': ('hard2forgetme', 'hard2forgetme', GITHUB + 'hard2forgetme/magpie-window-sill'),
}

TITLES = {
    ('mrdoob', 1): 'Folding Cloth',
    ('spite', 4): 'Tangle',
    ('adam', 1): 'Paper Map',
    ('adam', 14): 'Spider Web',
    ('adam', 15): 'Desert Oasis',
    ('theo', 4): 'Simulated Traffic Junction',
    ('theo', 5): 'Painting with Moss',
    ('theo', 6): 'Candy Orrery',
    ('theo', 7): 'Hollow Balloon',
    ('theo', 8): 'Telescopic Hypercube',
    ('theo', 9): 'Peel Me Not',
    ('theo', 12): 'Iridescent Hummingbird',
    ('theo', 14): 'One-string Instrument',
}

@lru_cache(maxsize=256)
def fetch(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 CodevemberGallery/1.0'})
    with urlopen(request, timeout=12) as response:
        return response.read(8_000_000).decode('utf-8', 'replace')

def soup(url):
    return BeautifulSoup(fetch(url), 'html.parser')

def module(base, document, selector='script[src]'):
    return fetch(urljoin(base, document.select_one(selector)['src']))

def day_from_path(href):
    match = re.search(r'(?:^|/)(\d{1,3})(?:[-_/]|$)', urlsplit(href).path)
    return int(match[1]) if match and int(match[1]) in DAY_RANGE else None

def absolute(base, value):
    if not value:
        return None
    url = urljoin(base, value)
    return url if urlsplit(url).scheme in ('http', 'https') else None

def entry(creator, day, url, image=None, title=None, source=None, **extra):
    base = CREATORS[creator][2] if creator in CREATORS else url
    result = {
        'creator': creator,
        'title': title or TITLES.get((creator, day)) or (THEMES[day - 1] if day else extra['theme']),
        'url': absolute(base, url),
        'source': absolute(base, source or base),
        **({'day': day} if day else {}),
        **extra,
    }
    if image:
        result['image'] = image if image.startswith('./covers/') else absolute(base, image)
    return result

def gallery_links(creator):
    base = CREATORS[creator][2]
    document = soup(base)
    for link in document.select('a[href]'):
        href = link['href']
        if urlsplit(urljoin(base, href)).netloc != urlsplit(base).netloc:
            continue
        day = day_from_path(href.removeprefix('2026/'))
        title = None
        if creator == 'drschizzo':
            tag = link.select_one('.num')
            day = day_from_path(tag.get_text(strip=True).removeprefix('Day ')) if tag else None
            tag = link.select_one('.tag')
            title = tag.get_text(strip=True) if tag else None
        if creator == 'loktar' and href.rstrip('/').endswith('/moss'):
            day = 5
        if not day:
            continue
        image_tag = link.select_one('.scene, img, video')
        if creator == 'drschizzo':
            image_tag = link.select_one('.scene')
        image = (image_tag.get('src') if image_tag.name == 'img' else image_tag.get('poster')) if image_tag else None
        if creator == 'adam':
            slug = href.rstrip('/').split('/')[-1]
            image = f'{slug}.jpg'
        elif creator == 'akella':
            image = f'{day}/cover.jpg'
        elif creator == 'drschizzo':
            image = image_tag.get('data-src') or image if image_tag else None
        yield entry(creator, day, href, image, title)

def web_gallery(creator):
    base = CREATORS[creator][2]
    document = soup(base)
    if creator == 'spite':
        listing = fetch(urljoin(base, 'modules/days.js'))
        match = re.search(r'\]\s*,\s*\w+\s*=\s*\[([\d,\s]+)\]', listing)
        days = [int(n) for n in re.findall(r'\d+', match[1])] if match else []
        # The gallery can lag behind a published day page.
        repo = GITHUB + 'spite/codevember-2026'
        paths = repository_paths('spite/codevember-2026')
        for day in DAY_RANGE:
            if day in days:
                yield entry(creator, day, f'{day}/', f'screenshots/{day}.jpg')
            elif f'{day}/index.html' in paths:
                url = urljoin(base, f'{day}/')
                if 'Codevember 2026' in fetch(url):
                    image_path = f'screenshots/{day}.jpg'
                    yield entry(creator, day, url, image_path if image_path in paths else None, source=f'{repo}/tree/HEAD/{day}')
        return
    if creator == 'eric':
        script = document.select_one('link[rel=modulepreload][href*="days-"]')
        listing = fetch(urljoin(base, script['href']))
        for day, title, fields in re.findall(r'day:\s*(\d+),\s*title:\s*"([^"]+)"(.*?)(?=\},\{day:|\}\])', listing, re.S):
            path = re.search(r'\bpath:\s*"([^"]+)"', fields)
            href = urljoin(base, (path[1] if path else day.zfill(2)) + '/')
            page = soup(href)
            og = page.select_one('meta[property="og:image"]')
            yield entry(creator, int(day), href, og.get('content') if og else None, title)
        return

    listing = module(base, document, 'script[type=module][src]')
    if creator == 'frida':
        path = re.search(r'[\x22\x60](\./days-[^\x22\x60]+\.js)', listing)
        listing = fetch(urljoin(urljoin(base, document.select_one('script[type=module][src]')['src']), path[1]))
    if creator == 'felix':
        images = dict(re.findall(r'\b(\w+)=`(/assets/thumbnail-640-[^\x60]+)`', listing))
        for day, name in re.findall(r'"\./(\d+)-[^"]+/thumbnail-640\.webp":(\w+)', listing):
            yield entry(creator, int(day), f'{day}/', images.get(name))
        return
    day_set = re.search(r'new Set\(\[([\d,\s]+)\]\)', listing)
    if not day_set:
        return
    for value in re.findall(r'\d+', day_set[1]):
        day = int(value)
        if day not in DAY_RANGE:
            continue
        if creator == 'vipin':
            yield entry(creator, day, f'days/{day:02}-{THEMES[day - 1].lower()}/', f'thumbs/{day:02}.jpg')
        else:
            yield entry(creator, day, f'{day:03}/', f'thumbs/{day:03}.jpg')

def repository_paths(repo):
    listing = json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1'))
    return {item['path'] for item in listing['tree']}

def repository(creator):
    repo = CREATORS[creator][2].removeprefix(GITHUB)
    base = GITHUB + repo
    raw = RAW + repo + '/HEAD/'
    paths = repository_paths(repo)
    if creator == 'greg':
        readme = fetch(raw + 'README.md')
        for day, title, live in re.findall(r'Day\s+(\d+):\s+\[([^\]]+)\]\((https://[^)]+)\)', readme):
            folder = day.zfill(2)
            cover = next((f'{folder}/social-preview.{ext}' for ext in ('webp', 'jpg', 'png')
                          if f'{folder}/social-preview.{ext}' in paths), None)
            source = f'{base}/tree/HEAD/{folder}'
            try:
                fetch(live)
            except OSError:
                live = source
            yield entry(creator, int(day), live, raw + cover if cover else None, title, source)
        return
    if creator == 'niyati':
        for path in sorted(paths):
            match = re.fullmatch(r'(day-(\d+)-[^/]+)/index.html', path)
            if match:
                day = int(match[2])
                source = f'{base}/tree/HEAD/{match[1]}'
                live = f'https://niyati82.github.io/codevember-2026/{match[1]}/'
                try:
                    fetch(live)
                except OSError:
                    live = source
                yield entry(creator, day, live, source=source)
        return
    for path in sorted(paths):
        match = re.fullmatch(r'(\d\d-[a-z]+)/index.html', path)
        if not match:
            continue
        day = day_from_path(match[1])
        if not day:
            continue
        cover = f'screenshots/day-{match[1]}-initial.png'
        live = f'https://codevember-2026.vercel.app/{match[1]}/'
        try:
            if not re.search(rf'<title>Day {day:02}\b', fetch(live), re.I):
                continue
        except OSError:
            continue
        yield entry(creator, day, live, raw + cover if cover in paths else None,
                    source=f'{base}/tree/HEAD/{match[1]}')

def media_for(item):
    media = item.select_one('.attachment.image img, video[poster], .video-container img')
    if media:
        url = media.get('src') or media.get('poster')
        if url and 'pbs.twimg.com/' in url:
            return url.split('?')[0] + '?name=large'

def posts(creator, pages=2):
    handle = CREATORS[creator][1]
    url = urljoin(MIRROR, handle)
    for _ in range(pages):
        page = soup(url)
        for item in page.select('.timeline-item'):
            author = item.select_one('.username')
            stamp = item.select_one('.tweet-date a')
            content = item.select_one('.tweet-content')
            if not author or not stamp or not content or author.get_text(strip=True).lower() != '@' + handle.lower():
                continue
            yield (
                stamp['href'].split('/status/')[-1].split('#')[0],
                content.get_text(' ', strip=True),
                [a['href'] for a in content.select('a[href^="https://"]')],
                media_for(item),
            )
        more = page.select('.show-more a')
        if not more:
            break
        url = urljoin(MIRROR, more[-1]['href'])

def social(creator):
    base = CREATORS[creator][2]
    previews = {}
    for post_id, message, links, image in posts(creator):
        source = X + CREATORS[creator][1] + '/status/' + post_id
        for link in links:
            match = {
                'lars': r'larsberg\.github\.io/2026-codevember-(\d+)',
                'pwd': r'dasprinzip\.com/codevember2026/(\d+)',
            }.get(creator)
            if match and re.search(match, link):
                yield entry(creator, int(re.search(match, link)[1]), link, image, source=source)
        if creator == 'gregory':
            match = re.search(r'#codevember\s+day\s+(\d+)', message, re.I)
            if match and not message.lower().startswith('working on'):
                previews.setdefault(int(match[1]), (source, image))
        if creator == 'aki':
            for link in links:
                if link.startswith(base + '#codevember='):
                    slug = link.split('=')[-1]
                    if slug in THEMES:
                        yield entry(creator, THEMES.index(slug) + 1, link, image, source=source)
    if creator == 'gregory':
        for link in soup(base).select('a[href]'):
            href = link['href']
            day = day_from_path(href)
            if day and re.fullmatch(r'\d\d_[a-z]+/', href):
                source, image = previews.pop(day, (base, None))
                yield entry(creator, day, href, image, source=source)
        for day, (source, image) in previews.items():
            if image:
                yield entry(creator, day, source, image, source=source)

def gather(task):
    creator, reader = task
    found = []
    try:
        found.extend(reader(creator))
        if not found:
            raise ValueError('source returned no entries')
    except Exception as error:
        # Keep both earlier discoveries and saved records if a source is temporarily unavailable.
        print(f'{creator}: {error}')
        return found, creator
    return found, None

def normalized(value):
    parts = urlsplit(value)
    if parts.scheme not in ('https', 'http') or not parts.hostname:
        raise ValueError(f'Expected an HTTP link, got {value!r}')
    return urlunsplit(('https', parts.netloc.lower(), parts.path.rstrip('/'), parts.query, parts.fragment))

def work_key(work):
    creator = work['creator']
    day = work.get('day', 0)
    # Some sources move the same numbered work from a release post or repo to a live demo.
    url = '' if creator in ('niyati', 'greg', 'gregory') else normalized(work['url'])
    return creator, day, url

def merge(rows, row):
    key = work_key(row)
    previous = rows.get(key, {})
    # Keep an existing image if the upstream listing temporarily stops advertising it.
    rows[key] = {**previous, **{k: v for k, v in row.items() if v is not None}}

def image_is_live(url):
    try:
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Range': 'bytes=0-127'})
        with urlopen(request, timeout=8) as response:
            return response.headers.get_content_maintype() == 'image' and bool(response.read(1))
    except OSError:
        return False

def daily_updates(old, rows, today):
    previous = old.get('dailyUpdates', {})
    themes = set(previous.get('themes', [])) if previous.get('date') == today else set()
    known = {work_key(work) for work in old.get('works', [])}
    for key, work in rows.items():
        if key not in known:
            themes.add(f'{work["day"]:02}' if work.get('day') else 'free')
    return {'date': today, 'themes': sorted(themes)}

def refresh(validate_images):
    old = json.loads(DATA.read_text()) if DATA.exists() else {}
    curated = json.loads(ENTRIES.read_text())
    creators = {**old.get('creators', {}), **{key: dict(zip(('name', 'handle', 'url'), values))
                                               for key, values in CREATORS.items()}}
    creators.update(curated.get('creators', {}))
    rows = {work_key(row): row for row in old.get('works', [])}
    previous_rows = rows.copy()
    before = set(rows)
    tasks = (
        [(key, gallery_links) for key in ('mrdoob', 'adam', 'akella', 'theo', 'drschizzo', 'shoreless', 'loktar')]
        + [(key, web_gallery) for key in ('spite', 'vipin', 'frida', 'eric', 'felix')]
        + [(key, repository) for key in ('andrew', 'greg', 'niyati')]
        + [(key, social) for key in ('lars', 'gregory', 'aki', 'pwd')]
    )
    failed = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for items, warning in pool.map(gather, tasks):
            for row in items:
                merge(rows, row)
            if warning:
                failed.append(warning)
    for row in curated['works']:
        merge(rows, entry(row['creator'], row.get('day'), row['url'], row.get('image'),
                          row.get('title'), row.get('source'), **{k: row[k] for k in ('theme',) if k in row}))
    for row in rows.values():
        if row['creator'] not in creators or not (row.get('day') in DAY_RANGE or row.get('theme')):
            raise ValueError(f'Invalid work: {row}')
        normalized(row['source'])
        normalized(row['url'])
        image = row.get('image')
        if image and image.startswith('./covers/'):
            if not re.fullmatch(r'\./covers/[a-z0-9.-]+', image) or not (ROOT / image).is_file():
                raise ValueError(f'Invalid local cover: {image}')
        elif image:
            normalized(image)

    ordered = sorted(rows.values(), key=lambda work: (
        work.get('day', 31), list(creators).index(work['creator']), work['title'], work['url'],
    ))
    if validate_images:
        with ThreadPoolExecutor(max_workers=16) as pool:
            images = {work['image'] for work in ordered if work.get('image', '').startswith('http')}
            broken = {url for url, valid in zip(images, pool.map(image_is_live, images)) if not valid}
        for work in ordered:
            if work.get('image') in broken:
                print(f'Cover unavailable: @{work["creator"]} {work.get("day")} {work["image"]}')
                # Ignore a new invalid image and keep the previous catalogue's verified URL.
                prior = previous_rows.get(work_key(work), {})
                if prior.get('image'):
                    work['image'] = prior['image']
                else:
                    work.pop('image')
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
    data = {
        'themes': THEMES, 'creators': creators, 'works': ordered,
        'dailyUpdates': daily_updates(old, rows, today),
    }
    content_changed = any(data[key] != old.get(key) for key in ('themes', 'creators', 'works'))
    if content_changed or old.get('updated'):
        data['updated'] = today if content_changed else old['updated']
    if any(data[key] != old.get(key) for key in data):
        with tempfile.NamedTemporaryFile(mode='w', dir=DATA.parent, encoding='utf-8', delete=False) as output:
            temp = Path(output.name)
            try:
                json.dump(data, output, ensure_ascii=False, indent=2)
                output.write('\n')
                output.close()
                temp.chmod(0o644)
                temp.replace(DATA)
            finally:
                temp.unlink(missing_ok=True)
    print(f'{len(rows)} works, {len(rows.keys() - before)} new, {len(failed)} source warnings')
    return bool(failed)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-images', action='store_true', help='Check image URLs before writing the catalogue')
    args = parser.parse_args()
    with Path(__file__).open() as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        raise SystemExit(refresh(args.check_images))
