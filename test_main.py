import json
import os
import tempfile
import unittest

# main.py charge la config à l'import : on pointe vers l'exemple fourni.
os.environ.setdefault('NERDMC_CONFIG', 'config.json.example')

import main  # noqa: E402


class LoadConfigTest(unittest.TestCase):
    def _write(self, payload):
        f = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8')
        f.write(payload)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_example_config_is_valid(self):
        data = main.load_config('config.json.example')
        self.assertIn('token', data)
        self.assertIn('command_prefix', data)

    def test_missing_file_exits(self):
        with self.assertRaises(SystemExit):
            main.load_config('/nonexistent/config.json')

    def test_missing_token_exits(self):
        path = self._write(json.dumps({'command_prefix': '!'}))
        with self.assertRaises(SystemExit):
            main.load_config(path)

    def test_invalid_json_exits(self):
        path = self._write('{not json')
        with self.assertRaises(SystemExit):
            main.load_config(path)


class ChatRegexTest(unittest.TestCase):
    def test_matches_chat_line(self):
        match = main.CHAT_RE.search('[12:00:00] [Server thread/INFO]: <Steve> hello')
        self.assertEqual(match.groups(), ('Steve', 'hello'))

    def test_ignores_system_line(self):
        self.assertIsNone(main.CHAT_RE.search('[12:00:00] [Server thread/INFO]: Steve joined the game'))


if __name__ == '__main__':
    unittest.main()
