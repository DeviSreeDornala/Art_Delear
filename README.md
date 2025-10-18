# 🎨 Art Dealer Game  
**An Educational Pattern Recognition Card Game (K–8 Learning Tool)**  

---

## 🧩 Overview  
The **Art Dealer Game** is a Python-based educational application designed to teach **pattern recognition, logic, and arithmetic reasoning** through interactive gameplay.  
Players act as “sellers” displaying cards, while the computer (“dealer”) secretly follows a hidden pattern. The player’s task is to identify this pattern by observing which cards are bought after each submission.  

Built using **Python**, **Tkinter**, and **object-oriented design**, the game provides progressive learning levels tailored for grades **K–2**, **3–5**, and **6–8**.

---

## 🎯 Key Features  
- 🃏 **Interactive 12-Card Grid** – visually engaging interface for easy card selection.  
- 💡 **Three Difficulty Levels** – pattern types scale with player grade level.  
- 🔄 **Reshuffle & Replay Options** – refresh cards without changing the pattern.  
- 🔊 **Optional Sound & Animation** – enhances engagement (via Pygame).  
- 🧠 **Educational Focus** – teaches logic, arithmetic, and observation through play.  
- 🧱 **Modular Codebase** – clean separation of UI, logic, and data patterns.  

---

## 🖥️ Tech Stack  
- **Language:** Python 3.9+  
- **GUI Framework:** Tkinter  
- **Image Handling:** Pillow (PIL)  
- **Optional Audio:** Pygame  
- **Code Architecture:** Modular OOP (UI / Logic / Patterns / Audio Utilities)

---

## 📁 Project Structure  

```
├── src/
│ ├── main.py # Entry point for launching the game
│ ├── game_logic.py # Core game mechanics and card logic
│ ├── ui.py # Tkinter-based user interface
│ ├── patterns.py # Pattern definitions by grade level
│ ├── audio_utils.py # Optional audio feedback utilities
│ ├── resource.py # Asset path resolver (works with frozen builds)
│
├── assets/
│ ├── cards/ # Card face and back images
│ ├── sounds/ # Background and feedback sounds
│
├── README.md
└── requirements.txt
```
