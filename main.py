"""A self-contained visual novel adaptation of the supplied Vallhelm story."""

from __future__ import annotations

import argparse
import array
import datetime
import json
import math
import os
import random
import queue
import re
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

APP_NAME = "Echoes of the Fifty Six Worlds"
SUBTITLE = "Requiem of the Maid"
SAVE_VERSION = 6
FLAG_NAMES = {"bond", "peace", "resolve", "family_final", "reputation"}

def get_save_path(slot: int) -> Path:
    if os.name == "nt": base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin": base = Path.home() / "Library" / "Application Support"
    else: base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FiftySixLives" / f"save_{slot}.json"

RESET_COUNT_FILE = get_save_path(1).parent / "reset_meta.json"
RESET_COUNT = 0

def load_meta():
    global RESET_COUNT
    if RESET_COUNT_FILE.exists():
        try:
            RESET_COUNT = json.loads(RESET_COUNT_FILE.read_text(encoding="utf-8")).get("count", 0)
        except Exception:
            pass

def save_meta():
    RESET_COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESET_COUNT_FILE.write_text(json.dumps({"count": RESET_COUNT}), encoding="utf-8")

@dataclass(frozen=True)
class Line:
    speaker: str
    text: str | tuple[str, ...]

@dataclass(frozen=True)
class Choice:
    text: str
    next_scene: str | None
    effects: dict[str, int] = field(default_factory=dict)
    outcome_lines: tuple[Line, ...] = ()

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

def resolve_text(text: str | tuple[str, ...], flags: dict[str, int]) -> str:
    if isinstance(text, str): return text
    if RESET_COUNT > 0 and len(text) == 4:
        return text[3]
    rep = flags.get("reputation", 0)
    if rep >= 2: return text[0]
    elif rep <= -2: return text[2]
    else: return text[1]

STORY: dict[str, Scene] = {
    "summoning": Scene(
        "The Summoning", "throne", ("Mallory Valerius", "Mika Amanogawa"),
        (
            Line("Narration", "The grand hall of Vallhelm is suffocatingly silent, save for the crackling hum of the ancient summoning circle etched into the marble floor. The air is thick with the scent of ozone, burning sage, and the cold sweat of desperate men."),
            Line("Narration", "King Galvath Valerius stands at the edge of the circle, his knuckles white as he grips the armrest of his throne. The Demon Lord's armies are a day's march away, and the kingdom's last hope rests on this forbidden ritual."),
            Line("Narration", "A flash of blinding, golden light erupts from the center of the runes. The shockwave knocks the royal mages off their feet, sending ancient scrolls fluttering into the air. When the smoke clears, the entire court gasps in unison."),
            Line("Narration", "Instead of a towering, armored warrior, a young woman stands in the center of the circle. She is wearing a simple, black-and-white maid's uniform, holding a feather duster like a sword. Her name is Mika Amanogawa."),
            Line("Mika Amanogawa", "Whoa! What the—? Where am I? One minute I'm scrubbing a stubborn coffee stain out of a hotel carpet, and the next I'm in a fantasy LARPing convention. Why is everyone staring at me like I just grew a second head?"),
            Line("King Galvath Valerius", "A servant! The prophecy promised a champion to save us from the abyss, and the heavens send us a scullery maid with a duster! The heavens mock us! Do they think a duster can parry a demon blade?"),
            Line("Narration", "Murmurs of panic ripple through the court. The royal mages exchange terrified glances. The circle had responded, but to what? To whom?"),
            Line("Mika Amanogawa", "Look, buddy, I don't know who you are or where this is, but I'm just as confused as you are. And frankly, I'd like to go back to my hotel. I have a schedule."),
            Line("Narration", "Mika takes a tentative step forward, her shoes clicking against the marble. She feels the hum of magic beneath her feet, a strange warmth that seems to recognize her."),
        ),
        (
            Choice(
                text="Step forward and offer to help her", 
                next_scene="first_impression", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mallory Valerius", (
                        "Father, please! Silence! The circle responded to her. The magic recognized her soul. We cannot dismiss her just because she doesn't look like a knight.",
                        "Father, please! Silence! The circle responded to her. The magic recognized her soul. We cannot dismiss her just because she doesn't look like a knight.",
                        "Father, please! Silence! The circle responded to her. The magic recognized her soul. We cannot dismiss her just because she doesn't look like a knight.",
                        "Father, please! Silence! But... why do I feel like I've seen her before? Something about her eyes... it terrifies me. Yet, we must not dismiss her."
                    )),
                    Line("Narration", "A young woman with tired, kind eyes steps forward from the shadows of the throne. Princess Mallory Valerius, the King's eldest daughter, looks at Mika not with disgust, but with desperate curiosity."),
                    Line("Mika Amanogawa", "Thanks for the save. I'm Mika, by the way. Mika Amanogawa. Nice to meet someone here who isn't immediately yelling at me."),
                    Line("Mallory Valerius", "I am Mallory. And I have a feeling we are going to need each other if we are going to survive this. Welcome to Vallhelm, Mika."),
                )
            ),
            Choice(
                text="Stand your ground and demand respect", 
                next_scene="first_impression", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika Amanogawa", "I can hear you, you know. I'm standing right here. And for the record, I've handled worse messes than a few angry soldiers. Have you ever cleaned up after a royal banquet?"),
                    Line("Narration", "The court gasps at her defiance. The King's face turns crimson with rage, and the guards tighten their grip on their weapons. The air grows cold."),
                    Line("Mallory Valerius", "Silence! The circle responded to her. We cannot dismiss her just because she doesn't look like a knight. Stand down! I will not have bloodshed in the summoning chamber!"),
                )
            ),
            Choice(
                text="Stay silent and observe the court", 
                next_scene="first_impression", 
                effects={"resolve": 1, "reputation": 0},
                outcome_lines=(
                    Line("Narration", "Mika narrows her eyes, saying nothing. She takes in the panicked nobles, the trembling mages, and the furious King. She catalogs every exit, every weapon."),
                    Line("King Galvath Valerius", "Nothing to say for yourself? A silent servant is at least better than a babbling one. Guards, take her to the dungeons until we can figure out this mess."),
                    Line("Mallory Valerius", "No! Father, I will vouch for her. If the magic brought her here, she is our responsibility. I will take her to the gardens to speak."),
                )
            ),
            Choice(
                text="Inspect the summoning circle", 
                next_scene="first_impression", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "Hold on. Look at these runes. They're not just a summoning circle. They're a binding spell. You didn't just call me here, you trapped me."),
                    Line("King Galvath Valerius", "What? That's impossible! The ritual was supposed to bring a champion!"),
                    Line("Mallory Valerius", "She's right. I can see the binding threads. Father, what have you done? She's not a guest, she's a prisoner. We owe her our apologies and our help."),
                )
            ),
        ),
    ),
    "first_impression": Scene(
        "The Wrong Hero", "throne", ("King Galvath Valerius", "Mallory Valerius", "Mika Amanogawa"),
        (
            Line("Narration", "The court's disappointment sharpens into suspicion. A seasoned captain of the guard steps forward, pointing his spear directly at Mika's untouched sleeves."),
            Line("King Galvath Valerius", "If the ritual brought a servant, then it has failed us. We need a champion who can wield a blade, not someone to dust the throne room while the kingdom burns."),
            Line("Mika Amanogawa", "I'm right here, you know. I have a name. It's Mika. And honestly, I'm just as confused as you are. But pointing weapons at people is a terrible way to make a first impression."),
            Line("Narration", "The tension in the room is palpable. The guards look nervous, their eyes darting between the King and the strange woman in the circle."),
        ),
        (
            Choice(
                text="Apologize and try to explain", 
                next_scene="coffee", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "Look, I don't know how I got here, but I'm not your enemy. I was just doing my job, and now I'm here. I just want to figure out how to go home without anyone getting hurt."),
                    Line("Narration", "The King hesitates, his expression softening slightly at her calm, rational tone. He lowers his hand, signaling the guards to stand down."),
                    Line("Mallory Valerius", "Let us speak in the gardens, away from this hostility. Please, follow me. We have much to discuss."),
                )
            ),
            Choice(
                text="Tell the King to shut up", 
                next_scene="coffee", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika Amanogawa", "Maybe if your kingdom wasn't such a mess, the heavens wouldn't have sent a maid. Ever think of that? Maybe try cleaning up your own messes for once."),
                    Line("Narration", "The guards tighten their grip on their weapons. The air grows cold, and the nearest torch gutters out. The King's face twists with fury."),
                    Line("Mallory Valerius", "Guards, to me! We need to get her out of here before this turns into a bloodbath. Father, please, let me handle this."),
                )
            ),
            Choice(
                text="Point out the flaws in their defense", 
                next_scene="coffee", 
                effects={"resolve": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "Instead of pointing spears at me, maybe you should point them at the Demon Lord. Look at this formation! If I were attacking this castle, I'd hit the east wall. It's completely undefended."),
                    Line("Narration", "The captain of the guard blinks, looking at the map on the wall, then back at Mika. His jaw drops."),
                    Line("Mallory Valerius", "She's right. The east wall is our weakest point. Perhaps the prophecy sent us someone who thinks before she fights. Follow me, Mika."),
                )
            ),
            Choice(
                text="Ask for a weapon to prove yourself", 
                next_scene="coffee", 
                effects={"resolve": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "You want a champion? Give me a sword. I'll fight your best guard right here, right now."),
                    Line("King Galvath Valerius", "You? A maid? Fine. If you win, I will listen. If you lose, you go to the dungeons."),
                    Line("Narration", "Mika picks up a guard's sword, her hands surprisingly steady. She disarms the guard in three swift movements, leaving him on the floor."),
                    Line("Mallory Valerius", "Impressive. You didn't just win, you did it without drawing blood. I think we found our champion."),
                )
            ),
        ),
    ),
    "coffee": Scene(
        "A Cup Before the Storm", "garden", ("Mallory Valerius", "Mika Amanogawa"),
        (
            Line("Narration", "Mallory walks Mika out of the echoing throne room and into the quiet, sprawling palace gardens. The night air is cool and carries the sweet scent of night-blooming jasmine."),
            Line("Narration", "They sit on a stone bench near a gently bubbling fountain. The distant sound of the panicked court fades away, replaced by the chirping of crickets."),
            Line("Mallory Valerius", (
                "I apologize for my father. He is terrified. We all are. Vallhelm has always relied on prophecy, and now that the prophecy is here... we forgot how to fight for ourselves. But I am not ready to give up on you yet.",
                "I apologize for my father. He is terrified. We all are. Vallhelm has always relied on prophecy, and now that the prophecy is here... we forgot how to fight for ourselves. But I am not ready to give up on you yet.",
                "I apologize for my father. He is terrified. We all are. Vallhelm has always relied on prophecy, and now that the prophecy is here... we forgot how to fight for ourselves. But I am not ready to give up on you yet.",
                "I apologize for my father... But I can't help but feel a strange sense of dread around you. Like I shouldn't trust you. Like I've seen you do terrible things."
            )),
            Line("Narration", "Mallory pours a cup of steaming tea from a silver pot, handing it to Mika. The warmth seeps into Mika's cold fingers."),
        ),
        (
            Choice(
                text="Offer to help her anyway", 
                next_scene="market", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "It's okay. I'm used to people underestimating me. Let me see what I can do to help. I might not be a knight, but I'm a fast learner. And I'm great at organizing."),
                    Line("Narration", "Mallory smiles, a genuine, tired smile that reaches her eyes. She reaches out and gently squeezes Mika's hand."),
                    Line("Mallory Valerius", "You are a rare soul, Mika. Thank you. Truly."),
                )
            ),
            Choice(
                text="Demand to be sent home immediately", 
                next_scene="market", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika Amanogawa", "I don't care about your war or your prophecies. I want to go home. Now. Find a way to send me back."),
                    Line("Mallory Valerius", "I... I don't know how to send you back. The ritual only works one way. It binds you to us."),
                    Line("Mika Amanogawa", "Then find a way. Or I'll find it myself."),
                )
            ),
            Choice(
                text="Ask her about the history of the ritual", 
                next_scene="market", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "This ritual... has it been used before? Who wrote it? There has to be a loophole, a reason why it brought me here."),
                    Line("Mallory Valerius", "The archives are sealed, but I can get us in. If anyone can figure out the true nature of the summoning, it's you. I'll help you find the truth."),
                    Line("Narration", "Mika nods. For the first time, she feels a sliver of hope. Not just of going home, but of understanding why she was chosen."),
                )
            ),
            Choice(
                text="Warn her about the upcoming war", 
                next_scene="market", 
                effects={"resolve": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika Amanogawa", "The Demon Lord's armies are a day's march away. Your father is panicking. You need a plan, not a prophecy. I can help you strategize."),
                    Line("Mallory Valerius", "You'd help us? Even after my father threatened you?"),
                    Line("Mika Amanogawa", "I don't abandon people in need. It's not in my nature. Even if I am wearing a maid's dress."),
                )
            ),
        ),
    ),
    "market": Scene(
        "The City Market", "garden", ("Mallory Valerius", "Mika Amanogawa"),
        (
            Line("Narration", "Before the sun rises, Mallory disguises herself in a heavy, worn cloak and takes Mika into the lower city. The streets are damp with morning fog, and the market is bustling, but a thick layer of fear hangs in the air."),
            Line("Narration", "The people are thin, their faces gaunt. The war has taken its toll on the kingdom's poorest."),
            Line("Mika Amanogawa", "The people are scared. I used to clean rooms for people who never looked me in the eye. It's strange, being the one everyone is staring at now."),
            Line("Narration", "A small child, distracted by the commotion, bumps into Mika, dropping a woven basket of apples. The fruit scatters across the muddy cobblestones."),
        ),
        (
            Choice(
                text="Help the child gather the apples", 
                next_scene="knight_mistake", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Oh! Careful there, little one. Let me help you. Don't want these delicious apples getting bruised."), 
                    Line("Narration", "Mika kneels in the mud, her pristine maid's uniform getting dirty as she gathers the apples. The child stares at her in awe."),
                    Line("Mallory Valerius", "You care for them already. You have a gentle heart, Mika. A rare thing in these dark times."),
                )
            ),
            Choice(
                text="Ignore the child and keep walking", 
                next_scene="knight_mistake", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Watch where you're going. I don't have time for this."), 
                    Line("Mallory Valerius", "That was cold, Mika. These are my people. They are suffering."),
                )
            ),
            Choice(
                text="Buy the child's entire basket of apples", 
                next_scene="knight_mistake", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Here, let me buy the rest. You shouldn't be out here in this cold anyway. Go home to your family."),
                    Line("Narration", "Mika presses a few silver coins into the child's hand. The child's eyes go wide, and they run off, beaming."),
                    Line("Mallory Valerius", "You gave her more than enough to feed her family for a week. You didn't have to do that."),
                    Line("Mika Amanogawa", "I know. But I wanted to."),
                )
            ),
            Choice(
                text="Ask the merchant about the food shortage", 
                next_scene="knight_mistake", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Why is everything so expensive? The crops should be ready for harvest."),
                    Line("Merchant", "The King's soldiers took most of it. Said it was for the war effort. We're starving, but the nobles eat like kings."),
                    Line("Mallory Valerius", "That's... not right. My father wouldn't allow this."),
                    Line("Mika Amanogawa", "Someone is, Mallory. And we need to find out who."),
                )
            ),
        ),
    ),
    "knight_mistake": Scene(
        "The Knight's Mistake", "throne", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"),
        (
            Line("Narration", "Back at the palace, tensions boil over. A frightened, young guard, believing Mika's intervention at the market was demonic manipulation, lunges at her with a spear."),
            Line("Narration", "Mika doesn't flinch. She pivots on her heel, sidestepping the thrust by a hair's breadth, grabs the wooden shaft of the spear, and snaps it in two with a sharp twist of her wrist."),
            Line("Lira Vanguard", "Enough! Stand down, soldier! Stand down! She could have broken your arm. Instead, she disarmed you without drawing a drop of blood. That takes skill."),
            Line("Narration", "A tall, imposing woman with silver armor and a scarred face steps forward. This is Lira Vanguard, Captain of the Royal Guard."),
        ),
        (
            Choice(
                text="Forgive the guard", 
                next_scene="archive", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I know what fear makes people do. It's okay. Let's just make sure it doesn't happen again."), 
                    Line("Lira Vanguard", "You have my respect, Maid. I am Lira, Captain of the Royal Guard."),
                )
            ),
            Choice(
                text="Threaten the guard", 
                next_scene="archive", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If he tries that again, I won't be so gentle. Tell your men to stay out of my way."), 
                    Line("Lira Vanguard", "Watch your tongue, Maid. You are not in charge here."),
                )
            ),
            Choice(
                text="Ask Lira about the guard's training", 
                next_scene="archive", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If your men are this jumpy, the Demon Lord won't even need to fight. They'll rout themselves."),
                    Line("Lira Vanguard", "You're right. They are terrified. We all are. But seeing you disarm him without a scratch... it gives them pause. Maybe there's hope for us yet."),
                )
            ),
            Choice(
                text="Inspect the broken spear", 
                next_scene="archive", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Wait a minute. This spear... it's not standard issue. The metal is too heavy, the balance is wrong."),
                    Line("Lira Vanguard", "You noticed? It's a ceremonial weapon. We're running out of actual weapons. The treasury has been drained."),
                    Line("Mika Amanogawa", "Drained? By who?"),
                    Line("Lira Vanguard", "That's the question, isn't it? Follow me, Maid. We need to talk to the Princess."),
                )
            ),
        ),
    ),
    "archive": Scene(
        "The Ancient Record", "archive", ("King Galvath Valerius", "Mallory Valerius", "Mika Amanogawa"),
        (
            Line("Narration", "King Galvath, humbled but still suspicious, summons the three women to the restricted section of the royal archives. The room smells of old paper, ozone, and dust."),
            Line("Narration", "He opens a massive, ancient tome bound in dragon leather. The pages glow with a faint, ethereal light."),
            Line("King Galvath Valerius", "This book names you, Mika Amanogawa. It describes fifty-five lives before this one. Each time, your memories were wiped clean. You are a cosmic pawn. A weapon to be spent and discarded."),
            Line("Mika Amanogawa", "Fifty-five lives? You mean I've done this before? I've died before? Fifty-five times?"),
            Line("Narration", "The weight of the revelation hits Mika like a physical blow. Her hands tremble, her mind reeling with the implication of countless deaths."),
        ),
        (
            Choice(
                text="Accept the responsibility", 
                next_scene="training", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Then let this life belong to me. I will help you, but I choose what home means. No more wiping my memories."), 
                    Line("Mallory Valerius", "Thank you, Mika. We will stand by you."),
                )
            ),
            Choice(
                text="Refuse the prophecy", 
                next_scene="training", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I am not a pawn. I won't be your sacrifice. Find someone else to do your dirty work."), 
                    Line("Mallory Valerius", "Please, Mika. We need you. The whole world needs you."),
                )
            ),
            Choice(
                text="Demand to know how to break the cycle", 
                next_scene="training", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If this has happened fifty-five times, how did it end? Did I fail? Did I win? Tell me everything."),
                    Line("King Galvath Valerius", "The book... it stops at the fifty-fifth page. The rest is blank. No one knows what happens next."),
                    Line("Mika Amanogawa", "Then I'll write my own ending. One that doesn't involve me dying."),
                )
            ),
            Choice(
                text="Read the margins of the book", 
                next_scene="training", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika ignores the King and peers closely at the faded writing in the margins. Her eyes widen."),
                    Line("Mika Amanogawa", "These aren't just records. They're notes. From me. Past me. She wrote... 'Don't trust the King. He knows more than he says.'"),
                    Line("Mallory Valerius", "Father? Is this true?"),
                    Line("King Galvath Valerius", "I... I don't know what that means. The book is ancient!"),
                    Line("Mika Amanogawa", "It means the cycle is rigged. And I'm going to break it."),
                )
            ),
        ),
    ),
    "training": Scene(
        "Sparring with Lira", "throne", ("Mika Amanogawa", "Lira Vanguard"), 
        (
            Line("Narration", "The training yard is filled with the harsh clang of steel. Lira is a whirlwind of precision and grace, her sword cutting through the air. Mika, however, is struggling to adjust to the weight of a real blade."), 
            Line("Lira Vanguard", "Your strength is incredible, Mika, but your footwork is sloppy! You fight like you're holding a mop!"), 
            Line("Mika Amanogawa", "A mop can be pretty dangerous if you know how to swing it! I once fought off a drunk noble with a bucket of soapy water!"),
            Line("Narration", "Despite the taunts, Mika is learning fast. Her movements, while unorthodox, carry a raw, devastating power."),
        ), 
        (
            Choice(
                text="Help Lira up", 
                next_scene="garden", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Lira laughs, a genuine, warm sound. She lunges again, but Mika anticipates it. She sweeps Lira's leg with the flat of her blade, knocking the captain into the dirt."), 
                    Line("Mika Amanogawa", "Good match, Captain."), 
                    Line("Lira Vanguard", "You are full of surprises, Maid. Perhaps you really are the hero the prophecy spoke of."),
                )
            ), 
            Choice(
                text="Gloat over her", 
                next_scene="garden", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika disarms Lira with a swift strike, sending her sword clattering to the ground."), 
                    Line("Mika Amanogawa", "Not so tough now, are you, Captain?"), 
                    Line("Lira Vanguard", "Don't push your luck, Maid. I was going easy on you."),
                )
            ),
            Choice(
                text="Ask Lira for a real fight", 
                next_scene="garden", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Stop holding back. I need to know what it feels like to fight someone who actually wants to kill me."),
                    Line("Narration", "Lira's eyes widen, then harden. She nods. The next exchange is brutal, leaving Mika bruised and breathless, but she doesn't yield."),
                    Line("Lira Vanguard", "You are a glutton for punishment. But... I think you might actually survive this war."),
                )
            ),
            Choice(
                text="Ask Lira about her scar", 
                next_scene="garden", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "That scar on your face. Where did you get it?"),
                    Line("Lira Vanguard", "The border. Three years ago. A demon took my eye, but I took its head. I earned this scar."),
                    Line("Mika Amanogawa", "It's a badge of honor. You're a true warrior."),
                    Line("Lira Vanguard", "And you, Maid, are a quick learner. You'll be a warrior yet."),
                )
            ),
        )
    ),
    "garden": Scene(
        "A Quiet Afternoon", "garden", ("Mallory Valerius", "Mika Amanogawa"), 
        (
            Line("Narration", "Days pass in relative peace, a calm before the inevitable storm. Mallory leads Mika to a hidden garden behind the palace walls, overgrown with wild roses and ivy."), 
            Line("Mallory Valerius", "The palace garden is peaceful. No one will bother you here. This was my mother's favorite place."), 
            Line("Mika Amanogawa", "It's beautiful. A quiet place, a warm drink, and no urgent prophecy. I could get used to this."),
            Line("Narration", "They sit together, watching the butterflies dance among the flowers. For a moment, the war feels a thousand miles away."),
        ), 
        (
            Choice(
                text="Open up to Mallory", 
                next_scene="goblin_warning", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika smiles softly, the first genuine smile she has shown since arriving. They spend hours talking about her world, her small apartment, her love of cleaning, and the peaceful, mundane life she left behind."), 
                    Line("Mika Amanogawa", "I used to think my life was boring. Just waking up, going to work, coming home. But now... I'd give anything for one boring Tuesday."), 
                    Line("Mallory Valerius", "You make this place feel like home too, Mika."),
                )
            ), 
            Choice(
                text="Keep your distance", 
                next_scene="goblin_warning", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika stares at the roses, refusing to meet Mallory's eyes."), 
                    Line("Mika Amanogawa", "I'm not here to make friends, Mallory. I'm here because I have to be."), 
                    Line("Mallory Valerius", "I see. I'm sorry for prying."),
                )
            ),
            Choice(
                text="Ask Mallory about her mother", 
                next_scene="goblin_warning", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "What was she like? Your mother?"),
                    Line("Mallory Valerius", "She was strong. Stronger than my father. She used to tell me that true strength isn't about swinging a sword. It's about knowing when to put it down."),
                    Line("Narration", "Mallory's eyes water, but she doesn't cry. Mika quietly places a hand on her shoulder, offering silent comfort."),
                )
            ),
            Choice(
                text="Pick a rose for Mallory", 
                next_scene="goblin_warning", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika carefully cuts a single wild rose, pricking her finger on a thorn in the process."),
                    Line("Mika Amanogawa", "Ouch. Here. For you. A queen should have a flower."),
                    Line("Mallory Valerius", "You're bleeding..." ),
                    Line("Mika Amanogawa", "It's just a scratch. Don't worry about it."),
                    Line("Mallory Valerius", "Thank you, Mika. I'll treasure it."),
                )
            ),
        )
    ),
    "goblin_warning": Scene(
        "Tracks at the Orchard", "farm", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "The royal orchard on the outskirts of the city is in ruins. The wooden fence is cut from the inside. Wet footprints lead toward the goblin road, but none lead back."), 
            Line("Mika Amanogawa", "This wasn't an attack from the outside. Look at the cut. Someone from the city cut this from the inside and dragged the scouts out."), 
            Line("Lira Vanguard", "We should report this to the King immediately. This is high treason."),
        ), 
        (
            Choice(
                text="Investigate quietly", 
                next_scene="raid", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If we report this, the King will just send an army. Then the real traitor wins. We need to find out who benefits before we call anyone an enemy. We need evidence."), 
                    Line("Mallory Valerius", "Agreed. We do this your way, Mika."),
                )
            ), 
            Choice(
                text="Report to the King", 
                next_scene="raid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Let the army handle it. That's what they're paid for, right?"), 
                    Line("Lira Vanguard", "As you wish. I will inform His Majesty immediately."),
                )
            ),
            Choice(
                text="Follow the tracks alone", 
                next_scene="raid", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'm going to follow the tracks. You two stay here and cover for me."),
                    Line("Lira Vanguard", "Are you insane? You'll be captured or killed!"),
                    Line("Mika Amanogawa", "I've died fifty-five times. I'm not afraid of the dark anymore."),
                    Line("Narration", "Mika disappears into the woods before they can stop her."),
                )
            ),
            Choice(
                text="Analyze the footprints", 
                next_scene="raid", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Look at the prints. They're heavy, dragging. And they're wearing boots. City boots. Not goblin feet."),
                    Line("Lira Vanguard", "You can read tracks?"),
                    Line("Mika Amanogawa", "I clean up messes. You learn to tell who made them."),
                    Line("Mallory Valerius", "Someone from the palace did this. Someone with access to the King's boots."),
                )
            ),
        )
    ),
    "raid": Scene(
        "The Goblin Raid", "farm", ("Mika Amanogawa", "Gorthak Stonefist", "Mallory Valerius"), 
        (
            Line("Narration", "A goblin band storms the countryside, setting fire to the wheat fields. Mika shields Mallory, raising her broken spear to fight. But as the smoke clears, she notices the raiders are not warriors, but refugees."), 
            Line("Gorthak Stonefist", "Our village has nothing left! The blight took our crops, and the king's soldiers poisoned our wells! We came for food, not a war with your people!"), 
            Line("Mallory Valerius", "Mika, what should we do? If we attack, we prove we're monsters. If we don't, they'll take everything."),
        ), 
        (
            Choice(
                text="Hear them out", 
                next_scene="treaty", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika drops her weapon to the mud. The silence that follows is deafening. Gorthak stares at her, bewildered by her courage."), 
                    Line("Mika Amanogawa", "Put down your weapons. All of you. We can settle this without bloodshed."), 
                    Line("Gorthak Stonefist", "Why should we trust you? You are human."), 
                    Line("Mika Amanogawa", "Because I'm the only one here who has seen enough death. Fifty-five lifetimes of it. I'm not looking for more."),
                )
            ), 
            Choice(
                text="Attack", 
                next_scene="treaty", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika charges forward, her broken spear flashing in the firelight. The goblins scatter, terrified by her ferocity."), 
                    Line("Mika Amanogawa", "Drive them back! Show them what happens when they threaten Vallhelm!"), 
                    Line("Gorthak Stonefist", "We will remember this, human! We will remember!"),
                )
            ),
            Choice(
                text="Offer them a place in the palace kitchens", 
                next_scene="treaty", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If you're hungry, I know a place. The palace throws away more food in a day than you could eat in a month. Work for us, and you won't have to raid."),
                    Line("Gorthak Stonefist", "You would offer a goblin work? You are either very brave or very foolish."),
                    Line("Mallory Valerius", "Perhaps a little of both. But it's a better offer than a spear to the chest."),
                )
            ),
            Choice(
                text="Ask about the poisoned wells", 
                next_scene="treaty", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Wait. You said the King's soldiers poisoned your wells. Where did they do it? What did the poison look like?"),
                    Line("Gorthak Stonefist", "It was black ash. It burned the water. It came from a councilman with a dark artifact."),
                    Line("Mika Amanogawa", "A councilman... Mallory, we need to get to the archives. Now."),
                )
            ),
        )
    ),
    "treaty": Scene(
        "A Language of Understanding", "throne", ("Gorthak Stonefist", "Mika Amanogawa", "Mallory Valerius"), 
        (
            Line("Narration", "Once the danger passes, Mika forces both sides to sit at the negotiating table. The tension in the throne room is thick enough to cut with a knife."), 
            Line("Gorthak Stonefist", "Give our people a fair chance, and we will stand between Vallhelm and its enemies. We are warriors, not thieves."), 
            Line("King Galvath Valerius", "You expect me to ally with goblins? They have raided our lands for generations! My father died fighting them!"),
        ), 
        (
            Choice(
                text="Push for peace", 
                next_scene="goblin_home", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "And you expect me to fight for a kingdom that would let children starve over a grudge? A treaty is only worth something if we keep choosing to honor it."), 
                    Line("Mallory Valerius", "Mika is right, Father. The real enemy is at our borders. We need Gorthak's army."), 
                    Line("Gorthak Stonefist", "You are a strange human, Mika. You fight like a demon, but you speak like an angel."),
                )
            ), 
            Choice(
                text="Suggest a truce", 
                next_scene="goblin_home", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'm not saying we hold hands and sing songs. I'm saying we accept a temporary truce until the Demon Lord is defeated."), 
                    Line("King Galvath Valerius", "A temporary measure. Nothing more. Do not expect me to break bread with them."), 
                    Line("Gorthak Stonefist", "Cautious. But acceptable."),
                )
            ),
            Choice(
                text="Threaten the King", 
                next_scene="goblin_home", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "You can either fight the goblins and the Demon Lord at the same time, or you can swallow your pride and accept their help. Choose wisely."),
                    Line("Narration", "The King's face goes white. He looks at Mallory, then back at Mika, and slumps into his throne."),
                    Line("King Galvath Valerius", "...Fine. A truce. But I will not forgive them."),
                )
            ),
            Choice(
                text="Reveal the King's betrayal", 
                next_scene="goblin_home", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Father, why don't you tell them what you did? The poisoned wells? The black ash?"),
                    Line("King Galvath Valerius", "What? I did no such thing!"),
                    Line("Gorthak Stonefist", "The human lies. We saw the councilman. Vane Blackwood. He wore the King's seal."),
                    Line("Mika Amanogawa", "Then someone in this room is lying. And it's not the goblins."),
                )
            ),
        )
    ),
    "goblin_home": Scene(
        "A Village at the Edge", "farm", ("Gorthak Stonefist", "Mika Amanogawa", "Mallory Valerius"), 
        (
            Line("Narration", "Mika follows Gorthak to Crag-Vale, a goblin village nestled in the jagged mountains. It is a ruin of empty granaries, poisoned wells, and crying children. The smell of rot is overwhelming."), 
            Line("Gorthak Stonefist", "We did not raid your farms until the blight took ours. We were desperate. We are dying."), 
            Line("Mika Amanogawa", "Then we have been fighting over the same wound. Someone poisoned your wells, cut our fences, and killed our scouts. They wanted this war."),
        ), 
        (
            Choice(
                text="Sympathize", 
                next_scene="shadow", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "A sudden whistle cuts through the air. An arrow strikes the ground between them, vibrating with force. Its shaft bears the king's seal."), 
                    Line("Mika Amanogawa", "Look at the shaft. It bears the king's seal. But he wouldn't... this is a forgery. We'll fix this, Gorthak. I promise."), 
                    Line("Gorthak Stonefist", "Thank you, Mika. You are different from the others."),
                )
            ), 
            Choice(
                text="Demand answers", 
                next_scene="shadow", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "A sudden whistle cuts through the air. An arrow strikes the ground between them, vibrating with force."), 
                    Line("Mika Amanogawa", "Who did this? Who poisoned your wells? Tell me what you know!"), 
                    Line("Gorthak Stonefist", "We don't know! We are not your enemy, but you are making it very hard to remember that!"),
                )
            ),
            Choice(
                text="Offer to heal the sick children", 
                next_scene="shadow", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'm not a doctor, but I know a thing or two about cleaning up messes. Let me help the children while we talk."),
                    Line("Narration", "Mika spends hours washing wounds and boiling water. The goblins watch her with a mixture of confusion and awe."),
                    Line("Gorthak Stonefist", "You have the hands of a healer and the heart of a warrior. Perhaps we have been wrong about humans."),
                )
            ),
            Choice(
                text="Inspect the poisoned well", 
                next_scene="shadow", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "This isn't blight. It's alchemy. Someone did this on purpose."),
                    Line("Gorthak Stonefist", "Can you fix it?"),
                    Line("Mika Amanogawa", "I can try. But I'll need the help of the royal mages."),
                    Line("Mallory Valerius", "I'll convince my father. We owe your people this much."),
                )
            ),
        )
    ),
    "shadow": Scene(
        "The Demon Lord's Shadow", "battle", ("Mika Amanogawa", "Mallory Valerius", "Gorthak Stonefist"), 
        (
            Line("Narration", "The Demon Lord's forces gather at the border. A massive army of dark knights, wraiths, and fire-breathing beasts stretches across the horizon, blotting out the sun."), 
            Line("Narration", "Knights, mages, and goblins stand shoulder to shoulder, preparing to defend Vallhelm together. The air smells of ozone, ash, and fear."), 
            Line("Mallory Valerius", "You do not have to face the whole army by yourself. We are with you. Vallhelm is with you."),
        ), 
        (
            Choice(
                text="Lead together", 
                next_scene="war_council", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I know. I just need to remember that when the fighting starts. Fear makes people do terrible things. But it can also make them brave."), 
                    Line("Gorthak Stonefist", "My people will hold the left flank. Show them the strength of a champion, Maid. We fight as one!"),
                )
            ), 
            Choice(
                text="Lead alone", 
                next_scene="war_council", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I can handle this. I've done it before. Just make sure the civilians are safe."), 
                    Line("Mallory Valerius", "Be careful, Mika. Please. Don't do anything reckless."),
                )
            ),
            Choice(
                text="Propose a diversionary tactic", 
                next_scene="war_council", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "We don't need to meet them head-on. Gorthak, can your people create a diversion at the gorge while we flank them?"),
                    Line("Gorthak Stonefist", "Aye. We are quick and quiet. We can draw them into the valley."),
                    Line("Mallory Valerius", "Brilliant. We'll catch them in a crossfire."),
                )
            ),
            Choice(
                text="Inspect the enemy's formation", 
                next_scene="war_council", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Look at the center. It's too thin. They're trying to bait us into a trap. If we strike the flanks and push inward, we can surround them."),
                    Line("Lira Vanguard", "She's right. It's a classic envelopment tactic."),
                    Line("Mallory Valerius", "We'll trust your eyes, Mika. Let's do it."),
                )
            ),
        )
    ),
    "war_council": Scene(
        "The Empty Place at Council", "throne", ("King Galvath Valerius", "Mallory Valerius", "Mika Amanogawa", "Gorthak Stonefist"), 
        (
            Line("Narration", "Before the war council can agree on a plan, the king's maps are found covered in black ash. Every road leads to the same ruined valley, a death trap."), 
            Line("King Galvath Valerius", "The enemy is steering us toward the north. It's a trap. We have no choice but to spring it."), 
            Line("Mallory Valerius", "Then we choose the ground together. Mika is not a weapon we point at it. We fight as one, or we don't fight at all."),
        ), 
        (
            Choice(
                text="Plan together", 
                next_scene="sacrifice", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "If we're walking into a trap, we make sure we spring it on our terms. We use the valley's terrain to our advantage."), 
                    Line("Mallory Valerius", "Smart. We'll coordinate the mages to provide cover."),
                )
            ), 
            Choice(
                text="Charge in", 
                next_scene="sacrifice", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "We attack now. We don't give them time to fortify their positions."), 
                    Line("King Galvath Valerius", "Reckless! You will get us all killed!"),
                )
            ),
            Choice(
                text="Suggest a retreat to draw them out", 
                next_scene="sacrifice", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "We retreat. We give them the valley. And when they think they've won, we burn the forest around them."),
                    Line("King Galvath Valerius", "Burn the forest? That's madness!"),
                    Line("Mika Amanogawa", "It's war. You wanted a champion, and a champion doesn't fight fair."),
                )
            ),
            Choice(
                text="Expose the traitor in the room", 
                next_scene="sacrifice", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Wait. How did the maps get covered in ash? Someone in this room did it. Someone who wants us to walk into that trap."),
                    Line("Narration", "Mika looks directly at Councilman Vane, who is sweating profusely in the corner."),
                    Line("Vane Blackwood", "I... I don't know what you're talking about!"),
                    Line("Mika Amanogawa", "Lira, arrest him."),
                )
            ),
        )
    ),
    "sacrifice": Scene(
        "The Cost of Victory", "battle", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "The battle is brutal. The valley runs red. The allied forces are pushed to the brink, but they hold the line. The battle breaks the enemy's advance, but at a terrible cost."), 
            Line("Narration", "Mika spends everything she has to keep Mallory and the defenders alive. She channels the raw, unrefined magic of the summoning circle, feeling her very essence tearing apart."), 
            Line("Mika Amanogawa", "[shake]Mallory! Get behind me![/shake]"),
        ), 
        (
            Choice(
                text="Hold on for them", 
                next_scene="grief", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "A blinding flash of light erupts from Mika's body, consuming the remaining shadow beasts. The blast levels the valley. When the light fades, Mika collapses into the mud."), 
                    Line("Mallory Valerius", "Mika! Stay with us. Please. Don't close your eyes! I can't lose you!"), 
                    Line("Narration", "The light fades from Mika's eyes. She smiles softly, knowing she saved them."),
                )
            ), 
            Choice(
                text="Let go", 
                next_scene="grief", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika lets out a final, exhausted sigh, closing her eyes as the magic consumes her."), 
                    Line("Mika Amanogawa", "I'm sorry... I couldn't hold on..."), 
                    Line("Narration", "She is gone. The cycle has claimed another life."),
                )
            ),
            Choice(
                text="Channel the magic into Lira", 
                next_scene="grief", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Lira! Take my hand! I can't hold it, but you can!"),
                    Line("Narration", "Lira grabs Mika's hand, and the magic flows through her, amplifying her sword strikes into arcs of pure light. She cuts down the remaining beasts in seconds."),
                    Line("Lira Vanguard", "You... you saved us without dying! We did it together!"),
                    Line("Mika Amanogawa", "Together. That's the secret."),
                )
            ),
            Choice(
                text="Use the environment to your advantage", 
                next_scene="grief", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika looks at the crumbling ruins around them. She dodges a blast of shadow and brings the entire ceiling down on top of the entity."),
                    Line("Lira Vanguard", "She's insane! Brilliant, but insane!"),
                    Line("Narration", "The shadow roars as it is crushed under tons of stone."),
                )
            ),
        )
    ),
    "grief": Scene(
        "After the Battle", "infirmary", ("Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Vallhelm mourns. The kingdom is saved, but the champion is gone. The capital is draped in black banners."), 
            Line("Lira Vanguard", "You should not have to hold all this grief alone, Your Highness. You haven't left her side in days. You need to eat."), 
            Line("Mallory Valerius", (
                "I promised her she wouldn't be alone. I failed her. I couldn't protect her. She died for us.",
                "I promised her she wouldn't be alone. I failed her. I couldn't protect her. She died for us.",
                "I promised her she wouldn't be alone. I failed her. I couldn't protect her. She died for us.",
                "I promised her... but maybe it's a mercy she died. I saw the way she looked at the King. She was a monster waiting to happen."
            )),
        ), 
        (
            Choice(
                text="Comfort her", 
                next_scene="lira_maid", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Lira Vanguard", "She protected us. And she would want you to keep living. She wouldn't want you to waste away in this room. Let me help you."), 
                    Line("Mallory Valerius", "Then stay beside me. And when Mika comes home, we will tell her together."),
                )
            ), 
            Choice(
                text="Leave her be", 
                next_scene="lira_maid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Lira Vanguard", "As you wish, Your Highness. I will be outside if you need me."), 
                    Line("Mallory Valerius", "...")
                )
            ),
            Choice(
                text="Promise to find a way to bring her back", 
                next_scene="lira_maid", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Lira Vanguard", "There might be a way. The summoning circle... it's still glowing. Faintly. It might be enough."),
                    Line("Mallory Valerius", "Then we use it. We bring her back. I don't care what it costs."),
                )
            ),
            Choice(
                text="Blame the King", 
                next_scene="lira_maid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mallory Valerius", "It's his fault. He sent her to the front lines. He wanted her to die so he could claim the victory."),
                    Line("Lira Vanguard", "Your Highness, please. We don't know that."),
                    Line("Mallory Valerius", "I know my father, Lira. And I know he'll pay for this."),
                )
            ),
        )
    ),
    "lira_maid": Scene(
        "The New Maid", "infirmary", ("Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Grief makes the days blur. To keep the palace running and to keep Mallory from drowning in sorrow, Lira asks to serve as her personal maid until Mika can return."), 
            Line("Mallory Valerius", "It is not a replacement. I need help, and I trust you. You are my anchor in this storm."), 
            Line("Lira Vanguard", "I will wear the apron, Your Highness. But I will never pretend to be Mika. She is one of a kind."),
        ), 
        (
            Choice(
                text="Accept Lira", 
                next_scene="return", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mallory laughs for the first time in weeks, though it is tinged with sadness. She pins Mika's pale ribbon beside the appointment order."), 
                    Line("Mallory Valerius", "I know. She would be furious if we replaced her. She'd probably throw a bucket of soapy water at us."), 
                    Line("Lira Vanguard", "I'll do my best to keep your spirits up."),
                )
            ), 
            Choice(
                text="Resent Lira", 
                next_scene="return", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mallory Valerius", "It hurts, Lira. Every time I see you in that apron, it hurts."), 
                    Line("Lira Vanguard", "I'm sorry, Your Highness. I never meant to cause you pain."),
                )
            ),
            Choice(
                text="Ask Lira to teach you to fight", 
                next_scene="return", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mallory Valerius", "If Mika isn't here to protect us, I need to learn to protect myself. Teach me, Lira."),
                    Line("Lira Vanguard", "It would be an honor, Your Highness. But let's start with a wooden sword. I don't want to explain to the King how you lost a finger."),
                )
            ),
            Choice(
                text="Organize a memorial", 
                next_scene="return", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mallory Valerius", "We should do something. A memorial. A statue. Something to remember her by."),
                    Line("Lira Vanguard", "A statue in the garden. Where she loved to sit."),
                    Line("Mallory Valerius", "Yes. And we'll put a feather duster in her hand."),
                )
            ),
        )
    ),
    "return": Scene(
        "The Return", "dawn", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "At the garden memorial, Mallory and Lira speak to Mika as if she can still hear them. A soft, golden glow gathers around the fragments of her soul."), 
            Line("Mika Amanogawa", "Mallory...? Lira...? I'm all right. I could feel how much you wanted me back."), 
            Line("Mallory Valerius", (
                "You are home. This time, you do not have to be alone. We're here.",
                "You are home. This time, you do not have to be alone. We're here.",
                "You are home. This time, you do not have to be alone. We're here.",
                "You are back... But I remember things. I remember the blood. I remember you killing me. Don't come any closer."
            )),
        ), 
        (
            Choice(
                text="Embrace them", 
                next_scene="jealousy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "It was dark. So dark. But I heard your voice calling me. It was like a lighthouse."), 
                    Line("Mika Amanogawa", "I missed you. Both of you. So much."), 
                    Line("Mallory Valerius", "We missed you too, Mika. Welcome back."),
                )
            ), 
            Choice(
                text="Be distant", 
                next_scene="jealousy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Thanks. For bringing me back. I guess."), 
                    Line("Mallory Valerius", "Mika? What's wrong? Did something happen in the dark?"), 
                    Line("Mika Amanogawa", "I don't want to talk about it right now."),
                )
            ),
            Choice(
                text="Apologize for dying", 
                next_scene="jealousy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'm sorry. I didn't mean to leave you. I just... I wanted to protect you."),
                    Line("Mallory Valerius", "Don't apologize for saving our lives. Just... don't do it again. I can't go through that twice."),
                )
            ),
            Choice(
                text="Ask how long you were gone", 
                next_scene="jealousy", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "How long was I out?"),
                    Line("Lira Vanguard", "Three weeks. Three weeks of the Princess crying over your grave."),
                    Line("Mika Amanogawa", "I'm sorry. I didn't know."),
                    Line("Mallory Valerius", "You're here now. That's all that matters."),
                )
            ),
        )
    ),
    "jealousy": Scene(
        "The Place Beside the Princess", "moon", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "A servant mistakenly calls Lira the princess's 'new maid' in passing. Mika's smile falters. Lira is wearing the very apron Mika used to fold each morning."), 
            Line("Mika Amanogawa", "You found someone to take my place before I even came back. I was gone for five minutes. Well, a few weeks."), 
            Line("Mallory Valerius", "Mika, please. Tell me what you heard. It's not what you think. Lira was just helping me survive."),
        ), 
        (
            Choice(
                text="Talk it out", 
                next_scene="confrontation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I saved this world. I died for it. Why does it feel as if I have already been erased from it?"), 
                    Line("Mika Amanogawa", "I was scared. I'm still scared. But I don't want to push you away."), 
                    Line("Mallory Valerius", "I'm so sorry, Mika. I never meant to make you feel that way."),
                )
            ), 
            Choice(
                text="Lash out", 
                next_scene="confrontation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "You're all the same. Fifty-five times I've died for people, and fifty-five times I've been replaced the second I closed my eyes."), 
                    Line("Mallory Valerius", "Mika, please! It's not like that!"), 
                    Line("Mika Amanogawa", "Then what is it like? Because it looks exactly like that from where I'm standing."),
                )
            ),
            Choice(
                text="Laugh it off", 
                next_scene="confrontation", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "A maid? Lira? She can't even fold a napkin. No offense, Captain."),
                    Line("Lira Vanguard", "None taken. I'm better with a sword than a duster."),
                    Line("Mika Amanogawa", "Good. Because I'm not sharing my apron."),
                )
            ),
            Choice(
                text="Ask Lira to step down", 
                next_scene="confrontation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Lira, I need you to take off the apron. You're a warrior, not a maid."),
                    Line("Lira Vanguard", "If that's what you want, I'll do it. But I was only trying to help."),
                    Line("Narration", "Lira removes the apron and leaves the room without another word. Mallory looks at Mika with a mix of sadness and disappointment."),
                )
            ),
        )
    ),
    "confrontation": Scene(
        "The Words Left Unsaid", "archive", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Mika, Mallory, and Lira retreat to the archive to talk. A window slams shut though there is no wind. An ink-black handprint appears on the inside of the glass, smoking slightly."), 
            Line("Mika Amanogawa", "When I heard 'new maid,' it felt like the last place in the world that was mine disappeared. Like I was just a ghost."), 
            Line("Lira Vanguard", "I wanted to keep your place warm. I never wanted to stand in it. I'm sorry, Mika."),
        ), 
        (
            Choice(
                text="Unite", 
                next_scene="reconciliation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I know you didn't mean to hurt me. But it did hurt. I've lost everyone fifty-five times over. I'm terrified of being forgotten."), 
                    Line("Mika Amanogawa", "Something in this palace wants us to doubt each other. It's feeding on our fear. We can't let it win."), 
                    Line("Mallory Valerius", "Together. We face it together."),
                )
            ), 
            Choice(
                text="Blame them", 
                next_scene="reconciliation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "This is your fault. Both of you. You made me feel like I was nothing."), 
                    Line("Mallory Valerius", "Mika! That's not fair and you know it!"), 
                    Line("Mika Amanogawa", "Fair? Nothing about this is fair."),
                )
            ),
            Choice(
                text="Suggest they share the role", 
                next_scene="reconciliation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Look, you can't be the maid, Lira. You're terrible at it. But you can be the Princess's guard. And I can be the maid. We both have our roles."),
                    Line("Lira Vanguard", "I like that idea. I'll guard the door, you handle the tea."),
                    Line("Mallory Valerius", "I think... I think I can live with that."),
                )
            ),
            Choice(
                text="Investigate the handprint", 
                next_scene="reconciliation", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Forget the maid thing for a second. Look at this handprint. It's not human. It's shadow magic."),
                    Line("Lira Vanguard", "The Demon Lord? He's here?"),
                    Line("Mika Amanogawa", "No. Something older. Something that wants us to tear each other apart."),
                    Line("Mallory Valerius", "Then we won't give it the satisfaction."),
                )
            ),
        )
    ),
    "reconciliation": Scene(
        "The Ribbon Returned", "garden", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Lira places Mika's pale ribbon on the table instead of putting it on. She waits for Mika to decide what it means, a gesture of ultimate respect."), 
            Line("Mallory Valerius", "I want both of you here. Not as copies of one another—as yourselves. You both mean the world to me."), 
            Line("Mika Amanogawa", "I was scared. I still am. But I don't want fear choosing for me."),
        ), 
        (
            Choice(
                text="Tie the ribbon", 
                next_scene="trio", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika picks up the ribbon and ties it back into her hair. The garden lanterns flare to life one by one, pushing back the darkness."), 
                    Line("Mika Amanogawa", "I'm not going anywhere. And I'm not going to let a little jealousy ruin this. We're a team."), 
                    Line("Lira Vanguard", "Agreed. We are stronger together."),
                )
            ), 
            Choice(
                text="Leave it", 
                next_scene="trio", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I need time. I'm not ready to just pretend everything is okay."), 
                    Line("Mallory Valerius", "Okay. Take all the time you need. We'll be here when you're ready."),
                )
            ),
            Choice(
                text="Ask Mallory to tie it for you", 
                next_scene="trio", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I can't do it myself. My hands are shaking. Can you...?"),
                    Line("Narration", "Mallory steps forward, gently gathering Mika's hair and tying the ribbon. Her hands are warm and steady."),
                    Line("Mallory Valerius", "There. Perfect. Welcome home, Mika."),
                )
            ),
            Choice(
                text="Give the ribbon to Lira", 
                next_scene="trio", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Actually, Lira, you should wear it. As a promise. To protect the Princess."),
                    Line("Lira Vanguard", "I... I would be honored."),
                    Line("Mallory Valerius", "And you, Mika? What will you wear?"),
                    Line("Mika Amanogawa", "I don't need a ribbon. I have you two."),
                )
            ),
        )
    ),
    "trio": Scene(
        "Three Places at the Table", "garden", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Mika returns to the household by choice. Mallory keeps Lira as her maid and Mika takes charge of the palace staff; Lira remains the princess's trusted guard and closest confidante."), 
            Line("Lira Vanguard", "No one here needs to disappear for someone else to belong. We're a team. A weird, chaotic team."), 
            Line("Mika Amanogawa", "Then let us keep the table wide enough for all of us."),
        ), 
        (
            Choice(
                text="Celebrate", 
                next_scene="assassination", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "For the first time in weeks, the palace feels like a place of warmth, rather than a fortress under siege."), 
                    Line("Mika Amanogawa", "Let's eat! I'm starving!"), 
                    Line("Mallory Valerius", "I'll have the chefs prepare a feast!"),
                )
            ), 
            Choice(
                text="Stay quiet", 
                next_scene="assassination", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Okay. Sounds good."), 
                    Line("Lira Vanguard", "... Is everything alright, Mika?"), 
                    Line("Mika Amanogawa", "Yeah. Just tired. Let's get some rest."),
                )
            ),
            Choice(
                text="Plan a training session", 
                next_scene="assassination", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "We can celebrate after we survive the next assassination attempt. Let's run drills in the garden."),
                    Line("Lira Vanguard", "I'll get the wooden swords. You're no fun, Mika."),
                    Line("Mika Amanogawa", "I'm alive. That's the point."),
                )
            ),
            Choice(
                text="Ask about the shadow handprint", 
                next_scene="assassination", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "That handprint in the archive. It's been bothering me. What if it's not just a prank?"),
                    Line("Lira Vanguard", "The archives are ancient. There are things down there that even the King doesn't know about."),
                    Line("Mika Amanogawa", "Then we should explore them. Tomorrow. Right now, let's eat."),
                )
            ),
        )
    ),
    "assassination": Scene(
        "A Threat in the Garden", "moon", ("Lira Vanguard", "Mika Amanogawa", "Mallory Valerius"), 
        (
            Line("Narration", "A hidden faction tries to strike at the royal family during a moonlit walk. Lira spots the glint of a blade first, a flash of silver in the bushes."), 
            Line("Lira Vanguard", "Mika, down! Assassin on the east wall!"), 
            Line("Narration", "Mika throws herself in front of Mallory, catching a poisoned dart on her armored sleeve. The three women fight back-to-back, a perfect unit."),
        ), 
        (
            Choice(
                text="Protect them", 
                next_scene="conspiracy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Stay behind me! I won't let them touch you!"), 
                    Line("Lira Vanguard", "The palace is safer when we trust each other enough to share the watch."), 
                    Line("Mallory Valerius", "Thank you, Mika. You saved my life."),
                )
            ), 
            Choice(
                text="Offensive", 
                next_scene="conspiracy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'll hunt them down. They won't get far."), 
                    Line("Lira Vanguard", "Careful! It could be a trap!"), 
                    Line("Narration", "Mika charges into the darkness, determined to end the threat permanently."),
                )
            ),
            Choice(
                text="Use the assassin's poison against them", 
                next_scene="conspiracy", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "They're using poison. That means they're cowards. Lira, cover me. I'm going to make them taste their own medicine."),
                    Line("Narration", "Mika scoops up the poisoned dart and hurls it back into the bushes. A muffled gasp confirms her aim was true."),
                    Line("Lira Vanguard", "Remind me never to get on your bad side."),
                )
            ),
            Choice(
                text="Capture one alive", 
                next_scene="conspiracy", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Lira, don't kill them! We need one alive!"),
                    Line("Narration", "Lira knocks the assassin out with the flat of her blade and drags him into the light."),
                    Line("Mallory Valerius", "He's wearing the King's colors. But the crest is wrong."),
                    Line("Mika Amanogawa", "A fake. Someone is trying to frame the King."),
                )
            ),
        )
    ),
    "conspiracy": Scene(
        "The Hand Behind the Knife", "archive", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "The trail leads below the old archive. A locked door opens from the other side. Standing there is Councilman Vane Blackwood, holding a glowing, dark artifact, his eyes clouded with dark magic."), 
            Line("Mika Amanogawa", "You. You're the one who poisoned the wells. You killed our scouts. Why?"), 
            Line("Vane Blackwood", "For the glory of Vallhelm! The Demon Lord promised me power beyond imagination!"),
        ), 
        (
            Choice(
                text="Arrest", 
                next_scene="healing", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika disarms Vane with a swift strike, pinning him to the ground."), 
                    Line("Mika Amanogawa", "Take him away. Let him rot in the dungeons for his crimes."), 
                    Line("Mallory Valerius", "Justice will be served. Thank you, Mika."),
                )
            ), 
            Choice(
                text="Execute", 
                next_scene="healing", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika's blade flashes in the dim light. Vane falls to the ground, the dark artifact shattering into dust."), 
                    Line("Mika Amanogawa", "You die now. Traitors don't deserve a trial."), 
                    Line("Lira Vanguard", "Mika, no... It wasn't your place to execute him."),
                )
            ),
            Choice(
                text="Smash the artifact first", 
                next_scene="healing", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika ignores Vane, swinging her sword at the glowing artifact. It shatters, and Vane screams as the dark magic leaves him, leaving him a weeping, broken man."),
                    Line("Mika Amanogawa", "He's not a traitor. He's a victim. Take him to the healers."),
                    Line("Mallory Valerius", "You broke the spell. You saved him."),
                )
            ),
            Choice(
                text="Interrogate him", 
                next_scene="healing", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Who gave you the artifact? Tell me!"),
                    Line("Vane Blackwood", "The shadow... it spoke to me. It promised me a crown."),
                    Line("Mika Amanogawa", "A crown? Not power?"),
                    Line("Vane Blackwood", "The Demon Lord is just a pawn. The real darkness is the one whispering in the throne room."),
                )
            ),
        )
    ),
    "healing": Scene(
        "The Healing Kitchen", "infirmary", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "The conspirators are stopped, but the battle leaves Mika's old wounds burning. She tries to hide the tremor in her hands from the others."), 
            Line("Mallory Valerius", "You don't have to be useful to deserve rest. Let me bandage that."), 
            Line("Lira Vanguard", "Then tonight, we keep watch while you heal. You've earned a moment of peace."),
        ), 
        (
            Choice(
                text="Accept help", 
                next_scene="prophecy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mallory gently cleans Mika's wounds, humming a soft lullaby. Mika finally allows herself to relax, leaning into Mallory's touch."), 
                    Line("Mika Amanogawa", "Thank you. Both of you. For making me feel human again."), 
                    Line("Mallory Valerius", "Always, Mika. Always."),
                )
            ), 
            Choice(
                text="Push away", 
                next_scene="prophecy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Leave me. I can take care of myself."), 
                    Line("Lira Vanguard", "... As you wish. We'll be right outside if you need us."), 
                    Line("Narration", "Mika sits alone in the dark, wincing as she tries to bandage her own wounds."),
                )
            ),
            Choice(
                text="Ask for a drink", 
                next_scene="prophecy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Bandages are nice, but I could really use a cup of coffee. Or whatever the fantasy equivalent is."),
                    Line("Mallory Valerius", "I think we can manage some tea. Stay right here."),
                    Line("Narration", "For the first time in a long time, Mika laughs."),
                )
            ),
            Choice(
                text="Discuss the prophecy", 
                next_scene="prophecy", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "The book said there was a true enemy. Older than the Demon Lord. What if the shadow was talking about itself?"),
                    Line("Lira Vanguard", "Then we need a plan. We can't just wait for it to attack."),
                    Line("Mika Amanogawa", "Agreed. We rest tonight, and we plan tomorrow."),
                )
            ),
        )
    ),
    "prophecy": Scene(
        "The Prophecy Unfolds", "archive", ("Lira Vanguard", "Mika Amanogawa", "Mallory Valerius"), 
        (
            Line("Narration", "The old book reveals one final warning: a darkness older than the Demon Lord is drawing near. The true enemy approaches."), 
            Line("Lira Vanguard", "I found a way to focus the magic without asking Mika to carry it all. We can channel it together. A shared burden."), 
            Line("Mallory Valerius", "Then we face the storm as a family, with the whole kingdom behind us."),
        ), 
        (
            Choice(
                text="Accept", 
                next_scene="winter_vigil", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Fifty-five times I did this alone. Not this time. Let's do it together."), 
                    Line("Mallory Valerius", "Yes. Together."), 
                    Line("Narration", "The ground trembles. The black winter has arrived."),
                )
            ), 
            Choice(
                text="Alone", 
                next_scene="winter_vigil", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "No. I'll do it. I'm the champion, aren't I? I'm the one who has to make the sacrifice."), 
                    Line("Lira Vanguard", "Stubborn fool. You don't have to carry this alone."), 
                    Line("Narration", "The ground trembles. The black winter has arrived."),
                )
            ),
            Choice(
                text="Ask for more details about the darkness", 
                next_scene="winter_vigil", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "What exactly is the darkness? Is it a monster? A spell? A person?"),
                    Line("Lira Vanguard", "The book says it has no face. It is the absence of hope itself."),
                    Line("Mika Amanogawa", "Then we give it a face. And we punch it."),
                )
            ),
            Choice(
                text="Search for a counter-spell", 
                next_scene="winter_vigil", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "There has to be a way to weaken it before it gets here. Something in the library?"),
                    Line("Lira Vanguard", "The forbidden section. The King would have our heads."),
                    Line("Mika Amanogawa", "He'll have our heads anyway if we lose. Let's go."),
                )
            ),
        )
    ),
    "winter_vigil": Scene(
        "The Longest Night", "winter", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard", "Gorthak Stonefist"), 
        (
            Line("Narration", "On the eve of the black winter, the four keep watch at the garden fountain. The sky is an inky void, devoid of stars."), 
            Line("Shadow", "[shake]Fifty-five times you died alone. The fifty-sixth will end the pattern. You will break.[/shake]"), 
            Line("Mika Amanogawa", "You're wrong. This time, I have people who know my name."),
        ), 
        (
            Choice(
                text="Strong", 
                next_scene="storm", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "The shadow smiles with Mika's own face and vanishes beneath the ice."), 
                    Line("Mika Amanogawa", "I have people who know my name. I am not alone."), 
                    Line("Mallory Valerius", "We are here. We will always be here."),
                )
            ), 
            Choice(
                text="Doubt", 
                next_scene="storm", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "The shadow smiles with Mika's own face and vanishes beneath the ice."), 
                    Line("Mika Amanogawa", "Maybe I will break. Maybe this is the time I finally fail."), 
                    Line("Lira Vanguard", "Don't say that. We need you to be strong."),
                )
            ),
            Choice(
                text="Laugh at the shadow", 
                next_scene="storm", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "You're a shadow. You're literally a spooky voice in the dark. I've cleaned up scarier things than you."),
                    Line("Shadow", "You mock me?"),
                    Line("Mika Amanogawa", "I mock bad hotel carpet stains. You're not even top ten."),
                    Line("Narration", "The shadow recoils, confused by her defiance."),
                )
            ),
            Choice(
                text="Ask the shadow why it's doing this", 
                next_scene="storm", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "Why? Why do you keep bringing me back just to kill me?"),
                    Line("Shadow", "Because your suffering is delicious. Each time you break, I grow stronger."),
                    Line("Mika Amanogawa", "Then I'll stop breaking. I'll become something you can't swallow."),
                    Line("Mallory Valerius", "And we'll be right there with her."),
                )
            ),
        )
    ),
    "storm": Scene(
        "The Gathering Storm", "winter", ("Mallory Valerius", "Mika Amanogawa", "Lira Vanguard"), 
        (
            Line("Narration", "Winter turns the sky black. Beyond the walls, a vast shadow opens over Vallhelm. The final battle is at hand."), 
            Line("Mika Amanogawa", "Fifty-six lives, and I finally know what I want to protect."), 
            Line("Mallory Valerius", (
                "Whatever happens out there... I love you, Mika. I should have said it sooner.",
                "Whatever happens out there... I love you, Mika. I should have said it sooner.",
                "Whatever happens out there... I love you, Mika. I should have said it sooner.",
                "Whatever happens out there... I want to trust you, Mika. But there's a darkness in your eyes that I've seen before. Please, prove me wrong."
            )),
        ), 
        (
            Choice(
                text="Love you too", 
                next_scene="final_battle", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I love you too. Let's end this. Together."), 
                    Line("Mallory Valerius", "Let's go."), 
                    Line("Narration", "They charge into the darkness, side by side."),
                )
            ), 
            Choice(
                text="Silent", 
                next_scene="final_battle", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "..."), 
                    Line("Mallory Valerius", "Mika? Please, say something."), 
                    Line("Mika Amanogawa", "There's no time for words. We have a battle to win."),
                )
            ),
            Choice(
                text="Promise to return", 
                next_scene="final_battle", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika Amanogawa", "I'll come back. I swear. You won't have to wait for me this time."),
                    Line("Mallory Valerius", "I'll hold you to that."),
                    Line("Narration", "They share a brief, fierce embrace before turning to face the storm."),
                )
            ),
            Choice(
                text="Kiss her", 
                next_scene="final_battle", 
                effects={"bond": 2, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika steps forward and kisses Mallory, a fierce, desperate kiss that tastes of tears and hope."),
                    Line("Mika Amanogawa", "For luck."),
                    Line("Mallory Valerius", "Come back to me, Mika."),
                )
            ),
        )
    ),
    "final_battle": Scene(
        "The Final Battle", "battle", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard", "Shadow"), 
        (
            Line("Narration", "The sky cracks open. The ancient shadow descends, a massive entity of writhing darkness and glowing red eyes."), 
            Line("Shadow", "[color=#ff0000]You are nothing but a servant. You cannot defeat me.[/color]"), 
            Line("Mika Amanogawa", "I am a servant. But I am also a hero. And this is my home!"),
        ), 
        (
            Choice(
                text="Together", 
                next_scene="ending_gate", 
                effects={"family_final": 1, "bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika raises her weapon, channeling all her power into a single strike. Mallory and Lira stand beside her, combining their magic."), 
                    Line("Mika Amanogawa", "[shake]Together![/shake]"), 
                    Line("Shadow", "Impossible!"),
                )
            ), 
            Choice(
                text="Sacrifice", 
                next_scene="ending_gate", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika pushes Mallory and Lira out of the way, charging directly into the shadow."), 
                    Line("Mika Amanogawa", "[shake]I'll do it alone![/shake]"), 
                    Line("Mallory Valerius", "No! Mika!"),
                )
            ),
            Choice(
                text="Use the environment", 
                next_scene="ending_gate", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika looks at the crumbling ruins around them. She dodges a blast of shadow and brings the entire ceiling down on top of the entity."),
                    Line("Lira Vanguard", "She's insane! Brilliant, but insane!"),
                    Line("Narration", "The shadow roars as it is crushed under tons of stone."),
                )
            ),
            Choice(
                text="Use the power of the 55 lives", 
                next_scene="ending_gate", 
                effects={"resolve": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika closes her eyes, reaching into the depths of her soul. She feels all 55 of her past lives, all their pain, all their love."),
                    Line("Mika Amanogawa", "You killed me 55 times. Now I'm going to use every single one of those deaths to kill you."),
                    Line("Narration", "A brilliant golden light erupts from her body, obliterating the shadow."),
                )
            ),
        )
    ),
    "ending_home": Scene(
        "A New Dawn", "dawn", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Together, they break the ancient shadow. The entity shatters into a million pieces of light. Mika falls to her knees, exhausted."), 
            Line("Mallory Valerius", "You came back. You are loved, Mika. You are home."), 
            Line("Mika Amanogawa", "As long as a fragment of me remains, I will always find my way back to you. This time, I am staying home. Forever."), 
            Line("Lira Vanguard", "The dawn is breaking. We actually did it."),
            Line("Narration", "The weeks that follow are a blur of rebuilding and celebration. The kingdom throws a festival in Mika's honor, but she spends most of it hiding in the kitchens, baking pies with the staff."),
            Line("Narration", "Mallory finds her there, covered in flour, laughing with the scullery maids."),
            Line("Mallory Valerius", "The hero of Vallhelm, everyone! Hiding from her own party."),
            Line("Mika Amanogawa", "I'm not hiding. I'm just... organizing the dessert table. It's a very important job."),
            Line("Narration", "Mallory takes her hand, pulling her into a dance among the ovens and hanging pots."),
            Line("Mallory Valerius", "I love you, Mika Amanogawa. Not because you're a hero. But because you're you."),
            Line("Mika Amanogawa", "I love you too, Mallory. And I promise, no more dying. At least, not for a very long time."),
            Line("Narration", "Lira watches from the doorway, a rare smile on her face. The cycle is finally broken. And for the first time in fifty-six lives, Mika is truly home."),
            Line("Narration", "Years pass. The kingdom flourishes. And the summoning circle remains dark, never to be used again."),
        ), 
        ending=True
    ),
    "ending_peace": Scene(
        "The Kingdom United", "dawn", ("Gorthak Stonefist", "Mika Amanogawa", "Mallory Valerius"), 
        (
            Line("Narration", "The goblin alliance turns the tide. Together, the people of Vallhelm shatter the darkness and keep their promise of peace."), 
            Line("Gorthak Stonefist", "Today we fought as neighbors. Let us live that way tomorrow."), 
            Line("Mika Amanogawa", "I used to think protecting people meant standing in front of them. Now I know it can mean standing beside them."), 
            Line("Narration", "A new era of unity begins. Goblins and humans rebuild the kingdom together, and Mika stands at the center of it all."),
            Line("Narration", "Months later, the first joint harvest festival is held in the lower city. Humans and goblins trade goods, share stories, and dance around a massive bonfire."),
            Line("Gorthak Stonefist", "You changed everything, Mika. You gave my people a future."),
            Line("Mika Amanogawa", "I just cleaned up the mess. You did the fighting."),
            Line("Mallory Valerius", "Don't sell yourself short. You brought us together. You gave us hope."),
            Line("Narration", "Mika looks at the fire, at the faces of her friends, and finally feels the heavy burden of the prophecy lift from her shoulders."),
            Line("Mika Amanogawa", "You know, I think this world might just be my home after all."),
            Line("Narration", "The kingdom of Vallhelm becomes a beacon of unity, and Mika Amanogawa, the maid who saved the world, is remembered not as a weapon, but as a bridge."),
        ), 
        ending=True
    ),
    "ending_cycle": Scene(
        "The Fifty-Sixth Return", "dawn", ("Mika Amanogawa", "Mallory Valerius", "Lira Vanguard"), 
        (
            Line("Narration", "Mika meets the darkness alone and wins, though the familiar cycle claims its price once more."), 
            Line("Narration", "In the quiet that follows, Mallory and Lira refuse to let her go. Their voices guide her back to the garden."), 
            Line("Mika Amanogawa", "I will try again. Next time, I will let you stand beside me."), 
            Line("Mallory Valerius", "I'll be waiting for you. Always."),
            Line("Narration", "But the world resets. The kingdom is restored, the wounds are healed, and the summoning circle begins to glow once more."),
            Line("Narration", "King Galvath is alive. The Demon Lord is a distant threat. And Mallory sits on her throne, a strange, painful ache in her chest that she cannot explain."),
            Line("Narration", "She doesn't know why she cries when the mages attempt the summoning. She doesn't know why she feels a mix of hope and dread when the golden light fills the hall."),
            Line("Narration", "But when she sees the maid with the feather duster appear, Mallory knows one thing for certain: this time, she will not let her die alone."),
        ), 
        ending=True
    ),
    "ending_evil_kingdom": Scene(
        "Kingdom of Ash", "throne", ("Mika_Evil", "Lira Vanguard", "King Galvath Valerius"), 
        (
            Line("Narration", "Rain hammers against the stained glass of the throne room. Mika stands before the King and Lira, her maid's dress soaked in mud, blood, and rain. In her trembling hands, she holds the shattered hilt of Mallory's sword."),
            Line("Narration", "Mallory had ridden to the border, believing she could negotiate a truce with the neighboring kingdom. Instead, they had strung her up like a banner of war. Her body now lay in the palace infirmary, cold and lifeless."),
            Line("Lira Vanguard", "Mika, please... say something. You've been silent for hours."),
            Line("King Galvath Valerius", "It was her choice to go! She knew the risks of diplomacy! We must not let her sacrifice be in vain. We rally the troops! We burn their kingdom to the ground!"),
            Line("Mika_Evil", "[shake]Her choice?[/shake]"),
            Line("Narration", "Mika's voice is unnervingly quiet, a sharp contrast to the King's booming rage."),
            Line("Mika_Evil", "[shake]You sent her there. You knew it was a trap. You wanted a martyr to rally your pathetic army.[/shake]"),
            Line("Lira Vanguard", "Mika, no! That's treason! The King would never—"),
            Line("King Galvath Valerius", "Watch your tongue, servant! I am your King, and I will not be spoken to in such a manner by a scullery maid!"),
            Line("Mika_Evil", "[shake]TODAY I HAD ENOUGH OF YOUR RUDENESS![/shake]"),
            Line("Narration", "Mika brandishes her sword, the blade singing a terrible, high-pitched note as it leaves the scabbard. The guards barely have time to draw their weapons before she lunges at the King, cutting him down in a single, devastating arc."),
            Line("Lira Vanguard", "NO! Mika, stop! You're betraying everything Mallory stood for! You're betraying her!"),
            Line("Narration", "Lira draws her blade, tears streaming down her face. She steps between Mika and the throne, her hands shaking."),
            Line("Mika_Evil", "[shake]Betraying her? I am the only one who loved her![/shake]"),
            Line("Narration", "With a feral scream, Mika clashes with Lira. The fight is brutal, a whirlwind of steel and grief. Mika's grief gives her a terrifying strength. She parries Lira's strike and drives her blade deep into the Captain's chest."),
            Line("Narration", "Lira falls, her blood pooling on the marble floor. Mika stands alone in the throne room, surrounded by the bodies of the King and the Captain."),
            Line("Narration", "Mika reaches down, her fingers slick with blood, and plucks the heavy golden crown from the dead King's head. She places it upon her own brow, the cold metal a stark contrast to the heat of the burning kingdom."),
            Line("Mika_Evil", "The kingdom is mine now. I will kill them all. Every single one of them. For Mallory."),
            Line("Narration", "The girl who was once a maid is gone. In her place stands the Queen of Ash, her heart consumed by the very darkness she swore to destroy."),
            Line("Narration", "The reign of Queen Mika begins in blood. She does not stop with the neighboring kingdom. She burns everything. And when the world is ash, she sits on the throne, wearing Mallory's ribbon, waiting for a reset that will never come."),
        ), 
        ending=True
    ),
    "ending_betrayal": Scene(
        "The Final Betrayal", "moon", ("Mika_Evil", "Mallory Valerius"), 
        (
            Line("Narration", "The other kingdom's forces surround them. Mallory is injured, leaning heavily on Mika. The rain is cold, washing the blood from their wounds."),
            Line("Mika_Evil", "I'll save you from them, Mallory. I'll protect you. Just trust me."),
            Line("Mallory Valerius", "I trust you, Mika. Always. We'll get through this. Together."),
            Line("Narration", "Mika smiles, a soft, broken thing. She leans in close, as if to embrace the Princess. Instead, she drives a concealed dagger deep into Mallory's back."),
            Line("Mallory Valerius", "M-Mika...? Why...?"),
            Line("Mika_Evil", "I can't save you. I couldn't save anyone. But I can reset the world. I can try again. I can bring you back."),
            Line("Narration", "Mallory's eyes widen in shock and despair. She reaches out, her fingers brushing Mika's tear-stained cheek, before her body goes limp."),
            Line("Narration", "As the light fades from Mallory's eyes, a terrible realization dawns on her. On the next reset, her trust in Mika will be forever shattered, even though the events remain unchanged. The cycle begins anew."),
            Line("Mika_Evil", "I'll fix it. I'll fix everything. Just wait for me, Mallory."),
            Line("Narration", "Mika pulls the dagger from Mallory's back and turns it on herself, casting the reset spell with her own blood. The world twists, shatters, and reforms."),
            Line("Narration", "But something is wrong. The spell is corrupted. Mika is not a hero anymore. She is a ghost in the machine. And Mallory... Mallory is terrified."),
            Line("Narration", "The new timeline begins with Mallory looking at Mika not with love, but with pure, unadulterated fear. And Mika? Mika just smiles, ready to try again."),
        ), 
        ending=True
    ),
}

CHAPTERS = (
    Chapter("01", "The Summoning", "summoning", ARCS[0]), Chapter("02", "The Wrong Hero", "first_impression", ARCS[0]),
    Chapter("03", "A Cup Before the Storm", "coffee", ARCS[0]), Chapter("04", "The City Market", "market", ARCS[0]),
    Chapter("05", "The Knight's Mistake", "knight_mistake", ARCS[0]), Chapter("06", "The Ancient Record", "archive", ARCS[0]),
    Chapter("07", "Sparring with Lira", "training", ARCS[1]), Chapter("08", "A Quiet Afternoon", "garden", ARCS[1]),
    Chapter("09", "Tracks at the Orchard", "goblin_warning", ARCS[1]), Chapter("10", "The Goblin Raid", "raid", ARCS[1]),
    Chapter("11", "A Language of Understanding", "treaty", ARCS[1]), Chapter("12", "A Village at the Edge", "goblin_home", ARCS[1]),
    Chapter("13", "The Demon Lord's Shadow", "shadow", ARCS[2]), Chapter("14", "The Empty Place at Council", "war_council", ARCS[2]),
    Chapter("15", "The Cost of Victory", "sacrifice", ARCS[2]), Chapter("16", "After the Battle", "grief", ARCS[2]),
    Chapter("17", "The New Maid", "lira_maid", ARCS[2]), Chapter("18", "The Return", "return", ARCS[3]),
    Chapter("19", "The Place Beside the Princess", "jealousy", ARCS[3]), Chapter("20", "The Words Left Unsaid", "confrontation", ARCS[3]),
    Chapter("21", "The Ribbon Returned", "reconciliation", ARCS[3]), Chapter("22", "Three Places at the Table", "trio", ARCS[3]),
    Chapter("23", "A Threat in the Garden", "assassination", ARCS[4]), Chapter("24", "The Hand Behind the Knife", "conspiracy", ARCS[4]),
    Chapter("25", "The Healing Kitchen", "healing", ARCS[4]), Chapter("26", "The Prophecy Unfolds", "prophecy", ARCS[4]),
    Chapter("27", "The Longest Night", "winter_vigil", ARCS[4]), Chapter("28", "The Gathering Storm", "storm", ARCS[5]),
    Chapter("29", "The Final Battle", "final_battle", ARCS[5]), Chapter("30", "A New Dawn", "ending_home", ARCS[5]),
    Chapter("31", "The Kingdom United", "ending_peace", ARCS[5]), Chapter("32", "The Fifty-Sixth Return", "ending_cycle", ARCS[5]),
    Chapter("33", "Kingdom of Ash", "ending_evil_kingdom", ARCS[5]), Chapter("34", "The Final Betrayal", "ending_betrayal", ARCS[5]),
)
CHAPTER_BY_SCENE = {chapter.scene_id: chapter for chapter in CHAPTERS}
CHAPTER_MUSIC = {chapter.scene_id: Path("assets") / "chapter_music" / f"chapter_{chapter.key}{'.mp3' if chapter.key == '01' else '.wav'}" for chapter in CHAPTERS}
SOUND_EFFECTS = (("summon", "Summoning Rune"), ("pages", "Forbidden Pages"), ("garden", "Garden Fountain"), ("heartbeat", "Fearful Heartbeat"), ("footsteps", "Hallway Footsteps"), ("sword", "Sword Draw"), ("wind", "Black Winter Wind"), ("hope", "Return of Hope"))


def asset_path(*parts: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root.joinpath(*parts)

class BackgroundMusic:
    def __init__(self) -> None:
        try: import pygame
        except ImportError: self._pygame = None; self._error = "Install pygame."; return
        self._pygame = pygame; self._error = None; self._loaded_track = None
        self.volume = 0.5
    @property
    def available(self) -> bool: return self._pygame is not None
    @property
    def error(self) -> str | None: return self._error
    def play(self, track: Path | None = None) -> None:
        if not self.available: raise OSError(self._error or "MP3 unavailable.")
        track = track or asset_path("assets", "menu_bgm.mp3")
        if not track.is_file(): return
        track = track.resolve()
        try:
            if not self._pygame.mixer.get_init(): self._pygame.mixer.init(frequency=44100, size=-16, channels=2)
            self._pygame.mixer.music.set_volume(self.volume)
            if self._loaded_track != track:
                self._pygame.mixer.music.load(str(track)); self._pygame.mixer.music.play(-1); self._loaded_track = track
            else: self._pygame.mixer.music.unpause()
        except self._pygame.error as error: raise OSError(f"Error: {error}") from error
    def stop(self) -> None:
        if self.available and self._pygame.mixer.get_init(): self._pygame.mixer.music.pause()
    def close(self) -> None:
        if self.available and self._pygame.mixer.get_init():
            try: self._pygame.mixer.music.stop(); self._pygame.mixer.quit()
            except self._pygame.error as error: raise OSError(f"Error: {error}") from error

class EightBitVoiceOver:
    def __init__(self, pygame_module: object | None) -> None:
        self._pygame = pygame_module
        self.available = self._pygame is not None
        self.error = "Install pygame." if not self.available else None
        self.volume = 0.5
        self._active_sounds = []
        
    def play_blip(self, speaker: str):
        if not self.available: return
        try:
            if not self._pygame.mixer.get_init():
                self._pygame.mixer.init(frequency=22050, size=-16, channels=1)
            base_freqs = {
                "Mika": 600, "Mika Amanogawa": 600,
                "Mallory": 500, "Mallory Valerius": 500,
                "Lira": 550, "Lira Vanguard": 550,
                "King Galvath": 200, "King Galvath Valerius": 200,
                "Gorthak": 150, "Gorthak Stonefist": 150,
                "Shadow": 100,
                "Narration": 350,
                "Mika_Evil": 1400
            }
            freq = base_freqs.get(speaker, 400) + random.randint(-10, 10)
            sample_rate = self._pygame.mixer.get_init()[0]
            duration = 0.03
            count = int(sample_rate * duration)
            samples = array.array("h")
            for i in range(count):
                time = i / sample_rate
                val = 1.0 if math.sin(2 * math.pi * freq * time) > 0 else -1.0
                progress = i / count
                env = 1.0 if progress < 0.8 else (1.0 - progress) * 5.0
                samples.append(int(val * env * 6000 * self.volume))
            if sys.byteorder != "little": samples.byteswap()
            sound = self._pygame.mixer.Sound(buffer=samples.tobytes())
            sound.play()
        except Exception: pass

class Soundboard:
    SAMPLE_RATE = 22050
    def __init__(self, pygame_module: object | None) -> None:
        self._pygame = pygame_module; self.error = None; self._sounds = {}
        self.volume = 0.5
    @property
    def available(self) -> bool: return self._pygame is not None
    def _make_sound(self, key: str) -> object:
        pygame = self._pygame
        if pygame is None: raise OSError("Need pygame.")
        if not pygame.mixer.get_init(): pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
        sample_rate = pygame.mixer.get_init()[0]; duration = 0.85 if key not in {"wind", "garden"} else 1.5
        count = int(sample_rate * duration); samples = array.array("h"); rng = random.Random(key)
        for index in range(count):
            time = index / sample_rate; progress = index / count
            envelope = min(1, progress * 18) * min(1, (1 - progress) * 8)
            if key == "summon": sample = math.sin(2 * math.pi * (180 + 580 * progress) * time) * 0.48
            elif key == "pages": sample = (rng.random() * 2 - 1) * 0.24
            elif key == "garden": sample = (rng.random() * 2 - 1) * 0.13 + math.sin(2 * math.pi * 420 * time) * 0.16
            elif key == "heartbeat": sample = math.sin(2 * math.pi * 58 * time) * math.exp(-((time % 0.62 - 0.10) / 0.055) ** 2) * 0.7
            elif key == "footsteps": sample = (rng.random() * 2 - 1) * math.exp(-(time % 0.44) * 24) * 0.52
            elif key == "sword": sample = math.sin(2 * math.pi * (1200 - 850 * progress) * time) * 0.38
            elif key == "wind": sample = (rng.random() * 2 - 1) * 0.3
            else: sample = math.sin(2 * math.pi * (880 - 430 * progress) * time) * 0.3
            samples.append(int(max(-1, min(1, sample * envelope)) * 26000))
        if sys.byteorder != "little": samples.byteswap()
        snd = pygame.mixer.Sound(buffer=samples.tobytes())
        snd.set_volume(self.volume)
        return snd
    def play(self, key: str) -> None:
        if not self.available: self.error = "Need pygame."; return
        try:
            sound = self._sounds.get(key)
            if sound is None: sound = self._make_sound(key); self._sounds[key] = sound
            sound.set_volume(self.volume)
            sound.play(); self.error = None
        except self._pygame.error as error: self.error = f"Error: {error}"
        except OSError as error: self.error = str(error)

def ending_for(flags: dict[str, int]) -> str:
    rep = flags.get("reputation", 0)
    bond = flags.get("bond", 0)

    # BAD ENDING PATH
    if rep <= -2:
        if bond >= 2:
            return "ending_evil_kingdom"
        return "ending_betrayal"

    # GOOD ENDING PATH
    if flags.get("family_final", 0) and bond >= 2: 
        return "ending_home"
    if flags.get("peace", 0) >= 2: 
        return "ending_peace"
        
    # NEUTRAL ENDING PATH
    return "ending_cycle"

def validate_story() -> int:
    if not STORY: raise ValueError("No scenes.")
    for key, scene in STORY.items():
        for choice in scene.choices:
            target = ending_for({**{"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}, **choice.effects}) if choice.next_scene == "ending_gate" else choice.next_scene
            if target and target not in STORY: raise ValueError(f"Bad link {key}")
        if scene.next_scene is not None and scene.next_scene not in STORY: raise ValueError(f"Bad link {key}")
        if not scene.lines: raise ValueError(f"No lines {key}")
    if len(CHAPTERS) != len(STORY): raise ValueError("Chapter mismatch")
    return len(STORY)

class VisualNovel:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import messagebox
        self.tk = tk; self.messagebox = messagebox
        self.root = tk.Tk(); self.root.title(APP_NAME); self.root.geometry("1100x740"); self.root.minsize(820, 600)
        self.canvas = tk.Canvas(self.root, bg="#06080a", highlightthickness=0); self.canvas.pack(fill="both", expand=True)
        
        if HAS_PIL:
            try:
                base_dir = Path(__file__).resolve().parent
                icon_path = None
                for folder in ["assets/characters", "assets", ""]:
                    p = base_dir / folder / "Mika.png" if folder else base_dir / "Mika.png"
                    if p.exists(): icon_path = p; break
                if icon_path:
                    icon_img = Image.open(icon_path)
                    icon_img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    self._icon_photo = ImageTk.PhotoImage(icon_img)
                    self.root.iconphoto(True, self._icon_photo)
            except Exception: pass

        self.current_scene: str | None = None
        self.line_index = 0
        self.flags = {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}
        
        self.temp_lines: tuple[Line, ...] | None = None
        self.temp_index: int = 0
        self.pending_next_scene: str | None = None

        self.undo_stack = []
        self.menu = True
        self.menu_hidden = True
        self.save_select_visible = False
        self.save_mode = "load"
        self._save_return_to_game = False
        
        self._canvas_size = (1100, 740)
        self._animated_tags = []
        self._idle_offset = 0; self._idle_direction = -1
        self._char_offsets = {} 
        
        self.typewriter_speed = 25
        self.is_typing = False
        self.full_text = ""
        self.display_text = ""
        self.typing_idx = 0
        self.text_id = None
        self.history = []
        self.auto_play = False
        self.immersive_mode = False
        self.shake_timer = 0
        self.shake_intensity = 0
        self._is_shaking_text = False
        self._text_color = "#f3eee5"

        self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False
        self.music = BackgroundMusic(); self.music_enabled = self.music.available; self.music_error = None
        self.soundboard = Soundboard(self.music._pygame); self.sfx_enabled = self.soundboard.available
        self.voice = EightBitVoiceOver(self.music._pygame)
        self.voice_enabled = self.voice.available
        self.voice_error = self.voice.error
        
        self._last_spoken = None; self.highest_chapter = 0
        self._image_cache = {}; self._bg_cache = {}
        self.particles = []
        self._current_backdrop = ""
        
        if self.music_enabled: self._start_music()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.root.bind("<Key>", self._reveal_menu)
        self.root.bind("<Return>", lambda _event: self.advance())
        self.root.bind("<space>", lambda _event: self.advance())
        self.root.bind("<BackSpace>", lambda _event: self.go_back())
        self.root.bind("<Control-s>", lambda _event: self.save_shortcut())
        self.root.bind("<Escape>", lambda _event: self.show_menu())
        self.root.bind("<h>", lambda _event: self.toggle_immersive())
        for key, index in (("1", 0), ("2", 1), ("3", 2), ("4", 3)):
            self.root.bind(key, lambda _event, choice_index=index: self.choose(choice_index))
            
        self.draw()
        self.root.after(220, self._animate_idle)

    def _reveal_menu(self, event=None):
        if self.menu and self.menu_hidden and not self.chapter_select and not self.soundboard_visible and not self.soundtrack_visible and not self.credits and not self.save_select_visible:
            self.menu_hidden = False
            self.draw()

    def toggle_immersive(self):
        self.immersive_mode = not self.immersive_mode
        self.draw()

    def _trigger_shake(self, duration=20, intensity=10):
        self.shake_timer = duration
        self.shake_intensity = intensity

    def _snapshot(self): return {"current_scene": self.current_scene, "line_index": self.line_index, "flags": self.flags.copy(), "menu": self.menu, "highest_chapter": self.highest_chapter}
    def _remember(self): self.undo_stack.append(self._snapshot())
    def _restore(self, state):
        self.current_scene = state["current_scene"]; self.line_index = int(state["line_index"]); self.flags = dict(state["flags"]); self.menu = bool(state["menu"]); self.highest_chapter = int(state.get("highest_chapter", 0))
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self._char_offsets.clear()
        if self.music_enabled: self._start_music()
        self.draw()

    def new_game(self):
        self.undo_stack.clear(); self.flags = {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}; self.highest_chapter = 0
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.history.clear(); self._char_offsets.clear()
        self.immersive_mode = False
        self.save_select_visible = False
        self._enter_scene("summoning"); self.line_index = 0; self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.play_scene_sfx("summoning"); self.draw()

    def reset_game(self):
        if not self.messagebox.askyesno(APP_NAME, "Start a new cycle? Mallory will remember past timelines and be more wary of you."):
            return
        global RESET_COUNT
        RESET_COUNT += 1
        save_meta()
        self.new_game()

    def show_menu(self):
        self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self.save_select_visible = False
        self.menu = True; self._last_spoken = None
        self.immersive_mode = False
        self.menu_hidden = True 
        if self.music_enabled: self._start_music()
        self.draw()
        
    def show_credits(self):
        self.menu = True; self.credits = True; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self.save_select_visible = False
        self.draw()
        
    def show_chapter_select(self):
        self.menu = True; self.credits = False; self.chapter_select = True; self.soundboard_visible = False; self.soundtrack_visible = False; self.save_select_visible = False
        self.draw()
        
    def show_soundboard(self):
        self.menu = True; self.credits = False; self.chapter_select = False; self.soundboard_visible = True; self.soundtrack_visible = False; self.save_select_visible = False
        self.draw()

    def show_soundtrack(self):
        self.menu = True; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = True; self.save_select_visible = False
        self.draw()

    def show_save_select(self, mode="load"):
        return_to_game = self.current_scene is not None and not self.menu
        if mode == "save":
            if not return_to_game:
                self.messagebox.showinfo(APP_NAME, "Start a story before saving.")
                return
            if self.temp_lines:
                self.messagebox.showinfo(APP_NAME, "Finish this dialogue before saving.")
                return
        self._save_return_to_game = return_to_game
        self.menu = True; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False
        self.save_select_visible = True
        self.save_mode = mode
        self.draw()

    def save_shortcut(self):
        if self.current_scene is not None and not self.menu:
            self.show_save_select(mode="save")

    def close_save_select(self):
        self.save_select_visible = False
        self.menu = not self._save_return_to_game
        self._save_return_to_game = False
        self.draw()

    def show_log(self):
        if not self.history: return
        win = self.tk.Toplevel(self.root)
        win.title("Dialogue History")
        win.geometry("600x500")
        win.configure(bg="#101722")
        text = self.tk.Text(win, bg="#1a2938", fg="#f4ead6", font=("Segoe UI", 11), wrap="word", padx=10, pady=10)
        text.pack(expand=True, fill="both", padx=10, pady=10)
        for speaker, txt in self.history:
            clean_txt = re.sub(r"\[.*?\]", "", txt)
            text.insert("end", f"【{speaker.replace('_EVIL', '')}】\n{clean_txt}\n\n", "speaker")
        text.tag_config("speaker", foreground="#d9bd82", font=("Segoe UI", 11, "bold"))
        text.config(state="disabled")

    def show_settings(self):
        win = self.tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("350x300")
        win.configure(bg="#101722")
        
        self.tk.Label(win, text="Audio Settings", bg="#101722", fg="#edcf88", font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        def update_music(val): self.music.volume = float(val); self.music._pygame.mixer.music.set_volume(self.music.volume) if self.music.available else None
        def update_sfx(val): self.soundboard.volume = float(val)
        def update_voice(val): self.voice.volume = float(val)
        
        for label, func, init in (("Music Volume", update_music, self.music.volume), 
                                   ("SFX Volume", update_sfx, self.soundboard.volume), 
                                   ("Voice Volume", update_voice, self.voice.volume)):
            self.tk.Label(win, text=label, bg="#101722", fg="#c5c0bd").pack()
            scale = self.tk.Scale(win, from_=0, to=1, resolution=0.1, orient="horizontal", command=func, bg="#1a2938", fg="#f4ead6", highlightthickness=0)
            scale.set(init)
            scale.pack(fill="x", padx=20, pady=5)

    def choose_chapter(self, index: int):
        if not 0 <= index <= self.highest_chapter or index >= len(CHAPTERS): return
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.history.clear(); self._char_offsets.clear()
        self.save_select_visible = False
        self._enter_scene(CHAPTERS[index].scene_id); self.line_index = 0; self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.play_scene_sfx(self.current_scene or ""); self.draw()

    def _start_music(self):
        try:
            track = CHAPTER_MUSIC.get(self.current_scene) if not self.menu and self.current_scene else None
            self.music.play(asset_path(*track.parts) if track is not None else None)
        except (OSError, FileNotFoundError) as error: self.music_enabled = False; self.music_error = str(error)

    def toggle_music(self):
        if not self.music.available: self.music_error = self.music.error or "Unavailable."; self.draw(); return
        if self.music_enabled:
            try: self.music.stop()
            except OSError as error: self.music_error = str(error); self.draw(); return
            self.music_enabled = False
        else: self.music_error = None; self.music_enabled = True; self._start_music()
        self.draw()

    def toggle_voice(self):
        if not self.voice.available: self.voice_error = self.voice.error or "Unavailable."; self.draw(); return
        self.voice_enabled = not self.voice_enabled
        self.draw()

    def toggle_sound_effects(self):
        self.sfx_enabled = not self.sfx_enabled
        if not self.sfx_enabled and self.music.available: self.music._pygame.mixer.stop()
        self.draw()

    def toggle_auto(self):
        self.auto_play = not self.auto_play
        if self.auto_play and not self.is_typing: self.root.after(1000, self._auto_advance)
        self.draw()

    def _auto_advance(self):
        if self.auto_play and not self.is_typing:
            self.advance()

    def play_scene_sfx(self, scene_id: str):
        if not self.menu and scene_id in CHAPTER_MUSIC and self.music_enabled: self._start_music()
        if not self.sfx_enabled: return
        cue = {"summoning": "summon", "first_impression": "wind", "coffee": "garden", "market": "footsteps", "knight_mistake": "sword", "archive": "pages", "training": "sword", "garden": "garden", "goblin_warning": "footsteps", "raid": "sword", "treaty": "hope", "goblin_home": "wind", "shadow": "wind", "war_council": "heartbeat", "sacrifice": "heartbeat", "grief": "heartbeat", "lira_maid": "pages", "return": "hope", "jealousy": "heartbeat", "confrontation": "heartbeat", "reconciliation": "hope", "trio": "garden", "assassination": "sword", "conspiracy": "footsteps", "healing": "garden", "prophecy": "pages", "winter_vigil": "wind", "storm": "wind", "final_battle": "sword", "ending_home": "hope", "ending_peace": "hope", "ending_cycle": "heartbeat", "ending_evil_kingdom": "sword", "ending_betrayal": "heartbeat"}
        sound_key = cue.get(scene_id)
        if sound_key: self.soundboard.play(sound_key)

    def play_effect(self, key: str):
        if self.sfx_enabled: self.soundboard.play(key)
        self.draw()

    def _start_typing(self, speaker, full_text):
        self._is_shaking_text = "[shake]" in full_text
        full_text = full_text.replace("[shake]", "").replace("[/shake]", "")
        
        self._text_color = "#f3eee5"
        if "[color=" in full_text:
            match = re.search(r"\[color=(.*?)\](.*?)\[/color\]", full_text)
            if match:
                self._text_color = match.group(1)
                full_text = re.sub(r"\[color=.*?\]|\[/color\]", "", full_text)
                
        if speaker == "Shadow" or "Mika" in speaker and "sacrifice" in self.current_scene or speaker == "Mika_Evil":
            self._trigger_shake(15, 5)
            
        self.full_text = full_text
        self.typing_idx = 0
        self.display_text = ""
        self.is_typing = True
        self._current_speaker = speaker
        self._type_char()

    def _type_char(self):
        if not self.is_typing or self.typing_idx >= len(self.full_text):
            self.is_typing = False
            self.display_text = self.full_text
            if self.text_id: self.canvas.itemconfigure(self.text_id, text=self.display_text)
            if self.auto_play: self.root.after(1500, self._auto_advance)
            return
        
        self.typing_idx += 1
        self.display_text = self.full_text[:self.typing_idx]
        if self.text_id: self.canvas.itemconfigure(self.text_id, text=self.display_text)
        
        if self.typing_idx % 2 == 0 and self.voice_enabled:
            self.voice.play_blip(self._current_speaker)
            
        self.root.after(self.typewriter_speed, self._type_char)

    def close(self):
        try: self.music.close()
        except OSError as error: self.messagebox.showerror(APP_NAME, f"Error:\n{error}")
        self.root.destroy()

    def _on_resize(self, event):
        width = max(820, int(getattr(event, "width", 1100))); height = max(600, int(getattr(event, "height", 740)))
        if (width, height) != self._canvas_size: 
            self._canvas_size = (width, height)
            if self.current_scene and not self.menu:
                self._reset_particles()
            self.draw()

    def _on_click(self, event):
        if self.menu and self.menu_hidden and not self.save_select_visible:
            self.menu_hidden = False
            self.draw()
            return

        item = self.canvas.find_withtag("current")
        clicked_button = False
        if item:
            tags = self.canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("choice_"): self.choose(int(tag.split("_", 1)[1])); return
                if tag.startswith("chapter_"):
                    chapter_key = tag.removeprefix("chapter_")
                    chapter_index = next((i for i, chapter in enumerate(CHAPTERS) if chapter.key == chapter_key), None)
                    if chapter_index is not None: self.choose_chapter(chapter_index)
                    return
                if tag.startswith("track_"):
                    chapter_key = tag.removeprefix("track_")
                    chapter = next((c for c in CHAPTERS if c.key == chapter_key), None)
                    if chapter:
                        track_path = CHAPTER_MUSIC.get(chapter.scene_id)
                        if track_path and self.music_enabled:
                            try: self.music.play(asset_path(*track_path.parts))
                            except Exception: pass
                    return
                if tag.startswith("effect_"): self.play_effect(tag.removeprefix("effect_")); return
                if tag.startswith("slot_"):
                    slot_num = int(tag.split("_")[1])
                    if self.save_mode == "save":
                        self.save_game(slot_num)
                    else:
                        self.load_game(slot_num)
                    return
                if tag.startswith("menu_"):
                    clicked_button = True
                    action = tag[5:]
                    if action == "new": self.new_game()
                    elif action == "continue": self.show_save_select(mode="load")
                    elif action == "chapters": self.show_chapter_select()
                    elif action == "soundtrack": self.show_soundtrack()
                    elif action == "soundboard": self.show_soundboard()
                    elif action == "credits": self.show_credits()
                    elif action == "settings": self.show_settings()
                    elif action == "sound": self.toggle_music()
                    elif action == "voice": self.toggle_voice()
                    elif action == "effects": self.toggle_sound_effects()
                    elif action == "back": self.show_menu()
                    elif action == "save_cancel": self.close_save_select()
                    elif action == "quit": self.close()
                    return
                if tag.startswith("control_"):
                    clicked_button = True
                    action = tag[8:]
                    if action == "save": self.show_save_select(mode="save")
                    elif action == "back": self.go_back()
                    elif action == "menu": self.show_menu()
                    elif action == "music": self.toggle_music()
                    elif action == "voice": self.toggle_voice()
                    elif action == "effects": self.toggle_sound_effects()
                    elif action == "chapters": self.show_chapter_select()
                    elif action == "soundboard": self.show_soundboard()
                    elif action == "auto": self.toggle_auto()
                    elif action == "log": self.show_log()
                    elif action == "settings": self.show_settings()
                    elif action == "reset": self.reset_game()
                    elif action == "skip": 
                        self.is_typing = False
                        self.display_text = self.full_text
                        self.advance()
                        self.advance()
                    return
                if tag == "advance":
                    scene = STORY[self.current_scene]
                    if scene.ending and self.line_index == len(scene.lines) - 1 and not self.temp_lines:
                        self.reset_game()
                    else:
                        self.advance()
                    return

        if not self.menu and not clicked_button and not self.chapter_select and not self.soundboard_visible and not self.soundtrack_visible and not self.credits:
            self.advance()

    def _enter_scene(self, scene_id: str):
        self.current_scene = scene_id
        chapter_index = next(index for index, chapter in enumerate(CHAPTERS) if chapter.scene_id == scene_id)
        self.highest_chapter = max(self.highest_chapter, chapter_index)
        
        scene = STORY[scene_id]
        for name in scene.cast:
            self._char_offsets[name] = 0
            
        if scene.backdrop != self._current_backdrop:
            self._current_backdrop = scene.backdrop
            self._reset_particles()

    def _next_scene(self, target: str):
        if target == "ending_gate": self._enter_scene(ending_for(self.flags))
        else: self._enter_scene(target)
        self.line_index = 0; self._last_spoken = None; self.play_scene_sfx(self.current_scene or "")

    def advance(self):
        if self.menu or self.current_scene is None: return
        
        if self.is_typing:
            self.is_typing = False
            self.display_text = self.full_text
            if self.text_id: self.canvas.itemconfigure(self.text_id, text=self.display_text)
            if self.auto_play: self.root.after(1500, self._auto_advance)
            return

        if self.temp_lines:
            self.temp_index += 1
            if self.temp_index >= len(self.temp_lines):
                target = self.pending_next_scene
                self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
                if target: self._next_scene(target)
                else: self.menu = True
            else:
                self.draw() 
            return

        scene = STORY[self.current_scene]
        if scene.choices and self.line_index >= len(scene.lines) - 1: return
        self._remember()
        if self.line_index < len(scene.lines) - 1:
            self.line_index += 1
            self.draw() 
        elif scene.next_scene is not None:
            self._next_scene(scene.next_scene); self.draw()
        elif scene.ending:
            self.menu = True; self._last_spoken = None
            if self.music_enabled: self._start_music()
            self.draw()

    def choose(self, index: int):
        if self.menu or self.current_scene is None or self.temp_lines: return
        scene = STORY[self.current_scene]
        if self.line_index < len(scene.lines) - 1 or index >= len(scene.choices): return
        choice = scene.choices[index]; self._remember()
        for name, value in choice.effects.items(): self.flags[name] += value
        
        if choice.outcome_lines:
            self.temp_lines = choice.outcome_lines
            self.temp_index = 0
            self.pending_next_scene = choice.next_scene
            self.draw()
        else:
            self._next_scene(choice.next_scene); self.draw()

    def go_back(self):
        if not self.undo_stack: return
        self._restore(self.undo_stack.pop())

    def _reset_particles(self):
        self.particles = []
        width, height = self._canvas_size
        backdrop = self._current_backdrop
        
        if backdrop in ("winter", "battle"):
            for _ in range(60):
                self.particles.append({"x": random.randint(0, width), "y": random.randint(0, height), "dx": random.randint(-2, 2), "dy": random.randint(3, 8), "color": "white" if backdrop == "winter" else "#ffaa00", "size": random.randint(1, 3)})
        elif backdrop == "archive":
            for _ in range(40):
                self.particles.append({"x": random.randint(0, width), "y": random.randint(0, height), "dx": random.uniform(-0.5, 0.5), "dy": random.uniform(-0.5, 0.5), "color": "#d9bd82", "size": random.randint(1, 2)})
        elif backdrop == "garden":
            for _ in range(30):
                self.particles.append({"x": random.randint(0, width), "y": random.randint(0, height), "dx": random.uniform(-1, 1), "dy": random.uniform(-1, 1), "color": "#88ff88", "size": random.randint(1, 2)})

    def _animate_idle(self):
        previous_offset = self._idle_offset
        self._idle_offset += self._idle_direction
        if self._idle_offset <= 0: self._idle_offset = 0; self._idle_direction = 1
        elif self._idle_offset >= 2: self._idle_offset = 2; self._idle_direction = -1
        delta_offset = self._idle_offset - previous_offset

        dx = dy = 0
        if self.shake_timer > 0:
            dx = random.randint(-self.shake_intensity, self.shake_intensity)
            dy = random.randint(-self.shake_intensity, self.shake_intensity)
            self.shake_timer -= 1

        if not self.menu and self.current_scene:
            width, height = self._canvas_size
            for i, p in enumerate(self.particles):
                p["x"] += p["dx"]
                p["y"] += p["dy"]
                if p["y"] > height: p["y"] = 0; p["x"] = random.randint(0, width)
                if p["y"] < 0: p["y"] = height; p["x"] = random.randint(0, width)
                if p["x"] > width: p["x"] = 0
                if p["x"] < 0: p["x"] = width
                self.canvas.coords(f"particle_{i}", p["x"], p["y"], p["x"]+p["size"], p["y"]+p["size"])

        for tag in self._animated_tags:
            self.canvas.move(tag, dx, dy - delta_offset)

        if self.text_id and self._is_shaking_text:
            tx = random.randint(-3, 3)
            ty = random.randint(-3, 3)
            self.canvas.move(self.text_id, tx, ty)

        self.root.after(220, self._animate_idle)

    def save_game(self, slot: int):
        if self.current_scene is None or self.temp_lines: return
        path = get_save_path(slot)
        
        chapter = CHAPTER_BY_SCENE.get(self.current_scene)
        title = f"Chapter {chapter.key} - {chapter.title}" if chapter else self.current_scene
        
        data = {
            "version": SAVE_VERSION, 
            "current_scene": self.current_scene, 
            "line_index": self.line_index, 
            "flags": self.flags, 
            "highest_chapter": self.highest_chapter,
            "preview_title": title,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        try: 
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            self.close_save_select()
        except OSError as e: 
            self.messagebox.showerror(APP_NAME, f"Failed to save:\n{e}")

    def load_game(self, slot: int):
        path = get_save_path(slot)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            scene_id = data["current_scene"]; line_index = data["line_index"]; flags = data["flags"]
            if not 0 <= line_index < len(STORY[scene_id].lines): raise ValueError()
            highest_chapter = data.get("highest_chapter", 0)
        except FileNotFoundError:
            self.messagebox.showinfo(APP_NAME, "This slot is empty.")
            return
        except Exception: 
            self.messagebox.showerror(APP_NAME, "Save file is corrupted.")
            return
        
        self.undo_stack.clear(); self._enter_scene(scene_id); self.line_index = line_index; self.flags = flags; self.highest_chapter = max(highest_chapter, self.highest_chapter)
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self.save_select_visible = False; self._last_spoken = None
        self._save_return_to_game = False
        self.history.clear()
        self.play_scene_sfx(scene_id); self.draw()

    def _button(self, x, y, width, height, label, tag, font_size=15):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill="#101722", outline="#c4a879", width=1, tags=(tag,))
        self.canvas.create_text(x + width / 2, y + height / 2, text=label, fill="#e0d5c1", font=("Georgia", font_size), tags=(tag,), width=width - 8)

    def _draw_background(self, backdrop: str, width: int, height: int):
        self.canvas.create_rectangle(0, 0, width, height, fill="#06080a", outline="")
        if not HAS_PIL: return
        filename = f"{backdrop}.png"; image_path = None; base_dir = Path(__file__).resolve().parent
        
        for folder in ["assets/backgrounds", "assets", "backgrounds", "images", ""]:
            p = base_dir / folder / filename if folder else base_dir / filename
            if p.exists(): image_path = p; break
        
        if not image_path: return
        cache_key = (str(image_path), width, height)
        if cache_key not in self._bg_cache:
            try:
                original = Image.open(image_path); orig_w, orig_h = original.size
                scale = max(width / orig_w, height / orig_h)
                target_w = int(orig_w * scale); target_h = int(orig_h * scale)
                resized = original.resize((target_w, target_h), Image.Resampling.LANCZOS)
                left = (target_w - width) // 2; top = (target_h - height) // 2
                cropped = resized.crop((left, top, left + width, top + height))
                self._bg_cache[cache_key] = ImageTk.PhotoImage(cropped)
            except Exception: return
        
        self.canvas.create_image(0, 0, image=self._bg_cache[cache_key], anchor="nw")
        overlay = Image.new("RGBA", (width, height), (6, 8, 10, 160))
        self._bg_cache[("overlay", width, height)] = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(0, 0, image=self._bg_cache[("overlay", width, height)], anchor="nw")

    def _draw_particles(self):
        for i, p in enumerate(self.particles):
            self.canvas.create_oval(p["x"], p["y"], p["x"]+p["size"], p["y"]+p["size"], fill=p["color"], outline="", tags=(f"particle_{i}",))

    def _draw_character(self, name: str, x: float, ground: float, width: int, index: int, scale_factor: float = 1.0):
        sprite_tag = f"sprite_{index}"
        self._animated_tags.append(sprite_tag)
        
        filename_map = {
            "Mika": "Mika",
            "Mika Amanogawa": "Mika",
            "Mallory": "Mallory",
            "Mallory Valerius": "Mallory",
            "King Galvath": "Galvath",
            "King Galvath Valerius": "Galvath",
            "Lira": "Lira",
            "Lira Vanguard": "Lira",
            "Gorthak": "Gorthak",
            "Gorthak Stonefist": "Gorthak",
            "Vane": "Vane",
            "Vane Blackwood": "Vane",
            "Shadow": "shadow",
            "Mika_Evil": "Mika_Evil"
        }
        base_name = filename_map.get(name, name)
        
        display_name = "Mika" if name == "Mika_Evil" else name
        
        expression = ""
        if name in ("Mika", "Mika Amanogawa") and self.current_scene in {"grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"}: expression = "_sad"
        elif name in ("Mika", "Mika Amanogawa") and self.current_scene in {"ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"}: expression = "_happy"
        elif name in ("Mallory", "Mallory Valerius") and self.current_scene in {"grief", "lira_maid", "sacrifice"}: expression = "_sad"

        base_dir = Path(__file__).resolve().parent
        def find_file(fn):
            for folder in ["assets/characters", "assets", "characters", "images", "sprites", ""]:
                p = base_dir / folder / fn if folder else base_dir / fn
                if p.exists(): return p
            return None

        img_path = find_file(f"{base_name}{expression}.png") or find_file(f"{base_name}.png")
        
        if not img_path:
            self.canvas.create_rectangle(x-100, ground-250, x+100, ground, fill="#1a2938", outline="#c4a879", width=2, tags=(sprite_tag,))
            self.canvas.create_text(x, ground-125, text=display_name, fill="#e0d5c1", font=("Georgia", 20, "bold"), tags=(sprite_tag,))
            self.canvas.create_text(x, ground-100, text="[Portrait Missing]", fill="#8c8478", font=("Segoe UI", 10), tags=(sprite_tag,))
            self.canvas.create_text(x, ground + 15, text=display_name, fill="#e0d5c1", font=("Segoe UI", 11, "bold"), tags=(sprite_tag,))
            return

        if not HAS_PIL: return

        cache_key = (str(img_path), width, ground, scale_factor)
        
        if cache_key not in self._image_cache:
            try:
                original = Image.open(img_path).convert("RGBA")
                bbox = original.getchannel("A").getbbox()
                if bbox: original = original.crop(bbox)
                orig_w, orig_h = original.size
                
                available_height = ground - 70 
                target_height = int(available_height * 0.80 * scale_factor)
                ratio = orig_w / orig_h
                target_width = int(target_height * ratio)
                
                resized = original.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self._image_cache[cache_key] = ImageTk.PhotoImage(resized)
            except Exception as e: 
                print(f"Char Error {img_path.name}: {e}")
                return

        tk_image = self._image_cache[cache_key]
        ground -= self._idle_offset
        self.canvas.create_image(x, ground, image=tk_image, anchor="s", tags=(sprite_tag,))
        self.canvas.create_text(x, ground + 15, text=display_name, fill="#e0d5c1", font=("Segoe UI", 11, "bold"), tags=(sprite_tag,))

    def _draw_menu(self, width: int, height: int):
        backdrop = "archive" if self.chapter_select or self.soundtrack_visible else "winter" if self.soundboard_visible else "garden"
        self._draw_background(backdrop, width, height)
        
        if self.save_select_visible:
            self.canvas.create_rectangle(0, 0, width, height, fill="#06080a", stipple="gray50", outline="")
            self.canvas.create_text(width/2, height*0.15, text="SAVE GAME" if self.save_mode == "save" else "LOAD GAME", fill="#edcf88", font=("Georgia", 24, "bold"))
            
            for i in range(1, 4):
                slot_path = get_save_path(i)
                slot_data = None
                if slot_path.exists():
                    try: slot_data = json.loads(slot_path.read_text(encoding="utf-8"))
                    except Exception: pass
                
                title = slot_data.get("preview_title", "Unknown Chapter") if slot_data else "Empty Slot"
                date = slot_data.get("timestamp", "") if slot_data else ""
                
                y = height * 0.25 + (i-1) * 100
                btn_w, btn_h = min(600, width * 0.6), 80
                x = (width - btn_w) / 2
                
                self.canvas.create_rectangle(x, y, x + btn_w, y + btn_h, fill="#101722", outline="#c4a879", width=1, tags=(f"slot_{i}",))
                self.canvas.create_text(x + 20, y + 25, anchor="w", text=f"Slot {i}", fill="#e0d5c1", font=("Georgia", 16, "bold"), tags=(f"slot_{i}",))
                
                text_color = "#f5e9d2" if slot_data else "#4a505c"
                self.canvas.create_text(x + 20, y + 55, anchor="w", text=title, fill=text_color, font=("Segoe UI", 12), tags=(f"slot_{i}",))
                
                if slot_data:
                    self.canvas.create_text(x + btn_w - 20, y + 55, anchor="e", text=date, fill="#8c8478", font=("Segoe UI", 10), tags=(f"slot_{i}",))
                    
            self._button(width / 2 - 100, height - 80, 200, 40, "CANCEL", "menu_save_cancel", 12)
            return

        if not self.chapter_select and not self.soundboard_visible and not self.soundtrack_visible and not self.credits: 
            self._draw_coverpage(width, height); return
            
        self.canvas.create_rectangle(0, 0, width, 62, fill="#06080a", outline="#c4a879", width=2)
        self.canvas.create_text(width / 2, 26, text=APP_NAME.upper(), fill="#f5e9d2", font=("Georgia", min(32, max(20, width // 45)), "bold"))

        if self.credits:
            self.canvas.create_rectangle(0, height * 0.59, width, height, fill="#06080a", outline="#c4a879", width=2)
            self.canvas.create_text(width / 2, height * 0.65, text="CREDITS", fill="#edcf88", font=("Georgia", 21, "bold"))
            self.canvas.create_text(width / 2, height * 0.72, text="Story & Visual Novel Creator", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.77, text="Phantom Nightmare Developer", fill="#fff4de", font=("Georgia", 17, "bold"))
            self.canvas.create_text(width / 2, height * 0.83, text="Original soundtrack and lyrics by:", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.88, text="Phantom Nightmare Developer", fill="#e6d6b8", font=("Segoe UI", 13, "bold"))
            self._button(width / 2 - 110, height * 0.51, 220, 34, "BACK TO TITLE", "menu_back", 10)
            return

        if self.chapter_select:
            self.canvas.create_rectangle(0, 62, width, height - 36, fill="#06080a", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 105, text="CHAPTER SELECT", fill="#edcf88", font=("Georgia", 19, "bold"))
            
            column_gap = 20
            column_width = (width - 60 - column_gap * 2) / 3
            
            for column in range(3):
                x = 30 + column * (column_width + column_gap)
                button_top = 150
                for arc in (ARCS[column * 2], ARCS[column * 2 + 1]):
                    self.canvas.create_text(x + 4, button_top, anchor="nw", text=arc, fill="#edcf88", font=("Segoe UI", 9, "bold"), width=column_width - 8)
                    button_top += 27
                    for chapter_index, chapter in enumerate(CHAPTERS):
                        if chapter.arc != arc: continue
                        unlocked = chapter_index <= self.highest_chapter
                        self._button(x, button_top, column_width, 30, f"{chapter.key}  {chapter.title}" if unlocked else f"{chapter.key}  LOCKED", f"chapter_{chapter.key}" if unlocked else "locked", 9)
                        button_top += 35
                    button_top += 5
            self._button(width / 2 - 105, height - 33, 210, 27, "BACK TO TITLE", "menu_back", 9)
            return

        if self.soundboard_visible:
            self.canvas.create_rectangle(0, 62, width, height - 38, fill="#06080a", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 105, text="VALLHELM SOUND LIBRARY", fill="#edcf88", font=("Georgia", 19, "bold"))
            columns = 2; button_width = min(410, (width - 110) / columns)
            for index, (key, label) in enumerate(SOUND_EFFECTS):
                x = (width - (2 * button_width + 16)) / 2 + (index % columns) * (button_width + 16)
                y = height * 0.25 + (index // columns) * 77
                self._button(x, y, button_width, 52, f"PLAY  ·  {label}", f"effect_{key}", 12)
            self._button(width / 2 - 105, height - 43, 210, 30, "BACK TO TITLE", "menu_back", 9)
            return

        if self.soundtrack_visible:
            self.canvas.create_rectangle(0, 62, width, height - 38, fill="#06080a", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 105, text="SOUNDTRACK LIST", fill="#edcf88", font=("Georgia", 19, "bold"))
            columns = 3; button_width = (width - 80) / columns; button_height = 30
            for index, chapter in enumerate(CHAPTERS):
                col = index % columns; row = index // columns
                x = 40 + col * button_width; y = 150 + row * (button_height + 8)
                self._button(x, y, button_width - 10, button_height, f"{chapter.key} - {chapter.title}", f"track_{chapter.key}", 10)
            self._button(width / 2 - 105, height - 43, 210, 30, "BACK TO TITLE", "menu_back", 9)
            return

        self.canvas.create_rectangle(0, height * 0.55, width, height, fill="#06080a", outline="#c4a879", width=2)
        button_w, button_h = min(320, width * 0.46), 34; start_x = (width - button_w) / 2
        actions = (("NEW STORY", "new"), ("CONTINUE", "continue"), ("CHAPTER SELECT", "chapters"), ("SOUNDTRACK", "soundtrack"), ("SETTINGS", "settings"), ("CREDITS", "credits"), ("QUIT", "quit"))
        for index, (label, action) in enumerate(actions):
            self._button(start_x, height * 0.60 + index * 35, button_w, button_h, label, f"menu_{action}", 10)

    def _draw_coverpage(self, width: int, height: int):
        self.canvas.create_rectangle(0, 0, width, height, fill="#030406", outline="")
        
        cx, cy = width / 2, height * 0.35
        
        self.canvas.create_oval(cx - 200, cy - 200, cx + 200, cy + 200, outline="#1a2233", width=1)
        self.canvas.create_oval(cx - 170, cy - 170, cx + 170, cy + 170, outline="#a78b58", width=1, dash=(4, 8))
        self.canvas.create_oval(cx - 140, cy - 140, cx + 140, cy + 140, outline="#1a2233", width=1)
        
        self.canvas.create_line(cx - 220, cy, cx + 220, cy, fill="#1a2233", width=1)
        self.canvas.create_line(cx, cy - 220, cx, cy + 220, fill="#1a2233", width=1)
        
        self.canvas.create_polygon(cx, cy - 190, cx + 10, cy - 180, cx, cy - 170, cx - 10, cy - 180, fill="#a78b58", outline="")
        self.canvas.create_polygon(cx, cy + 190, cx + 10, cy + 180, cx, cy + 170, cx - 10, cy + 180, fill="#a78b58", outline="")
        
        self.canvas.create_text(cx, cy - 40, text="E C H O E S   O F   T H E", fill="#8c8478", font=("Georgia", 14))
        self.canvas.create_text(cx, cy + 20, text="FIFTY SIX WORLDS", fill="#f5e9d2", font=("Georgia", 45, "bold"))
        self.canvas.create_text(cx, cy + 75, text="R E Q U I E M   O F   T H E   M A I D", fill="#a78b58", font=("Georgia", 11, "bold"))
        
        self.canvas.create_line(cx - 260, cy + 60, cx - 110, cy + 60, fill="#a78b58", width=1)
        self.canvas.create_line(cx + 110, cy + 60, cx + 260, cy + 60, fill="#a78b58", width=1)
        
        rng = random.Random(42)
        for _ in range(40):
            px, py = rng.randrange(width), rng.randrange(height)
            radius = rng.choice((1, 1, 2))
            self.canvas.create_oval(px, py, px + radius, py + radius, fill="#3a4559", outline="")
        
        if self.menu_hidden:
            self.canvas.create_text(
                width / 2, height * 0.85, text="Click or press any key", 
                fill="#4a505c", font=("Segoe UI", 10), justify="center"
            )
            return
            
        button_width = min(300, width * 0.3)
        button_height = 35
        button_gap = 10
        start_y = height * 0.53
        
        actions = (
            ("START GAME", "new"), 
            ("CONTINUE", "continue"), 
            ("CHAPTER SELECT", "chapters"), 
            ("SOUNDTRACK", "soundtrack"), 
            ("SETTINGS", "settings"), 
            ("CREDITS", "credits"), 
            ("QUIT", "quit")
        )
        
        for index, (label, action) in enumerate(actions):
            x = (width - button_width) / 2
            y = start_y + index * (button_height + button_gap)
            self._button(x, y, button_width, button_height, label, f"menu_{action}", 12)

    def draw(self):
        width, height = self._canvas_size
        self.canvas.delete("all"); self._animated_tags = []
        
        if self.menu or self.current_scene is None: self._draw_menu(width, height); return

        scene = STORY[self.current_scene]
        self._draw_background(scene.backdrop, width, height)
        self._draw_particles()
        chapter = CHAPTER_BY_SCENE[self.current_scene]
        
        if not self.immersive_mode:
            self.canvas.create_rectangle(0, 0, width, 70, fill="#06080a", outline="#c4a879", width=1)
            self.canvas.create_text(24, 13, anchor="nw", text=f"ARC  {chapter.arc}", fill="#e8c779", font=("Segoe UI", 9, "bold"))
            self.canvas.create_text(24, 38, anchor="nw", text=f"CHAPTER {chapter.key}  ·  {chapter.title.upper()}", fill="#f1e5ce", font=("Segoe UI", 11, "bold"))
            
            rep = self.flags.get("reputation", 0)
            if rep >= 2: rep_text, rep_color = "GOOD", "#4ade80"
            elif rep <= -2: rep_text, rep_color = "BAD", "#f87171"
            else: rep_text, rep_color = "NEUTRAL", "#fbbf24"
            self.canvas.create_text(24, 55, anchor="nw", text=f"REPUTATION: {rep_text}", fill=rep_color, font=("Segoe UI", 9, "bold"))
            
            controls = (
                ("CHAPTERS", "control_chapters", 75), 
                ("AUTO", "control_auto", 50),
                ("SKIP", "control_skip", 50),
                ("LOG", "control_log", 45),
                ("SETTINGS", "control_settings", 70),
                ("FX", "control_soundboard", 40), 
                ("VOICE", "control_voice", 55), 
                ("MUSIC", "control_music", 50), 
                ("SAVE", "control_save", 45), 
                ("RESET", "control_reset", 55),
                ("MENU", "control_menu", 45)
            )
            total = sum(button_width for _label, _tag, button_width in controls) + 6 * (len(controls) - 1)
            x = width - total - 14
            for label, tag, button_width in controls:
                self.canvas.create_rectangle(x, 18, x + button_width, 34 + 18, fill="#101722", outline="#c4a879", width=1, tags=(tag,))
                self.canvas.create_text(x + button_width / 2, 18 + 34 / 2, text=label, fill="#4ade80" if self.auto_play and label == "AUTO" else "#e0d5c1", font=("Segoe UI", 8, "bold"), tags=(tag,), width=button_width - 8)
                x += button_width + 6

        ready_for_choice = bool(scene.choices) and not self.temp_lines and self.line_index == len(scene.lines) - 1
        panel_top = height * (0.56 if ready_for_choice else 0.72)
        stage_ground = panel_top
        cast = scene.cast
        if cast:
            n = len(cast)
            
            if n == 1: scale_factor = 1.0
            elif n == 2: scale_factor = 0.85
            elif n == 3: scale_factor = 0.70
            else: scale_factor = 0.55
            
            if self.immersive_mode:
                scale_factor *= 0.9
            
            if n == 1:
                positions = [width * 0.5]
            elif n == 2:
                positions = [width * 0.3, width * 0.7]
            elif n == 3:
                positions = [width * 0.2, width * 0.5, width * 0.8]
            else:
                positions = [width * 0.15, width * 0.38, width * 0.62, width * 0.85]
                
            for index, name in enumerate(cast):
                self._draw_character(name, positions[index], stage_ground, width, index, scale_factor)

        if not self.immersive_mode:
            self.canvas.create_rectangle(0, panel_top, width, height, fill="#06080a", outline="#c4a879", width=2)
        else:
            self.canvas.create_rectangle(0, panel_top, width, height, fill="#06080a", stipple="gray50", outline="")
        
        if self.temp_lines:
            active_lines = self.temp_lines
            active_index = min(self.temp_index, len(active_lines) - 1)
            line = active_lines[active_index]
        else:
            active_lines = scene.lines
            active_index = min(self.line_index, len(active_lines) - 1)
            line = active_lines[active_index]
            
        final_text = resolve_text(line.text, self.flags)
        
        speaker_text = line.speaker.upper().replace("_EVIL", "")
        self.canvas.create_text(34, panel_top + 17, anchor="nw", text=speaker_text, fill="#d9bd82", font=("Segoe UI", 11, "bold"))
        text_font_size = max(12, round(width / 73))
        self.text_id = self.canvas.create_text(34, panel_top + 43, anchor="nw", text="", fill=self._text_color, font=("Segoe UI", text_font_size), width=width - 68)
        
        if ready_for_choice:
            self.is_typing = False 
            self.display_text = re.sub(r"\[.*?\]", "", final_text)
            self.canvas.itemconfigure(self.text_id, text=self.display_text)
            choice_count = len(scene.choices)
            button_h = min(38, max(25, (height - panel_top - 45 - 7 * (choice_count - 1)) / choice_count))
            choice_start_y = height - 18 - choice_count * button_h - 7 * (choice_count - 1)
            text_bottom_limit = choice_start_y - 12
            for font_size in range(text_font_size, 7, -1):
                self.canvas.itemconfigure(self.text_id, font=("Segoe UI", font_size))
                bbox = self.canvas.bbox(self.text_id)
                if bbox is None or bbox[3] <= text_bottom_limit:
                    break

            for index, choice in enumerate(scene.choices):
                self._button(34, choice_start_y + index * (button_h + 7), width - 68, button_h, f"{index + 1}. {choice.text}", f"choice_{index}", 12)
        else:
            if self.temp_lines and self.temp_index == len(self.temp_lines) - 1:
                label = "CONTINUE  >>"
            elif scene.ending and self.line_index == len(scene.lines) - 1 and not self.temp_lines:
                label = "RESET TIMELINE"
            else:
                label = "CONTINUE  >"
            
            if not self.immersive_mode:
                self._button(width - 210, height - 53, 176, 35, label, "advance", 10)
            
            if not self.history or self.history[-1] != (line.speaker, final_text):
                self.history.append((line.speaker, final_text))
            
            if self._last_spoken != (self.current_scene, self.line_index, self.temp_index):
                self._last_spoken = (self.current_scene, self.line_index, self.temp_index)
                self._start_typing(line.speaker, final_text)
            else:
                self.canvas.itemconfigure(self.text_id, text=self.display_text)

        if not self.immersive_mode and not ready_for_choice:
            self.canvas.create_text(34, height - 21, anchor="w", text="Click anywhere to advance   •   Press H for Immersive Mode   •   Space: continue   •   Backspace: undo", fill="#8c8478", font=("Segoe UI", 8))

def run():
    game = VisualNovel(); game.root.mainloop()

def main():
    global RESET_COUNT
    load_meta()
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--validate-story", action="store_true")
    args = parser.parse_args()
    if args.validate_story: print(f"Story validated: {validate_story()} scenes."); return 0
    run(); return 0

if __name__ == "__main__":
    if os.environ.get("ANDROID_ARGUMENT"):
        sys.modules.setdefault("main", sys.modules[__name__])
        from mobile_app import AndroidNovelApp
        AndroidNovelApp().run()
    else:
        raise SystemExit(main())