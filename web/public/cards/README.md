# Card images

Drop PNG files in this folder (`web/public/cards/`) and the app will use them automatically — no
code changes needed. Any card without a matching file just keeps the current plain colored-box
look, so you can upload a few at a time and see them mixed in with the rest.

## Naming

Name each file after the card's id: `0.png`, `1.png`, ... `47.png`. The id-to-card mapping below is
fixed by the engine (`engine/cards.py`) and matches RULES.md's deck table.

The card back (shown for the opponent's hidden hand) goes in `back.png`.

## Recommended image shape

Roughly portrait, about 2:3 (width:height) — matches the box the app already draws cards in
(52x76px at the current size, scaled up is fine). Any size works; it'll be scaled to fit, but a
source image close to that ratio will crop the least.

## The 48 ids, in order

| id | Month | Card | id | Month | Card |
|---|---|---|---|---|---|
| 0 | 1월 (Pine) | 광 — crane & sun | 24 | 7월 (Clover) | 동물 — boar |
| 1 | 1월 (Pine) | 홍단 (red ribbon) | 25 | 7월 (Clover) | 초단 (plain ribbon) |
| 2 | 1월 (Pine) | 피 | 26 | 7월 (Clover) | 피 |
| 3 | 1월 (Pine) | 피 | 27 | 7월 (Clover) | 피 |
| 4 | 2월 (Plum) | 동물 — bush warbler (고도리) | 28 | 8월 (Pampas) | 광 — full moon |
| 5 | 2월 (Plum) | 홍단 (red ribbon) | 29 | 8월 (Pampas) | 동물 — geese (고도리) |
| 6 | 2월 (Plum) | 피 | 30 | 8월 (Pampas) | 피 |
| 7 | 2월 (Plum) | 피 | 31 | 8월 (Pampas) | 피 |
| 8 | 3월 (Cherry) | 광 — curtain | 32 | 9월 (Chrysanthemum) | 동물 — sake cup |
| 9 | 3월 (Cherry) | 홍단 (red ribbon) | 33 | 9월 (Chrysanthemum) | 청단 (blue ribbon) |
| 10 | 3월 (Cherry) | 피 | 34 | 9월 (Chrysanthemum) | 피 |
| 11 | 3월 (Cherry) | 피 | 35 | 9월 (Chrysanthemum) | 피 |
| 12 | 4월 (Wisteria) | 동물 — cuckoo (고도리) | 36 | 10월 (Maple) | 동물 — deer |
| 13 | 4월 (Wisteria) | 초단 (plain ribbon) | 37 | 10월 (Maple) | 청단 (blue ribbon) |
| 14 | 4월 (Wisteria) | 피 | 38 | 10월 (Maple) | 피 |
| 15 | 4월 (Wisteria) | 피 | 39 | 10월 (Maple) | 피 |
| 16 | 5월 (Iris) | 동물 — bridge | 40 | 11월 (Paulownia) | 광 — phoenix |
| 17 | 5월 (Iris) | 초단 (plain ribbon) | 41 | 11월 (Paulownia) | 피 |
| 18 | 5월 (Iris) | 피 | 42 | 11월 (Paulownia) | 피 |
| 19 | 5월 (Iris) | 피 | 43 | 11월 (Paulownia) | 쌍피 (double junk) |
| 20 | 6월 (Peony) | 동물 — butterflies | 44 | 12월 (Rain) | 광 — rain man |
| 21 | 6월 (Peony) | 청단 (blue ribbon) | 45 | 12월 (Rain) | 동물 — swallow |
| 22 | 6월 (Peony) | 피 | 46 | 12월 (Rain) | 띠 (plain ribbon) |
| 23 | 6월 (Peony) | 피 | 47 | 12월 (Rain) | 쌍피 (double junk) |

Within a month, the two 피 (junk) cards are interchangeable — it doesn't matter which physical card
goes in the lower id vs. the higher one of the pair.
