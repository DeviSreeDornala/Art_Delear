"""Pattern predicates and registries adapted from provided logic.

This module provides:
- single-card predicates: functions(Card) -> bool used by 'single' patterns
- set predicates: functions(List[Card]) -> bool used by 'set' patterns

Patterns are registered in PATTERNS_BY_LEVEL with an 'id', 'name', 'type',
and 'predicate'. The GameState expects 'type' to be either 'single' or
'set' and predicate to be callable accordingly.
"""

from typing import List, Tuple
from .game_logic import Card
from collections import Counter

# Suit symbols present in Card.suit
HEARTS = '\u2665'
DIAMONDS = '\u2666'
CLUBS = '\u2663'
SPADES = '\u2660'

def rank_key(card: Card) -> str:
    return card.rank.lower()

# --- single-card predicates ---
def is_red(card: Card) -> bool:
    return card.suit in (HEARTS, DIAMONDS)

def is_black(card: Card) -> bool:
    return card.suit in (CLUBS, SPADES)

def is_hearts(card: Card) -> bool:
    return card.suit == HEARTS

def is_spades(card: Card) -> bool:
    return card.suit == SPADES

def is_clubs(card: Card) -> bool:
    return card.suit == CLUBS

def is_diamonds(card: Card) -> bool:
    return card.suit == DIAMONDS

def is_ace(card: Card) -> bool:
    return rank_key(card) == 'a'

def is_even_number(card: Card) -> bool:
    r = rank_key(card)
    return r.isdigit() and int(r) in {2, 4, 6, 8, 10}

def is_odd_number(card: Card) -> bool:
    r = rank_key(card)
    return r.isdigit() and int(r) in {3, 5, 7, 9}

def is_queen(card: Card) -> bool:
    return rank_key(card) == 'q'

def is_king(card: Card) -> bool:
    return rank_key(card) == 'k'

def is_jack(card: Card) -> bool:
    return rank_key(card) == 'j'

def is_number_card(card: Card) -> bool:
    return rank_key(card).isdigit()

def is_face_card(card: Card) -> bool:
    return rank_key(card) in {'j', 'q', 'k'}

def is_single_digit_prime(card: Card) -> bool:
    r = rank_key(card)
    return r.isdigit() and int(r) in {2, 3, 5, 7}

# helpers for mapping ranks
def rank_to_value_allow_faces(card: Card) -> Tuple[bool, int]:
    r = rank_key(card)
    if r == 'a':
        return True, 14
    if r == 'k':
        return True, 13
    if r == 'q':
        return True, 12
    if r == 'j':
        return True, 11
    if r.isdigit():
        return True, int(r)
    return False, 0

# --- set predicates (operate on 4-card selection) ---
def all_same_suit(cards: List[Card]) -> bool:
    if not cards:
        return False
    s = cards[0].suit
    return all(c.suit == s for c in cards)

def sum_to_9(cards: List[Card]) -> bool:
    if len(cards) != 4:
        return False
    total = 0
    for c in cards:
        r = rank_key(c)
        if not r.isdigit():
            return False
        total += int(r)
    return total == 9

def ace_and_black_jack(cards: List[Card]) -> bool:
    has_ace = any(is_ace(c) for c in cards)
    has_black_jack = any(is_jack(c) and is_black(c) for c in cards)
    return has_ace and has_black_jack

def all_single_digit_primes(cards: List[Card]) -> bool:
    if len(cards) != 4:
        return False
    return all(is_single_digit_prime(c) for c in cards)

def two_pairs(cards: List[Card]) -> bool:
    if len(cards) != 4:
        return False
    ranks = [rank_key(c) for c in cards]
    counts = Counter(ranks)
    pairs = [r for r, cnt in counts.items() if cnt == 2]
    return len(pairs) == 2

def is_straight(cards: List[Card]) -> bool:
    if len(cards) != 4:
        return False
    ranks = [rank_key(c) for c in cards]
    # numeric-only straight
    if all(r.isdigit() for r in ranks):
        nums = sorted(int(r) for r in ranks)
        return nums == list(range(nums[0], nums[0] + 4))
    # allow faces + ace mapping
    vals = []
    for c in cards:
        ok, v = rank_to_value_allow_faces(c)
        if not ok:
            return False
        vals.append(v)
    vals.sort()
    return vals == list(range(vals[0], vals[0] + 4))

def is_flush(cards: List[Card]) -> bool:
    return len(cards) == 4 and all_same_suit(cards)

def is_full_house(cards: List[Card]) -> bool:
    # Full house is a 5-card concept (3+2); not valid for 4 cards in our
    # selection model. Return False and document in 'desc'.
    return False

def four_of_a_kind(cards: List[Card]) -> bool:
    if len(cards) != 4:
        return False
    ranks = [rank_key(c) for c in cards]
    counts = Counter(ranks)
    return 4 in counts.values()

def is_straight_flush(cards: List[Card]) -> bool:
    return is_flush(cards) and is_straight(cards)

def is_royal_flush(cards: List[Card]) -> bool:
    # royal flush requires 5 cards (10,J,Q,K,A) - not available for 4-card play
    return False

def all_different_suits(cards: List[Card]) -> bool:
    suits = [c.suit for c in cards]
    return len(set(suits)) == 4 and len(cards) == 4

def all_different_numbers(cards: List[Card]) -> bool:
    ranks = [rank_key(c) for c in cards]
    return len(set(ranks)) == len(cards)

# --- pattern registries ---
K2_PATTERNS = [
    {'id': 'all_red', 'name': 'All red cards', 'type': 'single', 'predicate': is_red, 'desc': 'Hearts & Diamonds'},
    {'id': 'all_black', 'name': 'All black cards', 'type': 'single', 'predicate': is_black, 'desc': 'Clubs & Spades'},
    {'id': 'all_hearts', 'name': 'All hearts', 'type': 'single', 'predicate': is_hearts, 'desc': 'Hearts'},
    {'id': 'all_spades', 'name': 'All spades', 'type': 'single', 'predicate': is_spades, 'desc': 'Spades'},
    {'id': 'all_clubs', 'name': 'All clubs', 'type': 'single', 'predicate': is_clubs, 'desc': 'Clubs'},
    {'id': 'all_diamonds', 'name': 'All diamonds', 'type': 'single', 'predicate': is_diamonds, 'desc': 'Diamonds'},
    {'id': 'all_aces', 'name': 'All aces', 'type': 'single', 'predicate': is_ace, 'desc': 'Aces'},
    {'id': 'all_even', 'name': 'All even numbers', 'type': 'single', 'predicate': is_even_number, 'desc': 'Even numeric ranks'},
    {'id': 'all_odd', 'name': 'All odd numbers', 'type': 'single', 'predicate': is_odd_number, 'desc': 'Odd numeric ranks'},
    {'id': 'all_queens', 'name': 'All queens', 'type': 'single', 'predicate': is_queen, 'desc': 'Queens'},
    {'id': 'all_kings', 'name': 'All kings', 'type': 'single', 'predicate': is_king, 'desc': 'Kings'},
    {'id': 'all_jacks', 'name': 'All jacks', 'type': 'single', 'predicate': is_jack, 'desc': 'Jacks'},
    {'id': 'same_suit', 'name': 'All cards of the same suit', 'type': 'set', 'predicate': all_same_suit, 'desc': 'All same suit'},
]

# Backwards-compatible aliases for older IDs used in tests/UI
K2_PATTERNS.append({'id': 'red', 'name': 'All red cards', 'type': 'single', 'predicate': is_red, 'desc': 'Hearts & Diamonds'})
K2_PATTERNS.append({'id': 'hearts', 'name': 'All hearts', 'type': 'single', 'predicate': is_hearts, 'desc': 'Hearts'})

THREE_FIVE_PATTERNS = K2_PATTERNS + [
    {'id': 'single_digit_primes', 'name': 'All single-digit primes', 'type': 'single', 'predicate': is_single_digit_prime, 'desc': '2,3,5,7'},
    {'id': 'sum_to_9', 'name': 'Cards add to 9', 'type': 'set', 'predicate': sum_to_9, 'desc': 'Four numeric cards add to 9 (Ace not allowed)'},
    {'id': 'ace_black_jack', 'name': 'Ace and a black jack', 'type': 'set', 'predicate': ace_and_black_jack, 'desc': 'Contains an Ace and a black Jack'},
    {'id': 'all_number_cards', 'name': 'All number cards', 'type': 'single', 'predicate': is_number_card, 'desc': 'No face cards'},
    {'id': 'all_face_cards', 'name': 'All face cards', 'type': 'single', 'predicate': is_face_card, 'desc': 'All J,Q,K'},
]

SIX_EIGHT_PATTERNS = THREE_FIVE_PATTERNS + [
    {'id': 'two_pairs', 'name': 'Two pairs', 'type': 'set', 'predicate': two_pairs, 'desc': 'Two different pairs (4-card selection)'},
    {'id': 'straight', 'name': 'Straight', 'type': 'set', 'predicate': is_straight, 'desc': 'Four consecutive ranks (faces allowed)'},
    {'id': 'flush', 'name': 'Flush', 'type': 'set', 'predicate': is_flush, 'desc': 'All cards same suit'},
    {'id': 'full_house', 'name': 'Full house', 'type': 'set', 'predicate': is_full_house, 'desc': 'Full house requires 5 cards - not available for 4-card play'},
    {'id': 'four_of_a_kind', 'name': 'Four of a kind', 'type': 'set', 'predicate': four_of_a_kind, 'desc': 'Four cards of same rank'},
    {'id': 'straight_flush', 'name': 'Straight flush', 'type': 'set', 'predicate': is_straight_flush, 'desc': 'Straight and flush together'},
    {'id': 'royal_flush', 'name': 'Royal flush', 'type': 'set', 'predicate': is_royal_flush, 'desc': 'Royal flush requires 5 cards - not available for 4-card play'},
    {'id': 'all_different_suits', 'name': 'All different suits', 'type': 'set', 'predicate': all_different_suits, 'desc': 'Each card different suit'},
    {'id': 'all_different_numbers', 'name': 'All different numbers', 'type': 'set', 'predicate': all_different_numbers, 'desc': 'Each card a different rank'},
]

PATTERNS_BY_LEVEL = {
    'K2': K2_PATTERNS,
    '3-5': THREE_FIVE_PATTERNS,
    '6-8': SIX_EIGHT_PATTERNS,
}
