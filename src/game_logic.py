# src/game_logic.py
import random
import itertools
from dataclasses import dataclass
from typing import List, Callable, Optional, Dict, Tuple

RANKS = ['A','2','3','4','5','6','7','8','9','10','J','Q','K']
SUITS = ['♥','♦','♣','♠']

pip_value_map = {r: (10 if r=='10' else (11 if r=='A' else (10 if r in ['J','Q','K'] else int(r)))) for r in RANKS}
# For arithmetic teaching we may map A=1 for some patterns. We'll override in patterns when needed.

@dataclass
class Card:
    rank: str
    suit: str

    def label(self) -> str:
        return f"{self.rank}{self.suit}"

    def pip(self, ace_high=True):
        if self.rank=='A':
            return 11 if ace_high else 1
        if self.rank in ['J','Q','K']:
            return 10
        return int(self.rank)

def full_deck() -> List[Card]:
    return [Card(r,s) for s in SUITS for r in RANKS]

class GameState:
    def __init__(self, level:str='K2', two_player=False):
        self.level = level  # 'K2', '3-5', '6-8'
        self.two_player = two_player
        self.round = 0
        self.deck = []
        self.table = []  # 12 cards on the table
        self.secret_pattern = None  # pattern dict
        self.patterns_for_level = []
        self.guesses_remaining = 3
        self.last_bought_indices = []
        self.init_patterns()

    def init_patterns(self):
        # Import patterns lazily to avoid circular imports
        from .patterns import PATTERNS_BY_LEVEL
        self.patterns_for_level = PATTERNS_BY_LEVEL[self.level]

    def new_round(self, chosen_pattern_id:Optional[str]=None):
        self.round += 1
        d = full_deck()
        random.shuffle(d)
        self.deck = d
        self.table = d[:12]
        # choose pattern randomly unless two-player dealer selected one
        if chosen_pattern_id:
            # allow forcing the pattern when requested (useful for UI reshuffles)
            self.secret_pattern = next((p for p in self.patterns_for_level if p['id']==chosen_pattern_id), None)
            if self.secret_pattern is None:
                # fallback to random if id not found
                self.secret_pattern = random.choice(self.patterns_for_level)
        else:
            self.secret_pattern = random.choice(self.patterns_for_level)
        self.guesses_remaining = 3
        self.last_bought_indices = []
        return self.table

    def embed_pattern_on_table(self, pattern:Dict) -> bool:
        """Try to modify the current table (using cards from the deck) so that
        the given pattern is present. Returns True if successful.

        For 'single' patterns we look for one matching card in the remainder of
        the deck and swap it into the table. For 'set' patterns we look for a
        4-card combination in the remainder of the deck and replace four cards
        on the table.
        """
        if not pattern:
            return False
        pred = pattern.get('predicate')
        ptype = pattern.get('type','single')
        # remainder of deck after the table
        rest = self.deck[12:]
        # Normalize table and rest lengths
        if len(self.table) != 12:
            # ensure table is 12 cards long by drawing from rest if possible
            needed = 12 - len(self.table)
            if needed > 0 and len(rest) >= needed:
                self.table.extend(rest[:needed])
                rest = rest[needed:]

        if ptype == 'single':
            # For single-card patterns we consider a "win" to be when there are
            # at least 4 cards on the table that match the single-card predicate.
            # Attempt to bring matching cards from the rest into the table until
            # either we have four matching table cards or we exhaust reasonable
            # attempts.
            try:
                current_matches = [i for i,c in enumerate(self.table) if pred(c)]
            except Exception:
                return False

            if len(current_matches) >= 4:
                return True

            # collect matching cards from rest
            matches = [ (idx,card) for idx,card in enumerate(rest) if pred(card) ]
            if not matches:
                return False

            # replace non-matching table positions first
            non_matching_positions = [i for i,c in enumerate(self.table) if not pred(c)]
            placed = 0
            for rest_idx, card in matches:
                if len(current_matches) + placed >= 4:
                    break
                if not non_matching_positions:
                    break
                swap_idx = non_matching_positions.pop(0)
                old = self.table[swap_idx]
                self.table[swap_idx] = card
                # mark the rest slot as the old card so deck remains consistent
                rest[rest_idx] = old
                placed += 1

            self.deck = self.table + rest
            # return True only if we successfully achieved 4 matches on table
            new_matches = [i for i,c in enumerate(self.table) if pred(c)]
            return len(new_matches) >= 4
        else:
            # look for any 4-card combo in rest that satisfies pred
            from itertools import combinations
            for combo_idxs in combinations(range(len(rest)), 4):
                combo = [rest[i] for i in combo_idxs]
                try:
                    if pred(combo):
                        # replace first four table cards (or other available)
                        replace_idxs = list(range(4))
                        for ti, ri in enumerate(replace_idxs):
                            old = self.table[ri]
                            self.table[ri] = combo[ti]
                            rest[combo_idxs[ti]] = old
                        self.deck = self.table + rest
                        # verify the pattern is present on the table now
                        return True
                except Exception:
                    continue
            return False

    def pattern_present_on_table(self, pattern:Dict) -> bool:
        """Return True if the given pattern can be satisfied by the current table.

        For 'single' patterns we require at least one card on the table to match
        the predicate. For 'set' patterns we require that there exists a 4-card
        subset of the table for which the predicate returns True.
        """
        if not pattern:
            return False
        ptype = pattern.get('type','single')
        pred = pattern.get('predicate')
        if ptype == 'single':
            # For single-type patterns we require at least four matching cards
            # to consider the pattern "present" on the table. This matches the
            # gameplay requirement that the player should be able to lay out 4
            # cards that the dealer will buy.
            try:
                match_count = sum(1 for c in self.table if pred(c))
            except Exception:
                return False
            return match_count >= 4
        else:
            # set predicate expects list[Card]; check all 4-card combinations
            for combo in itertools.combinations(self.table, 4):
                try:
                    if pred(list(combo)):
                        return True
                except Exception:
                    continue
            return False

    def submit_selection(self, selected_indices: List[int]) -> Dict:
        """
        selected_indices: indices 0..11 into self.table, must be 4 long for normal play
        Returns dict with keys: 'bought_indices', 'bought_cards', 'won_set' (bool),
         'won_round' (bool if selected 4 bought and guess correct later)
        """
        pat = self.secret_pattern
        bought_indices = []

        # basic validation: selected indices must be 1..12 and unique
        if not selected_indices or len(selected_indices) > 4:
            return {'bought_indices': [], 'bought_cards': []}
        if any(i < 0 or i >= len(self.table) for i in selected_indices):
            return {'bought_indices': [], 'bought_cards': []}

        selected = [self.table[i] for i in selected_indices]

        # Patterns can be single-card or set-based
        if pat.get('type','single') == 'single':
            # In single mode, the dealer buys any of the selected cards that
            # match the single-card predicate. The UI/game expects feedback
            # about which of the four selected cards were bought.
            for i, card in zip(selected_indices, selected):
                try:
                    if pat['predicate'](card):
                        bought_indices.append(i)
                except Exception:
                    continue
        else:
            # set predicate expects list[Card]
            try:
                if pat['predicate'](selected):
                    # buys all selected cards
                    bought_indices = list(selected_indices)
                else:
                    bought_indices = []
            except Exception:
                bought_indices = []

        # record player's last selection (indices they submitted)
        self.last_selected_indices = list(selected_indices)
        self.last_bought_indices = bought_indices
        return {
            'bought_indices': bought_indices,
            'bought_cards': [self.table[i] for i in bought_indices]
        }

    # def check_guess(self, pattern_id:str)->bool:
    #     # First check pattern id matches the secret pattern
    #     if not self.secret_pattern or self.secret_pattern.get('id') != pattern_id:
    #         # wrong pattern guessed
    #         self.guesses_remaining -= 1
    #         return False

    #     # Pattern id matches; ensure the player's last submitted selection
    #     # (self.last_bought_indices) actually corresponds to the pattern.
    #     pat = self.secret_pattern
    #     ptype = pat.get('type','single')
    #     pred = pat.get('predicate')

    #     # Prefer using the player's last submitted selection when validating
    #     # the guess. Fall back to bought indices if selected indices not set.
    #     if hasattr(self, 'last_selected_indices') and self.last_selected_indices:
    #         indices_for_check = self.last_selected_indices
    #     elif self.last_bought_indices:
    #         indices_for_check = self.last_bought_indices
    #     else:
    #         # no submission to validate against
    #         self.guesses_remaining -= 1
    #         return False

    #     # Build the selected cards list
    #     try:
    #         selected_cards = [self.table[i] for i in indices_for_check]
    #     except Exception:
    #         self.guesses_remaining -= 1
    #         return False

    #     # For single-card patterns, require that ALL of the player's selected
    #     # cards satisfy the predicate (the player should have chosen the set
    #     # of matching cards). For set patterns, require the predicate to
    #     # accept the whole selected list.
    #     try:
    #         if ptype == 'single':
    #             # require all selected cards meet the single-card predicate
    #             if len(selected_cards) > 0 and all(pred(c) for c in selected_cards):
    #                 return True
    #             else:
    #                 self.guesses_remaining -= 1
    #                 return False
    #         else:
    #             # set predicate expects list[Card]
    #             if pred(selected_cards):
    #                 return True
    #             else:
    #                 self.guesses_remaining -= 1
    #                 return False
    #     except Exception:
    #         # If predicate raises, treat as incorrect
    #         self.guesses_remaining -= 1
    #         return False


    def check_guess(self, pattern_id: str, selected_indices: Optional[List[int]] = None) -> bool:
        """
        Check whether the guess (pattern_id) is correct for the supplied selection.

        selected_indices: optional list of indices (0..len(self.table)-1) representing
                          the player's current selection at the time of guessing.
                          If provided, this selection is used for validation.
                          If not provided, falls back to last_selected_indices,
                          then last_bought_indices. If none exist, counts as incorrect.

        Returns True if the guess is correct (pattern id matches AND the selection
        satisfies the pattern predicate), otherwise decrements guesses_remaining and
        returns False.
        """
        # First check whether pattern id matches the secret pattern id
        if not self.secret_pattern or self.secret_pattern.get('id') != pattern_id:
            # wrong pattern id guessed
            self.guesses_remaining -= 1
            return False

        # Determine which indices represent the selection to validate
        if selected_indices:
            indices_for_check = list(selected_indices)
        elif hasattr(self, 'last_selected_indices') and self.last_selected_indices:
            indices_for_check = list(self.last_selected_indices)
        elif self.last_bought_indices:
            indices_for_check = list(self.last_bought_indices)
        else:
            # no selection to validate against -> wrong guess
            self.guesses_remaining -= 1
            return False

        # Ensure indices are in-range
        try:
            selected_cards = [self.table[i] for i in indices_for_check]
        except Exception:
            self.guesses_remaining -= 1
            return False

        # Validate against the pattern predicate
        pat = self.secret_pattern
        ptype = pat.get('type', 'single')
        pred = pat.get('predicate')

        try:
            if ptype == 'single':
                # require all selected cards meet the single-card predicate
                if len(selected_cards) > 0 and all(pred(c) for c in selected_cards):
                    return True
                else:
                    self.guesses_remaining -= 1
                    return False
            else:
                # set predicate expects list[Card]
                if pred(selected_cards):
                    return True
                else:
                    self.guesses_remaining -= 1
                    return False
        except Exception:
            self.guesses_remaining -= 1
            return False
