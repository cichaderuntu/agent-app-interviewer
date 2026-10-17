"""Optional local round-state utility. This tool never grants approval.

No network operations. Schedule and target repository can be supplied through a
local JSON config. All state lives outside the distributable skill by default.
"""
import argparse
from datetime import datetime, time, timedelta, timezone
import json
from pathlib import Path
import re
import sys

from validate_bank import validate, verify_archive

UNFINISHED = {'running', 'pending_publish', 'publish_failed'}


def execute(args):
    config = json.loads(args.config.read_text(encoding='utf-8')) if args.config.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('Local config must be a JSON object')
    weekday, hour = config.get('weekday', 0), config.get('hour', 0)
    offset = config.get('utc_offset_hours', 0)
    if type(weekday) is not int or not 0 <= weekday <= 6 or type(hour) is not int or not 0 <= hour <= 23:
        raise ValueError('Config weekday/hour is out of range')
    if type(offset) is not int or not -12 <= offset <= 14:
        raise ValueError('Config UTC offset is out of range')
    repository = config.get('repository')
    if repository is not None and (not isinstance(repository, str) or not re.fullmatch(
            r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)):
        raise ValueError('Invalid configured repository')
    zone = timezone(timedelta(hours=offset))
    now = datetime.fromisoformat(args.at) if args.at else datetime.now(zone)
    if now.tzinfo is None:
        raise ValueError('--at must include a timezone')
    now = now.astimezone(zone)
    period_start = now.date() - timedelta(days=(now.weekday() - weekday) % 7)
    scheduled = datetime.combine(period_start, time(hour), zone)
    current = period_start.isoformat()
    rid = args.round_id or current
    stamp = now.isoformat(timespec='seconds')
    state = json.loads(args.state.read_text(encoding='utf-8')) if args.state.exists() else {
        'schema_version': 1, 'last_successful_search_at': None, 'rounds': {}}
    rounds = state['rounds']
    notify, changed = False, True
    if args.action == 'request':
        if now < scheduled or rid != current:
            raise ValueError('No request before the configured schedule')
        if rid in rounds:
            changed = False
        else:
            for old_id, old in rounds.items():
                if old_id < current and old['status'] in ('pending', 'approved'):
                    old.update(status='expired', expired_at=stamp)
            rounds[rid] = {'status': 'pending', 'requested_at': stamp}
            notify = True
    else:
        if rid not in rounds:
            raise ValueError('No request for this round; approval cannot be invented')
        record = rounds[rid]
        status = record['status']
        if args.action in ('approve', 'skip', 'start') and (rid != current or now < scheduled):
            raise ValueError('Approval/start is only valid for the requested current week')
        if args.action == 'approve':
            if status != 'pending':
                raise ValueError('Only a pending round can receive human approval')
            record.update(status='approved', approved_at=stamp, approval_note=args.note or 'Human approval recorded')
        elif args.action == 'skip':
            if status not in ('pending', 'approved'):
                raise ValueError('Only an unstarted round can be skipped')
            record.update(status='skipped', skipped_at=stamp)
        elif args.action == 'stop':
            if status not in ('pending', 'approved', *UNFINISHED) or not args.note:
                raise ValueError('Stopping requires an unfinished round and the actual cancellation/failure reason')
            record.update(status='stopped', stopped_at=stamp, stop_note=args.note)
        elif args.action == 'start':
            if status != 'approved':
                raise ValueError('Current round needs explicit human approval and must not have started')
            if any(key != rid and value['status'] in UNFINISHED for key, value in rounds.items()):
                raise ValueError('Finish/recover the unfinished round before starting another')
            last = state['last_successful_search_at']
            start = (datetime.fromisoformat(last).astimezone(zone).date() - timedelta(days=7)
                     if last else now.date() - timedelta(days=30))
            record.update(status='running', started_at=stamp, search_from=start.isoformat(),
                          search_to=now.date().isoformat())
        elif args.action == 'searched':
            if status != 'running':
                raise ValueError('Only a running approved search can be recorded')
            if not record.get('searched_at'):
                record['searched_at'] = stamp
                state['last_successful_search_at'] = stamp
        elif args.action in ('ready', 'no-changes'):
            if status != 'running' or not record.get('searched_at'):
                raise ValueError('Record a completed search before closing or publishing')
            result = validate(args.repo_root / 'agent-app-interviewer')
            if not result['ok']:
                raise ValueError('Bank validation failed: ' + '; '.join(result['errors']))
            record.update(status='pending_publish' if args.action == 'ready' else 'completed_no_changes',
                          checked_at=stamp)
        elif args.action == 'publish-failed':
            if status not in ('pending_publish', 'publish_failed') or not args.note:
                raise ValueError('Publication failure requires a pending publication and a reason')
            record.update(status='publish_failed', failure_note=args.note, failed_at=stamp)
        elif args.action == 'finish':
            if status not in ('pending_publish', 'publish_failed'):
                raise ValueError('No validated publication is pending')
            if not args.archive or not args.commit_url or not re.fullmatch(
                    r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/commit/[0-9a-f]{40}', args.commit_url):
                raise ValueError('Completion requires the actual commit URL and a downloaded verified archive')
            if repository and not args.commit_url.startswith('https://github.com/' + repository + '/commit/'):
                raise ValueError('Commit URL must match the configured repository')
            result = validate(args.repo_root / 'agent-app-interviewer')
            if not result['ok']:
                raise ValueError('Bank validation failed before completion')
            count = verify_archive(args.repo_root, args.archive)
            record.update(status='completed', completed_at=stamp, commit_url=args.commit_url,
                          verified_files=count)
    record = rounds[rid]
    if changed:
        args.state.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.state.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(args.state)
    return {'round_id': rid, 'status': record['status'], 'notify': notify,
            'may_search': args.action == 'start', 'search_from': record.get('search_from'),
            'unfinished_rounds': [key for key, value in rounds.items()
                                  if key != rid and value['status'] in UNFINISHED]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[2]
    parser.add_argument('--state', type=Path, default=repo / 'research/weekly-maintenance/state.json')
    parser.add_argument('--config', type=Path, default=repo / 'research/weekly-maintenance/config.json',
                        help='Optional local schedule/repository JSON config; keep private settings untracked')
    parser.add_argument('--at', help='Timezone-aware test time; omit for live runs')
    parser.add_argument('--round', dest='round_id', help='Resume an explicitly identified unfinished round')
    parser.add_argument('--repo-root', type=Path, default=repo)
    parser.add_argument('action', choices=('request', 'approve', 'skip', 'stop', 'start', 'searched',
                                         'ready', 'no-changes', 'publish-failed', 'finish'))
    parser.add_argument('--note')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--commit-url')
    args = parser.parse_args()
    # A short inherited-ACL directory lock prevents simultaneous state writers.
    args.state.parent.mkdir(parents=True, exist_ok=True)
    lock = args.state.with_suffix('.lock')
    try:
        lock.mkdir()
    except FileExistsError:
        print(json.dumps({'ok': False, 'error': 'State lock exists; inspect the active process before recovery'}))
        return 1
    try:
        result = execute(args)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=True))
        return 1
    finally:
        lock.rmdir()


if __name__ == '__main__':
    sys.exit(main())
