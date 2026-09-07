import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import common
import blocker
import radar
import audit
import review


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.cfg = common.load_config()

    def test_config_independent_of_cwd(self):
        previous = os.getcwd()
        try:
            os.chdir('/tmp')
            self.assertEqual(common.load_config(), self.cfg)
        finally:
            os.chdir(previous)

    def test_invalid_config(self):
        with tempfile.TemporaryDirectory() as directory:
            self.cfg['radar']['max_discoveries'] = -1
            Path(directory, 'config.json').write_text(json.dumps(self.cfg))
            with patch.object(common, 'ROOT', Path(directory)), self.assertRaises(ValueError):
                common.load_config()

    def test_disabled_engines_do_not_call_api(self):
        for engine, section in ((blocker, 'anti_bot'), (radar, 'radar'), (audit, 'review')):
            self.cfg[section]['enabled'] = False
            with patch.object(engine, 'load_config', return_value=self.cfg), patch.object(engine, 'github_request') as request, patch.object(sys, 'argv', ['engine.py']):
                engine.main()
                request.assert_not_called()

    def test_missing_token_is_failure(self):
        for engine in (blocker, radar):
            with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit) as error:
                engine.main()
            self.assertEqual(error.exception.code, 1)

    def test_hibernation_missing_invalid_expired_and_force(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'data'); path.mkdir()
            for value in (None, {}, {'last_dispatched_at': 'bad'},
                          {'last_dispatched_at': (datetime.now(timezone.utc)-timedelta(days=7)).isoformat()}):
                if value is not None:
                    (path/'radar.json').write_text(json.dumps(value))
                self.assertTrue(radar.check_hibernation(self.cfg, directory))
                self.assertFalse(radar.check_hibernation(self.cfg, directory, force=True))
            (path/'radar.json').write_text(json.dumps({'last_dispatched_at': datetime.now(timezone.utc).isoformat()}))
            self.assertFalse(radar.check_hibernation(self.cfg, directory))

    def test_heuristics(self):
        user = {'created_at': datetime.now(timezone.utc).isoformat(), 'following': 450, 'followers': 10}
        self.assertTrue(blocker.evaluate_bot_heuristics(user, self.cfg)[0])
        user['following'] = 20
        self.assertFalse(blocker.evaluate_bot_heuristics(user, self.cfg)[0])
        self.assertFalse(blocker.evaluate_bot_heuristics({}, self.cfg)[0])

    def test_http_timeout_and_error(self):
        response = Mock()
        response.raise_for_status.side_effect = common.requests.HTTPError('rate limited')
        with patch.object(common.requests, 'request', return_value=response) as request:
            with self.assertRaises(common.requests.HTTPError):
                common.github_request('GET', 'https://api.github.com/user/starred')
            self.assertEqual(request.call_args.kwargs['timeout'], 20)

    def test_missing_release_is_not_failure(self):
        response = Mock(status_code=404)
        with patch.object(common.requests, 'request', return_value=response):
            common.github_request('GET', 'https://api.github.com/repos/a/b/releases/latest')
            response.raise_for_status.assert_not_called()

    def test_radar_limits_and_manual_activity(self):
        self.cfg['radar'].update(max_starred_to_analyze=2, max_releases_to_track=1, max_discoveries=1)
        repos = [{'owner': {'login': 'test'}, 'name': str(i), 'language': 'Python', 'topics': ['cli']} for i in range(5)]
        def request(method, url, **kwargs):
            if url.endswith('/user/starred'):
                return Mock(json=lambda: repos)
            if url.endswith('/releases/latest'):
                return Mock(status_code=404)
            return Mock(status_code=200, json=lambda: {'items': [{'full_name': 'a/b', 'html_url': 'https://github.com/a/b', 'stargazers_count': 99}] * 3})
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), patch.object(sys, 'argv', ['radar.py', '--force']), patch.object(radar, 'load_config', return_value=self.cfg), patch.object(radar, 'github_request', side_effect=request) as api, patch.object(radar, 'update_radar_files') as save:
            radar.main()
            self.assertEqual(api.call_count, 3)
            data = save.call_args.args[0]
            self.assertEqual(len(data['discoveries']), 1)
            self.assertIsNotNone(data['last_dispatched_at'])

    def test_background_run_preserves_activity(self):
        self.cfg['radar'].update(max_starred_to_analyze=0, max_discoveries=0)
        original = json.loads((common.ROOT/'data/radar.json').read_text())['last_dispatched_at']
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), patch.object(sys, 'argv', ['radar.py']), patch.object(radar, 'load_config', return_value=self.cfg), patch.object(radar, 'check_hibernation', return_value=False), patch.object(radar, 'github_request') as api, patch.object(radar, 'update_radar_files') as save:
            radar.main()
            api.assert_not_called()
            self.assertEqual(save.call_args.args[0]['last_dispatched_at'], original)

    def test_blocker_paginates_followers(self):
        pages = [[{'login': f'user{i}'} for i in range(100)], [{'login': 'last-user'}]]
        seen = []
        def request(method, url, **kwargs):
            if url.endswith('/user/followers'):
                return Mock(json=lambda: pages[kwargs['params']['page']-1])
            seen.append(url)
            return Mock(status_code=200, json=lambda: {})
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), patch.object(blocker, 'fetch_upstream_blocklist', return_value=set()), patch.object(blocker, 'github_request', side_effect=request), patch.object(blocker, 'update_blocklist_files'):
            blocker.main()
        self.assertTrue(any(url.endswith('/last-user') for url in seen))



class OnboardingTests(unittest.TestCase):
    def test_public_profile_uses_named_user_and_filters_private_repos(self):
        cfg = common.load_config()
        cfg['radar'].update(max_starred_to_analyze=3, max_releases_to_track=0, max_discoveries=0)
        response = Mock(json=lambda: [
            {'private':True,'language':'SecretLanguage','topics':['secret']},
            {'private':False,'language':'Python','topics':['public']},
        ])
        with patch.dict(os.environ, {'GH_TOKEN':'automatic-token','RADAR_USERNAME':'example'}, clear=True), patch.object(sys,'argv',['radar.py','--force']), patch.object(radar,'load_config',return_value=cfg), patch.object(radar,'github_request',return_value=response) as request, patch.object(radar,'update_radar_files') as save:
            radar.main()
        self.assertEqual(request.call_args.args[1], 'https://api.github.com/users/example/starred')
        data = save.call_args.args[0]
        self.assertEqual(data['profile_dna']['top_languages'], ['Python'])
        self.assertEqual(data['profile_user'], 'example')

    def test_invalid_profile_rejected_before_api(self):
        with patch.dict(os.environ, {'GH_TOKEN':'token','RADAR_USERNAME':'../user'}), patch.object(radar,'github_request') as request, self.assertRaises(ValueError):
            radar.main()
        request.assert_not_called()

    def test_site_metadata_never_includes_environment_secrets(self):
        from build_site import build_site
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'data').mkdir(); (root/'docs').mkdir()
            (root/'data/radar.json').write_text('{}')
            with patch.dict(os.environ, {'GITHUB_REPOSITORY':'owner/fork','DEFAULT_BRANCH':'develop','GH_BLOCKER_TOKEN':'must-not-leak','GITHUB_TOKEN':'must-not-leak'}):
                build_site(root)
            self.assertEqual(json.loads((root/'docs/site.json').read_text()), {'repository':'owner/fork','default_branch':'develop'})
            self.assertEqual((root/'docs/data/radar.json').read_text(), '{}')

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.cfg = common.load_config()

    def fresh_bot(self):
        return {'login': 'farm-01',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'following': 450, 'followers': 10, 'public_repos': 0}

    def veteran_human(self):
        return {'login': 'mentor',
                'created_at': (datetime.now(timezone.utc) - timedelta(days=900)).isoformat(),
                'following': 120, 'followers': 800, 'public_repos': 45}

    def test_young_mass_follower_is_suspicious(self):
        trust, reasons, stats = review.score_user(self.fresh_bot(), 'follower', self.cfg)
        self.assertEqual(review.score_user(self.fresh_bot(), 'follower', self.cfg)[1][0]['code'], 'young_mass_follow')
        self.assertLess(trust, self.cfg['review']['trust_threshold'])
        self.assertEqual(stats['following'], 450)

    def test_mutual_veteran_is_trusted(self):
        trust, reasons, verdict_stats = review.score_user(self.veteran_human(), 'mutual', self.cfg)
        codes = {r['code'] for r in reasons}
        self.assertIn('mutual', codes)
        self.assertIn('veteran', codes)
        self.assertGreaterEqual(trust, self.cfg['review']['trust_threshold'])

    def test_missing_profile_data_never_crashes(self):
        trust, reasons, stats = review.score_user({}, 'follower', self.cfg)
        self.assertTrue(0 <= trust <= 100)
        self.assertIn('unknown_age', {r['code'] for r in reasons})
        self.assertIsNone(stats['age_days'])

    def test_parse_targets_accepts_mixed_separators_and_rejects_bad_logins(self):
        self.assertEqual(review.parse_targets('Alice, bob\nalice;BOB  carol-99'),
                         ['alice', 'bob', 'carol-99'])
        for bad in ('', '   ', 'evil!user', 'a' * 40, '-lead', 'trail-', 'a..b', 'a--b'):
            with self.assertRaises(ValueError, msg=bad):
                review.parse_targets(bad if bad.strip() else bad or ' , ')

    def test_merge_preserves_blocked_status_but_refreshes_stats(self):
        old = [{'login': 'farm-01', 'status': 'blocked', 'blocked_at': '2026-01-01T00:00:00+00:00',
                'trust': 4, 'verdict': 'suspicious', 'direction': 'follower',
                'profile_url': 'https://github.com/farm-01', 'reasons': [], 'stats': {}}]
        fresh = [{'login': 'FARM-01', 'status': 'pending', 'blocked_at': None,
                  'trust': 9, 'verdict': 'suspicious', 'direction': 'follower',
                  'profile_url': 'https://github.com/farm-01',
                  'reasons': [{'code': 'mass_follow', 'detail': '1/0', 'tone': 'bad'}],
                  'stats': {'followers': 0}}]
        merged = review.merge_users(old, fresh)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['status'], 'blocked')
        self.assertEqual(merged[0]['blocked_at'], '2026-01-01T00:00:00+00:00')
        self.assertEqual(merged[0]['stats'], {'followers': 0})

    def test_blocker_review_mode_never_puts_blocks(self):
        self.cfg['anti_bot']['review_mode'] = True
        bot = self.fresh_bot()
        pages = [[{'login': 'farm-01'}], []]
        calls = []

        def request(method, url, **kwargs):
            calls.append((method, url))
            if url.endswith('/user/followers'):
                page = kwargs['params']['page']
                return Mock(json=lambda p=page: pages[p - 1] if p - 1 < len(pages) else [])
            return Mock(status_code=200, json=lambda: dict(bot))

        saved = {}

        def save(users, threshold):
            saved['users'] = users
            return {'totals': {'suspicious': len(users)}}

        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(blocker, 'load_config', return_value=self.cfg), \
             patch.object(blocker, 'fetch_upstream_blocklist', return_value=set()), \
             patch.object(blocker, 'github_request', side_effect=request), \
             patch.object(blocker, 'update_blocklist_files'), \
             patch.object(review, 'load_queue', return_value={'users': []}), \
             patch.object(review, 'save_queue', side_effect=save):
            blocker.main()
        self.assertFalse(any(m == 'PUT' and '/user/blocks/' in u for m, u in calls))
        self.assertEqual(len(saved['users']), 1)
        self.assertEqual(saved['users'][0]['verdict'], 'suspicious')

    def test_audit_block_records_decision_and_continues_on_failure(self):
        self.cfg['review']['enabled'] = True
        queue = {'users': [{'login': 'farm-01', 'trust': 12, 'status': 'pending',
                            'profile_url': 'https://github.com/farm-01'}]}

        def request(method, url, **kwargs):
            if url.endswith('/user/blocks/farm-01'):
                return Mock(status_code=204)
            raise common.requests.HTTPError('gone')

        saved = {}
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request', side_effect=request), \
             patch.object(review, 'load_queue', return_value=queue), \
             patch.object(review, 'save_queue',
                          side_effect=lambda users, threshold: saved.setdefault('users', users)), \
             patch.object(audit, 'update_blocklist_files') as persist:
            with self.assertRaises(SystemExit) as error:
                audit.main(['--block', 'farm-01, ghost-404'])
            self.assertEqual(error.exception.code, 1)
        self.assertEqual(queue['users'][0]['status'], 'blocked')
        self.assertIsNotNone(queue['users'][0]['blocked_at'])
        self.assertEqual(saved['users'], queue['users'])
        self.assertTrue(any(b['username'] == 'farm-01' for b in persist.call_args.args[0]))

    def test_audit_scan_writes_queue_without_blocking(self):
        self.cfg['review'].update(enabled=True, max_users_to_scan=0)
        bot, human = self.fresh_bot(), self.veteran_human()
        profiles = {'farm-01': bot, 'mentor': human}

        def request(method, url, **kwargs):
            if url.endswith('/user/followers'):
                return Mock(json=lambda: [{'login': 'farm-01'}] if kwargs['params']['page'] == 1 else [])
            if url.endswith('/user/following'):
                return Mock(json=lambda: [{'login': 'mentor'}] if kwargs['params']['page'] == 1 else [])
            login = url.rsplit('/', 1)[-1]
            return Mock(status_code=200, json=lambda: profiles[login])

        saved = {}

        def fake_save(users, threshold):
            payload = {'totals': {'scanned': len(users),
                                  'trusted': sum(1 for u in users if u['verdict'] == 'trusted'),
                                  'suspicious': sum(1 for u in users if u['verdict'] == 'suspicious'),
                                  'blocked': 0}}
            saved['payload'] = (users, threshold)
            return payload

        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request', side_effect=request) as api, \
             patch.object(review, 'load_queue', return_value={'users': []}), \
             patch.object(review, 'save_queue', side_effect=fake_save):
            audit.main([])
        self.assertFalse(any(m == 'PUT' for m, _ in
                             ((c.args[0], c.args[1]) for c in api.call_args_list)))
        users, threshold = saved['payload']
        by_login = {u['login']: u for u in users}
        self.assertEqual(by_login['farm-01']['verdict'], 'suspicious')
        self.assertEqual(by_login['mentor']['direction'], 'following')

    def test_audit_scan_403_prints_actionable_permission_hint(self):
        import io
        from contextlib import redirect_stdout
        self.cfg['review']['enabled'] = True
        error = common.requests.HTTPError('forbidden')
        error.response = Mock(status_code=403)
        buffer = io.StringIO()
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request', side_effect=error):
            with redirect_stdout(buffer), self.assertRaises(common.requests.HTTPError):
                audit.main([])
        self.assertIn('Followers', buffer.getvalue())

    def test_propose_marks_approved_without_any_api_call(self):
        queue = {'users': [{'login': 'farm-01', 'trust': 12, 'status': 'pending',
                            'profile_url': 'https://github.com/farm-01'}]}
        saved = {}
        with patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request') as api, \
             patch.object(review, 'load_queue', return_value=queue), \
             patch.object(review, 'save_queue',
                          side_effect=lambda users, threshold: saved.setdefault('users', users)):
            audit.main(['--propose', 'farm-01, newcomer-99'])
        api.assert_not_called()
        by_login = {u['login']: u for u in saved['users']}
        self.assertEqual(by_login['farm-01']['status'], 'approved')
        self.assertEqual(by_login['newcomer-99']['status'], 'approved')
        self.assertNotIn('blocked_at', by_login['newcomer-99'])

    def test_execute_approved_blocks_only_approved_and_skips_save_when_idle(self):
        queue = {'users': [
            {'login': 'farm-01', 'trust': 5, 'status': 'approved',
             'profile_url': 'https://github.com/farm-01'},
            {'login': 'mentor', 'trust': 95, 'status': 'pending',
             'profile_url': 'https://github.com/mentor'},
        ]}

        def request(method, url, **kwargs):
            return Mock(status_code=204)

        saved = {}
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request', side_effect=request) as api, \
             patch.object(review, 'load_queue', return_value=queue), \
             patch.object(review, 'save_queue',
                          side_effect=lambda users, threshold: saved.setdefault('users', users)), \
             patch.object(audit, 'update_blocklist_files') as persist:
            audit.main(['--execute-approved'])
        puts = [c.args[1].rsplit('/', 1)[-1] for c in api.call_args_list]
        self.assertEqual(puts, ['farm-01'])
        self.assertEqual(queue['users'][0]['status'], 'blocked')
        self.assertEqual(queue['users'][1]['status'], 'pending')
        self.assertTrue(any(b['username'] == 'farm-01' for b in persist.call_args.args[0]))

    def test_execute_approved_without_approvals_is_noop(self):
        queue = {'users': [{'login': 'mentor', 'status': 'pending'}]}
        with patch.dict(os.environ, {'GH_TOKEN': 'test'}), \
             patch.object(audit, 'load_config', return_value=self.cfg), \
             patch.object(audit, 'github_request') as api, \
             patch.object(review, 'load_queue', return_value=queue), \
             patch.object(review, 'save_queue') as save:
            audit.main(['--execute-approved'])
        api.assert_not_called()
        save.assert_not_called()

if __name__ == '__main__':
    unittest.main()
