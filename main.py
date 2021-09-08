from __future__ import annotations

import argparse
import json
import operator
import os
import re

import requests  # type: ignore


slotID = {
    0: 'QB', 2: 'RB', 4: 'WR',
    6: 'TE', 16: 'DST', 17: 'K',
    20: 'Bench', 21: 'IR', 23: 'FLEX',
}

positionID = {
    1: 'QB', 2: 'RB', 3: 'WR',
    4: 'TE', 5: 'K', 16: 'DST',
}


class Colors:
    BLACK = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[32m'
    BGREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BWHITE = '\033[97m'
    ENDC = '\033[0m'


class Roster:
    def __init__(self) -> None:
        self.roster: list[Player] = []

    def generate_roster(self, d: dict, TID: int) -> None:
        print('\nAdding players to roster...')
        for team in d['teams']:
            if team['id'] == TID:
                for p in team['roster']['entries']:
                    name = p['playerPoolEntry']['player']['fullName']
                    slot = slotID[p['lineupSlotId']]
                    slot_id = p['lineupSlotId']
                    starting = False if slot == 'Bench' else True
                    pos = positionID[
                        p['playerPoolEntry']
                        ['player']['defaultPositionId']
                    ]
                    proj, score = 0, 0
                    for stat in p['playerPoolEntry']['player']['stats']:
                        if stat['statSourceId'] == 0:
                            score = stat['appliedTotal']
                        elif stat['statSourceId'] == 1:
                            proj = stat['appliedTotal']

                    status = 'ACTIVE'
                    try:
                        status = p['playerPoolEntry']['player']['injuryStatus']
                    except KeyError:
                        pass
                    player = Player(
                        name, slot, slot_id, pos,
                        starting, proj, score, status,
                    )

                    self.roster.append(player)

    def sort_roster(self) -> None:
        self.roster.sort(key=operator.attrgetter('slot_id'))

    def decide_flex(self) -> Player:
        print('Deciding flex position...')
        flex_ok = ['RB', 'WR', 'TE']
        flex_spot: list = list(
            filter(
                lambda x: x.pos in flex_ok and not x.starting,
                self.roster,
            ),
        )
        flex = flex_spot[0]
        current_flex: list = list(
            filter(
                lambda x: x.slot == 'FLEX',
                self.roster,
            ),
        )

        if flex.proj > current_flex[0].proj:
            flex.shouldStart = True
            current_flex[0].shouldStart = False
        else:
            flex.shouldStart = False
            current_flex[0].shouldStart = True
            flex = current_flex[0]

        flex.slot_id = 15
        return flex

    def decide_lineup(self) -> None:
        print('Deciding best lineup...')
        position_spots = {
            'QB': 1, 'RB': 2, 'WR': 2,
            'TE': 1, 'DST': 1, 'K': 1,
            'FLEX': 1,
        }

        for pos, num in position_spots.items():
            position_players = list(
                filter(
                    lambda x: x.pos == pos,
                    self.roster,
                ),
            )

            if pos == 'FLEX':
                flex = self.decide_flex()
                position_players.append(flex)
                continue

            for i in range(num):
                try:
                    p = position_players[i]
                    p.shouldStart = True
                except IndexError:
                    print(f'Skipping {pos}')

    def print_roster(self) -> None:
        header = ('\n{}{:>12}{:>18}{:>12}').format(
            'Slot', 'Player', 'Proj', 'Score',
        )
        print(header)
        print('----------------------------------------------')
        for p in self.roster:
            print(p)


class Player(Roster):
    def __init__(
        self, name: str, slot: str, slot_id: int, pos: str,
        starting: bool, proj: float, score: float, status: str,
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
        self.status = status

    def apply_color(self) -> None:
        color_starting = {True: Colors.BLUE, False: Colors.BLACK}
        color_shouldStart = {True: Colors.CYAN, False: Colors.BLACK}
        color_status = {
            'ACTIVE': Colors.GREEN,
            'QUESTIONABLE': Colors.YELLOW,
            'OUT': Colors.RED,
            'IR': Colors.RED,
        }
        self.color_starting = color_starting[self.starting]
        self.color_status = color_status[self.status]
        self.color_shouldStart = color_shouldStart[self.shouldStart]

    def __str__(self) -> str:
        self.apply_color()
        return f'{self.color_starting}' \
               f'{self.slot}' \
               f'{Colors.ENDC}:\t' \
               f'{self.color_status :<8}' \
               f'{self.first[0]}. ' \
               f'{self.last}' \
               f'{Colors.ENDC}\t' \
               f'{self.color_shouldStart}' \
               f'({self.proj})' \
               f'{Colors.ENDC}\t' \
               f'{self.score :>5}'.expandtabs(tabsize=16)


def load_cookies(key: str = None) -> int | dict:
    with open('cookies-dev.json') as rc:
        c = json.load(rc)
    return int(c[key]) if key else c


def save_weekly_data(d: dict, year: int, LID: int, TID: int, wk: int) -> None:
    try:
        with open(
            f'./weekly_data/FF_{year}_{LID}_{TID}_wk-{wk}.json',
            'w',
        ) as wf:
            json.dump(d, wf)
    except Exception as e:
        print(e)


def connect_FF(LID: int, wk: int) -> dict:
    c = load_cookies()
    year = c['season']  # type: ignore
    swid = c['SWID']  # type: ignore
    espn_s2 = c['espn_s2']  # type: ignore

    url = (
        f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/'
        'segments/0/leagues/131034?view=mMatchup&view=mMatchupScore'
    )

    try:
        r = requests.get(
            url, params={'scoringPeriodId': str(wk)},
            cookies={'SWID': swid, 'espn_s2': espn_s2},
        )
        d = r.json()
        return d

    except requests.exceptions.RequestException as e:
        raise SystemExit(f'{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}')


def last_updated_week() -> int:
    wks = os.listdir('./weekly_data')
    most_current = 0
    for wk in wks:
        wk_num = int(re.search(r'wk-(\d)', wk).group(1))  # type: ignore
        most_current = wk_num if wk_num > most_current else most_current
    return int(most_current)


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
        '-m', '--matchup',
        help='Show your matchup',
        action='store_true',
    )
    args = parser.parse_args()
    return args


def main() -> None:
    args = parse_args()
    year = load_cookies(key='season')
    if not args.week:
        args.week = last_updated_week()
    if not args.league_id:
        args.league_id = load_cookies(key='LID')
    if not args.team_id:
        args.team_id = load_cookies(key='TID')
    if not args.pull:
        try:
            with open(
                f'''./weekly_data/FF_{year}_'''
                f'''{args.league_id}_{args.team_id}_wk-{args.week}.json''',
            ) as rf:
                d = json.load(rf)
        except FileNotFoundError as e:
            raise SystemExit(f'{Colors.RED}{e}{Colors.ENDC}')
    else:
        d = connect_FF(args.league_id, args.week)
        save_weekly_data(
            d, year, args.league_id,  # type: ignore
            args.team_id, args.week,
        )
    myTeam = Roster()
    myTeam.generate_roster(d, args.team_id)
    myTeam.decide_lineup()
    myTeam.sort_roster()
    myTeam.print_roster()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
