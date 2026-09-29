from quiz import MODE_EN_UZ, MODE_MIXED, MODE_SENTENCE, SENTENCES, WORDS, build_questions, make_question


def test_every_word_has_sentences():
    assert len(SENTENCES) == len(WORDS)


def test_sentence_bank_is_well_formed():
    for word_id, sentences in SENTENCES.items():
        for s in sentences:
            assert s["text"].count("____") == 1, s["text"]
            options = [s["answer"], *s["wrong"]]
            assert len(options) == 4
            assert len({o.lower() for o in options}) == 4, s
            assert all(len(o) <= 100 for o in options)


def test_sentence_question_has_correct_answer_among_options():
    for word_id in range(0, len(WORDS), 25):
        q = make_question(word_id, MODE_SENTENCE)
        assert q.direction == MODE_SENTENCE
        assert "____" in q.prompt
        assert q.correct_answer in {s["answer"] for s in SENTENCES[word_id]}
        assert WORDS[word_id]["en"] in q.word_hint


def test_build_questions_keeps_fixed_direction():
    qs = build_questions(MODE_EN_UZ, [0, 1, 2])
    assert [q.direction for q in qs] == [MODE_EN_UZ] * 3
    assert [q.word_id for q in qs] == [0, 1, 2]


def test_mixed_mode_uses_all_directions():
    qs = build_questions(MODE_MIXED, list(range(200)))
    assert len({q.direction for q in qs}) == 3
