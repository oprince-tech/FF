import argparse
import builtins
import json
import sys
from unittest import mock

import pytest

from FF.main import check_cookies_exists
from FF.main import load_cookies
from FF.main import load_data
from FF.main import main
from FF.main import parse_args
from FF.main import print_cookies
from FF.main import Roster
from FF.main import save_data
from FF.main import update_cookies


class MyMock:
    def mock_json(*args):
        return {'test': 'test1'}

    def mock_cookies(*args):
        cookies = {
            'league_id': 0,
            'team_id': 0,
            'season': 0,
            'week': 0,
            'SWID': '',
                    'espn_s2': '',
        }
        return cookies

    def mock_args_cookies():
        return argparse.Namespace(
            league_id=131034,
            team_id=1,
            season=2021,
            week=1,
            SWID='{SWID}',
            espn_s2='ABCDE12345',
        )
    def mock_test_data_args():
        return argparse.Namespace(
            league_id=0,
            season=0,
            week=0,
        )
    def mock_test_data_args_missing_injuryStatus():
        return argparse.Namespace(
            league_id=1,
            season=0,
            week=0,
        )

    def mock_args_full():
        return argparse.Namespace(
            pull=True,
            week=1,
            league_id=123456,
            team_id=2,
            season=3333,
            cookies=True,
            SWID='{12345}',
            espn_s2='ABCDE12345',
            matchup=True,
            dev=False,
        )

    def mock_args_default():
        return argparse.Namespace(
            pull=False,
            week=None,
            league_id=None,
            team_id=None,
            season=None,
            cookies=False,
            SWID=None,
            espn_s2=None,
            matchup=False,
            dev=False,
        )



@pytest.fixture
def mock_cookies(monkeypatch):
    monkeypatch.setattr(json, 'load', MyMock.mock_cookies)


@pytest.fixture
def mock_json_data(monkeypatch):
    monkeypatch.setattr(json, 'load', MyMock.mock_json)


@pytest.fixture
def mock_roster():
    return Roster(9)

@pytest.fixture
def mock_generate_roster():
    r = Roster(9)
    d = load_data('./tests/data', MyMock.mock_test_data_args())
    r.generate_roster(d, 2021, 1)
    return r

@pytest.fixture
def mock_data_missing_status():
    d = load_data('./tests/data', MyMock.mock_test_data_args_missing_injuryStatus())
    return d


@pytest.fixture
def mock_template(monkeypatch):
    monkeypatch.setattr(json, 'dump', None)


@pytest.fixture
def mock_failed_open(monkeypatch):
    monkeypatch.setattr(builtins, 'open', None)


def test_parse_args_namespace():
    sys.argv = ['ff']
    args = parse_args()
    assert args == MyMock.mock_args_default()


@pytest.mark.parametrize(
    'input',
    (
        pytest.param(
            [
                'ff', '-p', '-w', '1', '-l', '123456', '-t', '2', '-s', '3333',
                '--SWID', '{12345}', '--espn-s2', 'ABCDE12345', '-m', '-c',
            ], id='Full args',
        ),
    ),
)
def test_parse_args_full(input):
    sys.argv = input
    args = parse_args()
    assert args == MyMock.mock_args_full()


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


def test_update_cookies_fail(tmpdir):
    with pytest.raises(SystemExit):
        file = tmpdir.join('cookies.json')
        args = argparse.Namespace()
        update_cookies(file, args)


@pytest.mark.parametrize(
    ('dev', 'key', 'expected'),
    [
        (
            True,
            None,
            {
                'league_id': 0,
                'team_id': 0,
                'season': 0,
                'week': 0,
                'SWID': '',
                'espn_s2': '',
            },
        ),
        (
            False,
            None,
            {
                'league_id': 0,
                'team_id': 0,
                'season': 0,
                'week': 0,
                'SWID': '',
                'espn_s2': '',
            },
        ),
        (
            True,
            'season',
            0,
        ),
        (
            True,
            'week',
            0,
        ),
    ],
)
def test_load_cookies(dev, key, expected, mock_cookies):
    assert load_cookies(dev, key=key) == expected


@pytest.mark.parametrize(
    ('input', 'error_type'),
    (
        ('fail', KeyError),
        ('SWID', ValueError),
        ('espn_s2', ValueError),
    ),
)
def test_load_cookies_fail(input, error_type):
    with pytest.raises(error_type):
        load_cookies(True, input)


@mock.patch('builtins.open', side_effect=FileNotFoundError)
def test_load_cookies_FileNotFoundError(mock_FileNotFoundError):
    with pytest.raises(FileNotFoundError):
        load_cookies(True, None)


def test_load_data(tmpdir, mock_json_data):
    file = tmpdir.join('data.json')
    with mock.patch('builtins.open', mock.mock_open(read_data='{}')):
        d = load_data(file, MyMock.mock_args_cookies())
        assert isinstance(d, dict)


def test_load_data_FileNotFoundError():
    with pytest.raises(FileNotFoundError):
        d = load_data('path/should/not/exist', MyMock.mock_args_cookies())


def test_save_data(tmpdir):
    file = tmpdir.join('FF_1_wk2_3.json')
    d = {'test': 'test'}
    save_data(tmpdir, d, 1, 2, 3)
    assert file.read() == '{"test": "test"}'


@mock.patch('builtins.open', side_effect=OSError)
def test_save_data_failed(mock_OSError, tmpdir):
    with pytest.raises(OSError):
        save_data(tmpdir, {}, 1, 2, 3)

def test_roster_init(mock_roster):
    assert isinstance(mock_roster.roster, list)
    assert isinstance(mock_roster.TID, int)


def test_Roster_roster(mock_generate_roster):
    assert len(mock_generate_roster.roster) == 1

def test_Roster_no_data(mock_roster):
    with pytest.raises(SystemExit):
        mock_roster.generate_roster({}, 0, 0)

def test_Roster_no_teams(mock_roster):
    with pytest.raises(SystemExit):
        mock_roster.generate_roster({'teams': {}}, 0, 0)

def test_Roster_no_players(mock_roster):
    with pytest.raises(SystemExit):
        mock_roster.generate_roster({'teams': [{'id': 9}]}, 0, 0)

def test_Roster_no_injuryStatus(mock_roster, mock_data_missing_status):
    mock_roster.generate_roster(mock_data_missing_status, 2021, 1)
    p = mock_roster.roster[0]
    assert p.status == 'ACTIVE'


@pytest.mark.parametrize(
    ('variable', 'value'),
    (
        ('first', 'Nick'),
        ('last', 'Chubb'),
        ('slot', 'FLX'),
        ('starting', True),
        ('pos', 'RB'),
        ('proj', 13.0),
        ('score', 20.1),
        ('status', 'ACTIVE'),
        ('rosterLocked', True),
    ),
)
def test_Roster_variables(variable, value, mock_generate_roster):
    p = mock_generate_roster.roster[0]
    assert getattr(p, variable) == value
