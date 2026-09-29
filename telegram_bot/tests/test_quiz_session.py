from config import MISTAKES_QUIZ_SIZE, POINTS_MAX, POINTS_MIN, QUESTION_COUNTS
from quiz import MODE_EN_UZ, build_session, speed_points


def test_question_counts_start_from_fifty():
    assert min(QUESTION_COUNTS) >= 50
    assert MISTAKES_QUIZ_SIZE >= 50


def test_speed_points_range():
    assert speed_points(0) == POINTS_MAX
    assert speed_points(10) == 75
    assert speed_points(20) == POINTS_MIN
    assert speed_points(35) == POINTS_MIN  # kechikkan javob ham minimumdan tushmaydi
    assert speed_points(-1) == POINTS_MAX


def test_session_has_requested_count():
    assert len(build_session(MODE_EN_UZ, 50).questions) == 50


def test_answer_uses_speed():
    session = build_session(MODE_EN_UZ, 50)
    correct = session.current.correct_index
    assert session.answer(correct, elapsed=0) == (True, POINTS_MAX)
    correct = session.current.correct_index
    assert session.answer(correct, elapsed=20) == (True, POINTS_MIN)
    assert session.score == POINTS_MAX + POINTS_MIN
    assert session.index == 2


def test_timeout_moves_to_next_question():
    session = build_session(MODE_EN_UZ, 50)
    first_word = session.current.word_id
    session.answer(session.current.correct_index, elapsed=1)
    session.timeout()
    session.timeout()
    assert session.index == 3
    assert session.streak == 0
    assert session.timeouts_in_row == 2
    assert session.score == speed_points(1)
    assert first_word not in session.wrong_words and len(session.wrong_words) == 2
    session.answer(0, elapsed=1)
    assert session.timeouts_in_row == 0
