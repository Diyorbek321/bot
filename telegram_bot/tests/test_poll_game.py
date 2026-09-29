from config import POINTS_MAX, POINTS_MIN, QUESTION_TIME
from poll_game import POLL_QUESTION_LIMIT, PollGame, poll_explanation, poll_question
from quiz import MODE_EN_UZ, MODE_SENTENCE, Question


def make_game(n: int = 5, is_group: bool = True) -> PollGame:
    questions = [Question(i, f"word{i} ____", MODE_SENTENCE, ["a", "b", "c", "d"], 1) for i in range(n)]
    game = PollGame(chat_id=1, is_group=is_group, mode=MODE_SENTENCE, questions=questions, started_by=7)
    game.polls = {f"p{i}": i for i in range(n)}
    game.sent_at = {i: 100.0 for i in range(n)}
    return game


def test_default_time_is_twenty_seconds():
    assert make_game().open_period == QUESTION_TIME == 20


def test_faster_answer_scores_more():
    game = make_game()
    assert game.record_answer("p0", 1, "Ali", 1, now=100.0)[1:] == (True, POINTS_MAX)
    assert game.record_answer("p0", 2, "Vali", 1, now=110.0)[1:] == (True, 75)
    assert game.record_answer("p0", 3, "Sami", 1, now=120.0)[1:] == (True, POINTS_MIN)
    assert game.players[1].score > game.players[2].score > game.players[3].score


def test_wrong_answer_scores_zero_and_resets_streak():
    game = make_game()
    game.record_answer("p0", 1, "Ali", 1, now=101.0)
    assert game.record_answer("p1", 1, "Ali", 0, now=101.0)[1:] == (False, 0)
    assert game.players[1].streak == 0


def test_duplicate_and_unknown_answers_ignored():
    game = make_game()
    game.record_answer("p0", 1, "Ali", 1, now=100.0)
    assert game.record_answer("p0", 1, "Ali", 1, now=100.0) is None
    assert game.record_answer("nope", 1, "Ali", 1, now=100.0) is None
    game.stopped = True
    assert game.record_answer("p1", 1, "Ali", 1, now=100.0) is None
    assert game.players[1].answered == 1


def test_answer_to_current_question_sets_event():
    game = make_game()
    game.index = 1
    game.record_answer("p0", 1, "Ali", 1, now=100.0)
    assert not game.answered.is_set()
    game.record_answer("p1", 2, "Vali", 1, now=100.0)
    assert game.answered.is_set()


def test_join_team_and_switch():
    game = make_game()
    assert game.join_team(1, "Ali", "red")
    assert not game.join_team(1, "Ali", "red")
    assert game.join_team(1, "Ali", "blue")
    assert [p.name for p in game.members("blue")] == ["Ali"]
    assert game.members("red") == []
    assert not game.join_team(1, "Ali", "purple")


def test_late_player_goes_to_smallest_active_team():
    game = make_game()
    game.join_team(1, "Ali", "red")
    game.join_team(2, "Vali", "red")
    game.join_team(3, "Sami", "blue")
    game.record_answer("p0", 4, "Kechikkan", 1, now=100.0)
    assert game.players[4].team == "blue"


def test_private_game_has_no_teams():
    game = make_game(is_group=False)
    game.record_answer("p0", 1, "Ali", 1, now=100.0)
    assert game.players[1].team is None
    assert game.team_ranking() == []


def test_team_ranking_sums_member_scores():
    game = make_game()
    game.join_team(1, "Ali", "red")
    game.join_team(2, "Vali", "blue")
    game.join_team(3, "Sami", "blue")
    game.record_answer("p0", 1, "Ali", 1, now=100.0)  # 100
    game.record_answer("p0", 2, "Vali", 1, now=120.0)  # 50
    game.record_answer("p0", 3, "Sami", 1, now=110.0)  # 75
    teams = game.team_ranking()
    assert [(t.key, t.score, t.correct, len(t.members)) for t in teams] == [
        ("blue", 125, 2, 2),
        ("red", 100, 1, 1),
    ]
    assert [p.name for p in teams[0].members] == ["Sami", "Vali"]


def test_ranking_orders_by_score():
    game = make_game()
    game.record_answer("p0", 1, "Ali", 0, now=100.0)
    game.record_answer("p0", 2, "Vali", 1, now=100.0)
    assert [p.name for p in game.ranking()] == ["Vali", "Ali"]


def test_poll_texts():
    q = Question(0, "I went outside to ____.", MODE_SENTENCE, ["a", "b", "c", "d"], 0)
    assert poll_question(q, 3, 50) == "[3/50] I went outside to ____."
    tr = Question(0, "achieve", MODE_EN_UZ, ["a", "b", "c", "d"], 0)
    assert poll_question(tr, 1, 50).startswith("[1/50] 🇬🇧 achieve")
    long_q = Question(0, "x" * 400, MODE_SENTENCE, ["a", "b", "c", "d"], 0)
    assert len(poll_question(long_q, 1, 1)) == POLL_QUESTION_LIMIT
    assert poll_explanation(q).startswith("📖 achieve")
