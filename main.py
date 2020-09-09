from bs4 import BeautifulSoup

class Colors:
    BLACK = '\033[90m'
    RED = '\033[91m'
    GREEN = '\033[32m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def main():

    with open("table.html", "r") as f:
        print("Reading data...")
        data = f.read()
        soup = BeautifulSoup(data, 'html.parser')

    roster = []
    def generate_players():
        players = soup.find_all("tr", class_="Table__TR")
        print("Adding players to roster...")
        for i, player in enumerate(players):

            # Conditional check for divider
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
            position = player_bio.find("span",
                                       class_="playerinfo__playerpos").text
            projection = cells[5].span.text
            inj_rpt = player_bio.find("span",
                                      class_="playerinfo__injurystatus")
            status = inj_rpt.text.strip() if inj_rpt else "OK"

            # 'Starting' check
            starting = 'S' if i <= 8 else 'B'

            # Create instance of player class and add to list of players
            p = {
                    "Name": name,
                    "Team": team,
                    "Position": position,
                    "Projection": float(projection),
                    "Starting": starting,
                    "Status": status
                    }
            roster.append(p)


    def projection_check(*position):
        #search position best projection is starting
        if position:
            prj_players = list(filter(lambda p: p['Position'] == position[0],
                                      roster))
        else:
            prj_players = roster
        prj_players.sort(key=lambda proj: proj.get('Projection'),
                               reverse=True)
        prj_players.sort(key=lambda strt: strt.get('Starting'),
                               reverse=True)
        for p in prj_players:
            position, name, projection, starting, status = [
                    p['Position'], p['Name'], p['Projection'],
                    p['Starting'], p['Status']
                    ]

            color_starting = {"S": Colors.BLUE, "B": Colors.BLACK}
            color_status = {
                    "OK": Colors.GREEN,
                    "Q": Colors.YELLOW,
                    "O": Colors.RED,
                    "IR": Colors.RED
                    }
            line_format = f"{color_starting[starting]}" \
                          f"{position}" \
                          f"{Colors.ENDC}: " \
                          f"{color_status[status]}" \
                          f"{name}" \
                          f"{Colors.ENDC} " \
                          f"({projection})"
            print(line_format)

        get_user_input()

    def injury_report():
        #makes sure bench doesn't have injured players
        get_user_input()


    def get_user_input():
        user_input = input("\nWhat is your action?: ").upper()
        user_args = user_input.split(" ")
        print()
        if user_args[0] == "PROJECTION":
            try:
                position = user_args[1]
                print(f"Generating {position} projections... \n")
                projection_check(position)
            except:
                print("Generating full roster projections... \n")
                projection_check()
        elif user_args[0] == "INJURY":
            print("Generating injury report")
            injury_report()
        else:
            print("Error")


    generate_players()
    get_user_input()

if __name__ == '__main__':
    main()
