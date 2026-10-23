from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import Workbook
from wordlearn.api import app


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def upload(self, name, data):
        return self.client.post('/words/upload', params={'filename': name}, content=data)

    def test_csv_headers_blanks_duplicates_and_first_word(self):
        for content in [b'word,meaning\napple,fruit\n\nApple,duplicate\nbanana,fruit', b'apple\nbanana']:
            result = self.upload('words.csv', content)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()['words'], ['apple', 'banana'])

    def test_xlsx_first_column(self):
        book = Workbook()
        book.active.append(['单词', '释义'])
        book.active.append(['nature', '自然'])
        book.active.append(['adapt', '适应'])
        buffer = BytesIO()
        book.save(buffer)
        response = self.upload('words.xlsx', buffer.getvalue())
        self.assertEqual(response.json()['words'], ['nature', 'adapt'])

    def test_invalid_files(self):
        for name, data in [('words.xlsx', b'broken'), ('words.csv', b'word\n\n'), ('words.txt', b'apple'), ('words.csv', '\n'.join(f'w{i}' for i in range(101)).encode())]:
            self.assertEqual(self.upload(name, data).status_code, 400)
        self.assertEqual(self.upload('words.csv', b'x' * (5 * 1024 * 1024 + 1)).status_code, 413)

    def test_uploaded_words_reach_generator_without_default_file(self):
        words = self.upload('words.csv', b'apple\nbanana').json()['words']
        with patch('wordlearn.api.load_words') as default, patch('wordlearn.api.generate_passage', return_value={'title': 't', 'paragraphs': ['p']}) as passage, patch('wordlearn.api.generate_questions', return_value={}):
            response = self.client.post('/generate', json={'provider': 'ollama', 'words': words})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(passage.call_args.args[0], words)
            default.assert_not_called()

    def test_empty_custom_words_are_not_silently_replaced(self):
        response = self.client.post('/generate', json={'provider': 'ollama', 'words': []})
        self.assertEqual(response.status_code, 400)
