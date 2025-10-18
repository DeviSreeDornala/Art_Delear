# src/audio_utils.py
"""Audio utilities.

The project originally used pyttsx3 for text-to-speech. The user asked to remove
the sound. To keep imports working but disable audio, `say()` is implemented as
a no-op. If you later want to re-enable audio, restore the pyttsx3 import and
the implementation below.
"""

# Initially provide the historical say() no-op for compatibility
def say(text: str):
    return


# Optional music/sound support using pygame.mixer. If pygame is not
# available, the functions below become no-ops so the app still runs.
try:
    import pygame
    # Initialize mixer lazily when first used to avoid requiring SDL/display
    pygame.init()
    try:
        pygame.mixer.init()
        PYGAME_AVAILABLE = True
    except Exception:
        PYGAME_AVAILABLE = False
except Exception:
    PYGAME_AVAILABLE = False

_music_channel = None

def _sound_path(filename: str) -> str:
    # Use resource helper so paths work when frozen
    try:
        from .resource import get_asset_path
        return get_asset_path('assets', 'sounds', filename)
    except Exception:
        import os
        base = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'sounds'))
        return os.path.join(base, filename)

def play_music(filename: str, loop: bool = False):
    if not PYGAME_AVAILABLE:
        return
    try:
        path = _sound_path(filename)
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1 if loop else 0)
    except Exception:
        pass

def stop_music():
    if not PYGAME_AVAILABLE:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

def play_sfx(filename: str):
    if not PYGAME_AVAILABLE:
        return
    try:
        path = _sound_path(filename)
        s = pygame.mixer.Sound(path)
        s.play()
    except Exception:
        pass
