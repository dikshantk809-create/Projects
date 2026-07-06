import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
from app.services.scoring import TennisMatch
from app.services.court import CourtModel, detect_bounce

def play(m, seq):
    for w in seq: m.point(w)
    return m

def test_basic_game_win():
    m = play(TennisMatch(), "aaaa")          # 4 straight points
    assert m.games == [1, 0]
    assert m.summary()["points"] == "0-0"

def test_deuce_advantage():
    m = TennisMatch()
    play(m, "aaabbb")                         # 40-40
    assert "deuce" in m.summary()["points"]
    m.point("a"); assert m.summary()["points"] == "AD-40"
    m.point("a"); assert m.games == [1, 0]    # won from advantage

def test_set_win_by_two():
    m = TennisMatch()
    for _ in range(6):                        # a wins 6 games to 0 → set
        play(m, "aaaa")
    assert m.sets == [1, 0]
    assert m.set_scores[0] == (6, 0)

def test_tiebreak_trigger_and_win():
    m = TennisMatch()
    # get to 5-5 then 6-6: alternate game winners
    for i in range(12):
        play(m, "aaaa" if i % 2 == 0 else "bbbb")
    assert m.in_tiebreak, "should be in tiebreak at 6-6"
    for _ in range(7): m.point("a")           # 7-0 tiebreak
    assert m.sets == [1, 0]

def test_best_of_three_match_end():
    m = TennisMatch(best_of=3)
    for _ in range(2):                        # win 2 sets
        for _ in range(6): play(m, "aaaa")
    assert m.finished and m.winner == "a"

def test_court_in_out():
    # identity-ish homography mapping px≈meters for the test
    H = [[1,0,0],[0,1,0],[0,0,1]]
    court = CourtModel(homography=H, singles=True)  # width 8.23, length 23.77
    assert court.call(4.0, 12.0)["call"] == "in"     # mid-court
    assert court.call(-0.5, 12.0)["call"] == "out"   # left of sideline
    close = court.call(0.01, 12.0)                    # 1 cm inside
    assert close["call"] == "in" and close["close"]

def test_detect_bounce():
    # y rises (ball falls) then drops (bounces up) at index 2
    traj = [(0,5,10),(1,5,20),(2,5,35),(3,5,22),(4,5,15)]
    assert 2 in detect_bounce(traj)
