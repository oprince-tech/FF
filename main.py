import operator
from typing import Dict
import requests
import json


slotID = {
        0: 'QB', 2: 'RB', 4: 'WR',
        6: 'TE', 16: 'DST', 17: 'K',
        20: 'Bench', 21: 'IR', 23: 'FLEX'
}

positionID = {
        1: 'QB', 2: 'RB', 3: 'WR',
        4: 'TE', 5: 'K', 16: 'DST'
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
    def __init__(self):
        self.roster = []

    def generate_roster(self, json_roster):
        print("\nAdding players to roster...")
        for team in d['teams']:
            if team['id'] == 9:
                for p in team['roster']['entries']:
                    name = p['playerPoolEntry']['player']['fullName']
                    slot = slotID[p['lineupSlotId']]
                    slot_id = p['lineupSlotId']
                    starting = False if slot == 'Bench' else True
                    pos = positionID[p['playerPoolEntry']['player']['defaultPositionId']]
                    proj, score = 0, 0
                    for stat in p['playerPoolEntry']['player']['stats']:
                        if stat['scoringPeriodId'] != 2:
                            continue
                        if stat['statSourceId'] == 0:
                            score = stat['appliedTotal']
                        elif stat['statSourceId'] == 1:
                            proj = stat['appliedTotal']

                    status = 'ACTIVE'
                    try:
                        status = p['playerPoolEntry']['player']['injuryStatus']
                    except:
                        pass

                    player = Player(name, slot, slot_id, pos, starting, proj, score, status)

                    self.roster.append(player)


    def sort_roster(self):
        self.roster.sort(key=operator.attrgetter('slot_id'))


    def decide_flex(self):
        print("Deciding flex position...")
        flex_ok = ["RB", "WR", "TE"]
        flex_spot = list(
                    filter(lambda x: x.pos in flex_ok and not x.starting,
                    self.roster))
        flex = flex_spot[0]
        current_flex = list(filter(lambda x: x.slot == "FLEX", self.roster))

        if flex.proj > current_flex[0].proj:
            flex.shouldStart = True
            current_flex[0].shouldStart = False
        else:
            flex.shouldStart = False
            current_flex[0].shouldStart = True
            flex = current_flex[0]

        flex.slot_id = 15
        return flex


    def decide_lineup(self):
        print("Deciding best lineup...")
        position_spots = {
                "QB": 1, "RB": 2, "WR": 2,
                "TE": 1, "DST": 1, "K": 1,
                "FLEX": 1
                }

        for pos, num in position_spots.items():
            position_players = list(filter(lambda x: x.pos == pos,
                                    self.roster))

            if pos == "FLEX":
                flex = self.decide_flex()
                position_players.append(flex)
                continue

            for i in range(num):
                try:
                    p = position_players[i]
                    p.shouldStart = True
                except:
                    print(f"Skipping {pos}")

    def print_roster(self):
        header = ("\n{}{:>12}{:>18}{:>12}").format('Slot', 'Player', 'Proj', 'Score')
        print(header)
        print("----------------------------------------------")
        for p in self.roster:
            print(p)


class Player(Roster):
    def __init__(self, name, slot, slot_id, pos, starting, proj, score, status):
        self.first = name.split(" ")[0]
        self.last = name.split(" ")[1]
        self.slot = slot
        self.slot_id = slot_id
        self.pos = pos.upper()
        self.starting = starting
        self.shouldStart = False
        self.proj = round(proj, 1)
        self.score = round(score, 1)
        self.status = status

    def apply_color(self):
        color_starting = {True: Colors.BLUE, False: Colors.BLACK}
        color_shouldStart = {True: Colors.CYAN, False: Colors.BLACK}
        color_status = {
                        "ACTIVE": Colors.GREEN,
                        "QUESTIONABLE": Colors.YELLOW,
                        "OUT": Colors.RED,
                        "IR": Colors.RED
                        }
        self.color_starting = color_starting[self.starting]
        self.color_status = color_status[self.status]
        self.color_shouldStart = color_shouldStart[self.shouldStart]


    def __str__(self):
        self.apply_color()
        return f"{self.color_starting}" \
               f"{self.slot}" \
               f"{Colors.ENDC}:\t" \
               f"{self.color_status :<8}" \
               f"{self.first[0]}. " \
               f"{self.last}" \
               f"{Colors.ENDC}\t" \
               f"{self.color_shouldStart}" \
               f"({self.proj})" \
               f"{Colors.ENDC}\t" \
               f"{self.score :>5}".expandtabs(tabsize=16)


def ID_check(LID, TID):
    try:
        LID = int(LID)
        TID = int(TID)
    except:
        raise TypeError("ID's must be a number")

    if not len(str(LID)) == 6:
        raise TypeError("League ID must have a length of 6")
    if not TID <= 12:
        raise TypeError(f"No team with a Team ID of {TID} was found")

def get_user_input():
    try:
        LID = input("League ID: ")
        TID = input("Team ID: ")
        ID_check(LID, TID)
        return {"LID": int(LID), "TID": int(TID)}
    except TypeError as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        quit()

def connect_FF(ID: Dict[str, int]):
    with open("cookies.json", "r") as rc:
        c = json.load(rc)

    swid = c['SWID']
    espn_s2 = c['espn_s2']
    url = f"https://fantasy.espn.com/apis/v3/games/ffl/seasons/2020/segments/0/leagues/{ID['LID']}?view=mMatchup&view=mMatchupScore"

    try:
        r = requests.get(url, params={'scoringPeriodId': 2},
                              cookies={"SWID": swid, "espn_s2": espn_s2})
        d = r.json()
        return d

    except requests.exceptions.RequestException as e:
        raise SystemExit(e)


if __name__ == '__main__':
    ID = get_user_input()

    d = connect_FF(ID)
    wk = d['scoringPeriodId']

    try:
        with open(f"weekly_data/FF_wk-{wk}.json", "w") as wf:
            json.dump(d, wf)
    except Exception as e:
        print(e)

    try:
        with open(f"weekly_data/FF_wk-{wk}.json", "r") as rf:
            d = json.load(rf)
    except Exception as e:
        print(e)

    myTeam = Roster()
    myTeam.generate_roster(d)
    myTeam.decide_lineup()
    myTeam.sort_roster()
    myTeam.print_roster()
