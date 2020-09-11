from bs4 import BeautifulSoup
import operator

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
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Roster:
    def __init__(self):
        self.roster = []

    def __str__(self):
        return self.roster

    def generate_roster(self, players):
        print("Adding players to roster...")
        for i, player in enumerate(players):
            first_cell_class = player.findChild()['class']
            if 'fw-medium' in first_cell_class:
                continue

            cells = player.find_all("td",
                                    class_="Table__TD")
            player_bio = player.find("div",
                                     class_="player-column__bio")
            name = player_bio.a.text.strip()
            team = player_bio.find("span",
                                   class_="playerinfo__playerteam").text
            slot = cells[0].div.text.strip()
            position = player_bio.find("span",
                                       class_="playerinfo__playerpos").text
            projection = cells[5].span.text
            inj_rpt = player_bio.find("span",
                                      class_="playerinfo__injurystatus")
            status = inj_rpt.text.strip() if inj_rpt else "OK"
            player = Player(name, team, slot, position,
                            projection, status)
            self.roster.append(player)


    def decide_flex(self):
        flex_ok = ["RB", "WR", "TE"]
        flex_spot = list(
                filter(lambda x: x.position in flex_ok and not x.start,
                self.roster))
        flex = flex_spot[0]
        flex.start = True

        return flex


    def decide_lineup(self):
        position_spots = {
                "QB": 1,
                "RB": 2,
                "WR": 2,
                "TE": 1,
                "D/ST": 1,
                "K": 1,
                "FLEX": 1
                }
        for pos, num in position_spots.items():
            position_players = list(filter(lambda x: x.position == pos,
                                    self.roster))
            if pos == "FLEX":
                flex = self.decide_flex()
                position_players.append(flex)

            for i in range(num):
                try:
                    p = position_players[i]
                    p.start = True
                except:
                    print(f"Skipping {pos}")


class Player(Roster):
    def __init__(self, name, team, slot, position, projection, status):
        self.first = name.split(" ")[0]
        self.last = name.split(" ")[1]
        self.team = team
        self.slot = slot
        self.position = position
        self.projection = float(projection)
        self.status = status
        self.start = False

    def apply_color(self):
        color_start = {True: Colors.BLUE, False: Colors.BLACK}
        color_slot = {"Bench": Colors.BLACK}
        color_status = {
        "OK": Colors.GREEN,
        "Q": Colors.YELLOW,
        "O": Colors.RED,
        "IR": Colors.RED
        }
        self.color_start = color_start[self.start]
        self.color_status = color_status[self.status]
        self.color_slot = color_slot[self.slot] if self.slot == "Bench" else Colors.BWHITE

    def __repr__(self):
        self.apply_color()
        return f"\n{self.color_start}" \
               f"{self.position}" \
               f"{Colors.ENDC}:\t" \
               f"{self.color_status}" \
               f"{self.first[0]}. " \
               f"{self.last}  " \
               f"{Colors.ENDC}\t" \
               f"{self.color_slot}" \
               f"({self.projection})" \
               f"{Colors.ENDC}"


def get_user_input():
    user_input = input("\nWhat is your action?: ").upper()

    if user_input == "PROJECTION":
        print(f"Generating projections... \n")
        myTeam.projection_check()
    else:
        print("Invalid Command")


if __name__ == '__main__':
    with open("table.html", "r") as f:
        print("Reading data...")
        data = f.read()
        soup = BeautifulSoup(data, 'html.parser')

    players = soup.find_all("tr", class_="Table__TR")
    myTeam = Roster()
    myTeam.generate_roster(players)
    myTeam.decide_lineup()
    print(myTeam.roster)
