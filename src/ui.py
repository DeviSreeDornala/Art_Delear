# src/ui.py
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox
from .game_logic import GameState
from .patterns import PATTERNS_BY_LEVEL
from .audio_utils import say, play_music, stop_music, play_sfx
from .resource import get_asset_path
import threading

# Try to use Pillow for high-quality resizing; fallback to Tk PhotoImage subsample
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# desired card display size in pixels
CARD_W, CARD_H = 100, 140

# Simple theme colors
THEME_BG = '#f5f7fb'
PANEL_BG = '#ffffff'
ACCENT = '#4a90e2'
BTN_BG = '#e6f0ff'
HINT_BG = '#fff8e1'
TEXT_COLOR = '#222222'

# Map suit symbols used in Card.label()/Card.suit to asset folder names
SUIT_NAME_MAP = {'♥': 'hearts', '♦': 'diamonds', '♣': 'clubs', '♠': 'spades'}

# -----------------------
# Animation & visual helpers
# -----------------------
def _lerp(a, b, t):
    return a + (b - a) * t

def _hex_lerp(a_hex, b_hex, t):
    # simple hex color lerp: '#rrggbb'
    a = int(a_hex.lstrip('#'), 16)
    b = int(b_hex.lstrip('#'), 16)
    ar, ag, ab = (a >> 16) & 0xff, (a >> 8) & 0xff, a & 0xff
    br, bg, bb = (b >> 16) & 0xff, (b >> 8) & 0xff, b & 0xff
    rr = int(_lerp(ar, br, t)); rg = int(_lerp(ag, bg, t)); rb = int(_lerp(ab, bb, t))
    return f'#{rr:02x}{rg:02x}{rb:02x}'

class Animator:
    """Tiny centralized animator that schedules frame updates via root.after.
       Usage: animator.animate(duration_ms, fps, update_fn, on_done=None)
       update_fn receives t in [0..1] each frame.
    """
    def __init__(self, root):
        self.root = root
        self.jobs = set()

    def animate(self, duration_ms, fps, update_fn, on_done=None):
        total_frames = max(1, int(duration_ms * (fps / 1000.0)))
        start = 0
        self._run_frame(0, total_frames, update_fn, on_done)

    def _run_frame(self, frame, total_frames, update_fn, on_done):
        t = frame / max(1, total_frames)
        try:
            update_fn(t)
        except Exception:
            pass
        if frame < total_frames:
            jid = self.root.after(int(1000/60), lambda: self._run_frame(frame+1, total_frames, update_fn, on_done))
            self.jobs.add(jid)
        else:
            if on_done:
                try:
                    on_done()
                except Exception:
                    pass

    def cancel_all(self):
        # not tracking jids fine-grained; this cancels none. Placeholder if you extend.
        return


class CardButton(tk.Button):
    def __init__(self, master, card_label, index, callback, image=None):
        # If an image is provided, show it; otherwise fall back to text label
        if image is not None:
            # avoid forcing width/height — let the image determine button size
            super().__init__(master, image=image, bd=2, relief='raised')
        else:
            super().__init__(master, text=card_label, width=8, height=3, font=('Arial',14))
        self.index = index
        self.selected = False
        self.callback = callback
        # keep a reference to the PhotoImage so Tk doesn't garbage-collect it
        self._image_ref = image
        # style defaults
        self.default_bg = BTN_BG
        self.selected_border = '#2ecc71'  # refreshing mint green
        self.selected_bg = '#e8fff0'
        self.hover_bg = '#eef6ff'
        self.configure(command=self.on_click, bg=self.default_bg, relief='raised', bd=2, highlightthickness=0)

    def set_selected_style(self, enable: bool):
        """Apply or remove visual selection styling without changing geometry."""
        self.selected = enable
        try:
            if enable:
                self.configure(highlightthickness=4, highlightbackground=self.selected_border, relief='sunken', bg=self.selected_bg)
            else:
                self.configure(highlightthickness=0, relief='raised', bg=self.default_bg)
        except Exception:
            pass

    def on_click(self):
        # toggle selection and call the callback
        new_state = not self.selected
        self.set_selected_style(new_state)
        self.callback(self.index, new_state)
    
    def bind_hover_effects(self):
        # subtle hover: change border color and background only (no padding)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, _ev=None):
        try:
            self.configure(highlightthickness=3, highlightbackground=ACCENT)
            # slightly tint the background for hover without changing size
            if not self.selected:
                self.configure(bg=self.hover_bg)
        except Exception:
            pass

    def _on_leave(self, _ev=None):
        try:
            if not self.selected:
                self.configure(highlightthickness=0)
                # restore default background; if image present, this won't change layout
                self.configure(bg=self.default_bg)
        except Exception:
            pass

    def pop(self):
        # quick color pop without changing geometry
        try:
            orig = self.cget('bg')
            self.configure(bg='#d6eaff')
            self.after(180, lambda: self.configure(bg=orig))
        except Exception:
            pass

class ArtDealerUI:
    def __init__(self, root):
        self.root = root
        root.title("Art Dealer Game")
        try:
            root.configure(bg=THEME_BG)
        except Exception:
            pass
        # bind Escape key to exit the application
        try:
            root.bind_all('<Escape>', lambda _ev: self.exit_game())
        except Exception:
            pass
        self.state = GameState('K2', two_player=False)
        self.selected_indices = set()
        self.card_buttons = []
        self.build_level_select()

        # inside ArtDealerUI class

    def _animate_card_entry(self, btn, delay_ms=0):
        """Slide the card from slightly below into its grid cell and pop scale."""
        # compute original geometry via grid_info
        try:
            # we will use place during animation then restore grid
            info = btn.grid_info()
            widget_master = btn.master
            # get absolute position within canvas/grid
            widget_master.update_idletasks()
            x = btn.winfo_x()
            y = btn.winfo_y()
            w = btn.winfo_width()
            h = btn.winfo_height()
        except Exception:
            return

        # overlay a toplevel-like effect: use place on same master
        btn.lift()
        start_y = y + 18
        end_y = y
        start_bg = '#ffffff00'  # ignored for button; we'll animate highlight instead

        def step_fn(t):
            # ease out
            eased = 1 - (1-t)*(1-t)
            new_y = int(_lerp(start_y, end_y, eased))
            try:
                btn.place(in_=btn.master, x=x, y=new_y, width=w, height=h)
                scale = 0.92 + 0.08 * eased
                # simulate pop by adjusting border width or padding
                btn.configure(font=('Arial', int(14*scale)))
            except Exception:
                pass

        def done():
            # restore grid layout
            try:
                btn.place_forget()
                btn.grid()  # ensure grid placement is used again
                btn.configure(font=('Arial', 14))
            except Exception:
                pass

        # schedule actual animation shortly after if delay_ms
        self.root.after(delay_ms, lambda: Animator(self.root).animate(260, 60, step_fn, done))


    def build_level_select(self):
        for widget in self.root.winfo_children(): widget.destroy()
        frm = tk.Frame(self.root, padx=20,pady=20, bg=THEME_BG)
        frm.pack(expand=True,fill='both')
        tk.Label(frm, text="Choose Level", font=('Arial',20), bg=THEME_BG, fg=TEXT_COLOR).pack(pady=10)
        for lvl in ['K2','3-5','6-8']:
            b = tk.Button(frm, text=lvl, font=('Arial',16), width=12, bg=BTN_BG, fg=TEXT_COLOR, command=lambda l=lvl: self.start_game(l))
            b.pack(pady=6)
        # play menu/start sound if available
        try:
            play_sfx('start-game-sound.mp3')
        except Exception:
            pass
        # exit button on level select screen
        try:
            exit_btn = tk.Button(frm, text='Exit', font=('Arial',12), width=10, bg='#ffd6d6', command=self.exit_game)
            exit_btn.pack(pady=10)
        except Exception:
            pass

    

    def start_game(self, level):
        self.state = GameState(level, two_player=self.state.two_player)
        self.table = self.state.new_round()
        self.selected_indices = set()
        # start background loop (if available)
        try:
            play_music('game-sound-lloop.mp3', loop=True)
        except Exception:
            pass
        self.build_game_screen()

    def build_game_screen(self):
        for widget in self.root.winfo_children(): widget.destroy()
        top = tk.Frame(self.root)
        top.pack(side='top', fill='x')
        tk.Label(top, text=f"Level: {self.state.level}", font=('Arial',14)).pack(side='left', padx=10)
        self.guess_label = tk.Label(top, text=f"Guesses left: {self.state.guesses_remaining}", font=('Arial',14))
        self.guess_label.pack(side='right', padx=10)
        # make a scrollable area for the card grid to handle responsiveness
        canvas_frame = tk.Frame(self.root, bg=THEME_BG)
        canvas_frame.pack(fill='both', expand=True, padx=8, pady=8)
        canvas = tk.Canvas(canvas_frame, height=CARD_H*3 + 60, bg=THEME_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='horizontal', command=canvas.xview)
        canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side='bottom', fill='x')
        canvas.pack(side='left', fill='both', expand=True)
        grid = tk.Frame(canvas, bg=THEME_BG)
        canvas.create_window((0,0), window=grid, anchor='nw')
        self.card_buttons = []
        # ensure we have an image cache to avoid GC of PhotoImage
        if not hasattr(self, 'img_cache'):
            self.img_cache = {}

        for i, card in enumerate(self.state.table):
            r = i // 4; c = i % 4
            # map Card.rank and Card.suit to filename like 'hearts_A.png'
            suit_name = SUIT_NAME_MAP.get(card.suit, None)
            filename = None
            if suit_name:
                # ranks in assets use 'A','2',...,'10','J','Q','K'
                filename = f"{suit_name}_{card.rank}.png"
            img = None
            if filename:
                path = get_asset_path('assets', 'cards', filename)
                try:
                    if PIL_AVAILABLE:
                        pil = Image.open(path).convert('RGBA')
                        pil = pil.resize((CARD_W, CARD_H), Image.LANCZOS)
                        img = ImageTk.PhotoImage(pil)
                    else:
                        # Tk's PhotoImage may load PNG; subsample if too big
                        img = tk.PhotoImage(file=path)
                        # if image too large, calculate integral subsample
                        iw = img.width(); ih = img.height()
                        sx = max(1, int(iw / CARD_W))
                        sy = max(1, int(ih / CARD_H))
                        subs = max(sx, sy)
                        if subs > 1:
                            try:
                                img = img.subsample(subs, subs)
                            except Exception:
                                pass
                    # cache by filename
                    self.img_cache[filename] = img
                except Exception:
                    img = None

            # if specific card image missing, try a generic back image
            img_to_use = self.img_cache.get(filename)
            if img_to_use is None:
                # try cached 'card_back.png'
                back_name = 'card_back.png'
                if back_name not in self.img_cache:
                    back_path = get_asset_path('assets', 'cards', back_name)
                    try:
                        if PIL_AVAILABLE:
                            pil = Image.open(back_path).convert('RGBA')
                            pil = pil.resize((CARD_W, CARD_H), Image.LANCZOS)
                            self.img_cache[back_name] = ImageTk.PhotoImage(pil)
                        else:
                            bi = tk.PhotoImage(file=back_path)
                            iw = bi.width(); ih = bi.height()
                            subs = max(1, int(max(iw/CARD_W, ih/CARD_H)))
                            if subs > 1:
                                bi = bi.subsample(subs, subs)
                            self.img_cache[back_name] = bi
                    except Exception:
                        # no back image; leave None
                        self.img_cache[back_name] = None
                img_to_use = self.img_cache.get(back_name)

            btn = CardButton(grid, card.label(), i, self.on_card_toggle, image=img_to_use)
            btn.grid(row=r, column=c, padx=8, pady=8)
            btn.bind_hover_effects()
            # ensure consistent initial visual state
            try:
                btn.set_selected_style(False)
            except Exception:
                pass
            self.card_buttons.append(btn)

        controls = tk.Frame(self.root, pady=10)
        controls.pack()
        self.submit_btn = tk.Button(controls, text="Submit 4 cards", state='disabled', command=self.on_submit)
        self.submit_btn.grid(row=0, column=0, padx=6)
        # guess combobox
        pattern_names = [p['name'] for p in self.state.patterns_for_level]
        self.pattern_map = {p['name']:p['id'] for p in self.state.patterns_for_level}
        self.guess_combo = ttk.Combobox(controls, values=pattern_names, state='readonly', width=40)
        self.guess_combo.grid(row=0, column=1, padx=6)
        self.guess_btn = tk.Button(controls, text="Guess pattern", command=self.on_guess)
        self.guess_btn.grid(row=0, column=2, padx=6)
        self.reshuffle_btn = tk.Button(controls, text="Reshuffle", command=self.on_reshuffle)
        self.reshuffle_btn.grid(row=0, column=3, padx=6)
        self.hint_lbl = tk.Label(self.root, text="Hint: ", font=('Arial',12), anchor='w')
        self.hint_lbl.pack(fill='x', padx=14, pady=6)
        # Add an Exit button to the game controls so user can quit during play
        try:
            exit_btn = tk.Button(controls, text='Exit', font=('Arial',10), width=10, bg='#ffd6d6', command=self.exit_game)
            exit_btn.grid(row=0, column=4, padx=6)
        except Exception:
            pass
        # update canvas scroll region after layout
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        say(f"Round {self.state.round}. Pick four cards and submit.")

    def exit_game(self):
        """Cleanly exit the game: stop music, close any threads if needed, and quit TK mainloop."""
        try:
            # stop background music if playing
            stop_music()
        except Exception:
            pass
        try:
            # ensure any animator jobs are cancelled if present
            # Animator.cancel_all is a placeholder, but call if exists
            if hasattr(self, 'animator') and hasattr(self.animator, 'cancel_all'):
                try:
                    self.animator.cancel_all()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            # use quit then destroy to ensure mainloop stops
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def on_card_toggle(self, index, selected):
        if selected:
            self.selected_indices.add(index)
        else:
            self.selected_indices.discard(index)
        # enforce max 4 selection
        if len(self.selected_indices) > 4:
            # unselect the last toggled
            # simple policy: prevent selection beyond 4
            self.selected_indices.remove(index)
            btn = self.card_buttons[index]
            btn.set_selected_style(False)
            messagebox.showinfo("Too many", "Please select at most 4 cards.")
        # update submit button
        # update visuals for the toggled button
        try:
            self.card_buttons[index].set_selected_style(selected)
        except Exception:
            pass
        self.submit_btn.configure(state=('normal' if len(self.selected_indices)==4 else 'disabled'))

    def on_submit(self):
        indices = sorted(list(self.selected_indices))
        res = self.state.submit_selection(indices)
        bought = set(res['bought_indices'])
        # show visual feedback: overlay a green border for bought cards
        for i,btn in enumerate(self.card_buttons):
            if i in bought:
                # flash and highlight
                btn.configure(highlightthickness=4, highlightbackground='green')
                try:
                    # quick visual flash: change bg briefly
                    orig = btn.cget('bg')
                    btn.configure(bg='#d4ffd4')
                    btn.pop()
                    self.root.update_idletasks()
                    btn.after(300, lambda b=btn, o=orig: b.configure(bg=o))
                except Exception:
                    pass
            else:
                btn.configure(highlightthickness=0)
        # hint logic: give immediate feedback and a progressive hint when appropriate
        bought_count = len(bought)
        if bought_count == 4 and self.state.secret_pattern.get('type','single')=='single':
            # perfect selection; prompt for guess
            say("All four were bought! Make your guess.")
            self.hint_lbl.configure(text="All 4 bought! Now guess the pattern.")
        elif bought_count==4 and self.state.secret_pattern.get('type','set')=='set':
            say("The dealer bought all four cards — the set condition matched. Make a guess.")
            self.hint_lbl.configure(text="All 4 bought (set matched). Now guess the pattern.")
        else:
            # give the number-of-matches feedback first to help narrow possibilities
            say(f"{bought_count} card(s) bought this turn.")
            if bought_count > 0:
                self.hint_lbl.configure(text=f"{bought_count} card(s) matched. Use that to refine your next pick.")
            else:
                self.hint_lbl.configure(text=f"No cards matched. Try a different selection.")
        self.guess_label.configure(text=f"Guesses left: {self.state.guesses_remaining}")
        # play a mild feedback sound on submit
        try:
            play_sfx('start-game-sound.mp3')
        except Exception:
            pass

    def on_reshuffle(self):
        """User-requested reshuffle: deal a new table but preserve the secret pattern
        when possible so the user can try again without the game changing the rule.
        This gives the player freedom to reshuffle when the right pattern isn't
        present on the current table.
        """
        # remember current pattern id if any
        old_pid = None
        if self.state.secret_pattern and isinstance(self.state.secret_pattern, dict):
            old_pid = self.state.secret_pattern.get('id')

        # Try to reshuffle while preserving the secret pattern and ensuring the
        # pattern is present on the table. We'll attempt up to 2 times to get a
        # table that contains the pattern (so the user has a chance to find it).
        attempts = 0
        max_attempts = 3  # initial attempt + up to 2 retries
        restored = None
        while attempts < max_attempts:
            self.table = self.state.new_round(chosen_pattern_id=old_pid)
            # if we had an old pattern id, make sure secret_pattern references it
            if old_pid:
                restored = next((p for p in self.state.patterns_for_level if p.get('id')==old_pid), None)
                if restored:
                    self.state.secret_pattern = restored
            # if the pattern is present on the new table, we're done
            if self.state.pattern_present_on_table(self.state.secret_pattern):
                break
            attempts += 1

        # optional reshuffle sfx
        try:
            play_sfx('start-game-sound.mp3')
        except Exception:
            pass
        # if after attempts pattern is still not present, try to embed it into
        # the current table by swapping cards from the deck (best-effort)
        if not self.state.pattern_present_on_table(self.state.secret_pattern):
            try:
                embedded = self.state.embed_pattern_on_table(self.state.secret_pattern)
                if embedded:
                    # update local table reference
                    self.table = self.state.table
            except Exception:
                pass

        # reset selections and redraw the screen
        self.selected_indices = set()
        self.build_game_screen()

    def on_guess(self):
        selection = self.guess_combo.get()
        if not selection:
            messagebox.showinfo("Choose", "Choose a pattern from the list to guess.")
            return
        pid = self.pattern_map[selection]
        correct = self.state.check_guess(pid)
        if correct:
            # stop background and play win sound
            try:
                stop_music()
                play_sfx('win-sound.mp3')
            except Exception:
                pass
            self.win_sequence(selection)
        else:
            # incorrect guess feedback
            try:
                play_sfx('start-game-sound.mp3')
            except Exception:
                pass
            say(f"Incorrect. You have {self.state.guesses_remaining} guesses left.")
            self.guess_label.configure(text=f"Guesses left: {self.state.guesses_remaining}")
            # progressive hints from the pattern definitions
            hints = self.state.secret_pattern.get('hints', []) if self.state.secret_pattern else []
            # guesses_remaining just decreased if wrong; show hints based on how many left
            if self.state.guesses_remaining == 2:
                # first pattern-specific hint
                if hints:
                    self.hint_lbl.configure(text=f"Hint: {hints[0]}")
                else:
                    self.hint_lbl.configure(text=f"Hint: {self.state.secret_pattern.get('desc','')}")
            elif self.state.guesses_remaining == 1:
                # second, stronger hint
                if len(hints) > 1:
                    self.hint_lbl.configure(text=f"Hint: {hints[1]}")
                elif hints:
                    self.hint_lbl.configure(text=f"Hint: {hints[0]}")
                else:
                    self.hint_lbl.configure(text=f"Hint: {self.state.secret_pattern.get('desc','')}")
            elif self.state.guesses_remaining <= 0:
                # final reveal
                try:
                    stop_music()
                    play_sfx('lose-sound.mp3')
                except Exception:
                    pass
                messagebox.showinfo("Out of guesses", f"Out of guesses. The pattern was: {self.state.secret_pattern['name']}")
                self.build_level_select()

    def win_sequence(self, selection_name):
        say("Correct! You won this round.")
        messagebox.showinfo("You Win!", f"Correct! The pattern was: {selection_name}. Balloons!")
        self.build_level_select()
