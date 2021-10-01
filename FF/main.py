from __future__ import annotations

import argparse
import json
import operator
import os

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
    'data/',
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

HEADER = ('{:<6}{:<4}{:<15}{:<6}{}').format(
    'Slot', 'Pos', 'Player', 'Proj', 'Score',
)


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

    def generate_roster(self, d: dict, year: int, week: int) -> None:
        print('\nAdding players to roster...')
        for team in d['teams']:
            if team['id'] == self.TID:
                for p in team['roster']['entries']:
                    name = p['playerPoolEntry']['player']['fullName']
                    slot = slotID[p['lineupSlotId']]
                    slot_id = p['lineupSlotId']
                    if slot_id == 23:
                        slot_id = 7
                    starting = False if slot == 'B' else True
                    pos = positionID[
                        p['playerPoolEntry']
                        ['player']['defaultPositionId']
                    ]
                    proj, score = 0, 0
                    for stat in p['playerPoolEntry']['player']['stats']:
                        if (
                            stat['externalId'] == str(year) and
                            stat['statSourceId'] == 0
                        ):
                            avg = stat['appliedAverage']
                        if stat['scoringPeriodId'] == week:
                            if stat['statSourceId'] == 0:
                                score = stat['appliedTotal']
                            elif stat['statSourceId'] == 1:
                                proj = stat['appliedTotal']

                    status = 'ACTIVE'
                    rosterLocked = p['playerPoolEntry']['rosterLocked']
                    try:
                        status = p['playerPoolEntry']['player']['injuryStatus']
                    except KeyError:
                        pass
                    player = Player(
                        name, slot, slot_id, pos,
                        starting, proj, score, avg, status, rosterLocked,
                    )

                    self.roster.append(player)

        if len(self.roster) == 0:
            raise SystemExit(
                f'{Colors.RED}Team id: {self.TID} does not exist'
                f'{Colors.ENDC}',
            )

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

        max = flex_spot[0].proj
        tiebreak = [p for p in flex_spot if p.proj == max]
        
        if len(tiebreak) >= 2:
            tiebreak.sort(key=operator.attrgetter('avg'), reverse=True)
            # need tiebreak for equal averages
            flex = tiebreak[0]
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

    def get_total_projected(self) -> None:
        self.total_projected = 0.0
        for p in self.roster:
            if p.starting:
                self.total_projected += p.proj

    def get_in_play(self) -> None:
        self.in_play = 0
        for p in self.roster:
            if not p.rosterLocked:
                while self.in_play < 9:
                    self.in_play += 1

    def print_roster(self) -> None:
        print(HEADER)
        print('-'*36)
        for p in self.roster:
            print(p)


class Player(Roster):
    def __init__(
        self, name: str, slot: str, slot_id: int, pos: str,
        starting: bool, proj: float, score: float, avg: float, status: str,
        rosterLocked: bool,
    ) -> None:
        self.first = name.split(' ')[0]
        self.last = name.split(' ')[1]
        self.slot = slot
        self.slot_id = slot_id
        self.pos = pos.upper()
        self.starting = starting
        self.shouldStart = False
        self.proj = round(proj, 1)
        self.score = round(score, 1)
        self.avg = round(avg, 1)
        self.status = status
        self.rosterLocked = rosterLocked
        self.performance = 'NAN'
        self.performance_check()

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
        }
        self.color_starting = color_starting[self.starting]
        self.color_status = color_status[self.status]
        self.color_shouldStart = color_shouldStart[self.shouldStart]
        self.color_performance = color_performance[self.performance]

    def truncate(self) -> None:
        if len(self.last) >= 12:
            self.last = f'{self.last[:7]}...'

    def performance_check(self) -> None:
        spread = (self.proj * .25)
        if self.rosterLocked:
            if self.score < (self.proj - spread):
                self.performance = 'LOW'
            elif (self.proj - spread) < self.score <= (self.proj + spread):
                self.performance = 'MID'
            elif self.score > (self.proj + spread):
                self.performance = 'HIGH'
            else:
                self.performance = 'NAN'

    def __str__(self) -> str:
        self.apply_color()
        self.truncate()
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
               f'{self.score :>6}' \
               f'{Colors.ENDC}'.expandtabs(3)


def load_cookies(dev: bool, key: str = None) -> int | dict:
    try:
        if dev:
            with open(COOKIES_DEV_PATH) as rc:
                c = json.load(rc)
        else:
            with open(COOKIES_PATH) as rc:
                c = json.load(rc)
        return int(c[key]) if key else c
    except ValueError as e:
        print_cookies()
        raise SystemExit(
            f'{Colors.RED}{type(e).__name__}: '
            'Error loading from your cookies file. '
            'Ensure all the fields are filled out.'
            f'{Colors.ENDC}',
        )
    except FileNotFoundError as e:
        raise SystemExit(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def save_data(d: dict, year: int, week: int, LID: int) -> None:
    try:
        with open(
            f'{DATA_PATH}/FF_{year}_wk{week}_{LID}.json',
            'w',
        ) as wf:
            json.dump(d, wf)
        print('Saving data...')
    except FileNotFoundError as e:
        raise SystemExit(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


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
    print(HEADER + sp + HEADER)
    print(('-'*36) + sp + ('-'*36))
    for i in range(len(myTeam.roster)):
        print(str(myTeam.roster[i]) + sp + str(opTeam.roster[i]))
    print(('-'*36) + sp + ('-'*36))

    in_play1 = f'Yet to Play: {myTeam.in_play}'
    in_play2 = f'Yet to Play: {opTeam.in_play}'
    projected1 = f'{round(myTeam.total_projected, 1):>15}'
    projected2 = f'{round(opTeam.total_projected, 1):>15}'
    print(
        in_play1 + projected1 + t1 +
        sp +
        in_play2 + projected2 + t2,
    )


def connect_FF(LID: int, wk: int, dev: bool) -> dict:
    c = load_cookies(dev)
    year = c['season']  # type: ignore
    swid = c['SWID']  # type: ignore
    espn_s2 = c['espn_s2']  # type: ignore

    url = (
        f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/'
        f'segments/0/leagues/{LID}?view=mMatchup&view=mMatchupScore'
        '&view=mPositionalRatings'
    )
    # Def ratings against position
    # https://fantasy.espn.com/apis/v3/games/ffl/seasons/2021/segments/0/leagues/131034?view=kona_player_info

    try:
        r = requests.get(
            url, params={'scoringPeriodId': str(wk)},
            cookies={'SWID': swid, 'espn_s2': espn_s2},
        )
        d = r.json()
        return d

    except requests.exceptions.RequestException as e:
        raise SystemExit(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def check_cookies_exists(args: argparse.Namespace) -> None:
    if not os.path.exists(COOKIES_PATH):
        template = {
            'league_id': 0,
            'team_id': 0,
            'season': 0,
            'SWID': '',
            'espn_s2': '',
        }
        try:
            with open(COOKIES_PATH, 'w') as wf:
                json.dump(template, wf)

        except Exception as e:
            raise SystemExit(e)


def update_cookies(args: argparse.Namespace) -> None:
    if args.dev:
        path = COOKIES_DEV_PATH
    else:
        path = COOKIES_PATH
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


def print_cookies() -> None:
    try:
        with open(COOKIES_PATH) as rf:
            for line in rf:
                print(line)
    except Exception as e:
        raise SystemExit(e)


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
    check_cookies_exists(args)
    update_cookies(args)
    year = int(load_cookies(args.dev, key='season'))  # type: ignore
    if not args.week:
        args.week = load_cookies(args.dev, key='week')  # type: ignore
    if not args.league_id:
        args.league_id = load_cookies(
            args.dev, key='league_id',
        )  # type: ignore
    if not args.team_id:
        args.team_id = load_cookies(args.dev, key='team_id')  # type: ignore
    if not args.pull:
        try:
            path = pkg_resources.resource_filename(
                __name__, 'data',
            )
            with open(
                f'''{path}/FF_{year}_wk{args.week}_'''
                f'''{args.league_id}.json''',
            ) as rf:
                d = json.load(rf)
        except FileNotFoundError as e:
            raise SystemExit(
                f'{Colors.RED}{type(e).__name__}: '
                f'{e}. Data must be pulled first. [ff --pull]'
                f'{Colors.ENDC}',
            )
    else:
        d = connect_FF(args.league_id, args.week, args.dev)
        save_data(
            d, year, args.week, args.league_id,
        )

    myTeam = Roster(args.team_id)
    myTeam.generate_roster(d, year, args.week)
    myTeam.get_matchup_score(d, args.week)
    myTeam.get_total_projected()
    myTeam.get_in_play()
    myTeam.decide_lineup()
    myTeam.sort_roster_by_pos()
    if args.matchup:
        opTeam = Roster(myTeam.op_TID)
        opTeam.generate_roster(d, year, args.week)
        opTeam.get_matchup_score(d, args.week)
        opTeam.get_total_projected()
        opTeam.get_in_play()
        opTeam.decide_lineup()
        opTeam.sort_roster_by_pos()
        print_matchup(myTeam, opTeam)
    else:
        myTeam.print_roster()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
