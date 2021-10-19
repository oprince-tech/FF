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
from FF.main import Player
from FF.main import print_cookies
from FF.main import print_matchup
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

    def mock_player_args():
        return(
            'John Reallylonglastname',
            'QB',
            0,
            'QB',
            True,
            100.0,
            0,
            50.0,
            'ACTIVE',
            False,
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

    def mock_args_one_player():
        return argparse.Namespace(
            league_id=0,
            season=0,
            week=0,
        )

    def mock_args_missing_injuryStatus():
        return argparse.Namespace(
            league_id=1,
            season=0,
            week=0,
        )

    def mock_args_three_players():
        return argparse.Namespace(
            league_id=2,
            season=0,
            week=0,
        )

    def mock_args_decide_flex():
        return argparse.Namespace(
            league_id=3,
            season=0,
            week=0,
        )

    def mock_args_full_team():
        return argparse.Namespace(
            league_id=4,
            season=0,
            week=0,
        )

    def mock_args_full_team_YTP():
        return argparse.Namespace(
            league_id=5,
            season=0,
            week=0,
        )

    def mock_args_matchup():
        return argparse.Namespace(
            league_id=7,
            season=0,
            week=0,
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
def mock_generate_roster(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_one_player())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_missing_status(mock_roster):
    d = load_data(
        './tests/data',
        MyMock.mock_args_missing_injuryStatus(),
    )
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_three_players(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_three_players())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_decide_flex_tiebreak(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_decide_flex())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_full_team(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_full_team())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_full_team_YTP(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_full_team_YTP())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_roster_one_player(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_one_player())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


@pytest.fixture
def mock_matchup(mock_roster):
    d = load_data('./tests/data', MyMock.mock_args_matchup())
    mock_roster.generate_roster(d, 2021, 1)
    return mock_roster


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
        load_data('path/should/not/exist', MyMock.mock_args_cookies())


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
    with pytest.raises(KeyError):
        mock_roster.generate_roster({}, 0, 0)


def test_Roster_no_teams(mock_roster):
    with pytest.raises(SystemExit):
        mock_roster.generate_roster({'teams': {}}, 0, 0)


def test_Roster_no_players(mock_roster):
    with pytest.raises(KeyError):
        mock_roster.generate_roster({'teams': [{'id': 9}]}, 0, 0)


def test_Roster_no_injuryStatus(mock_roster_missing_status):
    p = mock_roster_missing_status.roster[0]
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


def test_sort_by_pos(mock_roster_three_players):
    mock_roster_three_players.sort_roster_by_pos()
    assert mock_roster_three_players.roster[0].slot_id == 0
    assert mock_roster_three_players.roster[1].slot_id == 2
    assert mock_roster_three_players.roster[2].slot_id == 4


def test_decide_flex_tiebreak(mock_roster_decide_flex_tiebreak):
    mock_roster_decide_flex_tiebreak.decide_flex()
    assert mock_roster_decide_flex_tiebreak.roster[0].shouldStart is True


def test_decide_flex_three_players(mock_roster_three_players):
    mock_roster_three_players.decide_flex()
    assert mock_roster_three_players.roster[0].shouldStart is True
    assert mock_roster_three_players.roster[0].proj > \
        mock_roster_three_players.roster[1].proj


@pytest.mark.parametrize(
    ('index', 'last'),
    (
        (0, 'Allen'),
        (1, 'Chubb'),
        (2, 'Ekeler'),
        (3, 'Evans'),
        (4, 'Jones'),
        (5, 'Smith'),
        (6, 'Cooks'),
        (7, 'D/ST'),
        (8, 'Tucker'),
    ),
)
def test_decide_lineup(index, last, mock_roster_full_team):
    mock_roster_full_team.sort_roster_by_pos()
    mock_roster_full_team.decide_lineup()
    shouldStart = [p for p in mock_roster_full_team.roster if p.shouldStart]
    assert len(shouldStart) == 9
    assert mock_roster_full_team.roster[index].last == last


def test_get_total_projected(mock_roster_full_team):
    mock_roster_full_team.get_total_projected()
    assert mock_roster_full_team.total_projected == 91.8


def test_get_yet_to_play(mock_roster_full_team_YTP):
    mock_roster_full_team_YTP.get_yet_to_play()
    assert mock_roster_full_team_YTP.yet_to_play == 9


def test_get_yet_to_play_three_starting(mock_roster_three_players):
    mock_roster_three_players.get_yet_to_play()
    assert mock_roster_three_players.yet_to_play == 3


def test_print_roster(mock_roster_one_player, capsys):
    mock_roster_one_player.print_roster()
    out, err = capsys.readouterr()
    assert out == 'Slot  Pos Player         Proj  Score\n' \
                  '------------------------------------\n' \
                  '\x1b[94mFLX:\x1b[0m  RB  \x1b[32mN. ' \
                  'Chubb   \x1b[0m   \x1b[90m 13.0\x1b[0m ' \
                  '\x1b[32m  20.1\x1b[0m\n'


def test_truncate():
    name, slot, slot_id, pos, starting, \
        proj, score, avg, status, rosterLocked = MyMock.mock_player_args()
    mock_player = Player(
        name, slot, slot_id, pos, starting,
        proj, score, avg, status, rosterLocked,
    )
    mock_player.truncate()
    assert mock_player.last == 'Reallyl...'


def test_NAN_performance():
    p = Player(
        'John Smith', 'RB', 2, 'RB', True,
        0.0, 0.0, 15.0, 'ACTIVE', False,
    )
    p.rosterLocked = True
    p.performance_check()
    assert p.performance == 'NAN'


def test_HIGH_performance():
    p = Player(
        'John Smith', 'RB', 2, 'RB', True,
        0.0, 10.0, 15.0, 'ACTIVE', False,
    )
    p.rosterLocked = True
    p.performance_check()
    assert p.performance == 'HIGH'


def test_MID_performance():
    p = Player(
        'John Smith', 'RB', 2, 'RB', True,
        9.0, 9.5, 15.0, 'ACTIVE', False,
    )
    p.rosterLocked = True
    p.performance_check()
    assert p.performance == 'MID'


def test_LOW_performance():
    p = Player(
        'John Smith', 'RB', 2, 'RB', True,
        9.0, 0.0, 15.0, 'ACTIVE', False,
    )
    p.rosterLocked = True
    p.performance_check()
    assert p.performance == 'LOW'


@pytest.fixture
def mock_teams_t1_winner():
    t1 = Roster(1)
    t1.winner = True
    t1.total_score = 100.0
    t1.total_projected = 300.0
    t1.yet_to_play = 0
    t2 = Roster(2)
    t2.winner = False
    t2.total_score = 10.0
    t2.total_projected = 200.0
    t2.yet_to_play = 0
    return [t1, t2]


@pytest.fixture
def mock_teams_t2_winner():
    t1 = Roster(1)
    t1.winner = False
    t1.total_score = 100.0
    t1.total_projected = 300.0
    t1.yet_to_play = 0
    t2 = Roster(2)
    t2.winner = True
    t2.total_score = 10.0
    t2.total_projected = 200.0
    t2.yet_to_play = 0
    return [t1, t2]


@pytest.fixture
def mock_teams_no_winner():
    t1 = Roster(1)
    t1.winner = False
    t1.total_score = 100.0
    t1.total_projected = 300.0
    t1.yet_to_play = 1
    p1 = Player(
        'John Smith', 'RB', 2, 'RB', True,
        0.0, 10.0, 15.0, 'ACTIVE', False,
    )
    t1.roster.append(p1)
    t2 = Roster(2)
    t2.winner = False
    t2.total_score = 10.0
    t2.total_projected = 200.0
    t2.yet_to_play = 1
    p2 = Player(
        'Jane Doe', 'WR', 4, 'WR', True,
        0.0, 10.0, 15.0, 'ACTIVE', False,
    )
    t2.roster.append(p2)
    return [t1, t2]


def test_print_matchup_t1_winner(mock_teams_t1_winner, capsys):
    t1 = mock_teams_t1_winner[0]
    t2 = mock_teams_t1_winner[1]
    print_matchup(t1, t2)
    out, err = capsys.readouterr()
    color_spacer = '  \033[97;42m \033[0m\033[97;41m \033[0m  '
    HEADER = '------------------------------------'
    assert out == 'Slot  Pos Player         Proj  Score' \
                  f'{color_spacer}' \
                  'Slot  Pos Player         Proj  Score\n' \
                  f'{HEADER}' \
                  f'{color_spacer}' \
                  f'{HEADER}\n' \
                  f'{HEADER}' \
                  f'{color_spacer}' \
                  f'{HEADER}\n' \
                  'Yet to Play: 0          300.0\x1b[32m  ' \
                  '100.0\x1b[0m' \
                  f'{color_spacer}' \
                  'Yet to Play: 0          200.0\x1b[91m   ' \
                  '10.0\x1b[0m\n'


def test_print_matchup_t2_winner(mock_teams_t2_winner, capsys):
    t1 = mock_teams_t2_winner[0]
    t2 = mock_teams_t2_winner[1]
    print_matchup(t1, t2)
    out, err = capsys.readouterr()
    color_spacer = '  \033[97;41m \033[0m\033[97;42m \033[0m  '
    HEADER = '------------------------------------'
    assert out == 'Slot  Pos Player         Proj  Score' \
                  f'{color_spacer}' \
                  'Slot  Pos Player         Proj  Score\n' \
                  f'{HEADER}' \
                  f'{color_spacer}' \
                  f'{HEADER}\n' \
                  f'{HEADER}' \
                  f'{color_spacer}' \
                  f'{HEADER}\n' \
                  'Yet to Play: 0          300.0\x1b[91m  ' \
                  '100.0\x1b[0m' \
                  f'{color_spacer}' \
                  'Yet to Play: 0          200.0\x1b[32m   ' \
                  '10.0\x1b[0m\n'


def test_print_matchup_no_winner(mock_teams_no_winner, capsys):
    t1 = mock_teams_no_winner[0]
    t2 = mock_teams_no_winner[1]
    print_matchup(t1, t2)
    out, err = capsys.readouterr()
    HEADER = '------------------------------------'
    assert out == 'Slot  Pos Player         Proj  Score' \
                  '      ' \
                  'Slot  Pos Player         Proj  Score\n' \
                  f'{HEADER}' \
                  '      ' \
                  f'{HEADER}\n' \
                  '\x1b[94mRB:\x1b[0m   RB  \x1b[32mJ. Smith   ' \
                  '\x1b[0m   \x1b[90m  0.0\x1b[0m \x1b[97m  10.0\x1b[0m' \
                  '      \x1b[94mWR:\x1b[0m   WR  \x1b[32mJ. Doe     ' \
                  '\x1b[0m   \x1b[90m  0.0\x1b[0m \x1b[97m  10.0\x1b[0m\n' \
                  f'{HEADER}' \
                  '      ' \
                  f'{HEADER}\n' \
                  'Yet to Play: 1          300.0  ' \
                  '100.0' \
                  '      ' \
                  'Yet to Play: 1          200.0   ' \
                  '10.0\n'


def test_matchup_op_home_winner(mock_roster):
    args = argparse.Namespace(league_id=6, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.winner is False


def test_matchup_mt_away_winner(mock_roster):
    args = argparse.Namespace(league_id=7, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.winner is True


def test_matchup_mt_home_winner(mock_roster):
    args = argparse.Namespace(league_id=8, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.winner is True


def test_matchup_op_away_winner(mock_roster):
    args = argparse.Namespace(league_id=9, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.winner is False


def test_matchup_mt_home_live(mock_roster):
    args = argparse.Namespace(league_id=10, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.total_score == 10.0


def test_matchup_mt_away_live(mock_roster):
    args = argparse.Namespace(league_id=11, season=0, week=0)
    d = load_data('./tests/data', args)
    mock_roster.get_matchup_score(d, 1)
    assert mock_roster.total_score == 100.0
