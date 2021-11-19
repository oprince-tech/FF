from __future__ import annotations  # python3.7+

import argparse
import json
import operator
import os
from itertools import zip_longest

import pkg_resources  # type: ignore
import requests  # type: ignore

COOKIES_PATH = pkg_resources.resource_filename(
    __name__,
    'data/cookies.json',
)

COOKIES_DEV_PATH = pkg_resources.resource_filename(
    __name__,
    'data/cookies-dev.json',
)

DATA_PATH = pkg_resources.resource_filename(
    __name__,
    'data',
)

slotID = {
    0: 'QB', 2: 'RB', 4: 'WR',
    6: 'TE', 16: 'DST', 17: 'K',
    20: 'B', 21: 'IR', 23: 'FLX',
}

positionID = {
    1: 'QB', 2: 'RB', 3: 'WR',
    4: 'TE', 5: 'K', 16: 'DST',
}

TEAM_HEADER = ('\u2502{:<7}{:<9}{:<12}{:<6}\u2502').format(
    'Team', 'Record', 'Rank', 'PO%',
)


HEADER = ('{:<6}{:<4}{:<15}{:<6}{:<5}').format(
    'Slot', 'Pos', 'Player', 'Proj', 'Score',
)

HEADER_EXT = (
    '{:<6}{:<4}{:<15}{:<6}{:<7}{:<5}{:>7}{:>7}{:>5}{:>9}{:>8}'
).format(
    'Slot', 'Pos', 'Player', 'Proj', 'Score',
    'TAR/gm', 'Yds', 'Cmp%', 'TD', 'AVG', 'TOT',
)


class Box:
    TOP_BOX = ('{}{}{}').format('\u250C', '\u2500'*34, '\u2510')
    MID_BOX = ('{}{}{}').format('\u251C', '\u254C'*34, '\u2524')
    BTM_BOX = ('{}{}{}').format('\u2514', '\u2500'*34, '\u2518')
    DOUBLE_LINE = '\u2550'


class Colors:
    BLACK = '\033[90m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[32m'
    LGREEN = '\033[92m'
    BRED = '\033[97;41m'
    BYELLOW = '\033[97;93m'
    BGREEN = '\033[97;42m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    LWHITE = '\033[97m'
    ENDC = '\033[0m'


class Roster:
    def __init__(self, TID: int) -> None:
        self.roster: list[Player] = []
        self.TID = TID
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.rank = 0
        self.playoffPct = 0
        self.abbrev = ''
        self.yet_to_play = 0

    def generate_roster(self, d: dict, year: int, week: int) -> None:
        print('\nAdding players to roster...')
        try:
            for team in d['teams']:
                if team['id'] == self.TID:
                    result = team['currentSimulationResults']
                    self.rank = result['rank']
                    self.playoffPct = round(result['playoffPct'] * 100, 2)
                    self.abbrev = team['abbrev']
                    for p in team['roster']['entries']:
                        player = Player(p, year, week)
                        self.roster.append(player)
            if len(self.roster) == 0:
                raise SystemExit(
                    f'{Colors.RED}Team id: {self.TID} does not exist'
                    f'{Colors.ENDC}',
                )
        except KeyError as e:
            raise SystemExit(
                f'{Colors.RED}{type(e).__name__}: Error parsing data. '
                f'Please try pulling (-p) again.{Colors.ENDC}',
            )

    def generate_record(self, d: dict) -> None:
        for matchup in d['schedule']:
            if matchup['winner'] != 'UNDECIDED':
                if (
                    (
                        matchup['away']['teamId'] == self.TID and
                        matchup['winner'] == 'AWAY'
                    ) or
                    (
                        matchup['home']['teamId'] == self.TID and
                        matchup['winner'] == 'HOME'
                    )
                ):
                    self.wins += 1
                elif (
                    (
                        matchup['away']['teamId'] == self.TID and
                        matchup['winner'] == 'HOME'
                    ) or
                    (
                        matchup['home']['teamId'] == self.TID and
                        matchup['winner'] == 'AWAY'
                    )
                ):
                    self.losses += 1

    def sort_roster_by_pos(self) -> None:
        self.roster.sort(key=operator.attrgetter('slot_id'))

    def decide_flex(self) -> None:
        print('Deciding flex position...')
        flex_ok = ['RB', 'WR', 'TE']
        flex_spot: list = list(
            filter(
                lambda x: x.pos in flex_ok and not x.shouldStart,
                self.roster,
            ),
        )
        flex_spot.sort(key=operator.attrgetter('proj'), reverse=True)
        max_proj = flex_spot[0].proj
        tiebreak1 = [p for p in flex_spot if p.proj == max_proj]

        if len(tiebreak1) >= 2:
            tiebreak1.sort(key=operator.attrgetter('fpts_avg'), reverse=True)
            max_fpts_avg = tiebreak1[0].fpts_avg
            tiebreak2 = [p for p in tiebreak1 if p.fpts_avg == max_fpts_avg]
            if len(tiebreak2) >= 2:
                tiebreak2.sort(
                    key=operator.attrgetter(
                        'fpts_total',
                    ), reverse=True,
                )
                flex = tiebreak2[0]
            else:
                flex = tiebreak1[0]
        else:
            flex = flex_spot[0]
        flex.shouldStart = True

    def decide_lineup(self) -> None:
        print('Deciding best lineup...')
        position_spots = {
            'QB': 1, 'RB': 2, 'WR': 2,
            'TE': 1, 'DST': 1, 'K': 1,
            'FLEX': 1,
        }

        for pos, num in position_spots.items():
            position_players: list = list(
                filter(
                    lambda x: x.pos == pos,
                    self.roster,
                ),
            )
            position_players.sort(
                key=operator.attrgetter('proj'), reverse=True,
            )

            for i in range(num):
                try:
                    p = position_players[i]
                    p.shouldStart = True
                except IndexError:
                    print(f'Skipping {pos}')
            if pos == 'FLEX':
                self.decide_flex()

    def get_matchup_score(self, d: dict, wk: int) -> None:
        for matchup in d['schedule']:
            if matchup['matchupPeriodId'] == wk:
                if matchup['away']['teamId'] == self.TID:
                    self.op_TID = matchup['home']['teamId']
                    self.winner = None
                    if matchup['winner'] == 'AWAY':
                        self.winner = True
                    elif matchup['winner'] == 'HOME':
                        self.winner = False

                    if 'totalPointsLive' in matchup['away']:
                        self.total_score = matchup['away']['totalPointsLive']
                    else:
                        self.total_score = matchup['away']['totalPoints']

                elif matchup['home']['teamId'] == self.TID:
                    self.op_TID = matchup['away']['teamId']
                    self.winner = None
                    if matchup['winner'] == 'HOME':
                        self.winner = True
                    elif matchup['winner'] == 'AWAY':
                        self.winner = False

                    if 'totalPointsLive' in matchup['away']:
                        self.total_score = matchup['home']['totalPointsLive']
                    else:
                        self.total_score = matchup['home']['totalPoints']

    def ytp_projected(self) -> None:
        self.total_projected = 0.0
        self.yet_to_play = 0
        for p in self.roster:
            if p.starting:
                self.total_projected += p.proj
            if p.starting and not p.rosterLocked:
                self.yet_to_play += 1

    def print_roster(self) -> None:
        print(Box.TOP_BOX)
        print(f'{TEAM_HEADER:<34}')
        print(Box.MID_BOX)
        team_details = ('\u2502{:<7}{}-{}-{}    {:<12}{:<6}\u2502').format(
            self.abbrev,
            self.wins,
            self.losses,
            self.ties,
            self.rank,
            self.playoffPct,
        )
        print(team_details)
        print(Box.BTM_BOX)
        print(HEADER_EXT)
        print(Box.DOUBLE_LINE*80)
        for p in self.roster:
            print(p.print_player(ext=True))
        yet_to_play = f'Yet to Play: {self.yet_to_play}'
        projected1 = f'{round(self.total_projected, 1):>15}'
        total = f'{round(self.total_score, 1):>7}'
        print(Box.DOUBLE_LINE*80)
        print(f'{yet_to_play}{projected1}{total}')


class Player(Roster):
    def __init__(self, p: dict, year: int, week: int) -> None:
        self.year = year
        self.week = week
        self.proj = 0
        self.score = 0
        self.shouldStart = False
        self.rosterLocked = False
        self.performance = 'NAN'
        self.generate_player_info(p)
        self.generate_player_stats(p)
        self.performance_check()

    def generate_player_info(self, p: dict) -> None:
        self.rosterLocked = p['playerPoolEntry']['rosterLocked']
        self.first = p['playerPoolEntry']['player']['firstName']
        self.last = p['playerPoolEntry']['player']['lastName']
        self.slot_id = p['lineupSlotId']
        self.slot = slotID[self.slot_id]
        if self.slot_id == 23:
            self.slot_id = 7
        self.starting = False if self.slot == 'B' else True
        self.pos = positionID[
            p['playerPoolEntry']
            ['player']['defaultPositionId']
        ]
        try:
            self.injured = (
                p['playerPoolEntry']['player']['injured']
            )
            self.status = (
                p['playerPoolEntry']['player']['injuryStatus']
            )
        except KeyError:
            self.status = 'ACTIVE'
            pass

    def generate_player_stats(self, p: dict) -> None:
        stats = p['playerPoolEntry']['player']['stats']
        for stat in stats:
            if stat['id'] == '00' + str(self.year):
                # Current Year Stats
                self.games_played = int(stat['stats']['210'])
                self.fpts_avg = round(stat['appliedAverage'], 1)
                self.fpts_total = round(stat['appliedTotal'], 1)
                self.total_yards = 0
                self.completion_percentage = 0
                self.tar_per_game = 0
                self.tds = 0
                touches = 0
                if self.pos == 'QB':
                    self.tar_per_game = '-'  # type: ignore
                    self.total_yards += int(stat['stats']['3'])
                    self.total_yards += int(stat['stats']['24'])
                    att = stat['stats']['0']
                    cmp = stat['stats']['1']
                    self.completion_percentage = round((cmp / att) * 100, 1)
                    self.tds += int(stat['stats']['4'])
                elif self.pos in ['RB', 'WR', 'TE']:
                    self.completion_percentage = '-'  # type: ignore
                    try:
                        # Rushes
                        touches += int(stat['stats']['23'])
                        rush_yards = int(stat['stats']['24'])
                    except KeyError:
                        pass
                    else:
                        self.total_yards += rush_yards

                    try:
                        # Receptions
                        touches += int(stat['stats']['58'])
                        rec_yards = int(stat['stats']['42'])
                    except KeyError:
                        pass
                    else:
                        self.total_yards += rec_yards

                    self.tar_per_game = int(touches / self.games_played)

                elif self.pos == 'DST':
                    self.tar_per_game = '-'  # type: ignore
                    self.total_yards = '-'  # type: ignore
                    self.completion_percentage = '-'  # type: ignore
                elif self.pos == 'K':
                    self.tar_per_game = '-'  # type: ignore
                    self.total_yards = '-'  # type: ignore
                    fg_att = stat['stats']['84']
                    fg_cmp = stat['stats']['83']
                    xp_att = stat['stats']['87']
                    xp_cmp = stat['stats']['86']
                    self.completion_percentage = round(
                        ((fg_cmp+xp_cmp) / (fg_att+xp_att)) * 100, 1,
                    )
                try:
                    # Rushing TD
                    self.tds += int(stat['stats']['25'])
                except KeyError:
                    pass
                try:
                    # Receiving TD
                    self.tds += int(stat['stats']['43'])
                except KeyError:
                    pass

            if stat['scoringPeriodId'] == self.week:
                # Current Week Proj / Score
                if stat['statSourceId'] == 0:
                    self.score = round(stat['appliedTotal'], 1)
                elif stat['statSourceId'] == 1:
                    if stat['appliedTotal']:
                        self.proj = round(stat['appliedTotal'], 1)
                    else:
                        self.proj = round(stat['appliedTotal'], 1)
                        if not self.injured:
                            self.status = 'BYE'

    def apply_color(self) -> None:
        color_starting = {True: Colors.BLUE, False: Colors.BLACK}
        color_shouldStart = {True: Colors.CYAN, False: Colors.BLACK}
        color_performance = {
            'LOW': Colors.RED,
            'MID': Colors.BLUE,
            'HIGH': Colors.GREEN,
            'NAN': Colors.LWHITE,
        }
        color_status = {
            'ACTIVE': Colors.GREEN,
            'QUESTIONABLE': Colors.YELLOW,
            'OUT': Colors.RED,
            'DOUBTFUL': Colors.RED,
            'INJURY_RESERVE': Colors.RED,
            'SUSPENSION': Colors.RED,
            'BYE': Colors.MAGENTA,
        }
        self.color_starting = color_starting[self.starting]
        self.color_status = color_status[self.status]
        self.color_shouldStart = color_shouldStart[self.shouldStart]
        self.color_performance = color_performance[self.performance]

    def truncate(self) -> None:
        if len(self.last) >= 11:
            self.last = f'{self.last[:7]}...'

    def performance_check(self) -> None:
        spread = (self.proj * .25)
        if self.rosterLocked:
            if self.score < (self.proj - spread):
                self.performance = 'LOW'
            elif self.score > (self.proj + spread):
                self.performance = 'HIGH'
            else:
                self.performance = 'MID'

    def print_player(self, ext: bool = False) -> str:
        self.apply_color()
        self.truncate()
        if ext:
            return f'{self.color_starting}' \
                   f'{self.slot}:' \
                   f'{Colors.ENDC:<5}\t' \
                   f'{self.pos:<4}' \
                   f'{self.color_status:<4}' \
                   f'{self.first[0]}. ' \
                   f'{self.last:<8}' \
                   f'{Colors.ENDC}\t' \
                   f'{self.color_shouldStart}' \
                   f'{self.proj:>5}' \
                   f'{Colors.ENDC}\t' \
                   f'{self.color_performance}' \
                   f'{self.score:>6}' \
                   f'{Colors.ENDC}' \
                   f'  {self.tar_per_game:>2}' \
                   f'{Colors.BLACK}' \
                   f'{self.games_played:>4}' \
                   f'{Colors.ENDC}' \
                   f'{self.total_yards:>7}' \
                   f'{self.completion_percentage:>7}' \
                   f'{self.tds:>5}' \
                   f'{self.fpts_avg:>9}' \
                   f'{self.fpts_total:>8}'.expandtabs(3)
        else:
            return f'{self.color_starting}' \
                   f'{self.slot}:' \
                   f'{Colors.ENDC:<5}\t' \
                   f'{self.pos:<4}' \
                   f'{self.color_status:<4}' \
                   f'{self.first[0]}. ' \
                   f'{self.last:<8}' \
                   f'{Colors.ENDC}\t' \
                   f'{self.color_shouldStart}' \
                   f'{self.proj:>5}' \
                   f'{Colors.ENDC}\t' \
                   f'{self.color_performance}' \
                   f'{self.score:>6}' \
                   f'{Colors.ENDC}'.expandtabs(3)


def check_cookies_exists(path: str) -> None:
    if not os.path.exists(path):
        template = {
            'league_id': 0,
            'team_id': 0,
            'season': 0,
            'week': 0,
            'SWID': '',
            'espn_s2': '',
        }
        try:
            with open(path, 'w') as wf:
                json.dump(template, wf)

        except Exception as e:
            raise SystemExit(e)


def update_cookies(path: str, args: argparse.Namespace) -> None:
    try:
        with open(path, 'r+') as f:
            cookies = json.load(f)
            if args.league_id:
                cookies['league_id'] = args.league_id
            if args.team_id:
                cookies['team_id'] = args.team_id
            if args.season:
                cookies['season'] = args.season
            if args.week:
                cookies['week'] = args.week
            if args.SWID:
                cookies['SWID'] = args.SWID
            if args.espn_s2:
                cookies['espn_s2'] = args.espn_s2
            f.seek(0, 0)
            json.dump(cookies, f, indent=2)
            f.truncate()
    except Exception as e:
        raise SystemExit(e)


def load_cookies(dev: bool, key: str = None) -> int | dict:
    try:
        if dev:
            with open(COOKIES_DEV_PATH) as rc:
                c = json.load(rc)
        else:
            with open(COOKIES_PATH) as rc:
                c = json.load(rc)
        return int(c[key]) if key else c
    except KeyError as e:
        print_cookies()
        raise type(e)(
            f'{Colors.RED}{type(e).__name__}: '
            'Error loading from your cookies file. '
            'Ensure all the fields are filled out.'
            f'{Colors.ENDC}',
        )
    except ValueError as e:
        print_cookies()
        raise type(e)(
            f'{Colors.RED}{type(e).__name__}: '
            'Error loading from your cookies file. '
            'Ensure all the fields are filled out.'
            f'{Colors.ENDC}',
        )
    except FileNotFoundError as e:
        raise type(e)(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def print_cookies() -> None:
    try:
        with open(COOKIES_PATH) as rf:
            for line in rf:
                print(line)
    except Exception as e:
        raise SystemExit(e)


def save_data(path: str, d: dict, year: int, week: int, LID: int) -> None:
    try:
        with open(
            f'{path}/FF_{year}_wk{week}_{LID}.json',
            'w',
        ) as wf:
            json.dump(d, wf)
        print('Saving data...')
    except OSError as e:
        raise type(e)(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def load_data(path: str, args: argparse.Namespace) -> dict:
    try:
        with open(
            f'''{path}/FF_{args.season}_wk{args.week}_'''
            f'''{args.league_id}.json''',
        ) as rf:
            d = json.load(rf)
        return d
    except FileNotFoundError as e:
        raise type(e)(
            f'{Colors.RED}{type(e).__name__}: '
            f'{e}. Data must be pulled first. [ff --pull]'
            f'{Colors.ENDC}',
        )


def print_matchup(myTeam: Roster, opTeam: Roster) -> None:
    if myTeam.winner is True:
        sp = f'  {Colors.BGREEN} {Colors.ENDC}{Colors.BRED} {Colors.ENDC}  '
        t1 = f'{Colors.GREEN}{round(myTeam.total_score, 1):>7}{Colors.ENDC}'
        t2 = f'{Colors.RED}{round(opTeam.total_score, 1):>7}{Colors.ENDC}'
    elif opTeam.winner is True:
        sp = f'  {Colors.BRED} {Colors.ENDC}{Colors.BGREEN} {Colors.ENDC}  '
        t1 = f'{Colors.RED}{round(myTeam.total_score, 1):>7}{Colors.ENDC}'
        t2 = f'{Colors.GREEN}{round(opTeam.total_score, 1):>7}{Colors.ENDC}'
    else:
        sp = '      '
        t1 = f'{round(myTeam.total_score, 1):>7}'
        t2 = f'{round(opTeam.total_score, 1):>7}'
    myTeam_details = ('\u2502{:<7}{}-{}-{}    {:<12}{:<6}\u2502').format(
        myTeam.abbrev,
        myTeam.wins,
        myTeam.losses,
        myTeam.ties,
        myTeam.rank,
        myTeam.playoffPct,
    )
    opTeam_details = ('\u2502{:<7}{}-{}-{}    {:<12}{:<6}\u2502').format(
        opTeam.abbrev,
        opTeam.wins,
        opTeam.losses,
        opTeam.ties,
        opTeam.rank,
        opTeam.playoffPct,
    )

    print((Box.TOP_BOX) + sp + (Box.TOP_BOX))
    print(f'{TEAM_HEADER:<34}' + sp + f'{TEAM_HEADER:<34}')
    print(Box.MID_BOX + sp + Box.MID_BOX)
    print(myTeam_details + sp + opTeam_details)
    print(Box.BTM_BOX + sp + Box.BTM_BOX)

    print(HEADER + sp + HEADER)
    print(('\u2550'*36) + sp + ('\u2550'*36))

    empty = f'{Colors.BLACK}B:{(" "*34)}{Colors.ENDC}'
    for i, (myPlayer, opPlayer) in enumerate(
        zip_longest(
            myTeam.roster,
            opTeam.roster,
        ),
    ):
        if not myPlayer:
            print(empty + sp + opPlayer.print_player())
        elif not opPlayer:
            print(myPlayer.print_player() + sp + empty)
        else:
            print(myPlayer.print_player() + sp + opPlayer.print_player())
    print(('\u2550'*36) + sp + ('\u2550'*36))

    yet_to_play1 = f'Yet to Play: {myTeam.yet_to_play}'
    yet_to_play2 = f'Yet to Play: {opTeam.yet_to_play}'
    projected1 = f'{round(myTeam.total_projected, 1):>15}'
    projected2 = f'{round(opTeam.total_projected, 1):>15}'
    print(
        yet_to_play1 + projected1 + t1 +
        sp +
        yet_to_play2 + projected2 + t2,
    )


def connect_FF(LID: int, wk: int, dev: bool) -> tuple[int, dict]:
    c = load_cookies(dev)
    year = c['season']  # type: ignore
    swid = c['SWID']  # type: ignore
    espn_s2 = c['espn_s2']  # type: ignore

    url = (
        f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/'
        f'segments/0/leagues/{LID}?view=mStandings&view=mMatchup'
        '&view=mMatchupScore&view=mPositionalRatings'
    )

    try:
        print('Connecting to API...')
        r = requests.get(
            url, params={'scoringPeriodId': str(wk)},
            cookies={'SWID': swid, 'espn_s2': espn_s2},
            timeout=5,
        )
        code_color = Colors.GREEN if r.status_code == 200 else Colors.RED
        print(f'STATUS: {code_color}{r.status_code}{Colors.ENDC}')
        return r.status_code, r.json()

    except requests.exceptions.RequestException as e:
        raise SystemExit(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='FF CLI')
    parser.add_argument(
        '-p', '--pull',
        help='Update data (pull from API)',
        action='store_true',
    )
    parser.add_argument(
        '-w', '--week',
        help='Specify week',
        type=int,
    )
    parser.add_argument(
        '-l', '--league-id',
        help='League ID',
        type=int,
    )
    parser.add_argument(
        '-t', '--team-id',
        help='Team ID',
        type=int,
    )
    parser.add_argument(
        '-s', '--season',
        help='Year of season',
        type=int,
    )
    parser.add_argument(
        '-c', '--cookies',
        help='Display your cookies',
        action='store_true',
    )
    parser.add_argument(
        '--SWID',
        help='SWID',
        type=str,
    )
    parser.add_argument(
        '--espn-s2',
        help='espn_s2',
        type=str,
    )
    parser.add_argument(
        '-m', '--matchup',
        help='Show your matchup',
        action='store_true',
    )
    parser.add_argument(
        '-d', '--dev',
        help='Use dev cookies',
        action='store_true',
    )
    args = parser.parse_args()
    return args


def main() -> int:
    args = parse_args()
    if args.cookies:
        print_cookies()
        raise SystemExit()
    check_cookies_exists(COOKIES_PATH)
    if args.dev:
        update_cookies(COOKIES_DEV_PATH, args)
    else:
        update_cookies(COOKIES_PATH, args)
    if not args.season:
        args.season = int(load_cookies(args.dev, key='season'))  # type: ignore
    if not args.week:
        args.week = load_cookies(args.dev, key='week')  # type: ignore
    if not args.league_id:
        args.league_id = load_cookies(
            args.dev, key='league_id',
        )  # type: ignore
    if not args.team_id:
        args.team_id = load_cookies(args.dev, key='team_id')  # type: ignore
    if not args.pull:
        d = load_data(DATA_PATH, args)
    else:
        status_code, d = connect_FF(
            args.league_id, args.week, args.dev,
        )  # pragma: no cover
        save_data(  # pragma: no cover
            DATA_PATH, d, args.season, args.week, args.league_id,
        )

    myTeam = Roster(args.team_id)
    myTeam.generate_roster(d, args.season, args.week)
    myTeam.generate_record(d)
    myTeam.get_matchup_score(d, args.week)
    myTeam.ytp_projected()
    myTeam.decide_lineup()
    myTeam.sort_roster_by_pos()
    if args.matchup:
        opTeam = Roster(myTeam.op_TID)
        opTeam.generate_roster(d, args.season, args.week)
        opTeam.generate_record(d)
        opTeam.get_matchup_score(d, args.week)
        opTeam.ytp_projected()
        opTeam.decide_lineup()
        opTeam.sort_roster_by_pos()
        print_matchup(myTeam, opTeam)
    else:
        myTeam.print_roster()

    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
