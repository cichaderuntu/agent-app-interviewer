"""Offline, standard-library checks for the interview bank and release archives."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import zipfile

COUNT_PREFIXES = {'job_descriptions': 'J', 'interview_articles': 'I',
                  'community_threads': 'C', 'unverified_leads': 'L',
                  'technical_references': 'T', 'user_documents': 'D'}
TEXT_FIELDS = ('theme', 'kind', 'level', 'question', 'intent', 'rubric_origin',
               'stop_condition', 'retry_variant', 'technical_scope_note')
LIST_FIELDS = ('required_evidence', 'acceptable_alternatives', 'source_ids',
               'technical_source_ids')


def canonical_url(url):
    """Ignore fragments/tracking; preserve query values such as job IDs."""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in ('gclid', 'fbclid')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       parts.path.rstrip('/'), urlencode(sorted(query)), ''))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def validate(skill, baseline=None):
    skill = Path(skill).resolve()
    errors, cards, locations = [], {}, {}
    ledger = read_json(skill / 'references/sources.json')
    sources, urls = {}, {}
    for source in ledger['sources']:
        sid = source.get('id', '')
        if not re.fullmatch(r'[JICLTD]\d{2,}', sid) or sid in sources:
            errors.append(f'duplicate or invalid source ID: {sid}')
        sources[sid] = source
        for key in ('title', 'url', 'access'):
            if not isinstance(source.get(key), str) or not source[key].strip():
                errors.append(f'{sid}: missing source field {key}')
        url = source.get('url', '')
        if sid.startswith('D'):
            digest = source.get('sha256', '')
            count = source.get('page_count')
            pages = source.get('selected_pages')
            if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest) or url != 'urn:sha256:' + digest:
                errors.append(f'{sid}: invalid document digest/URI')
            if not isinstance(source.get('file_name'), str) or not source['file_name'].endswith('.pdf'):
                errors.append(f'{sid}: missing PDF file name')
            if type(count) is not int or count < 1 or not isinstance(pages, list) or not pages or any(
                    type(page) is not int or page < 1 or page > count for page in pages):
                errors.append(f'{sid}: invalid document page range')
        elif not isinstance(url, str) or urlsplit(url).scheme not in ('https', 'http'):
            errors.append(f'{sid}: invalid source URL')
            continue
        normalized = canonical_url(url)
        if normalized in urls:
            errors.append(f'duplicate source URL: {sid} and {urls[normalized]}')
        urls[normalized] = sid
    for key, prefix in COUNT_PREFIXES.items():
        if ledger['counts'].get(key, 0) != sum(sid.startswith(prefix) for sid in sources):
            errors.append(f'wrong source count: {key}')
    followups = 0
    for path in sorted((skill / 'references/cards').glob('*.json')):
        for card in read_json(path)['cards']:
            qid = card.get('id', '')
            if not re.fullmatch(r'Q\d{2,}', qid) or qid in cards:
                errors.append(f'duplicate or invalid question ID: {qid}')
            cards[qid] = card
            locations[qid] = 'cards/' + path.name
            for key in TEXT_FIELDS:
                if not isinstance(card.get(key), str) or not card[key].strip():
                    errors.append(f'{qid}: missing card field {key}')
            for key in LIST_FIELDS:
                value = card.get(key)
                if not isinstance(value, list) or (not value and key != 'technical_source_ids') or any(
                        not isinstance(item, str) or not item.strip() for item in value):
                    errors.append(f'{qid}: invalid or empty {key}')
            if 'reference_answer' in card and (not isinstance(card['reference_answer'], list)
                    or not card['reference_answer'] or any(not isinstance(item, str) or not item.strip()
                    for item in card['reference_answer'])):
                errors.append(f'{qid}: invalid reference answer')
            documents = {sid for sid in card.get('source_ids', []) if isinstance(sid, str) and sid.startswith('D')}
            located = set()
            for evidence in card.get('document_evidence', []):
                if not isinstance(evidence, dict):
                    errors.append(f'{qid}: invalid document evidence')
                    continue
                sid, pages = evidence.get('source_id'), evidence.get('pages')
                source = sources.get(sid, {})
                if sid not in documents or not isinstance(pages, list) or not pages or any(
                        type(page) is not int or page not in source.get('selected_pages', []) for page in pages):
                    errors.append(f'{qid}: invalid document evidence pages')
                else:
                    located.add(sid)
            if documents != located:
                errors.append(f'{qid}: missing document evidence page locator')
            for key in ('source_ids', 'technical_source_ids'):
                for sid in card.get(key, []) if isinstance(card.get(key), list) else []:
                    if not isinstance(sid, str) or sid not in sources:
                        errors.append(f'{qid}: unknown source {sid}')
                    elif sid.startswith('L'):
                        errors.append(f'{qid}: unverified lead {sid} cannot support a card')
                    elif key == 'technical_source_ids' and not sid.startswith('T'):
                        errors.append(f'{qid}: nontechnical source in technical evidence: {sid}')
            triggers = card.get('followup_triggers')
            if not isinstance(triggers, list) or not triggers:
                errors.append(f'{qid}: missing followup triggers')
                continue
            followups += len(triggers)
            for trigger in triggers:
                if not isinstance(trigger, dict) or any(
                        not isinstance(trigger.get(key), str) or not trigger[key].strip()
                        for key in ('trigger', 'question')):
                    errors.append(f'{qid}: incomplete followup trigger/question')
    index = (skill / 'references/question-index.md').read_text(encoding='utf-8-sig')
    indexed = set()
    for line in index.splitlines():
        if not re.match(r'^\|\s*Q\d+', line):
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        qid = cells[0]
        if qid in indexed or qid not in cards or len(cells) != 6:
            errors.append(f'invalid or duplicate index row: {qid}')
            continue
        indexed.add(qid)
        target = re.search(r'\]\(([^)]+)\)', cells[4])
        if not target or target[1] != locations[qid]:
            errors.append(f'{qid}: index points to wrong card file')
        if cells[3] != cards[qid]['question']:
            errors.append(f'{qid}: index question differs from card')
        if set(re.findall(r'\b[JICLTD]\d+\b', cells[5])) != set(cards[qid].get('source_ids', [])):
            errors.append(f'{qid}: index sources differ from card')
    if indexed != cards.keys():
        errors.append('index/card IDs differ')
    for match in re.finditer(r'(\d+)道基础题', index):
        if int(match[1]) != len(cards):
            errors.append('wrong index question count')
    readme = skill.parent / 'README.md'
    if readme.exists():
        text = readme.read_text(encoding='utf-8-sig')
        for pattern, count in ((r'(\d+)\s*张题卡', len(cards)),
                               (r'(\d+)\s*条(?:针对性)?追问', followups)):
            if any(int(match[1]) != count for match in re.finditer(pattern, text)):
                errors.append('wrong README question/followup count')
    for path in skill.rglob('*.md'):
        for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            if not (path.parent / target.split('#')[0]).exists():
                errors.append(f'broken local link: {path.relative_to(skill)} -> {target}')
    if baseline:
        baseline = Path(baseline)
        old_sources = {s['id'] for s in read_json(baseline / 'references/sources.json')['sources']}
        old_cards = {c['id'] for p in (baseline / 'references/cards').glob('*.json')
                     for c in read_json(p)['cards']}
        for label, removed in (('source', old_sources - sources.keys()), ('question', old_cards - cards.keys())):
            if removed:
                errors.append(f'removed historical {label} IDs: {sorted(removed)}')
    return {'ok': not errors, 'cards': len(cards), 'followups': followups,
            'sources': len(sources), 'errors': errors}


def release_files(repo):
    repo = Path(repo).resolve()
    files = {path.relative_to(repo).as_posix(): path for path in
             (repo / 'agent-app-interviewer').rglob('*') if path.is_file()
             and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')}
    for name in ('README.md', '.gitignore'):
        if (repo / name).exists():
            files[name] = repo / name
    return files


def verify_archive(repo, archive):
    """Compare distributable files without extracting untrusted ZIP paths."""
    expected = release_files(repo)
    with zipfile.ZipFile(archive) as bundle:
        files = {}
        for entry in bundle.infolist():
            if entry.is_dir():
                continue
            pieces = entry.filename.split('/', 1)
            if len(pieces) != 2 or pieces[1] in files:
                raise ValueError('invalid/duplicate archive path')
            files[pieces[1]] = entry
        for name, path in expected.items():
            if name not in files:
                raise ValueError(f'remote archive missing: {name}')
            if bundle.read(files[name]).replace(b'\r\n', b'\n') != path.read_bytes().replace(b'\r\n', b'\n'):
                raise ValueError(f'remote archive differs: {name}')
        extra = {name for name in files if name.startswith('agent-app-interviewer/')} - expected.keys()
        if extra:
            raise ValueError(f'unexpected remote skill files: {sorted(extra)}')
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--archive', type=Path, help='Also compare a GitHub ZIP against the local release')
    args = parser.parse_args()
    try:
        result = validate(args.skill, args.baseline)
        if result['ok'] and args.archive:
            result['verified_files'] = verify_archive(args.skill.parent, args.archive)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as exc:
        result = {'ok': False, 'errors': [str(exc)]}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
