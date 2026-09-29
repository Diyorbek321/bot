from config import MISTAKES_QUIZ_SIZE, POINTS_MAX, POINTS_MIN, QUESTION_COUNTS
from quiz import MODE_MISTAKES, build_questions, pick_words, speed_points


def test_question_counts_start_from_fifty():
    assert min(QUESTION_COUNTS) >= 50
    assert MISTAKES_QUIZ_SIZE >= 50


def test_speed_points_range():
    assert speed_points(0) == POINTS_MAX
    assert speed_points(10) == 75
    assert speed_points(20) == POINTS_MIN
    assert speed_points(35) == POINTS_MIN  # kechikkan javob ham minimumdan tushmaydi
    assert speed_points(-1) == POINTS_MAX


def test_pick_words_gives_requested_count():
    words = pick_words(50)
    assert len(words) == len(set(words)) == 50


def test_mistakes_mode_builds_mixed_poll_questions():
    questions = build_questions(MODE_MISTAKES, [0, 1, 2, 3])
    assert [q.word_id for q in questions] == [0, 1, 2, 3]
    assert all(len(q.options) == 4 and 0 <= q.correct_index < 4 for q in questions)
