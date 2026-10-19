"""A self-contained visual novel adaptation of the supplied Vallhelm story."""

from __future__ import annotations

import argparse
import array
import json
import math
import os
import random
import queue
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path


APP_NAME = "Fifty-Six Lives"
SAVE_VERSION = 2
FLAG_NAMES = {"bond", "peace", "resolve", "family_final"}


@dataclass(frozen=True)
class Line:
    speaker: str
    text: str


@dataclass(frozen=True)
class Choice:
    text: str
    next_scene: str
    effects: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Scene:
    title: str
    backdrop: str
    cast: tuple[str, ...]
    lines: tuple[Line, ...]
    choices: tuple[Choice, ...] = ()
    next_scene: str | None = None
    ending: bool = False


@dataclass(frozen=True)
class Chapter:
    key: str
    title: str
    scene_id: str
    arc: str


ARCS = (
    "I  ·  A HERO IN A MAID'S DRESS",
    "II  ·  A BORDER OF FEAR",
    "III  ·  THE PRICE OF MIRACLES",
    "IV  ·  THE SPACE BETWEEN US",
    "V  ·  KNIVES IN THE DARK",
    "VI  ·  THE FIFTY-SIXTH DAWN",
)


STORY: dict[str, Scene] = {
    "summoning": Scene(
        "The Summoning",
        "throne",
        ("Mallory", "Mika"),
        (
            Line("Narration", "Vallhelm's court calls for a champion as the Demon Lord's armies close in. A maid appears in the summoning circle instead."),
            Line("Mika", "Before we discuss saving a kingdom, could someone point me toward a cup of coffee?"),
            Line("Mallory", "You have crossed worlds, and that is the first thing you ask?"),
        ),
        (
            Choice("Offer to help her settle in", "first_impression", {"bond": 1}),
            Choice("Ask what she can do", "first_impression", {"resolve": 1}),
        ),
    ),
    "first_impression": Scene(
        "The Wrong Hero",
        "throne",
        ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "The court's disappointment sharpens into suspicion. A captain points at the maid's untouched sleeves and calls the summoning a failure."),
            Line("King Galvath", "If the ritual brought a servant, then it has failed us."),
            Line("Mika", "I heard you. I am standing right here."),
            Line("Narration", "The nearest torch gutters out. In the darkness, something on the other side of the circle whispers Mika's name."),
        ),
        next_scene="coffee",
    ),
    "coffee": Scene(
        "A Cup Before the Storm",
        "garden",
        ("Mallory", "Mika"),
        (
            Line("Narration", "Mallory walks Mika out of the echoing throne room. She asks for a drink before asking for a miracle."),
            Line("Mallory", "Coffee is rare here. I can find you tea, and a quiet room."),
            Line("Mika", "Then tea first. Questions after."),
            Line("Narration", "A bell rings from the northern watchtower. The messenger who carried it has vanished."),
        ),
        (
            Choice("Stay close to Mallory", "knight_mistake", {"bond": 1}),
            Choice("Go see what happened at the gate", "knight_mistake", {"resolve": 1}),
        ),
    ),
    "knight_mistake": Scene(
        "The Knight's Mistake",
        "throne",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "A frightened guard mistakes Mika's calm for demonic trickery and lunges. Mika sidesteps without drawing blood."),
            Line("Lira", "Enough! She could have broken your arm. Instead, she caught your spear."),
            Line("Mika", "I know what fear makes people do. Just don't make me prove I am harmless twice."),
            Line("Narration", "The spear tip is cold with frost. Something left it pointed at the palace from outside."),
        ),
        next_scene="archive",
    ),
    "archive": Scene(
        "The Ancient Record",
        "archive",
        ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "A forgotten royal book names Mika a legendary servant summoned to protect worlds. Its pages describe fifty-five lives before this one."),
            Line("King Galvath", "Each time, your memories were wiped clean. Vallhelm is the fifty-sixth world to call you."),
            Line("Mika", "Then let this life belong to me. I will help, but I choose what home means."),
        ),
        (
            Choice("Promise she will always have a choice", "garden", {"bond": 1}),
            Choice("Ask her to defend the kingdom", "garden", {"resolve": 1}),
        ),
    ),
    "garden": Scene(
        "A Quiet Afternoon",
        "garden",
        ("Mallory", "Mika"),
        (
            Line("Narration", "Mallory leads Mika away from the council chamber. For once, nobody asks her to demonstrate a power."),
            Line("Mallory", "The palace garden is peaceful. You can stay as long as you like."),
            Line("Mika", "A quiet place, a warm drink, and no urgent prophecy. I could get used to this."),
        ),
        (
            Choice("Stay and share the quiet", "goblin_warning", {"bond": 1}),
            Choice("Check the farm's outer fence", "goblin_warning", {"resolve": 1}),
        ),
    ),
    "goblin_warning": Scene(
        "Tracks at the Orchard",
        "farm",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "The orchard fence is cut from the inside. Wet footprints lead toward the goblin road, but none lead back."),
            Line("Mallory", "Someone wants us to blame the goblins."),
            Line("Mika", "Then let's find out who benefits before we call anyone an enemy."),
            Line("Narration", "A horn sounds. Goblins have entered the farm."),
        ),
        next_scene="raid",
    ),
    "raid": Scene(
        "The Goblin Raid",
        "farm",
        ("Mika", "Gorthak", "Mallory"),
        (
            Line("Narration", "A goblin band storms the countryside. Mika shields Mallory, then notices the raiders are hungry and desperate."),
            Line("Gorthak", "Our village has nothing left. We came for food, not a war with your people."),
            Line("Mallory", "Mika, what should we do?"),
        ),
        (
            Choice("Lower your weapon and hear them out", "treaty", {"peace": 1, "bond": 1}),
            Choice("Disarm the raiders before anyone is hurt", "treaty", {"resolve": 1}),
        ),
    ),
    "treaty": Scene(
        "A Language of Understanding",
        "throne",
        ("Gorthak", "Mika", "Mallory"),
        (
            Line("Narration", "Once the danger passes, Mika asks both sides to speak. A tense meeting becomes the beginning of a real agreement."),
            Line("Gorthak", "Give our people a fair chance, and we will stand between Vallhelm and its enemies."),
            Line("Mika", "A treaty is only worth something if we keep choosing to honor it."),
        ),
        (
            Choice("Welcome the goblins as neighbors", "goblin_home", {"peace": 1, "bond": 1}),
            Choice("Accept only a cautious truce", "goblin_home", {"resolve": 1}),
        ),
    ),
    "goblin_home": Scene(
        "A Village at the Edge",
        "farm",
        ("Gorthak", "Mika", "Mallory"),
        (
            Line("Narration", "Mika follows Gorthak to Crag-Vale. Empty granaries, poisoned wells, and a royal arrow buried in the mud tell a different story than the court's reports."),
            Line("Gorthak", "We did not raid your farms until the blight took ours."),
            Line("Mika", "Then we have been fighting over the same wound."),
            Line("Narration", "A fresh arrow strikes the ground between them. Its shaft bears the king's seal."),
        ),
        next_scene="shadow",
    ),
    "shadow": Scene(
        "The Demon Lord's Shadow",
        "battle",
        ("Mika", "Mallory", "Gorthak"),
        (
            Line("Narration", "The Demon Lord's forces gather at the border. Knights, mages, and goblins prepare to defend Vallhelm together."),
            Line("Mallory", "You do not have to face the whole army by yourself."),
            Line("Mika", "I know. I just need to remember that when the fighting starts."),
        ),
        (
            Choice("Take the vanguard alone", "war_council", {"resolve": 1}),
            Choice("Make a plan with every ally", "war_council", {"bond": 1, "peace": 1}),
        ),
    ),
    "war_council": Scene(
        "The Empty Place at Council",
        "throne",
        ("King Galvath", "Mallory", "Mika", "Gorthak"),
        (
            Line("Narration", "Before the war council can agree on a plan, the king's maps are found covered in black ash. Every road leads to the same ruined valley."),
            Line("King Galvath", "The enemy is steering us toward the north."),
            Line("Mallory", "Then we choose the ground together. Mika is not a weapon we point at it."),
            Line("Narration", "From beyond the windows comes an answer in a voice older than the kingdom."),
        ),
        next_scene="sacrifice",
    ),
    "sacrifice": Scene(
        "The Cost of Victory",
        "battle",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "The battle breaks the enemy's advance. Mika spends everything she has to keep Mallory and the defenders alive."),
            Line("Mallory", "Mika, stay with us. Please."),
            Line("Narration", "The light fades. For a time, the palace believes its quietest hero is gone."),
        ),
        next_scene="grief",
    ),
    "grief": Scene(
        "After the Battle",
        "infirmary",
        ("Mallory", "Lira"),
        (
            Line("Narration", "Vallhelm mourns. Lira, once Mallory's steadfast guard, helps the princess carry on while they wait for a miracle."),
            Line("Lira", "You should not have to hold all this grief alone, Your Highness."),
            Line("Mallory", "Then stay beside me. And when Mika comes home, we will tell her together."),
        ),
        next_scene="lira_maid",
    ),
    "lira_maid": Scene(
        "The New Maid",
        "infirmary",
        ("Mallory", "Lira"),
        (
            Line("Narration", "Grief makes the days blur. To keep the palace running, Mallory asks Lira to serve as her personal maid until Mika can return."),
            Line("Mallory", "It is not a replacement. I need help, and I trust you."),
            Line("Lira", "I will wear the apron, Your Highness. But I will never pretend to be Mika."),
            Line("Narration", "Mallory pins Mika's pale ribbon beside the appointment order. The memorial candle gutters, though every window is shut."),
        ),
        next_scene="return",
    ),
    "return": Scene(
        "The Return",
        "dawn",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "At the garden memorial, Mallory and Lira speak to Mika as if she can still hear them. A soft glow gathers around the fragments of her soul."),
            Line("Mika", "Mallory, I'm all right. I could feel how much you wanted me back."),
            Line("Mallory", "You are home. This time, you do not have to be alone."),
        ),
        (
            Choice("Let them see how much you missed them", "jealousy", {"bond": 1}),
            Choice("Promise to help keep Vallhelm safe", "jealousy", {"resolve": 1}),
        ),
    ),
    "jealousy": Scene(
        "The Place Beside the Princess",
        "moon",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "A servant calls Lira the princess's new maid. Mika's smile falters. Lira is wearing the apron she used to fold each morning."),
            Line("Mika", "You found someone to take my place before I even came back."),
            Line("Narration", "The garden's pale revival light dims. Under Mika's calm voice, a familiar emptiness opens: fifty-five goodbyes, and now the fear that home has moved on without her."),
            Line("Mika", "I saved this world. Why does it feel as if I have already been erased from it?"),
            Line("Mallory", "Mika, please. Tell me what you heard."),
        ),
        (
            Choice("Admit you are terrified of being replaced", "confrontation", {"bond": 2}),
            Choice("Hide the hurt and ask about palace security", "confrontation", {"resolve": 1, "bond": -1}),
        ),
    ),
    "confrontation": Scene(
        "The Words Left Unsaid",
        "archive",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Mika", "When I heard 'new maid,' it felt like the last place in the world that was mine disappeared."),
            Line("Mallory", "I chose Lira to help me survive the grief, not to erase you. I should have told you myself."),
            Line("Lira", "I wanted to keep your place warm. I never wanted to stand in it."),
            Line("Narration", "A window slams shut though there is no wind. An ink-black handprint appears on the inside of the glass."),
            Line("Mika", "Something in this palace wants us to doubt each other."),
        ),
        next_scene="reconciliation",
    ),
    "reconciliation": Scene(
        "The Ribbon Returned",
        "garden",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Lira places Mika's pale ribbon on the table instead of putting it on. She waits for Mika to decide what it means."),
            Line("Mallory", "I want both of you here. Not as copies of one another—as yourselves."),
            Line("Mika", "I was scared. I still am. But I don't want fear choosing for me."),
            Line("Narration", "Mika ties the ribbon back into her hair. The garden lanterns flare to life one by one."),
        ),
        next_scene="trio",
    ),
    "trio": Scene(
        "Three Places at the Table",
        "garden",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Mika returns to the household by choice. Mallory keeps Lira as her maid and Mika takes charge of the palace staff; Lira remains the princess's trusted guard."),
            Line("Lira", "No one here needs to disappear for someone else to belong."),
            Line("Mika", "Then let us keep the table wide enough for all of us."),
        ),
        next_scene="assassination",
    ),
    "assassination": Scene(
        "A Threat in the Garden",
        "moon",
        ("Lira", "Mika", "Mallory"),
        (
            Line("Narration", "A hidden faction tries to strike at the royal family. Lira spots the danger first, and the three women protect one another."),
            Line("Lira", "The palace is safer when we trust each other enough to share the watch."),
            Line("Mika", "Agreed. A home is not guarded by one person alone."),
        ),
        (
            Choice("Trust Lira to lead the response", "conspiracy", {"bond": 1}),
            Choice("Use your gifts to uncover the plot", "conspiracy", {"resolve": 1}),
        ),
    ),
    "conspiracy": Scene(
        "The Hand Behind the Knife",
        "archive",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "A seized assassin carries the same false royal seal as the arrow at Crag-Vale. The plot was designed to make Vallhelm turn on its allies."),
            Line("Lira", "The trail leads below the old archive. Someone has been reading the prophecy before we have."),
            Line("Mallory", "Then we go together. No one is bait."),
            Line("Narration", "A locked door opens from the other side."),
        ),
        next_scene="healing",
    ),
    "healing": Scene(
        "The Healing Kitchen",
        "infirmary",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "The conspirators are stopped, but the battle leaves Mika's old wounds burning. She tries to hide the tremor in her hands."),
            Line("Mallory", "You don't have to be useful to deserve rest."),
            Line("Mika", "I know that when I'm thinking clearly. I forget it when everyone looks frightened."),
            Line("Lira", "Then tonight, we keep watch while you heal."),
        ),
        next_scene="prophecy",
    ),
    "prophecy": Scene(
        "The Prophecy Unfolds",
        "archive",
        ("Lira", "Mika", "Mallory"),
        (
            Line("Narration", "The old book reveals one final warning: a darkness older than the Demon Lord is drawing near."),
            Line("Lira", "I found a way to focus the magic without asking Mika to carry it all."),
            Line("Mallory", "Then we face the storm as a family, with the whole kingdom behind us."),
        ),
        next_scene="winter_vigil",
    ),
    "winter_vigil": Scene(
        "The Longest Night",
        "winter",
        ("Mika", "Mallory", "Lira", "Gorthak"),
        (
            Line("Narration", "On the eve of the black winter, the four keep watch at the garden fountain. A second shadow stands behind Mika in the water."),
            Line("Shadow", "Fifty-five times you died alone. The fifty-sixth will end the pattern."),
            Line("Mika", "You're wrong. This time, I have people who know my name."),
            Line("Narration", "The shadow smiles with Mika's own face and vanishes beneath the ice."),
        ),
        next_scene="storm",
    ),
    "storm": Scene(
        "The Gathering Storm",
        "winter",
        ("Mallory", "Mika", "Lira"),
        (
            Line("Narration", "Winter turns the sky black. Beyond the walls, a vast shadow opens over Vallhelm."),
            Line("Mika", "Fifty-six lives, and I finally know what I want to protect."),
            Line("Lira", "We are with you. The kingdom is with you."),
        ),
        (
            Choice("Stand with Mallory, Lira, and every ally", "ending_gate", {"family_final": 1, "bond": 1}),
            Choice("Take the final strike on yourself", "ending_gate", {"resolve": 1}),
        ),
    ),
    "ending_home": Scene(
        "A New Dawn",
        "dawn",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Together, they break the ancient shadow. Mika falls, but the bonds she chose shine brighter than the old cycle."),
            Line("Mallory", "You came back. You are loved, Mika. You are home."),
            Line("Mika", "As long as a fragment of me remains, I will always find my way back to you. This time, I am staying home."),
        ),
        ending=True,
    ),
    "ending_peace": Scene(
        "The Kingdom United",
        "dawn",
        ("Gorthak", "Mika", "Mallory"),
        (
            Line("Narration", "The goblin alliance turns the tide. Together, the people of Vallhelm shatter the darkness and keep their promise of peace."),
            Line("Gorthak", "Today we fought as neighbors. Let us live that way tomorrow."),
            Line("Mika", "I used to think protecting people meant standing in front of them. Now I know it can mean standing beside them."),
        ),
        ending=True,
    ),
    "ending_cycle": Scene(
        "The Fifty-Sixth Return",
        "dawn",
        ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Mika meets the darkness alone and wins, though the familiar cycle claims its price once more."),
            Line("Narration", "In the quiet that follows, Mallory and Lira refuse to let her go. Their voices guide her back to the garden."),
            Line("Mika", "I will try again. Next time, I will let you stand beside me."),
        ),
        ending=True,
    ),
}

CHAPTERS = (
    Chapter("01", "The Summoning", "summoning", ARCS[0]),
    Chapter("02", "The Wrong Hero", "first_impression", ARCS[0]),
    Chapter("03", "A Cup Before the Storm", "coffee", ARCS[0]),
    Chapter("04", "The Knight's Mistake", "knight_mistake", ARCS[0]),
    Chapter("05", "The Ancient Record", "archive", ARCS[0]),
    Chapter("06", "A Quiet Afternoon", "garden", ARCS[1]),
    Chapter("07", "Tracks at the Orchard", "goblin_warning", ARCS[1]),
    Chapter("08", "The Goblin Raid", "raid", ARCS[1]),
    Chapter("09", "A Language of Understanding", "treaty", ARCS[1]),
    Chapter("10", "A Village at the Edge", "goblin_home", ARCS[1]),
    Chapter("11", "The Demon Lord's Shadow", "shadow", ARCS[2]),
    Chapter("12", "The Empty Place at Council", "war_council", ARCS[2]),
    Chapter("13", "The Cost of Victory", "sacrifice", ARCS[2]),
    Chapter("14", "After the Battle", "grief", ARCS[2]),
    Chapter("15", "The New Maid", "lira_maid", ARCS[2]),
    Chapter("16", "The Return", "return", ARCS[3]),
    Chapter("17", "The Place Beside the Princess", "jealousy", ARCS[3]),
    Chapter("18", "The Words Left Unsaid", "confrontation", ARCS[3]),
    Chapter("19", "The Ribbon Returned", "reconciliation", ARCS[3]),
    Chapter("20", "Three Places at the Table", "trio", ARCS[3]),
    Chapter("21", "A Threat in the Garden", "assassination", ARCS[4]),
    Chapter("22", "The Hand Behind the Knife", "conspiracy", ARCS[4]),
    Chapter("23", "The Healing Kitchen", "healing", ARCS[4]),
    Chapter("24", "The Prophecy Unfolds", "prophecy", ARCS[4]),
    Chapter("25", "The Longest Night", "winter_vigil", ARCS[4]),
    Chapter("26", "The Gathering Storm", "storm", ARCS[5]),
    Chapter("27", "A New Dawn", "ending_home", ARCS[5]),
    Chapter("28", "The Kingdom United", "ending_peace", ARCS[5]),
    Chapter("29", "The Fifty-Sixth Return", "ending_cycle", ARCS[5]),
)
CHAPTER_BY_SCENE = {chapter.scene_id: chapter for chapter in CHAPTERS}
CHAPTER_MUSIC = {
    chapter.scene_id: Path("assets")
    / "chapter_music"
    / f"chapter_{chapter.key}{'.mp3' if chapter.key == '01' else '.wav'}"
    for chapter in CHAPTERS
}
SOUND_EFFECTS = (
    ("summon", "Summoning Rune"),
    ("pages", "Forbidden Pages"),
    ("garden", "Garden Fountain"),
    ("heartbeat", "Fearful Heartbeat"),
    ("footsteps", "Hallway Footsteps"),
    ("sword", "Sword Draw"),
    ("wind", "Black Winter Wind"),
    ("hope", "Return of Hope"),
)


def save_path() -> Path:
    """Return a per-user save location without writing into the install folder."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FiftySixLives" / "save.json"


def asset_path(*parts: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root.joinpath(*parts)


class BackgroundMusic:
    def __init__(self) -> None:
        try:
            import pygame
        except ImportError:
            self._pygame = None
            self._error = "Install pygame to enable MP3 playback."
            return
        self._pygame = pygame
        self._error = None
        self._loaded_track: Path | None = None

    @property
    def available(self) -> bool:
        return self._pygame is not None

    @property
    def error(self) -> str | None:
        return self._error

    def play(self, track: Path | None = None) -> None:
        if not self.available:
            raise OSError(self._error or "MP3 playback is unavailable.")
        track = track or asset_path("assets", "The Maid of Light.mp3")
        if not track.is_file():
            raise FileNotFoundError(f"Soundtrack not found: {track}")
        track = track.resolve()
        try:
            if not self._pygame.mixer.get_init():
                self._pygame.mixer.init(frequency=44100, size=-16, channels=2)
            if self._loaded_track != track:
                self._pygame.mixer.music.load(str(track))
                self._pygame.mixer.music.play(-1)
                self._loaded_track = track
            else:
                self._pygame.mixer.music.unpause()
        except self._pygame.error as error:
            raise OSError(f"Could not play the soundtrack: {error}") from error

    def stop(self) -> None:
        if self.available and self._pygame.mixer.get_init():
            self._pygame.mixer.music.pause()

    def close(self) -> None:
        if self.available and self._pygame.mixer.get_init():
            try:
                self._pygame.mixer.music.stop()
                self._pygame.mixer.quit()
            except self._pygame.error as error:
                raise OSError(f"Could not stop the soundtrack: {error}") from error


class VoiceOver:
    def __init__(self) -> None:
        try:
            import pyttsx3
        except ImportError:
            self._pyttsx3 = None
            self.available = False
            self.error = "Install the voice-over dependency with pip install -r requirements.txt."
            return
        self._pyttsx3 = pyttsx3
        self.available = True
        self.error: str | None = None
        self._requests: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="voice-over", daemon=True)
        self._thread.start()

    @staticmethod
    def _voice_for(speaker: str, voices: list[object]) -> object | None:
        names = {
            "Mika": ("zira", "aria", "jenny", "female"),
            "Mallory": ("aria", "jenny", "zira", "female"),
            "Lira": ("hazel", "zira", "aria", "female"),
            "King Galvath": ("david", "mark", "male"),
            "Gorthak": ("david", "male"),
            "Shadow": ("david", "male"),
            "Narration": ("david", "mark", "english"),
        }
        desired = names.get(speaker, ("english",))
        for keyword in desired:
            for voice in voices:
                if keyword in f"{getattr(voice, 'name', '')} {getattr(voice, 'id', '')}".lower():
                    return voice
        return voices[0] if voices else None

    def _run(self) -> None:
        try:
            if sys.platform == "win32":
                import pythoncom
                pythoncom.CoInitialize()
            engine = self._pyttsx3.init()
            engine.setProperty("rate", 168)
            engine.setProperty("volume", 0.92)
            voices = list(engine.getProperty("voices"))
            rates = {
                "Mika": 160,
                "Mallory": 177,
                "Lira": 165,
                "King Galvath": 142,
                "Gorthak": 132,
                "Shadow": 112,
                "Narration": 153,
            }
            while True:
                request = self._requests.get()
                if request is None:
                    break
                speaker, text = request
                voice = self._voice_for(speaker, voices)
                if voice is not None:
                    engine.setProperty("voice", voice.id)
                engine.setProperty("rate", rates.get(speaker, 165))
                engine.say(text, name=speaker)
                engine.runAndWait()
            engine.stop()
        except Exception as error:
            self.error = f"Offline voice-over could not start: {error}"
            self.available = False
        finally:
            if sys.platform == "win32":
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except ImportError:
                    pass

    def speak(self, speaker: str, text: str) -> None:
        if not self.available:
            return
        while True:
            try:
                self._requests.get_nowait()
            except queue.Empty:
                break
        self._requests.put((speaker, text))

    def stop(self) -> None:
        if self.available:
            while True:
                try:
                    self._requests.get_nowait()
                except queue.Empty:
                    break

    def close(self) -> None:
        if self.available:
            self._requests.put(None)


class Soundboard:
    SAMPLE_RATE = 22050

    def __init__(self, pygame_module: object | None) -> None:
        self._pygame = pygame_module
        self.error: str | None = None
        self._sounds: dict[str, object] = {}

    @property
    def available(self) -> bool:
        return self._pygame is not None

    def _make_sound(self, key: str) -> object:
        pygame = self._pygame
        if pygame is None:
            raise OSError("Sound effects require pygame.")
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
        sample_rate = pygame.mixer.get_init()[0]
        duration = 0.85 if key not in {"wind", "garden"} else 1.5
        count = int(sample_rate * duration)
        samples = array.array("h")
        rng = random.Random(key)
        for index in range(count):
            time = index / sample_rate
            progress = index / count
            envelope = min(1, progress * 18) * min(1, (1 - progress) * 8)
            if key == "summon":
                frequency = 180 + 580 * progress
                sample = math.sin(2 * math.pi * frequency * time) * 0.48 + math.sin(2 * math.pi * frequency * 2.02 * time) * 0.18
            elif key == "pages":
                sample = (rng.random() * 2 - 1) * 0.24 + math.sin(2 * math.pi * (290 + 200 * progress) * time) * 0.08
            elif key == "garden":
                sample = (rng.random() * 2 - 1) * 0.13 + math.sin(2 * math.pi * (420 + 30 * math.sin(time * 5)) * time) * 0.16
            elif key == "heartbeat":
                beat = (time % 0.62)
                pulse = math.exp(-((beat - 0.10) / 0.055) ** 2) + 0.66 * math.exp(-((beat - 0.24) / 0.065) ** 2)
                sample = math.sin(2 * math.pi * (58 + 9 * math.sin(time * 2)) * time) * pulse * 0.7
            elif key == "footsteps":
                step = (time % 0.44)
                sample = (rng.random() * 2 - 1) * math.exp(-step * 24) * 0.52
            elif key == "sword":
                frequency = 1200 - 850 * progress
                sample = math.sin(2 * math.pi * frequency * time) * 0.38 + (rng.random() * 2 - 1) * 0.16
            elif key == "wind":
                sample = (rng.random() * 2 - 1) * (0.2 + 0.3 * abs(math.sin(time * 2))) + math.sin(2 * math.pi * (68 + 20 * math.sin(time * 1.2)) * time) * 0.14
            else:
                sample = math.sin(2 * math.pi * (880 - 430 * progress) * time) * 0.3 + math.sin(2 * math.pi * 1320 * time) * 0.15
            samples.append(int(max(-1, min(1, sample * envelope)) * 26000))
        if sys.byteorder != "little":
            samples.byteswap()
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, key: str) -> None:
        if not self.available:
            self.error = "Sound effects require pygame. Install the dependencies and try again."
            return
        try:
            sound = self._sounds.get(key)
            if sound is None:
                sound = self._make_sound(key)
                self._sounds[key] = sound
            sound.play()
            self.error = None
        except self._pygame.error as error:
            self.error = f"Could not play sound effect: {error}"
        except OSError as error:
            self.error = str(error)


def ending_for(flags: dict[str, int]) -> str:
    if flags["family_final"] and flags["bond"] >= 2:
        return "ending_home"
    if flags["peace"] >= 2:
        return "ending_peace"
    return "ending_cycle"


def validate_story() -> int:
    if not STORY:
        raise ValueError("The story has no scenes.")
    for key, scene in STORY.items():
        for choice in scene.choices:
            target = ending_for({**{"bond": 0, "peace": 0, "resolve": 0, "family_final": 0}, **choice.effects}) if choice.next_scene == "ending_gate" else choice.next_scene
            if target not in STORY:
                raise ValueError(f"Scene '{key}' points to missing scene '{target}'.")
            if len(choice.effects.keys() - FLAG_NAMES):
                raise ValueError(f"Scene '{key}' uses an unknown story flag.")
            if any(not isinstance(value, int) for value in choice.effects.values()):
                raise ValueError(f"Scene '{key}' has a non-integer flag effect.")
        if scene.next_scene is not None and scene.next_scene not in STORY:
            raise ValueError(f"Scene '{key}' points to missing scene '{scene.next_scene}'.")
        if not scene.lines:
            raise ValueError(f"Scene '{key}' has no dialogue.")
        if len(scene.choices) > 3:
            raise ValueError(f"Scene '{key}' has more than three choices.")
        if scene.ending and (scene.choices or scene.next_scene):
            raise ValueError(f"Ending '{key}' must not have choices or a next scene.")
    if len(CHAPTERS) != len(STORY):
        raise ValueError("Every story scene must have exactly one chapter selection entry.")
    if len({chapter.scene_id for chapter in CHAPTERS}) != len(CHAPTERS):
        raise ValueError("Each chapter selection entry must point to a unique story scene.")
    for chapter in CHAPTERS:
        if chapter.scene_id not in STORY or chapter.arc not in ARCS:
            raise ValueError(f"Chapter '{chapter.title}' references a missing scene or arc.")
    return len(STORY)


class VisualNovel:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import messagebox

        self.tk = tk
        self.messagebox = messagebox
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1100x740")
        self.root.minsize(820, 600)
        self.canvas = tk.Canvas(self.root, bg="#101722", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.current_scene: str | None = None
        self.line_index = 0
        self.flags = self._empty_flags()
        self.undo_stack: list[dict[str, object]] = []
        self.menu = True
        self._canvas_size = (1100, 740)
        self._animated_tags: list[str] = []
        self._blink_tags: list[tuple[str, str]] = []
        self._idle_offset = 0
        self._idle_direction = -1
        self._blink_wait = random.randint(12, 20)
        self._blink_remaining = 0
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = False
        self.music = BackgroundMusic()
        self.music_enabled = self.music.available
        self.music_error: str | None = None
        self.soundboard = Soundboard(self.music._pygame)
        self.sfx_enabled = self.soundboard.available
        self.voice = VoiceOver()
        self.voice_enabled = self.voice.available
        self.voice_error: str | None = None
        self._last_spoken: tuple[str, int] | None = None
        self.highest_chapter = 0
        if self.music_enabled:
            self._start_music()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.root.bind("<Return>", lambda _event: self.advance())
        self.root.bind("<space>", lambda _event: self.advance())
        self.root.bind("<BackSpace>", lambda _event: self.go_back())
        self.root.bind("<Control-s>", lambda _event: self.save_game())
        self.root.bind("<Control-l>", lambda _event: self.load_game())
        self.root.bind("<Control-m>", lambda _event: self.toggle_music())
        self.root.bind("<Control-v>", lambda _event: self.toggle_voice())
        self.root.bind("<Control-b>", lambda _event: self.show_soundboard())
        self.root.bind("<Control-c>", lambda _event: self.show_chapter_select())
        self.root.bind("<Escape>", lambda _event: self.show_menu())
        for key, index in (("1", 0), ("2", 1), ("3", 2)):
            self.root.bind(key, lambda _event, choice_index=index: self.choose(choice_index))
        self.draw()
        self.root.after(220, self._animate_idle)
        self.root.after(400, self._poll_voice_error)

    @staticmethod
    def _empty_flags() -> dict[str, int]:
        return {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0}

    def _snapshot(self) -> dict[str, object]:
        return {
            "current_scene": self.current_scene,
            "line_index": self.line_index,
            "flags": self.flags.copy(),
            "menu": self.menu,
            "highest_chapter": self.highest_chapter,
        }

    def _remember(self) -> None:
        self.undo_stack.append(self._snapshot())
        if len(self.undo_stack) > 250:
            self.undo_stack.pop(0)

    def _restore(self, state: dict[str, object]) -> None:
        self.current_scene = state["current_scene"]  # type: ignore[assignment]
        self.line_index = int(state["line_index"])
        self.flags = dict(state["flags"])  # type: ignore[arg-type]
        self.menu = bool(state["menu"])
        self.highest_chapter = int(state.get("highest_chapter", self.highest_chapter))
        if self.music_enabled:
            self._start_music()
        self.draw()

    def new_game(self) -> None:
        self.undo_stack.clear()
        self.flags = self._empty_flags()
        self.highest_chapter = 0
        self._enter_scene("summoning")
        self.line_index = 0
        self.menu = False
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = False
        self._last_spoken = None
        self.play_scene_sfx("summoning")
        self.draw()

    def show_menu(self) -> None:
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = False
        self.menu = True
        self.voice.stop()
        self._last_spoken = None
        if self.music_enabled:
            self._start_music()
        self.draw()

    def show_credits(self) -> None:
        self.menu = True
        self.credits = True
        self.chapter_select = False
        self.soundboard_visible = False
        self.voice.stop()
        if self.music_enabled:
            self._start_music()
        self.draw()

    def show_chapter_select(self) -> None:
        self.menu = True
        self.credits = False
        self.chapter_select = True
        self.soundboard_visible = False
        self.voice.stop()
        if self.music_enabled:
            self._start_music()
        self.draw()

    def show_soundboard(self) -> None:
        self.menu = True
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = True
        self.voice.stop()
        if self.music_enabled:
            self._start_music()
        self.draw()

    def choose_chapter(self, index: int) -> None:
        if not 0 <= index <= self.highest_chapter or index >= len(CHAPTERS):
            return
        self._enter_scene(CHAPTERS[index].scene_id)
        self.line_index = 0
        self.menu = False
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = False
        self._last_spoken = None
        self.play_scene_sfx(self.current_scene or "")
        self.draw()

    def _start_music(self) -> None:
        try:
            track = CHAPTER_MUSIC.get(self.current_scene) if not self.menu and self.current_scene else None
            self.music.play(asset_path(*track.parts) if track is not None else None)
        except (OSError, FileNotFoundError) as error:
            self.music_enabled = False
            self.music_error = str(error)

    def toggle_music(self) -> None:
        if not self.music.available:
            self.music_error = self.music.error or "MP3 soundtrack playback is unavailable."
            self.draw()
            return
        if self.music_enabled:
            try:
                self.music.stop()
            except OSError as error:
                self.music_error = str(error)
                self.draw()
                return
            self.music_enabled = False
        else:
            self.music_error = None
            self.music_enabled = True
            self._start_music()
        self.draw()

    def toggle_voice(self) -> None:
        if not self.voice.available:
            self.voice_error = self.voice.error or "Offline voice-over is unavailable."
            self.draw()
            return
        self.voice_enabled = not self.voice_enabled
        self.voice.stop()
        self._last_spoken = None
        if self.voice_enabled and not self.menu:
            self._speak_current(force=True)
        self.draw()

    def toggle_sound_effects(self) -> None:
        self.sfx_enabled = not self.sfx_enabled
        if not self.sfx_enabled and self.music.available:
            self.music._pygame.mixer.stop()
        self.draw()

    def play_scene_sfx(self, scene_id: str) -> None:
        if not self.menu and scene_id in CHAPTER_MUSIC and self.music_enabled:
            self._start_music()
        if not self.sfx_enabled:
            return
        cue = {
            "summoning": "summon",
            "first_impression": "wind",
            "coffee": "garden",
            "knight_mistake": "sword",
            "archive": "pages",
            "garden": "garden",
            "goblin_warning": "footsteps",
            "raid": "sword",
            "treaty": "hope",
            "goblin_home": "wind",
            "shadow": "wind",
            "war_council": "heartbeat",
            "sacrifice": "heartbeat",
            "grief": "heartbeat",
            "lira_maid": "pages",
            "return": "hope",
            "jealousy": "heartbeat",
            "confrontation": "heartbeat",
            "reconciliation": "hope",
            "trio": "garden",
            "assassination": "sword",
            "conspiracy": "footsteps",
            "healing": "garden",
            "prophecy": "pages",
            "winter_vigil": "wind",
            "storm": "wind",
            "ending_home": "hope",
            "ending_peace": "hope",
            "ending_cycle": "heartbeat",
        }
        sound_key = cue.get(scene_id)
        if sound_key:
            self.soundboard.play(sound_key)

    def play_effect(self, key: str) -> None:
        if self.sfx_enabled:
            self.soundboard.play(key)
        self.draw()

    def _poll_voice_error(self) -> None:
        if self.voice.error and self.voice_error != self.voice.error:
            self.voice_error = self.voice.error
            self.voice_enabled = False
            self.draw()
        self.root.after(400, self._poll_voice_error)

    def _speak_current(self, force: bool = False) -> None:
        if self.menu or self.current_scene is None or not self.voice_enabled:
            return
        key = (self.current_scene, self.line_index)
        if key == self._last_spoken and not force:
            return
        self._last_spoken = key
        line = STORY[self.current_scene].lines[self.line_index]
        self.voice.speak(line.speaker, line.text)

    def close(self) -> None:
        self.voice.close()
        try:
            self.music.close()
        except OSError as error:
            self.messagebox.showerror(APP_NAME, f"Could not close the soundtrack:\n{error}")
        self.root.destroy()

    def _on_resize(self, event: object) -> None:
        width = max(820, int(getattr(event, "width", 1100)))
        height = max(600, int(getattr(event, "height", 740)))
        if (width, height) != self._canvas_size:
            self._canvas_size = (width, height)
            self.draw()

    def _on_click(self, event: object) -> None:
        item = self.canvas.find_withtag("current")
        if not item:
            return
        tags = self.canvas.gettags(item[0])
        for tag in tags:
            if tag.startswith("choice_"):
                self.choose(int(tag.split("_", 1)[1]))
                return
            if tag.startswith("chapter_"):
                chapter_key = tag.removeprefix("chapter_")
                chapter_index = next((i for i, chapter in enumerate(CHAPTERS) if chapter.key == chapter_key), None)
                if chapter_index is not None:
                    self.choose_chapter(chapter_index)
                return
            if tag.startswith("effect_"):
                self.play_effect(tag.removeprefix("effect_"))
                return
            if tag.startswith("menu_"):
                action = tag[5:]
                if action == "new":
                    self.new_game()
                elif action == "continue":
                    self.load_game()
                elif action == "chapters":
                    self.show_chapter_select()
                elif action == "soundboard":
                    self.show_soundboard()
                elif action == "credits":
                    self.show_credits()
                elif action == "sound":
                    self.toggle_music()
                elif action == "voice":
                    self.toggle_voice()
                elif action == "effects":
                    self.toggle_sound_effects()
                elif action == "back":
                    self.show_menu()
                elif action == "quit":
                    self.close()
                return
            if tag.startswith("control_"):
                action = tag[8:]
                if action == "save":
                    self.save_game()
                elif action == "back":
                    self.go_back()
                elif action == "menu":
                    self.show_menu()
                elif action == "music":
                    self.toggle_music()
                elif action == "voice":
                    self.toggle_voice()
                elif action == "effects":
                    self.toggle_sound_effects()
                elif action == "chapters":
                    self.show_chapter_select()
                elif action == "soundboard":
                    self.show_soundboard()
                return
            if tag == "advance":
                self.advance()
                return

    def _enter_scene(self, scene_id: str) -> None:
        self.current_scene = scene_id
        chapter_index = next(
            index for index, chapter in enumerate(CHAPTERS)
            if chapter.scene_id == scene_id
        )
        self.highest_chapter = max(self.highest_chapter, chapter_index)

    def _next_scene(self, target: str) -> None:
        if target == "ending_gate":
            self._enter_scene(ending_for(self.flags))
        else:
            self._enter_scene(target)
        self.line_index = 0
        self._last_spoken = None
        self.play_scene_sfx(self.current_scene or "")

    def advance(self) -> None:
        if self.menu or self.current_scene is None:
            return
        scene = STORY[self.current_scene]
        if scene.choices and self.line_index >= len(scene.lines) - 1:
            return
        self._remember()
        if self.line_index < len(scene.lines) - 1:
            self.line_index += 1
        elif scene.next_scene is not None:
            self._next_scene(scene.next_scene)
        elif scene.ending:
            self.menu = True
            self._last_spoken = None
            if self.music_enabled:
                self._start_music()
        self.draw()

    def choose(self, index: int) -> None:
        if self.menu or self.current_scene is None:
            return
        scene = STORY[self.current_scene]
        if self.line_index < len(scene.lines) - 1 or index >= len(scene.choices):
            return
        choice = scene.choices[index]
        self._remember()
        for name, value in choice.effects.items():
            self.flags[name] += value
        self._next_scene(choice.next_scene)
        self.draw()

    def go_back(self) -> None:
        if not self.undo_stack:
            return
        self._restore(self.undo_stack.pop())

    def _animate_idle(self) -> None:
        previous_offset = self._idle_offset
        self._idle_offset += self._idle_direction
        if self._idle_offset <= 0:
            self._idle_offset = 0
            self._idle_direction = 1
        elif self._idle_offset >= 2:
            self._idle_offset = 2
            self._idle_direction = -1
        for tag in self._animated_tags:
            self.canvas.move(tag, 0, previous_offset - self._idle_offset)
        if self._blink_remaining:
            self._blink_remaining -= 1
            if not self._blink_remaining:
                for eyes_tag, blink_tag in self._blink_tags:
                    self.canvas.itemconfigure(eyes_tag, state="normal")
                    self.canvas.itemconfigure(blink_tag, state="hidden")
                self._blink_wait = random.randint(12, 20)
        else:
            self._blink_wait -= 1
            if self._blink_wait <= 0:
                for eyes_tag, blink_tag in self._blink_tags:
                    self.canvas.itemconfigure(eyes_tag, state="hidden")
                    self.canvas.itemconfigure(blink_tag, state="normal")
                self._blink_remaining = 1
        self.root.after(220, self._animate_idle)

    def save_game(self) -> None:
        if self.current_scene is None or self.menu:
            self.messagebox.showinfo(APP_NAME, "Start a story before saving.")
            return
        path = save_path()
        data = {
            "version": SAVE_VERSION,
            "current_scene": self.current_scene,
            "line_index": self.line_index,
            "flags": self.flags,
            "highest_chapter": self.highest_chapter,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as error:
            self.messagebox.showerror(APP_NAME, f"Could not save your game:\n{error}")
            return
        self.messagebox.showinfo(APP_NAME, f"Game saved to:\n{path}")

    def load_game(self) -> None:
        path = save_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("The save file must contain a JSON object.")
            version = data.get("version")
            if version not in (1, SAVE_VERSION):
                raise ValueError("This save belongs to an unsupported game version.")
            scene_id = data["current_scene"]
            line_index = data["line_index"]
            flags = data["flags"]
            if not isinstance(scene_id, str) or scene_id not in STORY or type(line_index) is not int:
                raise ValueError("The save file contains an invalid story position.")
            if not 0 <= line_index < len(STORY[scene_id].lines):
                raise ValueError("The save file contains an invalid dialogue position.")
            if not isinstance(flags, dict) or set(flags) != FLAG_NAMES:
                raise ValueError("The save file contains invalid story choices.")
            if any(type(flags[name]) is not int or abs(flags[name]) > 1000 for name in FLAG_NAMES):
                raise ValueError("The save file contains invalid story choices.")
            highest_chapter = data.get(
                "highest_chapter",
                next(i for i, chapter in enumerate(CHAPTERS) if chapter.scene_id == scene_id),
            )
            scene_chapter = next(i for i, chapter in enumerate(CHAPTERS) if chapter.scene_id == scene_id)
            if (
                type(highest_chapter) is not int
                or not scene_chapter <= highest_chapter < len(CHAPTERS)
            ):
                raise ValueError("The save file contains an invalid chapter selection.")
        except FileNotFoundError:
            self.messagebox.showinfo(APP_NAME, "No saved game was found on this device.")
            return
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            self.messagebox.showerror(APP_NAME, f"Could not load the saved game:\n{error}")
            return
        self.undo_stack.clear()
        self._enter_scene(scene_id)
        self.line_index = line_index
        self.flags = flags
        self.highest_chapter = max(highest_chapter, self.highest_chapter)
        self.menu = False
        self.credits = False
        self.chapter_select = False
        self.soundboard_visible = False
        self._last_spoken = None
        self.play_scene_sfx(scene_id)
        self.draw()

    def _button(self, x: float, y: float, width: float, height: float, label: str, tag: str, font_size: int = 15) -> None:
        self.canvas.create_rectangle(
            x, y, x + width, y + height,
            fill="#1a2938", outline="#a78b58", width=1, tags=(tag,),
        )
        self.canvas.create_text(
            x + width / 2, y + height / 2, text=label,
            fill="#f4ead6", font=("Segoe UI", font_size, "bold"),
            tags=(tag,), width=width - 18,
        )

    def _draw_background(self, backdrop: str, width: int, height: int) -> None:
        palettes = {
            "throne": ("#101b31", "#815b58"),
            "archive": ("#182435", "#875f42"),
            "garden": ("#1c3441", "#55735d"),
            "farm": ("#243244", "#947447"),
            "battle": ("#101628", "#714644"),
            "infirmary": ("#26354a", "#78839a"),
            "moon": ("#10162e", "#353b61"),
            "winter": ("#090e24", "#394d6b"),
            "dawn": ("#33334f", "#d28e72"),
            "title": ("#0d1428", "#56506e"),
        }
        top, bottom = palettes.get(backdrop, palettes["title"])
        top_rgb = tuple(int(top[index:index + 2], 16) for index in (1, 3, 5))
        bottom_rgb = tuple(int(bottom[index:index + 2], 16) for index in (1, 3, 5))
        for step in range(28):
            ratio = step / 27
            color = "#" + "".join(
                f"{round(top_rgb[channel] * (1 - ratio) + bottom_rgb[channel] * ratio):02x}"
                for channel in range(3)
            )
            y1 = height * step / 28
            y2 = height * (step + 1) / 28 + 1
            self.canvas.create_rectangle(0, y1, width, y2, fill=color, outline=color)

        rng = random.Random(backdrop)
        if backdrop in {"moon", "winter", "title", "battle", "dawn"}:
            for _ in range(75):
                x, y = rng.randrange(width), rng.randrange(int(height * 0.56))
                radius = rng.choice((1, 1, 2))
                self.canvas.create_oval(x, y, x + radius, y + radius, fill="#e5d8bd", outline="")

        horizon = height * (0.47 if backdrop in {"garden", "farm"} else 0.57)
        self.canvas.create_polygon(
            0, horizon + 25, width * 0.12, horizon - 20, width * 0.28, horizon + 30,
            width * 0.46, horizon - 40, width * 0.66, horizon + 20,
            width * 0.83, horizon - 15, width, horizon + 15, width, height,
            0, height, fill="#151c2c", outline="",
        )
        if backdrop == "garden":
            wall_y = height * 0.29
            wall_bottom = height * 0.49
            self.canvas.create_rectangle(0, wall_y, width, wall_bottom, fill="#9c9279", outline="#433f3a", width=3)
            self.canvas.create_rectangle(0, wall_y + 7, width, wall_y + 14, fill="#d1c5a3", outline="")
            for x in range(-10, width + 100, max(58, width // 12)):
                self.canvas.create_rectangle(x, wall_y - 13, x + 32, wall_y + 2, fill="#887f6d", outline="#413e39", width=2)
                self.canvas.create_rectangle(x + 10, wall_y - 23, x + 22, wall_y - 13, fill="#a59b82", outline="#514a3f")
            tower_width = width * 0.105
            for tower_x in (width * 0.19, width * 0.70):
                self.canvas.create_rectangle(tower_x, height * 0.12, tower_x + tower_width, wall_y + 5, fill="#b8ae94", outline="#403d38", width=3)
                self.canvas.create_polygon(
                    tower_x - 8, height * 0.13, tower_x + tower_width / 2, height * 0.025,
                    tower_x + tower_width + 8, height * 0.13,
                    fill="#53616a", outline="#383e40", width=2,
                )
                self.canvas.create_rectangle(tower_x + tower_width * 0.42, height * 0.17, tower_x + tower_width * 0.58, wall_y - 2, fill="#283745", outline="#665e50", width=2)
                for window_y in (height * 0.19, height * 0.25):
                    self.canvas.create_oval(tower_x + tower_width * 0.43, window_y, tower_x + tower_width * 0.57, window_y + height * 0.035, fill="#384552", outline="#dbcb9f", width=2)
            arch_width = width * 0.12
            arch_height = height * 0.16
            for arch_x in range(-20, width, int(max(60, arch_width))):
                arch_top = wall_y + 26
                arch_bottom = wall_bottom - 5
                self.canvas.create_rectangle(arch_x, arch_top + arch_height * 0.5, arch_x + arch_width, arch_bottom, fill="#324149", outline="#50483c", width=3)
                self.canvas.create_arc(arch_x, arch_top, arch_x + arch_width, arch_top + arch_height, start=0, extent=180, style="arc", outline="#d3c5a3", width=5)
                self.canvas.create_line(arch_x, arch_top + arch_height * 0.5, arch_x, arch_bottom, fill="#d3c5a3", width=4)
                self.canvas.create_line(arch_x + arch_width, arch_top + arch_height * 0.5, arch_x + arch_width, arch_bottom, fill="#d3c5a3", width=4)
            water_y = height * 0.485
            self.canvas.create_rectangle(0, water_y, width, height * 0.61, fill="#3b7778", outline="")
            for band in range(7):
                wave_y = water_y + band * height * 0.017
                self.canvas.create_line(0, wave_y, width, wave_y + 4, fill=("#78b4a6", "#4d9990", "#427e83")[band % 3], width=2)
            fall_x = width * 0.32
            fall_y = height * 0.33
            self.canvas.create_polygon(
                fall_x, fall_y, fall_x + width * 0.065, fall_y,
                fall_x + width * 0.08, water_y + 5, fall_x - width * 0.015, water_y + 5,
                fill="#87c8c6", outline="#d6e7d6", width=2,
            )
            for stream_x in range(int(fall_x + 8), int(fall_x + width * 0.07), 13):
                self.canvas.create_line(stream_x, fall_y + 9, stream_x + 2, water_y, fill="#def0e1", width=2)
            self.canvas.create_oval(fall_x - 13, water_y - 4, fall_x + width * 0.1, water_y + 13, fill="#b7d7c2", outline="#e3e4c8", width=2)
            tree_x = width * 0.91
            self.canvas.create_line(tree_x, height * 0.52, tree_x - width * 0.05, height * 0.06, fill="#493a2e", width=max(9, width // 65), smooth=True)
            self.canvas.create_line(tree_x - width * 0.02, height * 0.23, tree_x - width * 0.12, height * 0.09, fill="#594435", width=max(4, width // 130), smooth=True)
            self.canvas.create_line(tree_x - width * 0.035, height * 0.18, tree_x + width * 0.04, height * 0.06, fill="#594435", width=max(4, width // 130), smooth=True)
            for leaf_index in range(30):
                leaf_x = tree_x + rng.randrange(-int(width * 0.15), int(width * 0.08))
                leaf_y = rng.randrange(-5, int(height * 0.18))
                leaf_r = rng.randrange(9, 24)
                self.canvas.create_oval(leaf_x, leaf_y, leaf_x + leaf_r, leaf_y + leaf_r * 0.65, fill=("#425c43", "#516844", "#69774a", "#314c40")[leaf_index % 4], outline="")
            for pad_x, pad_y, radius in (
                (width * 0.10, height * 0.55, 21),
                (width * 0.23, height * 0.585, 15),
                (width * 0.78, height * 0.56, 19),
                (width * 0.89, height * 0.59, 15),
            ):
                self.canvas.create_oval(pad_x - radius, pad_y - radius * 0.45, pad_x + radius, pad_y + radius * 0.45, fill="#557953", outline="#b6be79", width=2)
                self.canvas.create_arc(pad_x - radius, pad_y - radius * 0.45, pad_x + radius, pad_y + radius * 0.45, start=315, extent=90, style="arc", outline="#d6cc91", width=2)
                self.canvas.create_oval(pad_x - 5, pad_y - 19, pad_x + 5, pad_y - 9, fill="#f3e8d2", outline="#d7b7c5")
            for bank_x in (0, width * 0.86):
                for blade in range(12):
                    bx = bank_x + rng.randrange(0, max(20, int(width * 0.13)))
                    by = height * 0.59 + rng.randrange(-8, 12)
                    self.canvas.create_line(bx, by, bx + rng.randrange(-12, 13), by - rng.randrange(16, 38), fill=("#86945c", "#a2a06a", "#687d4d")[blade % 3], width=2)
        elif backdrop == "farm":
            self.canvas.create_rectangle(0, height * 0.33, width, height * 0.49, fill="#92896a", outline="#4c4a39", width=2)
            for fence_x in range(0, width, max(40, width // 20)):
                self.canvas.create_line(fence_x, height * 0.38, fence_x, height * 0.53, fill="#c2a878", width=3)
            self.canvas.create_line(0, height * 0.41, width, height * 0.41, fill="#c2a878", width=3)
            self.canvas.create_line(0, height * 0.47, width, height * 0.47, fill="#c2a878", width=3)
            barn_x = width * 0.73
            barn_y = height * 0.20
            self.canvas.create_rectangle(barn_x, barn_y + 34, barn_x + width * 0.16, height * 0.39, fill="#8a5540", outline="#443833", width=3)
            self.canvas.create_polygon(barn_x - 10, barn_y + 38, barn_x + width * 0.08, barn_y, barn_x + width * 0.17, barn_y + 38, fill="#593a39", outline="#403637", width=3)
            self.canvas.create_rectangle(barn_x + width * 0.055, height * 0.29, barn_x + width * 0.11, height * 0.39, fill="#493638", outline="#d1b180", width=2)
        elif backdrop in {"throne", "archive", "infirmary", "moon", "dawn", "title"}:
            for x in (width * 0.08, width * 0.87):
                self.canvas.create_rectangle(x, height * 0.06, x + width * 0.055, horizon + 15, fill="#25283b", outline="#b28b61", width=2)
                self.canvas.create_rectangle(x + width * 0.013, height * 0.16, x + width * 0.042, height * 0.35, fill="#d39b5c", outline="")
            self.canvas.create_polygon(width * 0.18, horizon, width * 0.31, height * 0.31, width * 0.69, height * 0.31, width * 0.82, horizon, fill="#24283e", outline="#70634f", width=2)
            if backdrop == "throne":
                self.canvas.create_polygon(width * 0.34, height, width * 0.44, height * 0.41, width * 0.56, height * 0.41, width * 0.67, height, fill="#542d3a", outline="#b59458", width=3)
                for banner_x, banner_color in ((width * 0.22, "#733c52"), (width * 0.73, "#435376")):
                    self.canvas.create_polygon(banner_x, height * 0.11, banner_x + width * 0.065, height * 0.11, banner_x + width * 0.065, height * 0.32, banner_x + width * 0.033, height * 0.37, banner_x, height * 0.32, fill=banner_color, outline="#d2b66e", width=2)
                    self.canvas.create_text(banner_x + width * 0.033, height * 0.21, text="✦", fill="#e9d58e", font=("Georgia", 22, "bold"))
                self.canvas.create_rectangle(width * 0.39, height * 0.37, width * 0.61, height * 0.47, fill="#493943", outline="#b49a6d", width=3)
                self.canvas.create_rectangle(width * 0.42, height * 0.32, width * 0.58, height * 0.40, fill="#60505a", outline="#d0b57a", width=3)
            elif backdrop == "archive":
                for shelf_x in (width * 0.06, width * 0.78):
                    self.canvas.create_rectangle(shelf_x, height * 0.12, shelf_x + width * 0.14, height * 0.48, fill="#593d34", outline="#d0ad72", width=3)
                    for shelf_y in (height * 0.20, height * 0.30, height * 0.40):
                        self.canvas.create_line(shelf_x + 5, shelf_y, shelf_x + width * 0.135, shelf_y, fill="#c59f63", width=3)
                        for book_index in range(7):
                            book_x = shelf_x + 9 + book_index * width * 0.018
                            self.canvas.create_rectangle(book_x, shelf_y - height * 0.072, book_x + width * 0.013, shelf_y - 3, fill=("#784d55", "#425c60", "#927047", "#5a5168")[book_index % 4], outline="#d1b687")
            elif backdrop == "dawn":
                sun_x, sun_y = width * 0.5, height * 0.30
                self.canvas.create_oval(sun_x - 78, sun_y - 78, sun_x + 78, sun_y + 78, fill="#e6b574", outline="#f5dba4", width=3)
                self.canvas.create_rectangle(0, height * 0.44, width, height * 0.60, fill="#62796b", outline="")
                self.canvas.create_line(0, height * 0.48, width, height * 0.48, fill="#a88b71", width=3)
            else:
                arch_color = "#777080" if backdrop == "moon" else "#82766d"
                for arch_x in (width * 0.25, width * 0.68):
                    self.canvas.create_arc(arch_x, height * 0.18, arch_x + width * 0.14, height * 0.48, start=0, extent=180, style="arc", outline=arch_color, width=5)
                    self.canvas.create_rectangle(arch_x, height * 0.33, arch_x + width * 0.14, height * 0.49, fill="#252a39", outline="")
            if backdrop in {"moon", "dawn"}:
                for candle_x in (width * 0.30, width * 0.70):
                    self.canvas.create_oval(candle_x - 12, height * 0.33, candle_x + 12, height * 0.37, fill="#f2c873", outline="")
                    self.canvas.create_oval(candle_x - 5, height * 0.29, candle_x + 5, height * 0.34, fill="#fff2bf", outline="")
        elif backdrop in {"battle", "winter"}:
            for x in range(-40, width + 80, width // 5):
                peak_y = horizon - rng.randrange(25, 110)
                self.canvas.create_polygon(x, horizon + 35, x + width * 0.12, peak_y, x + width * 0.27, horizon + 35, fill="#20263a", outline="")

    def _draw_character(self, name: str, x: float, ground: float, scale: float, width: int, index: int) -> None:
        sprite_tag = f"sprite_{index}"
        self._animated_tags.append(sprite_tag)
        eye_tag = f"{sprite_tag}_eyes"
        blink_tag = f"{sprite_tag}_blink"
        self._blink_tags.append((eye_tag, blink_tag))
        ground -= self._idle_offset
        unit = min(0.92, max(0.65, width / 1180)) * scale
        px = lambda local_x: x + local_x * unit
        py = lambda local_y: ground + local_y * unit
        extra_tags: list[str] = []
        palette = {
            "Mika": {
                "hair": "#171722", "hair_light": "#45414f", "outfit": "#22202b",
                "trim": "#f6f0e7", "skin": "#f2d8c8", "iris": "#929bab",
            },
            "Mallory": {
                "hair": "#d7a94f", "hair_light": "#f1d886", "outfit": "#7042a0",
                "trim": "#f4d56c", "skin": "#f1d7c6", "iris": "#7d65b0",
            },
            "King Galvath": {
                "hair": "#aaa0a0", "hair_light": "#ded0be", "outfit": "#591d3b",
                "trim": "#d6b84f", "skin": "#dfbda8", "iris": "#68788b",
            },
            "Lira": {
                "hair": "#c5bdcf", "hair_light": "#f0e6ef", "outfit": "#554766",
                "trim": "#c7aecf", "skin": "#efd8cb", "iris": "#8b83b5",
            },
            "Gorthak": {
                "hair": "#454d3e", "hair_light": "#76805d", "outfit": "#42573f",
                "trim": "#c8a96a", "skin": "#a0a77e", "iris": "#c99545",
            },
        }
        colors = palette.get(name, palette["Lira"])
        hair, hair_light = colors["hair"], colors["hair_light"]
        outfit, accent, skin, iris = colors["outfit"], colors["trim"], colors["skin"], colors["iris"]

        def oval(left: float, top: float, right: float, bottom: float, fill: str, outline: str = "", line_width: int = 1) -> None:
            self.canvas.create_oval(
                px(left), py(top), px(right), py(bottom), fill=fill, outline=outline,
                width=line_width, tags=(sprite_tag, *extra_tags),
            )

        def shape(points: tuple[tuple[float, float], ...], fill: str, outline: str = "", line_width: int = 1) -> None:
            coords = [coord for point in points for coord in (px(point[0]), py(point[1]))]
            self.canvas.create_polygon(
                *coords, fill=fill, outline=outline, width=line_width,
                smooth=True, splinesteps=16, tags=(sprite_tag, *extra_tags),
            )

        def stroke(points: tuple[tuple[float, float], ...], color: str, line_width: int = 1) -> None:
            coords = [coord for point in points for coord in (px(point[0]), py(point[1]))]
            self.canvas.create_line(
                *coords, fill=color, width=line_width, smooth=True,
                splinesteps=16, capstyle="round", tags=(sprite_tag, *extra_tags),
            )

        # A waist-up portrait gives the eyes and costume the scale of a VN character sprite.
        oval(-93, -34, 93, 16, "#141723")
        if name == "King Galvath":
            shape(((-84, 5), (-76, -172), (-45, -218), (45, -218), (77, -172), (86, 5)), "#47192f", "#b58f43", 2)
            shape(((-80, -174), (-49, -218), (0, -192), (50, -218), (81, -174), (47, -147), (0, -166), (-45, -147)), "#782b4a", "#e2c766", 2)
            stroke(((0, -188), (0, -26)), "#e2c766", 3)
            oval(-6, -126, 6, -114, "#d7bd68")
        else:
            shape(((-80, 8), (-72, -159), (-44, -214), (44, -214), (72, -159), (80, 8)), outfit, "#d8c9dc", 2)
            if name == "Mika":
                shape(((-36, -212), (0, -183), (36, -212), (55, 7), (-55, 7)), "#f7f4ed")
                shape(((-23, -211), (0, -187), (23, -211), (35, -120), (-35, -120)), "#282530")
                shape(((-34, -171), (0, -153), (34, -171), (55, 6), (-55, 6)), "#fffdf7", "#ddd5cc")
                shape(((-22, -174), (0, -152), (22, -174), (30, -139), (-30, -139)), "#e9e1d8")
                for frill_x in range(-44, 45, 11):
                    oval(frill_x - 4, -164, frill_x + 4, -157, "#fffdf7")
                shape(((-24, -207), (0, -186), (24, -207), (13, -179), (-13, -179)), "#f5f0e7")
                shape(((-13, -177), (0, -185), (13, -177), (0, -164)), "#262430", "#d8cbb8")
            elif name == "Mallory":
                shape(((-70, -143), (-45, -210), (0, -228), (45, -210), (70, -143), (43, -96), (0, -119), (-44, -96)), "#8a5bb4")
                shape(((-36, -207), (-17, -171), (0, -187), (17, -171), (36, -207), (14, -214), (0, -202), (-14, -214)), accent, "#fff0a5")
                oval(-5, -204, 5, -194, "#fff0a5")
            elif name == "King Galvath":
                shape(((-24, -214), (0, -191), (24, -214), (0, -170)), accent, "#fff0a5")
            else:
                shape(((-22, -210), (0, -185), (22, -210), (0, -173)), accent)

        if name == "Gorthak":
            shape(((-46, -313), (-86, -339), (-74, -285)), skin, "#697354", 2)
            shape(((46, -313), (86, -339), (74, -285)), skin, "#697354", 2)

        # Long back-hair silhouette, face, and ears.
        shape(((-54, -332), (-69, -310), (-66, -265), (-75, -223), (-61, -183), (-42, -218), (42, -218), (61, -183), (76, -225), (66, -278), (57, -322), (31, -348)), hair, "#272431", 1)
        oval(-7, -237, 7, -208, skin)
        oval(-48, -330, 48, -216, skin, "#b98d86")
        oval(-54, -289, -43, -264, skin)
        oval(43, -289, 54, -264, skin)

        # Layered fringe and side locks frame the face.
        shape(((-47, -296), (-58, -322), (-44, -345), (-20, -355), (7, -352), (38, -342), (53, -313), (45, -295), (31, -308), (21, -320), (5, -302), (-3, -322), (-19, -299), (-31, -316)), hair, "")
        shape(((-45, -300), (-48, -341), (-34, -329), (-21, -317), (-8, -326), (-20, -302), (-30, -293)), hair, "")
        shape(((35, -302), (51, -329), (48, -285), (40, -249), (29, -224), (26, -277)), hair, "")
        stroke(((-41, -328), (-27, -341), (-11, -344)), hair_light, 2)
        stroke(((8, -345), (27, -339), (39, -328)), hair_light, 2)

        if name == "Mika":
            shape(((35, -333), (43, -364), (56, -344), (49, -326)), "#f4ecdf", "#fffaf0")
            shape(((40, -339), (62, -360), (57, -331), (48, -326)), "#f4ecdf", "#fffaf0")
            oval(40, -340, 49, -331, "#eee3d3")
        elif name == "Mallory":
            shape(((-49, -309), (-57, -336), (-40, -354), (-18, -357), (0, -365), (19, -355), (42, -355), (58, -332), (49, -307), (36, -324), (16, -330), (0, -319), (-18, -331), (-34, -321)), hair, "")
            stroke(((-35, -337), (-17, -347), (-4, -349)), hair_light, 3)
            stroke(((7, -349), (25, -344), (38, -333)), hair_light, 3)
        elif name == "King Galvath":
            shape(((-48, -319), (-54, -345), (-35, -356), (-15, -350), (0, -359), (20, -350), (41, -355), (54, -333), (47, -312), (26, -324), (7, -319), (-7, -330), (-26, -318)), hair, "")
            shape(((-37, -244), (-24, -231), (0, -226), (24, -231), (36, -244), (29, -222), (12, -213), (-12, -213), (-30, -224)), "#b7a397")

        # Large anime eyes with layered irises, glints, brows and a soft smile.
        sad_expression = name == "Mika" and self.current_scene in {"grief", "sacrifice", "jealousy", "confrontation"}
        extra_tags.append(eye_tag)
        for eye_x in (-20, 20):
            if sad_expression and eye_x < 0:
                brow = ((eye_x - 13, -299), (eye_x, -293), (eye_x + 12, -301))
            elif sad_expression:
                brow = ((eye_x - 12, -301), (eye_x, -293), (eye_x + 13, -299))
            else:
                brow = ((eye_x - 13, -292), (eye_x, -299), (eye_x + 12, -292))
            stroke(brow, hair if name != "King Galvath" else "#75605a", 2)
            oval(eye_x - 14, -289, eye_x + 14, -251, "#fff8f1", "#493c48", 2)
            oval(eye_x - 9, -284, eye_x + 9, -253, iris, "")
            oval(eye_x - 5, -278, eye_x + 5, -254, "#35283b", "")
            oval(eye_x - 5, -280, eye_x + 1, -273, "#fffdf8", "")
            oval(eye_x + 2, -263, eye_x + 6, -259, "#fffdf8", "")
            stroke(((eye_x - 14, -286), (eye_x - 3, -291), (eye_x + 10, -286)), hair, 2)
            stroke(((eye_x - 13, -284), (eye_x - 17, -289)), hair, 2)
            stroke(((eye_x + 12, -284), (eye_x + 16, -289)), hair, 2)
        extra_tags.clear()
        for cheek_x in (-34, 34):
            oval(cheek_x - 6, -248, cheek_x + 6, -243, "#d99a9c")
        for eye_x in (-20, 20):
            self.canvas.create_line(
                px(eye_x - 15), py(-270), px(eye_x), py(-265), px(eye_x + 15), py(-270),
                fill=hair, width=max(1, round(2 * unit)), smooth=True,
                tags=(sprite_tag, blink_tag), state="hidden",
            )
        stroke(((-2, -251), (0, -247), (2, -251)), "#c48f86", 1)
        mouth = ((-7, -237), (0, -240), (7, -237)) if sad_expression else ((-7, -237), (0, -235), (7, -237))
        stroke(mouth, "#a45e68", 2)
        oval(-3, -239, 3, -237, "#fff2e7")
        if sad_expression:
            oval(-42, -258, -37, -246, "#b7dce8", "#fff3eb")
            oval(37, -258, 42, -246, "#b7dce8", "#fff3eb")
        if name == "King Galvath":
            shape(((-35, -239), (-27, -226), (-13, -220), (0, -224), (13, -220), (27, -226), (35, -239), (25, -215), (12, -203), (0, -200), (-12, -203), (-25, -215)), "#b7a397", "#796b69")
            stroke(((-20, -231), (-12, -226), (-5, -229)), "#75615c", 2)
            stroke(((5, -229), (12, -226), (20, -231)), "#75615c", 2)

        if name == "Mika":
            # Retain her recognizable maid silhouette, pale ribbon, dark hair and grey eyes.
            shape(((-66, -158), (-55, -177), (-38, -154), (-50, -141)), "#fffdf7", "#d7cdbf")
            shape(((66, -158), (55, -177), (38, -154), (50, -141)), "#fffdf7", "#d7cdbf")
        elif name == "Mallory":
            shape(((-35, -337), (-42, -369), (-17, -355), (0, -379), (16, -355), (42, -369), (35, -337)), "#edc94f", "#fff0a5", 2)
            oval(-5, -361, 5, -351, "#a77ac2", "#fff0a5")
            stroke(((-41, -319), (-35, -306)), "#f1d886", 3)
            stroke(((41, -319), (35, -306)), "#f1d886", 3)
        elif name == "King Galvath":
            shape(((-42, -336), (-49, -367), (-20, -352), (0, -381), (19, -352), (48, -367), (41, -336)), "#edc94f", "#fff0a5", 2)
            oval(-5, -360, 5, -350, "#ad3956", "#fff0a5")
        else:
            stroke(((-42, -317), (-33, -308), (-24, -314)), hair_light, 2)
            stroke(((42, -317), (33, -308), (24, -314)), hair_light, 2)

        if name == "Lira" and self.current_scene in {"lira_maid", "jealousy"}:
            shape(((-39, -177), (-28, -187), (0, -176), (28, -187), (39, -177), (50, -22), (-50, -22)), "#f4f0e7", "#c8bdab", 2)
            shape(((-23, -176), (0, -189), (23, -176), (18, -138), (-18, -138)), "#fffaf0", "#c8bdab")
            shape(((-11, -140), (11, -140), (24, -108), (0, -95), (-24, -108)), "#d9d1c7", "#b9ad9e")
            for frill_x in range(-43, 44, 11):
                oval(frill_x - 3, -32, frill_x + 3, -26, "#fffaf0", "#c8bdab")
            stroke(((-29, -124), (-14, -118), (0, -115), (14, -118), (29, -124)), "#d1c3b3", 1)

        if name == "Gorthak":
            stroke(((-35, -226), (-26, -214)), "#eee3cf", 3)
            stroke(((35, -226), (26, -214)), "#eee3cf", 3)

        self.canvas.create_text(
            x, ground + 15, text=name, fill="#eee5d4",
            font=("Segoe UI", 11, "bold"), tags=(sprite_tag,),
        )

    def _draw_menu(self, width: int, height: int) -> None:
        backdrop = "archive" if self.chapter_select else "winter" if self.soundboard_visible else "garden"
        self._draw_background(backdrop, width, height)
        if not self.chapter_select and not self.soundboard_visible and not self.credits:
            self._draw_coverpage(width, height)
            return
        self.canvas.create_rectangle(0, 0, width, 62, fill="#101722", outline="#c4a879", width=2)
        self.canvas.create_text(width / 2, 26, text="FIFTY-SIX LIVES", fill="#f5e9d2", font=("Georgia", max(26, width // 32), "bold"))

        if self.credits:
            self.canvas.create_rectangle(0, height * 0.59, width, height, fill="#101722", outline="#c4a879", width=2)
            self.canvas.create_text(width / 2, height * 0.65, text="CREDITS", fill="#edcf88", font=("Georgia", 21, "bold"))
            self.canvas.create_text(width / 2, height * 0.72, text="Story & Visual Novel Creator", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.77, text="James Adrian B. Castro", fill="#fff4de", font=("Georgia", 17, "bold"))
            self.canvas.create_text(width / 2, height * 0.83, text="Original soundtrack and lyrics by:", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.88, text="James Adrian B. Castro - The Maid of Light", fill="#e6d6b8", font=("Segoe UI", 13, "bold"))
            self.canvas.create_text(width / 2, height * 0.93, text="Offline generated character voices • Original story adaptation", fill="#c5c0bd", font=("Segoe UI", 9))
            self._button(width / 2 - 110, height * 0.51, 220, 34, "BACK TO TITLE", "menu_back", 10)
            self._button(width - 163, 14, 135, 34, "SOUND ON" if self.music_enabled else "SOUND OFF", "menu_sound", 9)
            return

        if self.chapter_select:
            self.canvas.create_rectangle(0, 62, width, height - 36, fill="#101722", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 82, text="CHAPTER SELECT", fill="#edcf88", font=("Georgia", 19, "bold"))
            self.canvas.create_text(width / 2, 106, text="Complete chapters to unlock what comes next. Replaying a chapter keeps your choices.", fill="#c5c0bd", font=("Segoe UI", 9))
            button_top = 133
            column_gap = 12
            column_width = (width - 46 - column_gap * 2) / 3
            for column in range(3):
                x = 18 + column * (column_width + column_gap)
                chapter_groups = (ARCS[column * 2], ARCS[column * 2 + 1])
                y = button_top
                for arc in chapter_groups:
                    self.canvas.create_text(x + 4, y, anchor="nw", text=arc, fill="#edcf88", font=("Segoe UI", 9, "bold"), width=column_width - 8)
                    y += 27
                    for chapter_index, chapter in enumerate(CHAPTERS):
                        if chapter.arc != arc:
                            continue
                        unlocked = chapter_index <= self.highest_chapter
                        label = f"{chapter.key}  {chapter.title}" if unlocked else f"{chapter.key}  LOCKED"
                        self._button(
                            x, y, column_width, 30, label,
                            f"chapter_{chapter.key}" if unlocked else f"chapter_locked_{chapter.key}", 9,
                        )
                        y += 35
                    y += 5
            self._button(width / 2 - 105, height - 33, 210, 27, "BACK TO TITLE", "menu_back", 9)
            self._button(width - 163, 14, 135, 34, "SOUND ON" if self.music_enabled else "SOUND OFF", "menu_sound", 9)
            return

        if self.soundboard_visible:
            self.canvas.create_rectangle(0, 62, width, height - 38, fill="#101722", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 91, text="VALLHELM SOUND LIBRARY", fill="#edcf88", font=("Georgia", 19, "bold"))
            self.canvas.create_text(width / 2, 120, text="Play a cue, or hear story effects as they appear during chapters.", fill="#c5c0bd", font=("Segoe UI", 10))
            columns = 2
            button_width = min(410, (width - 110) / columns)
            for index, (key, label) in enumerate(SOUND_EFFECTS):
                column, row = index % columns, index // columns
                x = (width - (2 * button_width + 16)) / 2 + column * (button_width + 16)
                y = height * 0.23 + row * 77
                self._button(x, y, button_width, 52, f"PLAY  ·  {label}", f"effect_{key}", 12)
                descriptions = {
                    "summon": "A rising ring of spell-light.",
                    "pages": "The rustle of a warning from the old archive.",
                    "garden": "A soft wash of water and garden air.",
                    "heartbeat": "A low pulse for the moments Mika cannot speak.",
                    "footsteps": "Measured footsteps in a shadowed hall.",
                    "sword": "A sharp draw before danger breaks.",
                    "wind": "The breath of the black winter.",
                    "hope": "A warm, bell-like note of return.",
                }
                self.canvas.create_text(x + button_width / 2, y + 65, text=descriptions[key], fill="#c5c0bd", font=("Segoe UI", 9))
            self.canvas.create_text(width / 2, height - 83, text=f"Sound effects: {'ON' if self.sfx_enabled else 'OFF'}  •  Music: {'ON' if self.music_enabled else 'OFF'}  •  Voice-over: {'ON' if self.voice_enabled else 'OFF'}", fill="#c5c0bd", font=("Segoe UI", 10))
            if self.music_error or self.soundboard.error or self.voice_error:
                error_text = self.music_error or self.soundboard.error or self.voice_error or ""
                self.canvas.create_text(width / 2, height - 62, text=error_text, fill="#efad9a", font=("Segoe UI", 8), width=width - 40)
            self._button(width / 2 - 105, height - 43, 210, 30, "BACK TO TITLE", "menu_back", 9)
            self._button(width - 163, 14, 135, 34, "SOUND ON" if self.music_enabled else "SOUND OFF", "menu_sound", 9)
            self._button(width - 316, 14, 140, 34, "VOICE ON" if self.voice_enabled else "VOICE OFF", "menu_voice", 9)
            self._button(width - 469, 14, 140, 34, "FX ON" if self.sfx_enabled else "FX OFF", "menu_effects", 9)
            return

        self.canvas.create_rectangle(0, height * 0.55, width, height, fill="#101722", outline="#c4a879", width=2)
        self.canvas.create_text(width / 2, height * 0.59, text="A quiet maid. Fifty-five forgotten lives. One chance to call a place home.", fill="#e7e0d5", font=("Segoe UI", 12))
        button_w, button_h = min(320, width * 0.46), 34
        start_x = (width - button_w) / 2
        actions = (
            ("NEW STORY", "new"), ("CONTINUE", "continue"),
            ("CHAPTER SELECT", "chapters"), ("SOUNDBOARD", "soundboard"),
            ("CREDITS", "credits"), ("QUIT", "quit"),
        )
        for index, (label, action) in enumerate(actions):
            y = height * 0.62 + index * 37
            self._button(start_x, y, button_w, button_h, label, f"menu_{action}", 10)
        self._button(width - 163, 14, 135, 34, "SOUND ON" if self.music_enabled else "SOUND OFF", "menu_sound", 9)
        self._button(width - 316, 14, 140, 34, "VOICE ON" if self.voice_enabled else "VOICE OFF", "menu_voice", 9)
        self._button(width - 469, 14, 140, 34, "FX ON" if self.sfx_enabled else "FX OFF", "menu_effects", 9)

    def _draw_coverpage(self, width: int, height: int) -> None:
        mika_x = width * 0.35
        self.canvas.create_oval(
            mika_x - width * 0.19, height * 0.12,
            mika_x + width * 0.19, height * 0.99,
            outline="#d5bd82", width=2,
        )
        self.canvas.create_oval(
            mika_x - width * 0.17, height * 0.14,
            mika_x + width * 0.17, height * 0.97,
            outline="#867a70", width=1,
        )
        for petal_x, petal_y, petal_size in (
            (0.14, 0.32, 10), (0.55, 0.27, 8), (0.18, 0.69, 7),
            (0.52, 0.77, 11), (0.09, 0.52, 6),
        ):
            center_x, center_y = width * petal_x, height * petal_y
            self.canvas.create_oval(
                center_x - petal_size, center_y - petal_size * 0.55,
                center_x + petal_size, center_y + petal_size * 0.55,
                fill="#f0dce2", outline="#fff1e7",
            )
        self._draw_character(
            "Mika", mika_x, height * 0.99,
            min(1.6, max(1.25, width / 700)), width, 0,
        )
        self.canvas.create_text(
            width * 0.32, height * 0.075, text="FIFTY-SIX LIVES",
            fill="#fff3df", font=("Georgia", max(27, width // 29), "bold"),
        )
        self.canvas.create_text(
            width * 0.32, height * 0.145, text="THE TALE OF MIKA AMANOGAWA",
            fill="#f0d18a", font=("Segoe UI", max(10, width // 90), "bold"),
        )
        self.canvas.create_text(
            width * 0.32, height * 0.205,
            text="One quiet maid. Fifty-five forgotten lives.\nOne chance to call a place home.",
            fill="#f7f1e6", font=("Segoe UI", max(10, width // 100)),
        )

        panel_left = width * 0.62
        panel_top = height * 0.11
        panel_right = width * 0.98
        panel_bottom = height * 0.97
        self.canvas.create_rectangle(
            panel_left, panel_top, panel_right, panel_bottom,
            fill="#101722", outline="#c4a879", width=2,
        )
        self.canvas.create_text(
            (panel_left + panel_right) / 2, panel_top + 30,
            text="CHOOSE YOUR PATH", fill="#edcf88",
            font=("Georgia", max(13, width // 65), "bold"),
        )
        button_width = panel_right - panel_left - 28
        button_height = min(42, max(34, height * 0.065))
        button_gap = min(10, max(6, height * 0.014))
        button_x = panel_left + 14
        button_y = panel_top + height * 0.17
        actions = (
            ("NEW STORY", "new"), ("CONTINUE", "continue"),
            ("CHAPTER SELECT", "chapters"), ("SOUNDBOARD", "soundboard"),
            ("CREDITS", "credits"), ("QUIT", "quit"),
        )
        for index, (label, action) in enumerate(actions):
            self._button(
                button_x, button_y + index * (button_height + button_gap),
                button_width, button_height, label, f"menu_{action}",
                max(9, width // 105),
            )
        self.canvas.create_text(
            width * 0.80, panel_bottom - 31,
            text="AN ORIGINAL STORY • AN UNEXPECTED HOME",
            fill="#c5c0bd", font=("Segoe UI", max(7, width // 140)),
        )
        toggle_width = (button_width - 12) / 3
        for index, (label, tag, enabled) in enumerate((
            ("SOUND", "menu_sound", self.music_enabled),
            ("VOICE", "menu_voice", self.voice_enabled),
            ("FX", "menu_effects", self.sfx_enabled),
        )):
            status = "ON" if enabled else "OFF"
            self._button(
                button_x + index * (toggle_width + 6), panel_top + 54,
                toggle_width, 30, f"{label} {status}", tag, max(7, width // 135),
            )

    def draw(self) -> None:
        width, height = self._canvas_size
        self.canvas.delete("all")
        self._animated_tags = []
        self._blink_tags = []
        if self.menu or self.current_scene is None:
            self._draw_menu(width, height)
            return

        scene = STORY[self.current_scene]
        self._draw_background(scene.backdrop, width, height)
        chapter = CHAPTER_BY_SCENE[self.current_scene]
        self.canvas.create_rectangle(0, 0, width, 70, fill="#101722", outline="#c4a879", width=1)
        self.canvas.create_text(24, 13, anchor="nw", text=f"ARC  {chapter.arc}", fill="#e8c779", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(24, 38, anchor="nw", text=f"CHAPTER {chapter.key}  ·  {chapter.title.upper()}", fill="#f1e5ce", font=("Segoe UI", 11, "bold"))
        controls = (
            ("CHAPTERS", "control_chapters", 80),
            ("FX", "control_soundboard", 48),
            ("VOICE ON" if self.voice_enabled else "VOICE OFF", "control_voice", 78),
            ("MUSIC", "control_music", 54),
            ("SAVE", "control_save", 54),
            ("BACK", "control_back", 54),
            ("MENU", "control_menu", 54),
        )
        total = sum(button_width for _label, _tag, button_width in controls) + 6 * (len(controls) - 1)
        x = width - total - 14
        for label, tag, button_width in controls:
            self._button(x, 18, button_width, 34, label, tag, 8)
            x += button_width + 6

        stage_ground = height * 0.57
        cast = scene.cast
        if cast:
            spacing = min(width * 0.25, 250)
            center = width / 2
            start_x = center - spacing * (len(cast) - 1) / 2
            scale = min(1.15, max(0.78, width / 1100))
            for index, name in enumerate(cast):
                self._draw_character(name, start_x + index * spacing, stage_ground, scale, width, index)

        panel_top = height * 0.62
        self.canvas.create_rectangle(0, panel_top, width, height, fill="#101722", outline="#c4a879", width=2)
        line = scene.lines[self.line_index]
        self.canvas.create_text(34, panel_top + 17, anchor="nw", text=line.speaker.upper(), fill="#d9bd82", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(
            34, panel_top + 43, anchor="nw", text=line.text,
            fill="#f3eee5", font=("Segoe UI", max(12, round(width / 73))), width=width - 68,
        )
        ready_for_choice = bool(scene.choices) and self.line_index == len(scene.lines) - 1
        if ready_for_choice:
            button_h = min(38, (height - panel_top - 105) / len(scene.choices))
            spacing = 7
            y = panel_top + 105
            for index, choice in enumerate(scene.choices):
                self._button(34, y + index * (button_h + spacing), width - 68, button_h, f"{index + 1}. {choice.text}", f"choice_{index}", 12)
        else:
            if scene.ending and self.line_index == len(scene.lines) - 1:
                label = "RETURN TO TITLE"
            else:
                label = "CONTINUE  >"
            self._button(width - 210, height - 53, 176, 35, label, "advance", 10)
        self.canvas.create_text(34, height - 21, anchor="w", text="Enter: continue   1–3: choose   Backspace: undo   Ctrl+C: chapters   Ctrl+B: soundboard   Ctrl+V: voice", fill="#aaa9a6", font=("Segoe UI", 8))
        self._speak_current()


def run() -> None:
    game = VisualNovel()
    game.root.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--validate-story", action="store_true", help="Check that all story links and choices are valid.")
    args = parser.parse_args()
    if args.validate_story:
        count = validate_story()
        print(f"Story validated: {count} scenes.")
        return 0
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
