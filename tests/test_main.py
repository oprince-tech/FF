from pathlib import Path
import sys
import builtins
import argparse
import pytest
import json
from unittest import mock
from FF.main import parse_args
from FF.main import main
from FF.main import print_cookies
from FF.main import check_cookies_exists
from FF.main import update_cookies
from FF.main import load_cookies
from FF.main import Roster
from FF.main import load_data

class MyMock:
    def mock_json(*args):
        return {"test": "test1"}
    def mock_cookies(*args):
        cookies = {
                    "league_id": 0,
                    "team_id": 0,
                    "season": 0,
                    "week": 0,
                    "SWID": "",
                    "espn_s2": ""
                  }
        return cookies
    def mock_args():
        args = argparse.Namespace(
            league_id=131034,
            team_id=1,
            season=2021,
            week=1,
            SWID='{SWID}',
            espn_s2='ABCDE12345',
        )
        return args

@pytest.fixture
def mock_cookies(monkeypatch):
    monkeypatch.setattr(json, 'load', MyMock.mock_cookies)

@pytest.fixture
def mock_json_data(monkeypatch):
    monkeypatch.setattr(json, 'load', MyMock.mock_json)

@pytest.fixture
def mock_roster():
    return Roster(1)

@pytest.fixture
def mock_template(monkeypatch):
    monkeypatch.setattr(json, 'dump', None)

@pytest.fixture
def mock_failed_open(monkeypatch):
    monkeypatch.setattr(builtins, 'open', None)

def test_parse_args_namespace():
    sys.argv = ['ff']
    args = parse_args()
    expected = argparse.Namespace(
        pull=False,
        week=None,
        league_id=None,
        team_id=None,
        season=None,
        cookies=False,
        SWID=None,
        espn_s2=None,
        matchup=False,
        dev=False
    )
    assert args == expected


@pytest.mark.parametrize(
    'input',
    (
        pytest.param(
        [
            'ff', '-p', '-w', '1', '-l', '123456', '-t', '2', '-s', '3333',
            '--SWID', '{12345}', '--espn-s2', 'ABCDE12345', '-m', '-c'
        ], id='Full args'),
    ),
)
def test_parse_args_full(input):
    sys.argv = input
    args = parse_args()
    expected = argparse.Namespace(
        pull=True,
        week=1,
        league_id=123456,
        team_id=2,
        season=3333,
        cookies=True,
        SWID="{12345}",
        espn_s2="ABCDE12345",
        matchup=True,
        dev=False
    )
    assert args == expected

def test_print_cookies_succeed_exit():
    sys.argv = ['ff', '-c']
    with pytest.raises(SystemExit):
        main()



def test_print_cookies_fail(mock_failed_open):
    with pytest.raises(SystemExit):
        print_cookies()

def test_cookies_template(tmpdir):
    file = tmpdir.join('cookies.json')
    check_cookies_exists(file)
    assert file.read() == '{"league_id": 0, "team_id": 0, "season": 0, ' \
                          '"week": 0, "SWID": "", "espn_s2": ""}'



def test_check_cookies_exists_no_path_fail(tmpdir, mock_template):
    file = tmpdir.join('cookies.json')
    with pytest.raises(SystemExit):
        check_cookies_exists(file)

# @mock.patch('builtins.open', mock.mock_open(read_data='{"league_id": 0, ' \
#                                                       '"team_id": 0, ' \
#                                                       '"season": 0, ' \
#                                                       '"week": 0, ' \
#                                                       '"SWID": "", ' \
#                                                       '"espn_s2": ""}'))
# @pytest.mark.parametrize(
#     ('data', 'expected'),
#     (
#         (
#             '{"league_id": 0, ' +
#             '"team_id": 0, ' +
#             '"season": 0, ' +
#             '"week": 0, ' +
#             '"SWID": "", ' +
#             '"espn_s2": ""}',
#             '{"league_id": 131035, ' +
#             '"team_id": 1, ' +
#             '"season": 2021, ' +
#             '"week": 1, ' +
#             '"SWID": "{SWID}", ' +
#             '"espn_s2": "ABCDE12345"}',
#         ),
#     ),
# )
# def test_update_cookies(tmpdir, data, expected):
    # file = tmpdir.join('cookies.json')
#     args = argparse.Namespace(
#         league_id=131035,
#         team_id=1,
#         season=2021,
#         week=1,
#         SWID='{SWID}',
#         espn_s2='ABCDE12345',
#     )
#     json_data = json.dumps({
#                                 "league_id": 1,
#                                 "team_id": 1,
#                                 "season": 1,
#                                 "week": 1,
#                                 "SWID": "",
#                                 "espn_s2": ""
#     })
#     mock_open = mock.mock_open(read_data=json_data)
#     with mock.patch('builtins.open', mock_open):
#         update_cookies(args, file)
#         assert file.read() == 'test'

def test_update_cookies(tmpdir, mock_cookies):
    file = tmpdir.join('cookies.json')
    with mock.patch('builtins.open', mock.mock_open()):
        update_cookies(file, MyMock.mock_args())
        assert json.load(file) == '{}'

def test_update_cookies_fail(tmpdir):
    with pytest.raises(SystemExit):
        file = tmpdir.join('cookies.json')
        args = argparse.Namespace()
        update_cookies(args, file)

@mock.patch('builtins.open', mock.mock_open(read_data='{"league_id": 0, ' \
                                                      '"team_id": 0, ' \
                                                      '"season": 0, ' \
                                                      '"week": 0, ' \
                                                      '"SWID": "", ' \
                                                      '"espn_s2": ""}'))
@pytest.mark.parametrize(
    ('dev', 'key', 'expected'),
    [
        (
            True,
            None,
            {
                "league_id": 0,
                "team_id": 0,
                "season": 0,
                "week": 0,
                "SWID": "",
                "espn_s2": ""
            }
        ),
        (
            False,
            None,
            {
                "league_id": 0,
                "team_id": 0,
                "season": 0,
                "week": 0,
                "SWID": "",
                "espn_s2": ""
            }
        ),
        (
            True,
            'season',
            0
        ),
        (
            True,
            'week',
            0
        ),
    ],
)
def test_load_cookies(dev, key, expected, tmpdir):
    file = tmpdir.join('cookies.json')
    assert load_cookies(dev, key=key) == expected

@pytest.mark.parametrize(
    ('input', 'error_type'),
    (
        ('fail', KeyError),
        ('SWID', ValueError),
    ),
)
def test_load_cookies_fail(input, error_type, tmpdir):
    file = tmpdir.join('cookies.json')
    with pytest.raises(error_type):
        load_cookies(True, input)

@mock.patch('builtins.open', side_effect=FileNotFoundError)
def test_load_cookies_FileNotFoundError(mock_failed_open):
    with pytest.raises(FileNotFoundError):
        load_cookies(True, None)

# def test_load_cookies_file_fail(mock_failed_open):
#     with pytest.raises(FileNotFoundError):
#         load_cookies(True)



def test_roster_init(mock_roster):
    assert isinstance(mock_roster.roster, list)
    assert isinstance(mock_roster.TID, int)



def test_load_data(tmpdir, mock_json_data):
    file = tmpdir.join('data.json')
    with mock.patch('builtins.open', mock.mock_open()):
        d = load_data(file, MyMock.mock_args())
        assert isinstance(d, dict)

def test_load_data_FileNotFoundError():
    with pytest.raises(SystemExit):
        d = load_data('path/should/not/exist', MyMock.mock_args())
