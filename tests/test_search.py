import os
import tempfile
import pytest
from ld_audit.cli import search_directory, _search_file_with_encoding


class TestSearchFileWithEncoding:
    def test_search_file_single_flag(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write('flag_key = "test-flag-1"\n')
            f.write('if client.variation("test-flag-1", user, False):\n')
            f.flush()
            temp_path = f.name

        try:
            result = _search_file_with_encoding(temp_path, ['test-flag-1'], 'utf-8')
            assert 'test-flag-1' in result
            assert len(result['test-flag-1']) == 2
            assert result['test-flag-1'][0][1] == 1
            assert result['test-flag-1'][1][1] == 2
        finally:
            os.unlink(temp_path)

    def test_search_file_multiple_flags(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.js') as f:
            f.write('const flag1 = "feature-a";\n')
            f.write('const flag2 = "feature-b";\n')
            f.flush()
            temp_path = f.name

        try:
            result = _search_file_with_encoding(temp_path, ['feature-a', 'feature-b'], 'utf-8')
            assert 'feature-a' in result
            assert 'feature-b' in result
            assert len(result['feature-a']) == 1
            assert len(result['feature-b']) == 1
        finally:
            os.unlink(temp_path)

    def test_search_file_no_matches(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write('some code here\n')
            f.flush()
            temp_path = f.name

        try:
            result = _search_file_with_encoding(temp_path, ['nonexistent-flag'], 'utf-8')
            assert result == {}
        finally:
            os.unlink(temp_path)

    def test_search_file_single_quotes(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as f:
            f.write("flag_key = 'single-quote-flag'\n")
            f.flush()
            temp_path = f.name

        try:
            result = _search_file_with_encoding(temp_path, ['single-quote-flag'], 'utf-8')
            assert 'single-quote-flag' in result
            assert len(result['single-quote-flag']) == 1
        finally:
            os.unlink(temp_path)


class TestSearchDirectory:
    def test_search_directory_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file1_path = os.path.join(tmpdir, 'file1.py')
            file2_path = os.path.join(tmpdir, 'file2.js')

            with open(file1_path, 'w') as f:
                f.write('flag = "my-flag"\n')

            with open(file2_path, 'w') as f:
                f.write('const flag = "my-flag";\n')

            result = search_directory(tmpdir, ['my-flag'])

            assert 'my-flag' in result
            assert len(result['my-flag']) == 2

    def test_search_directory_with_extension_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = os.path.join(tmpdir, 'test.py')
            js_file = os.path.join(tmpdir, 'test.js')

            with open(py_file, 'w') as f:
                f.write('flag = "filter-flag"\n')

            with open(js_file, 'w') as f:
                f.write('const flag = "filter-flag";\n')

            result = search_directory(tmpdir, ['filter-flag'], extensions=['py'])

            assert 'filter-flag' in result
            assert len(result['filter-flag']) == 1

    def test_search_directory_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'subdir')
            os.makedirs(subdir)

            file1 = os.path.join(tmpdir, 'file1.py')
            file2 = os.path.join(subdir, 'file2.py')

            with open(file1, 'w') as f:
                f.write('flag = "recursive-flag"\n')

            with open(file2, 'w') as f:
                f.write('flag = "recursive-flag"\n')

            result = search_directory(tmpdir, ['recursive-flag'])

            assert 'recursive-flag' in result
            assert len(result['recursive-flag']) == 2

    def test_search_directory_excludes_common_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            node_modules = os.path.join(tmpdir, 'node_modules')
            os.makedirs(node_modules)

            excluded_file = os.path.join(node_modules, 'package.js')
            with open(excluded_file, 'w') as f:
                f.write('const flag = "excluded-flag";\n')

            result = search_directory(tmpdir, ['excluded-flag'])

            assert result == {}

    def test_search_directory_multiple_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'multi.py')

            with open(file_path, 'w') as f:
                f.write('flag1 = "flag-one"\n')
                f.write('flag2 = "flag-two"\n')
                f.write('flag3 = "flag-three"\n')

            result = search_directory(tmpdir, ['flag-one', 'flag-two', 'flag-three'])

            assert len(result) == 3
            assert 'flag-one' in result
            assert 'flag-two' in result
            assert 'flag-three' in result

    def test_search_directory_no_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, 'empty.py')

            with open(file_path, 'w') as f:
                f.write('no flags here\n')

            result = search_directory(tmpdir, ['nonexistent-flag'])

            assert result == {}

    def test_search_directory_skips_large_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from ld_audit.cli import MAX_FILE_SIZE_MB

            large_file = os.path.join(tmpdir, 'large.txt')

            with open(large_file, 'w') as f:
                f.write('x' * (MAX_FILE_SIZE_MB * 1024 * 1024 + 1000))

            result = search_directory(tmpdir, ['any-flag'])

            assert result == {}
