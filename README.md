# Fifty-Six Lives

A small, self-contained visual novel adaptation of the story supplied as a PDF. It follows Mika's summoning, the goblin treaty, her return to Mallory and Lira, and the final storm. Dialogue is newly written and condensed for play; the original PDF is not bundled.

The game is written in Python, uses Tkinter for its interface, pygame for soundtrack and sound effects, and pyttsx3 for optional offline dialogue voice-over. The supplied illustration is not copied into the game: it informs the original character and scenery designs. The title screen is a Mika Amanogawa cover page, with an original anime-inspired portrait in a code-drawn castle garden; her sprites blink and gently bob during play. Story locations include the garden fountain, throne room, archive, goblin farm, and moonlit palace. Character dialogue uses locally installed computer voices, with voices selected by character where possible and distinct speaking rates. The exact available voices depend on the player's system.

The original `assets\The Maid of Light.mp3` soundtrack and lyrics were created by James Adrian B. Castro and play on loop in the title screen. The **CREDITS** screen credits him for the original soundtrack and lyrics. Each numbered chapter has its own soundtrack in `assets\chapter_music`; its track loops during that chapter, and the title music resumes when you return to the menu. The eight soundboard effects also play automatically as story cues. Offline character voice-over can be switched on or off with **VOICE ON/OFF** or `Ctrl+V`. The exact voices depend on the voices installed on the player's Windows system.

A prebuilt Windows app is available from the [latest GitHub release](https://github.com/phantom-nightmare-code/fifty-six-lives-visual-novel/releases/latest).

The story has six title arcs and 29 selectable chapters. Chapters unlock as you play and unlocked chapters can be replayed. One chapter explores Mika's despair when she returns and discovers Mallory has asked Lira to serve as her new maid.

## Run from source

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). On Windows, enable **Add Python to PATH** in the installer.
2. Open a terminal in this folder and install the audio and voice-over dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Start the game:

   ```powershell
   python main.py
   ```

On Windows, offline speech uses installed SAPI voices. If compatible speech voices are unavailable, the game and soundboard still work; voice-over can be switched off.

## Build a Windows app

1. Install Python 3.10 or newer.
2. Double-click `build_windows.bat`, or run it from PowerShell.
3. When it finishes, share `dist\FiftySixLives.exe`. The title soundtrack and all 29 chapter tracks are bundled into the executable; characters and original scenery are drawn by the game. The recipient does not need Python installed or a separate assets folder. The original-quality WAV chapter tracks make the executable approximately 600 MB larger than the earlier release.

The first build needs an internet connection to install PyInstaller. For a distributable release, zip the `.exe` and include this README. Windows SmartScreen may show a warning for an unsigned app; code signing is optional and requires a certificate.

## Controls and saves

- Click a choice or press `1`, `2`, or `3`.
- Press `Enter` or `Space` to advance dialogue.
- Press `Backspace` or click **BACK** to undo the last step.
- Click **SAVE** or press `Ctrl+S`; choose **CONTINUE** from the title screen to load.
- Click **SOUND** to toggle the soundtrack.
- Use **VOICE ON/OFF** or `Ctrl+V` to enable or mute offline character dialogue.
- Open **SOUNDBOARD** or press `Ctrl+B` for the eight generated sound effects.
- Open **CHAPTER SELECT** or press `Ctrl+C` to replay unlocked chapters grouped by title arc.
- Choose **CREDITS** on the title screen to see the credits and soundtrack thanks.
- Click **MENU** to return to the title screen.

Save data is stored in the current user's application-data folder: `%LOCALAPPDATA%\FiftySixLives\save.json` on Windows, `~/Library/Application Support/FiftySixLives/save.json` on macOS, and `$XDG_DATA_HOME/FiftySixLives/save.json` (or `~/.local/share/FiftySixLives/save.json`) on Linux.

Choices shape Mika's bonds, the goblin alliance, and the ending. To check the story graph without opening the window, run `python main.py --validate-story`.
