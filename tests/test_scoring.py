from engine.scoring import RawScore, go_multiplier, score_player, settle

# Gwang ids: month1=0, month3=8, month8=28, month11=40, month12(rain)=44
GWANG_1, GWANG_3, GWANG_8, GWANG_11, GWANG_RAIN_12 = 0, 8, 28, 40, 44

# Godori animal ids: month2=4, month4=12, month8=29 ; other plain animals: month5=16, month6=20
GODORI_2, GODORI_4, GODORI_8 = 4, 12, 29
ANIMAL_5, ANIMAL_6 = 16, 20

# Ribbon ids: hongdan = month1/2/3 -> 1,5,9 ; plain ribbons for count padding: chodan month4/5 -> 13,17
HONGDAN_1, HONGDAN_2, HONGDAN_3 = 1, 5, 9
CHODAN_4, CHODAN_5 = 13, 17

# Junk ids: plain pi month1 -> 2,3 ; month2 -> 6,7 ; month4 -> 14,15 ; ssangpi month11/12 -> 43,47
PI_1A, PI_1B, PI_2A, PI_2B, PI_4A, PI_4B = 2, 3, 6, 7, 14, 15
SSANGPI_11, SSANGPI_12 = 43, 47


def test_gwang_scoring_table():
    assert score_player([GWANG_1, GWANG_3, GWANG_8, GWANG_11, GWANG_RAIN_12]).gwang == 15
    assert score_player([GWANG_1, GWANG_3, GWANG_8, GWANG_11]).gwang == 4
    assert score_player([GWANG_1, GWANG_3, GWANG_8]).gwang == 3
    assert score_player([GWANG_1, GWANG_3, GWANG_RAIN_12]).gwang == 2  # 3-gwang incl. rain
    assert score_player([GWANG_1, GWANG_3]).gwang == 0


def test_animal_threshold_and_godori_bonus():
    five_with_godori = [GODORI_2, GODORI_4, GODORI_8, ANIMAL_5, ANIMAL_6]
    assert score_player(five_with_godori).animal == 1 + 5  # count score (1) + godori (5)

    godori_only_three = [GODORI_2, GODORI_4, GODORI_8]
    assert score_player(godori_only_three).animal == 5  # below count threshold, godori still scores

    no_godori_five = [ANIMAL_5, ANIMAL_6, GODORI_2, 24, 32]  # only 1 of 3 godori birds
    assert score_player(no_godori_five).animal == 1  # count score only, no godori bonus


def test_ribbon_threshold_and_color_set_bonus():
    five_with_hongdan = [HONGDAN_1, HONGDAN_2, HONGDAN_3, CHODAN_4, CHODAN_5]
    assert score_player(five_with_hongdan).ribbon == 1 + 3  # count (1) + hongdan set (3)

    hongdan_only_three = [HONGDAN_1, HONGDAN_2, HONGDAN_3]
    assert score_player(hongdan_only_three).ribbon == 3  # below count threshold, set still scores

    no_set_three = [HONGDAN_1, HONGDAN_2, CHODAN_4]
    assert score_player(no_set_three).ribbon == 0


def test_pi_scoring_counts_ssangpi_as_two():
    eight_plain_plus_ssangpi = [PI_1A, PI_1B, PI_2A, PI_2B, PI_4A, PI_4B, SSANGPI_11]
    score = score_player(eight_plain_plus_ssangpi)
    assert score.pi_count == 8
    assert score.pi == 0

    add_two_more = eight_plain_plus_ssangpi + [SSANGPI_12]  # +2 -> 10 total
    score2 = score_player(add_two_more)
    assert score2.pi_count == 10
    assert score2.pi == 1


def test_pi_score_includes_bonus_penalties():
    base = [PI_1A, PI_1B, PI_2A, PI_2B, PI_4A, PI_4B, SSANGPI_11, SSANGPI_12]  # 10 pi
    without_bonus = score_player(base)
    assert without_bonus.pi_count == 10 and without_bonus.pi == 1
    with_received = score_player(base, bonus_pi_received=2)
    assert with_received.pi_count == 12 and with_received.pi == 3
    with_paid = score_player(base, bonus_pi_paid=3)
    assert with_paid.pi_count == 7 and with_paid.pi == 0


def test_go_multiplier_progression():
    assert [go_multiplier(g) for g in range(6)] == [1, 1, 1, 2, 4, 8]


def _raw(total=0, gwang=0, animal=0, pi=0, gwang_count=0, animal_count=0, pi_count=0):
    return RawScore(gwang=gwang, animal=animal, ribbon=0, pi=pi, total=total,
                     gwang_count=gwang_count, animal_count=animal_count, pi_count=pi_count)


def test_settle_plain_win_no_baks():
    winner_raw = _raw(total=7)
    loser_raw = _raw(gwang_count=1, pi_count=6, animal_count=3)
    result = settle(0, winner_raw, loser_raw, winner_go_count=0, loser_called_go=False)
    assert result.final_score == 7
    assert not (result.gwang_bak or result.pi_bak or result.meong_bak)


def test_settle_gwang_bak_and_pi_bak_stack():
    winner_raw = _raw(total=10, gwang=3, pi=1, gwang_count=3, pi_count=10)
    loser_raw = _raw(gwang_count=0, pi_count=3, animal_count=2)
    result = settle(0, winner_raw, loser_raw, winner_go_count=0, loser_called_go=False)
    assert result.gwang_bak and result.pi_bak
    assert result.multiplier == 4
    assert result.final_score == 40


def test_settle_meong_bak_from_winners_own_animal_count():
    winner_raw = _raw(total=8, animal_count=7)
    loser_raw = _raw(gwang_count=2, pi_count=6, animal_count=1)
    result = settle(0, winner_raw, loser_raw, winner_go_count=0, loser_called_go=False)
    assert result.meong_bak
    assert result.multiplier == 2
    assert result.final_score == 16


def test_settle_go_bonus_and_multiplier_and_gobak():
    winner_raw = _raw(total=7)
    loser_raw = _raw(gwang_count=1, pi_count=6, animal_count=2)
    result = settle(0, winner_raw, loser_raw, winner_go_count=3, loser_called_go=False)
    assert result.go_bonus == 3
    assert result.multiplier == 2  # go_multiplier(3) == 2
    assert result.final_score == (7 + 3) * 2

    result_gobak = settle(0, winner_raw, loser_raw, winner_go_count=3, loser_called_go=True)
    assert result_gobak.final_score == (7 + 3) * 2 * 2
