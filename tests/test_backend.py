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
        for engine, section in ((blocker, 'anti_bot'), (radar, 'radar')):
            self.cfg[section]['enabled'] = False
            with patch.object(engine, 'load_config', return_value=self.cfg), patch.object(engine, 'github_request') as request:
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

if __name__ == '__main__':
    unittest.main()
