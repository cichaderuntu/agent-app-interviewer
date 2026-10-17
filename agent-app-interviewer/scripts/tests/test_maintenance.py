"""Offline acceptance tests: no network, live approvals, or GitHub mutations."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
import zipfile

SKILL = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL / 'scripts'


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        # Inherit workspace ACLs; Python 3.14's owner-only temp ACL excludes
        # the Windows restricted token used by the desktop sandbox.
        self.scratch = SKILL.parent / '.validation'
        self.scratch.mkdir(exist_ok=True)
        self.root = self.scratch / ('tests-' + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(self.cleanup_fixture)
        self.skill = self.root / 'agent-app-interviewer'
        shutil.copytree(SKILL, self.skill, ignore=shutil.ignore_patterns('__pycache__'))
        self.state = self.root / 'private' / 'state.json'
        self.config = self.root / 'private' / 'config.json'
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({'weekday': 0, 'hour': 9,
            'utc_offset_hours': 0, 'repository': 'example/interview-bank'}), encoding='utf-8')

    def cleanup_fixture(self):
        if self.root.resolve().parent != self.scratch.resolve():
            raise ValueError('Test cleanup escaped its workspace')
        shutil.rmtree(self.root)

    def cli(self, script, *args):
        return subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / script), *map(str, args)],
                              text=True, capture_output=True, encoding='utf-8')

    def validate(self):
        return self.cli('validate_bank.py', '--skill', self.skill)

    def edit_json(self, relative, change):
        path = self.skill / relative
        data = json.loads(path.read_text(encoding='utf-8'))
        change(data)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def round(self, action, at='2024-01-01T09:00:00+00:00', *extra):
        return self.cli('weekly_state.py', '--state', self.state, '--config', self.config, '--at', at,
                        '--repo-root', self.root, action, *extra)

    def okay(self, result):
        self.assertEqual(result.returncode, 0, (result.stderr or '') + (result.stdout or ''))
        return json.loads(result.stdout)

    def running(self):
        self.okay(self.round('request'))
        self.okay(self.round('approve'))
        return self.okay(self.round('start'))

    def test_current_bank_validates(self):
        result = self.okay(self.validate())
        source_data = json.loads((self.skill / 'references/sources.json').read_text(encoding='utf-8'))
        card_data = [card for path in (self.skill / 'references/cards').glob('*.json')
                     for card in json.loads(path.read_text(encoding='utf-8'))['cards']]
        self.assertEqual(result['cards'], len(card_data))
        self.assertEqual(result['followups'], sum(len(card['followup_triggers']) for card in card_data))
        self.assertEqual(result['sources'], len(source_data['sources']))

    def test_valid_source_expansion_is_accepted(self):
        before = self.okay(self.validate())
        def add_source(data):
            source = dict(data['sources'][0], id='J999999', url='https://example.com/jobs/new-verified-role')
            data['sources'].append(source)
            data['counts']['job_descriptions'] += 1
        self.edit_json('references/sources.json', add_source)
        self.assertEqual(self.okay(self.validate())['sources'], before['sources'] + 1)

    def test_duplicate_question_id_is_rejected(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'].append(x['cards'][0]))
        self.assertNotEqual(self.validate().returncode, 0)

    def add_document(self):
        def change(data):
            data['sources'].append({'id': 'D999', 'title': 'User PDF fixture',
                'url': 'urn:sha256:' + 'f' * 64, 'sha256': 'f' * 64,
                'file_name': 'fixture.pdf', 'page_count': 12,
                'selected_pages': [3], 'access': 'selected pages read'})
            data['counts']['user_documents'] = data['counts'].get('user_documents', 0) + 1
        self.edit_json('references/sources.json', change)

    def test_local_pdf_provenance_is_accepted_without_fake_web_link(self):
        self.add_document()
        self.okay(self.validate())

    def test_local_pdf_digest_mismatch_is_rejected(self):
        self.add_document()
        self.edit_json('references/sources.json', lambda x: x['sources'][-1].update(sha256='a' * 64))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_local_pdf_page_outside_document_is_rejected(self):
        self.add_document()
        self.edit_json('references/sources.json', lambda x: x['sources'][-1].update(selected_pages=[13]))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_non_document_cannot_use_local_document_uri(self):
        self.edit_json('references/sources.json', lambda x: x['sources'][0].update(url='urn:sha256:' + 'a' * 64))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_empty_optional_reference_answer_is_rejected(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'][0].update(reference_answer=[]))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_pdf_question_requires_page_locator(self):
        self.add_document()
        def change(data):
            data['cards'][0]['source_ids'].append('D999')
        self.edit_json('references/cards/rag.json', change)
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('document evidence', result.stdout)

    def test_unknown_source_is_rejected(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'][0]['source_ids'].append('I999'))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_unverified_lead_cannot_support_a_card(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'][0]['source_ids'].append('L01'))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_nontechnical_source_cannot_be_technical_evidence(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'][0]['technical_source_ids'].append('I01'))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_missing_followup_question_is_rejected(self):
        self.edit_json('references/cards/rag.json', lambda x: x['cards'][0]['followup_triggers'][0].pop('question'))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_wrong_source_count_is_rejected(self):
        self.edit_json('references/sources.json', lambda x: x['counts'].update(job_descriptions=999))
        self.assertNotEqual(self.validate().returncode, 0)

    def test_duplicate_source_link_with_tracking_is_rejected(self):
        def duplicate(data):
            source = dict(data['sources'][0], id='J99')
            source['url'] += '?utm_source=weekly#top'
            data['sources'].append(source)
            data['counts']['job_descriptions'] += 1
        self.edit_json('references/sources.json', duplicate)
        self.assertNotEqual(self.validate().returncode, 0)

    def test_index_missing_card_is_rejected(self):
        path = self.skill / 'references/question-index.md'
        path.write_text('\n'.join(line for line in path.read_text(encoding='utf-8').splitlines()
                                  if not line.startswith('| Q05 |')), encoding='utf-8')
        self.assertNotEqual(self.validate().returncode, 0)

    def test_index_wrong_file_is_rejected(self):
        path = self.skill / 'references/question-index.md'
        path.write_text(path.read_text(encoding='utf-8').replace('[rag.json](cards/rag.json)',
                                                                 '[rag.json](cards/agents.json)', 1), encoding='utf-8')
        self.assertNotEqual(self.validate().returncode, 0)

    def test_baseline_removal_is_rejected(self):
        baseline = self.root / 'baseline'
        shutil.copytree(self.skill, baseline)
        self.edit_json('references/sources.json', lambda x: x['sources'].pop())
        result = self.cli('validate_bank.py', '--skill', self.skill, '--baseline', baseline)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('removed', result.stdout)

    def test_request_before_schedule_is_rejected(self):
        self.assertNotEqual(self.round('request', '2024-01-01T08:59:00+00:00').returncode, 0)
        self.assertFalse(self.state.exists())

    def test_configured_schedule_accepts_request(self):
        self.assertTrue(self.okay(self.round('request'))['notify'])

    def test_wrong_repository_cannot_complete_publication(self):
        self.running()
        self.okay(self.round('searched'))
        self.okay(self.round('ready'))
        result = self.round('finish', '2024-01-01T09:00:00+00:00', '--archive', self.root / 'missing.zip',
                            '--commit-url', 'https://github.com/other/repository/commit/' + 'a' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('configured repository', result.stdout)

    def test_duplicate_request_does_not_notify_twice(self):
        first = self.okay(self.round('request'))
        again = self.okay(self.round('request'))
        self.assertTrue(first['notify'])
        self.assertFalse(again['notify'])
        self.assertEqual(first['round_id'], '2024-01-01')
        self.assertFalse(first['may_search'])

    def test_unapproved_request_cannot_start(self):
        self.okay(self.round('request'))
        self.assertNotEqual(self.round('start').returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())['rounds']['2024-01-01']['status'], 'pending')

    def test_approved_round_can_start_only_once(self):
        self.assertTrue(self.running()['may_search'])
        self.assertNotEqual(self.round('start').returncode, 0)

    def test_approval_does_not_carry_into_next_week(self):
        self.okay(self.round('request'))
        self.okay(self.round('approve'))
        self.okay(self.round('request', '2024-01-08T09:00:00+00:00'))
        self.assertNotEqual(self.round('start', '2024-01-08T09:01:00+00:00').returncode, 0)
        state = json.loads(self.state.read_text())
        self.assertEqual(state['rounds']['2024-01-01']['status'], 'expired')

    def test_skip_does_not_start_work(self):
        self.okay(self.round('request'))
        self.okay(self.round('skip'))
        self.assertNotEqual(self.round('start').returncode, 0)

    def test_stopped_search_does_not_block_next_week_or_claim_search_success(self):
        self.running()
        self.okay(self.round('stop', '2024-01-01T09:05:00+00:00', '--note', 'User cancelled incomplete search'))
        state = json.loads(self.state.read_text())
        self.assertEqual(state['rounds']['2024-01-01']['status'], 'stopped')
        self.assertIsNone(state['last_successful_search_at'])
        at = '2024-01-08T09:00:00+00:00'
        for action in ['request', 'approve']:
            self.okay(self.round(action, at))
        result = self.okay(self.round('start', at))
        self.assertTrue(result['may_search'])
        self.assertEqual(result['search_from'], '2023-12-09')

    def test_unfinished_search_blocks_parallel_start(self):
        self.running()
        at = '2024-01-08T09:00:00+00:00'
        for action in ['request', 'approve']:
            self.okay(self.round(action, at))
        self.assertNotEqual(self.round('start', at).returncode, 0)

    def test_first_search_window_is_30_days(self):
        data = self.running()
        self.assertEqual(data['search_from'], '2023-12-02')

    def test_no_changes_records_search_without_publication(self):
        self.running()
        self.okay(self.round('searched'))
        result = self.okay(self.round('no-changes'))
        self.assertEqual(result['status'], 'completed_no_changes')
        state = json.loads(self.state.read_text())
        self.assertEqual(state['last_successful_search_at'], '2024-01-01T09:00:00+00:00')

    def test_next_search_overlaps_last_search_by_seven_days(self):
        self.test_no_changes_records_search_without_publication()
        at = '2024-01-08T09:00:00+00:00'
        for action in ['request', 'approve']:
            self.okay(self.round(action, at))
        self.assertEqual(self.okay(self.round('start', at))['search_from'], '2023-12-25')

    def test_publish_failure_cannot_be_marked_complete_without_verification(self):
        self.running()
        self.okay(self.round('searched'))
        self.okay(self.round('ready'))
        self.okay(self.round('publish-failed', '2024-01-01T09:00:00+00:00', '--note', 'login unavailable'))
        self.assertNotEqual(self.round('finish').returncode, 0)
        self.assertEqual(json.loads(self.state.read_text())['rounds']['2024-01-01']['status'], 'publish_failed')

    def test_verified_remote_archive_completes_round(self):
        self.running()
        self.okay(self.round('searched'))
        self.okay(self.round('ready'))
        archive = self.root / 'remote.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for path in self.skill.rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    z.write(path, 'agent-app-interviewer-main/' + path.relative_to(self.root).as_posix())
        result = self.okay(self.round('finish', '2024-01-01T09:00:00+00:00', '--archive', archive,
                                     '--commit-url', 'https://github.com/example/interview-bank/commit/' + 'a' * 40))
        self.assertEqual(result['status'], 'completed')

    def test_incomplete_remote_archive_does_not_complete_round(self):
        self.running()
        self.okay(self.round('searched'))
        self.okay(self.round('ready'))
        archive = self.root / 'remote.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('agent-app-interviewer-main/agent-app-interviewer/SKILL.md', 'wrong')
        self.assertNotEqual(self.round('finish', '2024-01-01T09:00:00+00:00', '--archive', archive,
                                      '--commit-url', 'https://github.com/example/interview-bank/commit/' + 'a' * 40).returncode, 0)


if __name__ == '__main__':
    unittest.main()
