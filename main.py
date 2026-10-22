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

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

APP_NAME = "Fifty-Six Lives"
SAVE_VERSION = 3
FLAG_NAMES = {"bond", "peace", "resolve", "family_final", "reputation"}

@dataclass(frozen=True)
class Line:
    speaker: str
    text: str | tuple[str, str, str]

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

def resolve_text(text: str | tuple[str, str, str], flags: dict[str, int]) -> str:
    if isinstance(text, str): return text
    rep = flags.get("reputation", 0)
    if rep >= 2: return text[0]
    elif rep <= -2: return text[2]
    else: return text[1]

STORY: dict[str, Scene] = {
    "summoning": Scene(
        "The Summoning", "throne", ("Mallory", "Mika"),
        (
            Line("Narration", "The grand hall of Vallhelm is suffocatingly silent, save for the crackling hum of the summoning circle etched into the marble floor."),
            Line("Narration", "A flash of blinding, golden light erupts from the center of the runes. The shockwave knocks the mages off their feet. When the smoke clears, the court gasps."),
            Line("Narration", "Instead of a towering, armored warrior, a young woman stands in the center of the circle. She is wearing a simple, black-and-white maid's uniform."),
            Line("Mika", "Whoa! What the—? Where am I? This is definitely not the hotel hallway I was just cleaning."),
            Line("King Galvath", "A servant! The prophecy promised a champion, and the heavens send us a scullery maid! This is a mockery!"),
        ),
        (
            Choice(
                text="Step forward and offer to help her", 
                next_scene="first_impression", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mallory", "Father, please! Silence! The circle responded to her. The magic recognized her soul."),
                    Line("Mika", "Thanks for the save. I'm Mika, by the way. Nice to meet someone here who isn't yelling at me."),
                    Line("Mallory", "I am Mallory. And I have a feeling we are going to need each other."),
                )
            ),
            Choice(
                text="Stand your ground and demand respect", 
                next_scene="first_impression", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika", "I can hear you, you know. I'm standing right here. And for the record, I've handled worse messes than a few angry soldiers."),
                    Line("Narration", "The court gasps at her defiance. The King's face turns crimson with rage."),
                    Line("Mallory", "Silence! The circle responded to her. We cannot dismiss her just because she doesn't look like a knight."),
                )
            ),
        ),
    ),
    "first_impression": Scene(
        "The Wrong Hero", "throne", ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "The court's disappointment sharpens into suspicion. A seasoned captain of the guard steps forward, pointing his spear at Mika."),
            Line("King Galvath", "If the ritual brought a servant, then it has failed us. We need a champion who can wield a blade."),
            Line("Mika", "I'm right here, you know. I have a name. It's Mika."),
        ),
        (
            Choice(
                text="Apologize and try to explain", 
                next_scene="coffee", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika", "Look, I don't know how I got here, but I'm not your enemy. I just want to go home."),
                    Line("Narration", "The King hesitates, his expression softening slightly at her calm tone."),
                    Line("Mallory", "Let us speak in the gardens, away from this hostility."),
                )
            ),
            Choice(
                text="Tell the King to shut up", 
                next_scene="coffee", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika", "Maybe if your kingdom wasn't such a mess, the heavens wouldn't have sent a maid. Ever think of that?"),
                    Line("Narration", "The guards tighten their grip on their weapons. The air grows cold, and the nearest torch gutters out."),
                    Line("Mallory", "Guards, to me! We need to get her out of here before this turns into a bloodbath."),
                )
            ),
        ),
    ),
    "coffee": Scene(
        "A Cup Before the Storm", "garden", ("Mallory", "Mika"),
        (
            Line("Narration", "Mallory walks Mika out of the echoing throne room and into the quiet, sprawling palace gardens."),
            Line("Narration", "They sit on a stone bench near a gently bubbling fountain. The distant sound of the panicked court fades away."),
            Line("Mallory", "I apologize for my father. He is terrified. We all are. But I am not ready to give up on you yet."),
        ),
        (
            Choice(
                text="Offer to help her anyway", 
                next_scene="market", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika", "It's okay. I'm used to people underestimating me. Let me see what I can do to help."),
                    Line("Mallory", "You are a rare soul, Mika."),
                )
            ),
            Choice(
                text="Demand to be sent home immediately", 
                next_scene="market", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika", "I don't care about your war. I want to go home. Now."),
                    Line("Mallory", "I... I don't know how to send you back. The ritual only works one way."),
                    Line("Mika", "Then find a way. Or I'll find it myself."),
                )
            ),
        ),
    ),
    "market": Scene(
        "The City Market", "garden", ("Mallory", "Mika"),
        (
            Line("Narration", "Before the sun rises, Mallory disguises herself in a heavy cloak and takes Mika into the lower city."),
            Line("Mika", "The people are scared. I used to clean rooms for people who never looked me in the eye."),
            Line("Narration", "A small child bumps into Mika, dropping a basket of apples. The fruit scatters."),
        ),
        (
            Choice(
                text="Help the child gather the apples", 
                next_scene="knight_mistake", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Here you go, little one. Be careful."), 
                    Line("Mallory", "You have a gentle heart."),
                )
            ),
            Choice(
                text="Ignore the child and keep walking", 
                next_scene="knight_mistake", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Watch where you're going."), 
                    Line("Mallory", "That was cold, Mika."),
                )
            ),
        ),
    ),
    "knight_mistake": Scene(
        "The Knight's Mistake", "throne", ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Back at the palace, a frightened young guard lunges at Mika with a spear."),
            Line("Narration", "Mika pivots, sidesteps the thrust, and snaps the spear in two with her bare hands."),
            Line("Lira", "Enough! Stand down, soldier! She could have broken your arm."),
        ),
        (
            Choice(
                text="Forgive the guard", 
                next_scene="archive", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I know what fear makes people do. It's okay."), 
                    Line("Lira", "You have my respect."),
                )
            ),
            Choice(
                text="Threaten the guard", 
                next_scene="archive", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "If he tries that again, I won't be so gentle."), 
                    Line("Lira", "Watch your tongue, Maid."),
                )
            ),
        ),
    ),
    "archive": Scene(
        "The Ancient Record", "archive", ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "King Galvath opens a massive, ancient tome bound in dragon leather."),
            Line("King Galvath", "This book names you, Mika. It describes fifty-five lives before this one."),
            Line("Mika", "Fifty-five lives? You mean I've done this before?"),
        ),
        (
            Choice(
                text="Accept the responsibility", 
                next_scene="training", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Then let this life belong to me. I will help you."), 
                    Line("Mallory", "Thank you, Mika."),
                )
            ),
            Choice(
                text="Refuse the prophecy", 
                next_scene="training", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I am not a pawn. I won't be your sacrifice."), 
                    Line("Mallory", "Please, Mika. We need you."),
                )
            ),
        ),
    ),
    "training": Scene(
        "Sparring with Lira", "throne", ("Mika", "Lira"), 
        (
            Line("Narration", "Lira swings her sword, but Mika holds her ground."), 
            Line("Lira", "Your footwork is sloppy!"), 
            Line("Mika", "A mop can be dangerous too!"),
        ), 
        (
            Choice(
                text="Help Lira up", 
                next_scene="garden", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Good match."), 
                    Line("Lira", "You are full of surprises."),
                )
            ), 
            Choice(
                text="Gloat over her", 
                next_scene="garden", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Not so tough now, are you?"), 
                    Line("Lira", "Don't push your luck."),
                )
            ),
        )
    ),
    "garden": Scene(
        "A Quiet Afternoon", "garden", ("Mallory", "Mika"), 
        (
            Line("Narration", "Days pass. Mallory leads Mika to a hidden garden."), 
            Line("Mallory", "This was my mother's favorite place."), 
            Line("Mika", "It's beautiful."),
        ), 
        (
            Choice(
                text="Open up to Mallory", 
                next_scene="goblin_warning", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I used to think my life was boring. Now I miss it."), 
                    Line("Mallory", "You make this place feel like home too."),
                )
            ), 
            Choice(
                text="Keep your distance", 
                next_scene="goblin_warning", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'm not here to make friends."), 
                    Line("Mallory", "I see."),
                )
            ),
        )
    ),
    "goblin_warning": Scene(
        "Tracks at the Orchard", "farm", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The orchard fence is cut from the inside."), 
            Line("Mika", "Someone wants us to blame the goblins."), 
            Line("Lira", "We should report this."),
        ), 
        (
            Choice(
                text="Investigate quietly", 
                next_scene="raid", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We need evidence."), 
                    Line("Mallory", "Agreed."),
                )
            ), 
            Choice(
                text="Report to the King", 
                next_scene="raid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Let the army handle it."), 
                    Line("Lira", "As you wish."),
                )
            ),
        )
    ),
    "raid": Scene(
        "The Goblin Raid", "farm", ("Mika", "Gorthak", "Mallory"), 
        (
            Line("Narration", "Goblins storm the countryside."), 
            Line("Gorthak", "Our village is starving!"), 
            Line("Mallory", "What do we do?"),
        ), 
        (
            Choice(
                text="Hear them out", 
                next_scene="treaty", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Put down your weapons."), 
                    Line("Gorthak", "You are strange."),
                )
            ), 
            Choice(
                text="Attack", 
                next_scene="treaty", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Drive them back!"), 
                    Line("Gorthak", "We will remember this!"),
                )
            ),
        )
    ),
    "treaty": Scene(
        "A Language of Understanding", "throne", ("Gorthak", "Mika", "Mallory"), 
        (
            Line("Narration", "Mika forces both sides to negotiate."), 
            Line("Gorthak", "Give us a chance."), 
            Line("King Galvath", "Ally with goblins?"),
        ), 
        (
            Choice(
                text="Push for peace", 
                next_scene="goblin_home", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We need them."), 
                    Line("Gorthak", "You speak like an angel."),
                )
            ), 
            Choice(
                text="Suggest a truce", 
                next_scene="goblin_home", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Only a truce."), 
                    Line("Gorthak", "Cautious."),
                )
            ),
        )
    ),
    "goblin_home": Scene(
        "A Village at the Edge", "farm", ("Gorthak", "Mika", "Mallory"), 
        (
            Line("Narration", "Mika visits the goblin village."), 
            Line("Gorthak", "We were desperate."), 
            Line("Mika", "Someone poisoned your wells."),
        ), 
        (
            Choice(
                text="Sympathize", 
                next_scene="shadow", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We'll fix this."), 
                    Line("Gorthak", "Thank you."),
                )
            ), 
            Choice(
                text="Demand answers", 
                next_scene="shadow", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Who did this?"), 
                    Line("Gorthak", "We don't know!"),
                )
            ),
        )
    ),
    "shadow": Scene(
        "The Demon Lord's Shadow", "battle", ("Mika", "Mallory", "Gorthak"), 
        (
            Line("Narration", "The Demon Lord's army gathers."), 
            Line("Mallory", "We are with you."), 
            Line("Mika", "Let's end this."),
        ), 
        (
            Choice(
                text="Lead together", 
                next_scene="war_council", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We fight as one."), 
                    Line("Gorthak", "For Vallhelm!"),
                )
            ), 
            Choice(
                text="Lead alone", 
                next_scene="war_council", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'll handle this."), 
                    Line("Mallory", "Be careful."),
                )
            ),
        )
    ),
    "war_council": Scene(
        "The Empty Place at Council", "throne", ("King Galvath", "Mallory", "Mika", "Gorthak"), 
        (
            Line("Narration", "Maps covered in ash."), 
            Line("King Galvath", "It's a trap."), 
            Line("Mallory", "We fight together."),
        ), 
        (
            Choice(
                text="Plan together", 
                next_scene="sacrifice", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We use the terrain."), 
                    Line("Mallory", "Smart."),
                )
            ), 
            Choice(
                text="Charge in", 
                next_scene="sacrifice", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "We attack now."), 
                    Line("King Galvath", "Reckless!"),
                )
            ),
        )
    ),
    "sacrifice": Scene(
        "The Cost of Victory", "battle", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The battle is brutal."), 
            Line("Mika", "Get behind me!"), 
            Line("Narration", "Mika collapses."),
        ), 
        (
            Choice(
                text="Hold on for them", 
                next_scene="grief", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mallory", "Stay with us!"), 
                    Line("Narration", "Mika fades."),
                )
            ), 
            Choice(
                text="Let go", 
                next_scene="grief", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'm sorry..."), 
                    Line("Narration", "She is gone."),
                )
            ),
        )
    ),
    "grief": Scene(
        "After the Battle", "infirmary", ("Mallory", "Lira"), 
        (
            Line("Narration", "Vallhelm mourns."), 
            Line("Lira", "You must eat."), 
            Line("Mallory", "I failed her."),
        ), 
        (
            Choice(
                text="Comfort her", 
                next_scene="lira_maid", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Lira", "I'm here."), 
                    Line("Mallory", "Thank you."),
                )
            ), 
            Choice(
                text="Leave her be", 
                next_scene="lira_maid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Lira", "As you wish."), 
                    Line("Mallory", "..."),
                )
            ),
        )
    ),
    "lira_maid": Scene(
        "The New Maid", "infirmary", ("Mallory", "Lira"), 
        (
            Line("Narration", "Lira becomes the maid."), 
            Line("Mallory", "It's not a replacement."), 
            Line("Lira", "I understand."),
        ), 
        (
            Choice(
                text="Accept Lira", 
                next_scene="return", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Lira", "I'll do my best."), 
                    Line("Mallory", "I know."),
                )
            ), 
            Choice(
                text="Resent Lira", 
                next_scene="return", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mallory", "It hurts."), 
                    Line("Lira", "I'm sorry."),
                )
            ),
        )
    ),
    "return": Scene(
        "The Return", "dawn", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "A soft glow."), 
            Line("Mika", "I'm back."), 
            Line("Mallory", "You are home."),
        ), 
        (
            Choice(
                text="Embrace them", 
                next_scene="jealousy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I missed you."), 
                    Line("Mallory", "We missed you too."),
                )
            ), 
            Choice(
                text="Be distant", 
                next_scene="jealousy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Thanks."), 
                    Line("Mallory", "Mika?"),
                )
            ),
        )
    ),
    "jealousy": Scene(
        "The Place Beside the Princess", "moon", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "A servant calls Lira the new maid."), 
            Line("Mika", "You replaced me."), 
            Line("Mallory", "No."),
        ), 
        (
            Choice(
                text="Talk it out", 
                next_scene="confrontation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I was scared."), 
                    Line("Mallory", "I'm sorry."),
                )
            ), 
            Choice(
                text="Lash out", 
                next_scene="confrontation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "You're all the same."), 
                    Line("Mallory", "Please!"),
                )
            ),
        )
    ),
    "confrontation": Scene(
        "The Words Left Unsaid", "archive", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "An ink-black handprint."), 
            Line("Mika", "Something is wrong."), 
            Line("Lira", "We must be careful."),
        ), 
        (
            Choice(
                text="Unite", 
                next_scene="reconciliation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "We can't let it win."), 
                    Line("Mallory", "Together."),
                )
            ), 
            Choice(
                text="Blame them", 
                next_scene="reconciliation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "This is your fault."), 
                    Line("Mallory", "Mika!"),
                )
            ),
        )
    ),
    "reconciliation": Scene(
        "The Ribbon Returned", "garden", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Lira places the ribbon down."), 
            Line("Mallory", "We want you here."), 
            Line("Mika", "I was scared."),
        ), 
        (
            Choice(
                text="Tie the ribbon", 
                next_scene="trio", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I'm staying."), 
                    Line("Lira", "Good."),
                )
            ), 
            Choice(
                text="Leave it", 
                next_scene="trio", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I need time."), 
                    Line("Mallory", "Okay."),
                )
            ),
        )
    ),
    "trio": Scene(
        "Three Places at the Table", "garden", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "A new household."), 
            Line("Lira", "A team."), 
            Line("Mika", "A family."),
        ), 
        (
            Choice(
                text="Celebrate", 
                next_scene="assassination", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Let's eat!"), 
                    Line("Mallory", "Yes!"),
                )
            ), 
            Choice(
                text="Stay quiet", 
                next_scene="assassination", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Okay."), 
                    Line("Lira", "..."),
                )
            ),
        )
    ),
    "assassination": Scene(
        "A Threat in the Garden", "moon", ("Lira", "Mika", "Mallory"), 
        (
            Line("Narration", "An assassin strikes."), 
            Line("Lira", "Down!"), 
            Line("Mika", "I got her!"),
        ), 
        (
            Choice(
                text="Protect them", 
                next_scene="conspiracy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Stay behind me."), 
                    Line("Mallory", "Thank you."),
                )
            ), 
            Choice(
                text="Go on the offensive", 
                next_scene="conspiracy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'll hunt them down."), 
                    Line("Lira", "Careful!"),
                )
            ),
        )
    ),
    "conspiracy": Scene(
        "The Hand Behind the Knife", "archive", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Councilman Vane revealed."), 
            Line("Mika", "Why?"), 
            Line("Vane", "For the glory."),
        ), 
        (
            Choice(
                text="Arrest him", 
                next_scene="healing", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Take him away."), 
                    Line("Mallory", "Justice."),
                )
            ), 
            Choice(
                text="Execute him", 
                next_scene="healing", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "You die now."), 
                    Line("Lira", "Mika, no!"),
                )
            ),
        )
    ),
    "healing": Scene(
        "The Healing Kitchen", "infirmary", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Mika's wounds burn."), 
            Line("Mallory", "Rest."), 
            Line("Mika", "I can't."),
        ), 
        (
            Choice(
                text="Accept help", 
                next_scene="prophecy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Okay."), 
                    Line("Mallory", "Good."),
                )
            ), 
            Choice(
                text="Push them away", 
                next_scene="prophecy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Leave me."), 
                    Line("Lira", "..."),
                )
            ),
        )
    ),
    "prophecy": Scene(
        "The Prophecy Unfolds", "archive", ("Lira", "Mika", "Mallory"), 
        (
            Line("Narration", "The final warning."), 
            Line("Lira", "We can share the burden."), 
            Line("Mallory", "Together."),
        ), 
        (
            Choice(
                text="Accept the burden", 
                next_scene="winter_vigil", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Let's do it."), 
                    Line("Mallory", "Yes."),
                )
            ), 
            Choice(
                text="Carry it alone", 
                next_scene="winter_vigil", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "No, I'll do it."), 
                    Line("Lira", "Stubborn."),
                )
            ),
        )
    ),
    "winter_vigil": Scene(
        "The Longest Night", "winter", ("Mika", "Mallory", "Lira", "Gorthak"), 
        (
            Line("Narration", "The black winter."), 
            Line("Shadow", "You will break."), 
            Line("Mika", "No, I won't."),
        ), 
        (
            Choice(
                text="Stand strong", 
                next_scene="storm", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I have people who know my name."), 
                    Line("Mallory", "We are here."),
                )
            ), 
            Choice(
                text="Doubt yourself", 
                next_scene="storm", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Maybe I will."), 
                    Line("Lira", "Don't say that."),
                )
            ),
        )
    ),
    "storm": Scene(
        "The Gathering Storm", "winter", ("Mallory", "Mika", "Lira"), 
        (
            Line("Narration", "The final battle."), 
            Line("Mika", "I know what to protect."), 
            Line("Mallory", "I love you."),
        ), 
        (
            Choice(
                text="Say I love you too", 
                next_scene="final_battle", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I love you too."), 
                    Line("Mallory", "Let's go."),
                )
            ), 
            Choice(
                text="Stay silent", 
                next_scene="final_battle", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "..."), 
                    Line("Mallory", "Mika?"),
                )
            ),
        )
    ),
    "final_battle": Scene(
        "The Final Battle", "battle", ("Mika", "Mallory", "Lira", "Shadow"), 
        (
            Line("Narration", "The shadow descends."), 
            Line("Shadow", "You cannot win."), 
            Line("Mika", "I am a hero!"),
        ), 
        (
            Choice(
                text="Fight together", 
                next_scene="ending_gate", 
                effects={"family_final": 1, "bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Together!"), 
                    Line("Shadow", "Impossible!"),
                )
            ), 
            Choice(
                text="Sacrifice yourself", 
                next_scene="ending_gate", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'll do it alone!"), 
                    Line("Mallory", "No!"),
                )
            ),
        )
    ),
    "ending_home": Scene("A New Dawn", "dawn", ("Mika", "Mallory", "Lira"), (Line("Narration", "The shadow breaks."), Line("Mallory", "You are home."), Line("Mika", "Forever.")), ending=True),
    "ending_peace": Scene("The Kingdom United", "dawn", ("Gorthak", "Mika", "Mallory"), (Line("Narration", "The goblin alliance holds."), Line("Gorthak", "Neighbors."), Line("Mika", "Beside them.")), ending=True),
    "ending_cycle": Scene("The Fifty-Sixth Return", "dawn", ("Mika", "Mallory", "Lira"), (Line("Narration", "Mika wins, but the cycle continues."), Line("Mika", "Next time."), Line("Mallory", "Always.")), ending=True),
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
)
CHAPTER_BY_SCENE = {chapter.scene_id: chapter for chapter in CHAPTERS}
CHAPTER_MUSIC = {chapter.scene_id: Path("assets") / "chapter_music" / f"chapter_{chapter.key}{'.mp3' if chapter.key == '01' else '.wav'}" for chapter in CHAPTERS}
SOUND_EFFECTS = (("summon", "Summoning Rune"), ("pages", "Forbidden Pages"), ("garden", "Garden Fountain"), ("heartbeat", "Fearful Heartbeat"), ("footsteps", "Hallway Footsteps"), ("sword", "Sword Draw"), ("wind", "Black Winter Wind"), ("hope", "Return of Hope"))


def save_path() -> Path:
    if os.name == "nt": base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin": base = Path.home() / "Library" / "Application Support"
    else: base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FiftySixLives" / "save.json"

def asset_path(*parts: str) -> Path:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return bundle_root.joinpath(*parts)

class BackgroundMusic:
    def __init__(self) -> None:
        try: import pygame
        except ImportError: self._pygame = None; self._error = "Install pygame."; return
        self._pygame = pygame; self._error = None; self._loaded_track = None
    @property
    def available(self) -> bool: return self._pygame is not None
    @property
    def error(self) -> str | None: return self._error
    def play(self, track: Path | None = None) -> None:
        if not self.available: raise OSError(self._error or "MP3 unavailable.")
        track = track or asset_path("assets", "The Maid of Light.mp3")
        if not track.is_file(): raise FileNotFoundError(f"Not found: {track}")
        track = track.resolve()
        try:
            if not self._pygame.mixer.get_init(): self._pygame.mixer.init(frequency=44100, size=-16, channels=2)
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
        self._requests = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="8bit-voice", daemon=True)
        self._thread.start()
        self._stop_event = threading.Event()
        self._current_sound = None
        
    def _run(self) -> None:
        while True:
            req = self._requests.get()
            if req is None: break
            speaker, text = req
            self._play_voice(speaker, text)
            
    def _play_voice(self, speaker, text):
        if not self.available or not text: return
        try:
            if not self._pygame.mixer.get_init():
                self._pygame.mixer.init(frequency=22050, size=-16, channels=1)
            base_freqs = {"Mika": 600, "Mallory": 500, "Lira": 550, "King Galvath": 200, "Gorthak": 150, "Shadow": 100, "Narration": 350}
            base_freq = base_freqs.get(speaker, 400)
            sample_rate = self._pygame.mixer.get_init()[0]
            char_duration = 0.035 
            samples = array.array("h")
            for char in text:
                if self._stop_event.is_set(): break
                if char.isspace(): samples.extend([0] * int(sample_rate * char_duration)); continue
                freq = base_freq + (ord(char) % 30) - 15
                count = int(sample_rate * char_duration)
                for i in range(count):
                    time = i / sample_rate
                    val = 1.0 if math.sin(2 * math.pi * freq * time) > 0 else -1.0
                    progress = i / count
                    env = 1.0 if progress < 0.8 else (1.0 - progress) * 5.0
                    samples.append(int(val * env * 6000))
            if sys.byteorder != "little": samples.byteswap()
            sound = self._pygame.mixer.Sound(buffer=samples.tobytes())
            self._current_sound = sound
            sound.play()
            duration = len(text) * char_duration
            self._stop_event.wait(duration)
            self._current_sound = None
        except Exception as e: print(f"8-bit voice error: {e}")

    def speak(self, speaker: str, text: str) -> None:
        if not self.available: return
        self.stop(); self._stop_event.clear(); self._requests.put((speaker, text))
    def stop(self) -> None:
        self._stop_event.set()
        if self._current_sound:
            try: self._current_sound.stop()
            except: pass
        while True:
            try: self._requests.get_nowait()
            except queue.Empty: break
    def close(self) -> None: self._requests.put(None)

class Soundboard:
    SAMPLE_RATE = 22050
    def __init__(self, pygame_module: object | None) -> None:
        self._pygame = pygame_module; self.error = None; self._sounds = {}
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
        return pygame.mixer.Sound(buffer=samples.tobytes())
    def play(self, key: str) -> None:
        if not self.available: self.error = "Need pygame."; return
        try:
            sound = self._sounds.get(key)
            if sound is None: sound = self._make_sound(key); self._sounds[key] = sound
            sound.play(); self.error = None
        except self._pygame.error as error: self.error = f"Error: {error}"
        except OSError as error: self.error = str(error)

def ending_for(flags: dict[str, int]) -> str:
    if flags["family_final"] and flags["bond"] >= 2: return "ending_home"
    if flags["peace"] >= 2: return "ending_peace"
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
        self.canvas = tk.Canvas(self.root, bg="#101722", highlightthickness=0); self.canvas.pack(fill="both", expand=True)
        
        self.current_scene: str | None = None
        self.line_index = 0
        self.flags = {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}
        
        self.temp_lines: tuple[Line, ...] | None = None
        self.temp_index: int = 0
        self.pending_next_scene: str | None = None

        self.undo_stack = []
        self.menu = True
        self._canvas_size = (1100, 740)
        self._animated_tags = []
        self._idle_offset = 0; self._idle_direction = -1
        
        self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False
        self.music = BackgroundMusic(); self.music_enabled = self.music.available; self.music_error = None
        self.soundboard = Soundboard(self.music._pygame); self.sfx_enabled = self.soundboard.available
        self.voice = EightBitVoiceOver(self.music._pygame)
        self.voice_enabled = self.voice.available
        self.voice_error = self.voice.error
        
        self._last_spoken = None; self.highest_chapter = 0
        self._image_cache = {}; self._bg_cache = {}; self._character_width_ratio = None
        
        if self.music_enabled: self._start_music()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.root.bind("<Return>", lambda _event: self.advance())
        self.root.bind("<space>", lambda _event: self.advance())
        self.root.bind("<BackSpace>", lambda _event: self.go_back())
        self.root.bind("<Control-s>", lambda _event: self.save_game())
        self.root.bind("<Control-l>", lambda _event: self.load_game())
        self.root.bind("<Escape>", lambda _event: self.show_menu())
        for key, index in (("1", 0), ("2", 1), ("3", 2)):
            self.root.bind(key, lambda _event, choice_index=index: self.choose(choice_index))
            
        self.draw()
        self.root.after(220, self._animate_idle)

    def _snapshot(self): return {"current_scene": self.current_scene, "line_index": self.line_index, "flags": self.flags.copy(), "menu": self.menu, "highest_chapter": self.highest_chapter}
    def _remember(self): self.undo_stack.append(self._snapshot())
    def _restore(self, state):
        self.current_scene = state["current_scene"]; self.line_index = int(state["line_index"]); self.flags = dict(state["flags"]); self.menu = bool(state["menu"]); self.highest_chapter = int(state.get("highest_chapter", 0))
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        if self.music_enabled: self._start_music()
        self.draw()

    def new_game(self):
        self.undo_stack.clear(); self.flags = {"bond": 0, "peace": 0, "resolve": 0, "family_final": 0, "reputation": 0}; self.highest_chapter = 0
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self._enter_scene("summoning"); self.line_index = 0; self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.play_scene_sfx("summoning"); self.draw()

    def show_menu(self):
        self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self.menu = True; self.voice.stop(); self._last_spoken = None
        if self.music_enabled: self._start_music()
        self.draw()
        
    def show_credits(self):
        self.menu = True; self.credits = True; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False
        self.draw()
        
    def show_chapter_select(self):
        self.menu = True; self.credits = False; self.chapter_select = True; self.soundboard_visible = False; self.soundtrack_visible = False
        self.draw()
        
    def show_soundboard(self):
        self.menu = True; self.credits = False; self.chapter_select = False; self.soundboard_visible = True; self.soundtrack_visible = False
        self.draw()

    def show_soundtrack(self):
        self.menu = True; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = True
        self.draw()

    def choose_chapter(self, index: int):
        if not 0 <= index <= self.highest_chapter or index >= len(CHAPTERS): return
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
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
        self.voice_enabled = not self.voice_enabled; self.voice.stop(); self._last_spoken = None
        if self.voice_enabled and not self.menu: self._speak_current(force=True)
        self.draw()

    def toggle_sound_effects(self):
        self.sfx_enabled = not self.sfx_enabled
        if not self.sfx_enabled and self.music.available: self.music._pygame.mixer.stop()
        self.draw()

    def play_scene_sfx(self, scene_id: str):
        if not self.menu and scene_id in CHAPTER_MUSIC and self.music_enabled: self._start_music()
        if not self.sfx_enabled: return
        cue = {"summoning": "summon", "first_impression": "wind", "coffee": "garden", "market": "footsteps", "knight_mistake": "sword", "archive": "pages", "training": "sword", "garden": "garden", "goblin_warning": "footsteps", "raid": "sword", "treaty": "hope", "goblin_home": "wind", "shadow": "wind", "war_council": "heartbeat", "sacrifice": "heartbeat", "grief": "heartbeat", "lira_maid": "pages", "return": "hope", "jealousy": "heartbeat", "confrontation": "heartbeat", "reconciliation": "hope", "trio": "garden", "assassination": "sword", "conspiracy": "footsteps", "healing": "garden", "prophecy": "pages", "winter_vigil": "wind", "storm": "wind", "final_battle": "sword", "ending_home": "hope", "ending_peace": "hope", "ending_cycle": "heartbeat"}
        sound_key = cue.get(scene_id)
        if sound_key: self.soundboard.play(sound_key)

    def play_effect(self, key: str):
        if self.sfx_enabled: self.soundboard.play(key)
        self.draw()

    def _speak_current(self, force: bool = False):
        if self.menu or self.current_scene is None or not self.voice_enabled: return
        
        if self.temp_lines:
            if self.temp_index >= len(self.temp_lines): return
            line = self.temp_lines[self.temp_index]
            key = (self.current_scene, "temp", self.temp_index)
        else:
            scene = STORY[self.current_scene]
            line = scene.lines[self.line_index]
            key = (self.current_scene, self.line_index)
            
        if key == self._last_spoken and not force: return
        self._last_spoken = key
        
        final_text = resolve_text(line.text, self.flags)
        self.voice.speak(line.speaker, final_text)

    def close(self):
        self.voice.close()
        try: self.music.close()
        except OSError as error: self.messagebox.showerror(APP_NAME, f"Error:\n{error}")
        self.root.destroy()

    def _on_resize(self, event):
        width = max(820, int(getattr(event, "width", 1100))); height = max(600, int(getattr(event, "height", 740)))
        if (width, height) != self._canvas_size: self._canvas_size = (width, height); self.draw()

    def _on_click(self, event):
        item = self.canvas.find_withtag("current")
        if not item: return
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
                        except Exception as e: print("Music Error:", e)
                return
            if tag.startswith("effect_"): self.play_effect(tag.removeprefix("effect_")); return
            if tag.startswith("menu_"):
                action = tag[5:]
                if action == "new": self.new_game()
                elif action == "continue": self.load_game()
                elif action == "chapters": self.show_chapter_select()
                elif action == "soundboard": self.show_soundboard()
                elif action == "soundtrack": self.show_soundtrack()
                elif action == "credits": self.show_credits()
                elif action == "sound": self.toggle_music()
                elif action == "voice": self.toggle_voice()
                elif action == "effects": self.toggle_sound_effects()
                elif action == "back": self.show_menu()
                elif action == "quit": self.close()
                return
            if tag.startswith("control_"):
                action = tag[8:]
                if action == "save": self.save_game()
                elif action == "back": self.go_back()
                elif action == "menu": self.show_menu()
                elif action == "music": self.toggle_music()
                elif action == "voice": self.toggle_voice()
                elif action == "effects": self.toggle_sound_effects()
                elif action == "chapters": self.show_chapter_select()
                elif action == "soundboard": self.show_soundboard()
                return
            if tag == "advance": self.advance(); return

    def _enter_scene(self, scene_id: str):
        self.current_scene = scene_id
        chapter_index = next(index for index, chapter in enumerate(CHAPTERS) if chapter.scene_id == scene_id)
        self.highest_chapter = max(self.highest_chapter, chapter_index)

    def _next_scene(self, target: str):
        if target == "ending_gate": self._enter_scene(ending_for(self.flags))
        else: self._enter_scene(target)
        self.line_index = 0; self._last_spoken = None; self.play_scene_sfx(self.current_scene or "")

    def advance(self):
        if self.menu or self.current_scene is None: return
        
        if self.temp_lines:
            self.temp_index += 1
            if self.temp_index >= len(self.temp_lines):
                target = self.pending_next_scene
                self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
                if target: self._next_scene(target)
                else: self.menu = True
            self._speak_current(force=True)
            self.draw()
            return

        scene = STORY[self.current_scene]
        if scene.choices and self.line_index >= len(scene.lines) - 1: return
        self._remember()
        if self.line_index < len(scene.lines) - 1:
            self.line_index += 1
        elif scene.next_scene is not None:
            self._next_scene(scene.next_scene)
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
            self._speak_current(force=True)
        else:
            self._next_scene(choice.next_scene)
        self.draw()

    def go_back(self):
        if not self.undo_stack: return
        self._restore(self.undo_stack.pop())

    def _animate_idle(self):
        previous_offset = self._idle_offset
        self._idle_offset += self._idle_direction
        if self._idle_offset <= 0: self._idle_offset = 0; self._idle_direction = 1
        elif self._idle_offset >= 2: self._idle_offset = 2; self._idle_direction = -1
        
        for tag in self._animated_tags:
            self.canvas.move(tag, 0, previous_offset - self._idle_offset)

        self.root.after(220, self._animate_idle)

    def save_game(self):
        if self.current_scene is None or self.menu or self.temp_lines:
            self.messagebox.showinfo(APP_NAME, "Cannot save during an outcome sequence.")
            return
        path = save_path(); data = {"version": SAVE_VERSION, "current_scene": self.current_scene, "line_index": self.line_index, "flags": self.flags, "highest_chapter": self.highest_chapter}
        try: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as error: self.messagebox.showerror(APP_NAME, f"Error:\n{error}"); return
        self.messagebox.showinfo(APP_NAME, f"Saved to:\n{path}")

    def load_game(self):
        path = save_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            scene_id = data["current_scene"]; line_index = data["line_index"]; flags = data["flags"]
            if not isinstance(scene_id, str) or scene_id not in STORY or type(line_index) is not int: raise ValueError("Invalid save.")
            if not 0 <= line_index < len(STORY[scene_id].lines): raise ValueError("Invalid pos.")
            if not isinstance(flags, dict) or set(flags) != FLAG_NAMES: raise ValueError("Invalid flags.")
            highest_chapter = data.get("highest_chapter", 0)
        except FileNotFoundError: self.messagebox.showinfo(APP_NAME, "No save found."); return
        except Exception as error: self.messagebox.showerror(APP_NAME, f"Error loading:\n{error}"); return
        
        self.undo_stack.clear(); self._enter_scene(scene_id); self.line_index = line_index; self.flags = flags; self.highest_chapter = max(highest_chapter, self.highest_chapter)
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.play_scene_sfx(scene_id); self.draw()

    def _button(self, x, y, width, height, label, tag, font_size=15):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill="#1a2938", outline="#a78b58", width=1, tags=(tag,))
        self.canvas.create_text(x + width / 2, y + height / 2, text=label, fill="#f4ead6", font=("Segoe UI", font_size, "bold"), tags=(tag,), width=width - 18)

    def _draw_background(self, backdrop: str, width: int, height: int):
        self.canvas.create_rectangle(0, 0, width, height, fill="#101722", outline="")
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
            except Exception as e: print(f"BG Error {filename}: {e}"); return
        
        self.canvas.create_image(0, 0, image=self._bg_cache[cache_key], anchor="nw")
        
        overlay = Image.new("RGBA", (width, height), (16, 23, 34, 120))
        self._bg_cache[("overlay", width, height)] = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(0, 0, image=self._bg_cache[("overlay", width, height)], anchor="nw")

    def _draw_character(self, name: str, x: float, ground: float, width: int, index: int):
        sprite_tag = f"sprite_{index}"
        self._animated_tags.append(sprite_tag)
        
        filename_map = {"Mika": "Mika", "Mallory": "Mallory", "King Galvath": "Galvath", "Lira": "Lira", "Gorthak": "Gorthak", "Shadow": "shadow"}
        base_name = filename_map.get(name, name)

        expression = ""
        if name == "Mika":
            if self.current_scene in {"grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"}: expression = "_sad"
            elif self.current_scene in {"ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"}: expression = "_happy"
        elif name == "Mallory":
            if self.current_scene in {"grief", "lira_maid", "sacrifice"}: expression = "_sad"
        elif name == "Lira":
            if self.current_scene in {"jealousy", "confrontation"}: expression = "_sad"

        base_filename = f"{base_name}{expression}"
        base_dir = Path(__file__).resolve().parent
        
        def find_file(fn):
            for folder in ["assets/characters", "assets", "characters", "images", "sprites", ""]:
                p = base_dir / folder / fn if folder else base_dir / fn
                if p.exists(): return p
            return None

        img_path = find_file(f"{base_filename}.png") or find_file(f"{base_name}.png")
        if not img_path:
            self.canvas.create_rectangle(x - 50, ground - 200, x + 50, ground, fill="#333", outline="#a78b58", tags=(sprite_tag,))
            self.canvas.create_text(x, ground + 15, text=name, fill="#eee5d4", font=("Segoe UI", 11, "bold"), tags=(sprite_tag,))
            return

        if not HAS_PIL: return

        if self._character_width_ratio is None:
            reference_path = find_file("Mallory.png")
            if reference_path is None: return
            try:
                with Image.open(reference_path) as reference:
                    reference = reference.convert("RGBA")
                    bbox = reference.getchannel("A").getbbox()
                    if bbox: mallory_width_ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
                    else: return
            except OSError: return

            max_height_ratio = 0
            character_files = ("Galvath.png", "Gorthak.png", "Lira.png", "Lira_sad.png", "Mallory_sad.png", "Mika.png", "Mika_happy.png", "Mika_sad.png", "shadow.png")
            for filename in character_files:
                character_path = find_file(filename)
                if character_path is None: continue
                try:
                    with Image.open(character_path) as character:
                        bbox = character.convert("RGBA").getchannel("A").getbbox()
                        if bbox:
                            char_width = bbox[2] - bbox[0]; char_height = bbox[3] - bbox[1]
                            max_height_ratio = max(max_height_ratio, char_height / char_width)
                except OSError: pass
            if max_height_ratio == 0: return
            self._character_width_ratio = min(mallory_width_ratio, 1 / max_height_ratio)

        max_height = int((ground - 80) * 0.98)
        target_width = int(max_height * self._character_width_ratio)

        cache_key = (str(img_path), width, ground)
        if cache_key not in self._image_cache:
            try:
                original = Image.open(img_path).convert("RGBA")
                bbox = original.getchannel("A").getbbox()
                if bbox: original = original.crop(bbox)
                
                orig_w, orig_h = original.size
                target_height = int(orig_h * target_width / orig_w)
                
                resized = original.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self._image_cache[cache_key] = ImageTk.PhotoImage(resized)
            except Exception as e: print(f"Char Error {img_path.name}: {e}"); return

        tk_image = self._image_cache[cache_key]
        
        ground -= self._idle_offset
        img_id = self.canvas.create_image(x, ground, image=tk_image, anchor="s", tags=(sprite_tag,))
        
        self.canvas.create_text(x, ground + 15, text=name, fill="#eee5d4", font=("Segoe UI", 11, "bold"), tags=(sprite_tag,))

    def _draw_menu(self, width: int, height: int):
        backdrop = "archive" if self.chapter_select or self.soundtrack_visible else "winter" if self.soundboard_visible else "garden"
        self._draw_background(backdrop, width, height)
        if not self.chapter_select and not self.soundboard_visible and not self.soundtrack_visible and not self.credits: 
            self._draw_coverpage(width, height); return
            
        self.canvas.create_rectangle(0, 0, width, 62, fill="#101722", outline="#c4a879", width=2)
        self.canvas.create_text(width / 2, 26, text="FIFTY-SIX LIVES", fill="#f5e9d2", font=("Georgia", max(26, width // 32), "bold"))

        if self.credits:
            self.canvas.create_rectangle(0, height * 0.59, width, height, fill="#101722", outline="#c4a879", width=2)
            self.canvas.create_text(width / 2, height * 0.65, text="CREDITS", fill="#edcf88", font=("Georgia", 21, "bold"))
            self.canvas.create_text(width / 2, height * 0.72, text="Story & Visual Novel Creator", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.77, text="James Adrian B. Castro", fill="#fff4de", font=("Georgia", 17, "bold"))
            self.canvas.create_text(width / 2, height * 0.83, text="Original soundtrack and lyrics by:", fill="#d8c8aa", font=("Segoe UI", 11))
            self.canvas.create_text(width / 2, height * 0.88, text="James Adrian B. Castro - The Maid of Light", fill="#e6d6b8", font=("Segoe UI", 13, "bold"))
            self._button(width / 2 - 110, height * 0.51, 220, 34, "BACK TO TITLE", "menu_back", 10)
            return

        if self.chapter_select:
            self.canvas.create_rectangle(0, 62, width, height - 36, fill="#101722", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 82, text="CHAPTER SELECT", fill="#edcf88", font=("Georgia", 19, "bold"))
            
            column_gap = 20
            column_width = (width - 60 - column_gap * 2) / 3
            
            for column in range(3):
                x = 30 + column * (column_width + column_gap)
                button_top = 120 # Reset top position for each column!
                
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
            self.canvas.create_rectangle(0, 62, width, height - 38, fill="#101722", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 91, text="VALLHELM SOUND LIBRARY", fill="#edcf88", font=("Georgia", 19, "bold"))
            columns = 2; button_width = min(410, (width - 110) / columns)
            for index, (key, label) in enumerate(SOUND_EFFECTS):
                x = (width - (2 * button_width + 16)) / 2 + (index % columns) * (button_width + 16)
                y = height * 0.23 + (index // columns) * 77
                self._button(x, y, button_width, 52, f"PLAY  ·  {label}", f"effect_{key}", 12)
            self._button(width / 2 - 105, height - 43, 210, 30, "BACK TO TITLE", "menu_back", 9)
            return

        if self.soundtrack_visible:
            self.canvas.create_rectangle(0, 62, width, height - 38, fill="#101722", outline="#c4a879", width=1)
            self.canvas.create_text(width / 2, 85, text="SOUNDTRACK LIST", fill="#edcf88", font=("Georgia", 19, "bold"))
            columns = 3; button_width = (width - 80) / columns; button_height = 30
            for index, chapter in enumerate(CHAPTERS):
                col = index % columns; row = index // columns
                x = 40 + col * button_width; y = 140 + row * (button_height + 8)
                self._button(x, y, button_width - 10, button_height, f"{chapter.key} - {chapter.title}", f"track_{chapter.key}", 10)
            self._button(width / 2 - 105, height - 43, 210, 30, "BACK TO TITLE", "menu_back", 9)
            return

        self.canvas.create_rectangle(0, height * 0.55, width, height, fill="#101722", outline="#c4a879", width=2)
        button_w, button_h = min(320, width * 0.46), 34; start_x = (width - button_w) / 2
        actions = (("NEW STORY", "new"), ("CONTINUE", "continue"), ("CHAPTER SELECT", "chapters"), ("SOUNDTRACK", "soundtrack"), ("SOUNDBOARD", "soundboard"), ("CREDITS", "credits"), ("QUIT", "quit"))
        for index, (label, action) in enumerate(actions):
            self._button(start_x, height * 0.60 + index * 35, button_w, button_h, label, f"menu_{action}", 10)

    def _draw_coverpage(self, width: int, height: int):
        mika_x = width * 0.35
        self.canvas.create_oval(mika_x - width * 0.19, height * 0.12, mika_x + width * 0.19, height * 0.99, outline="#d5bd82", width=2)
        
        self._draw_character("Mika", mika_x, height * 0.99, width, 0)
        
        self.canvas.create_text(width * 0.32, height * 0.075, text="FIFTY-SIX LIVES", fill="#fff3df", font=("Georgia", max(27, width // 29), "bold"))
        self.canvas.create_text(width * 0.32, height * 0.145, text="THE TALE OF MIKA AMANOGAWA", fill="#f0d18a", font=("Segoe UI", max(10, width // 90), "bold"))
        self.canvas.create_text(width * 0.32, height * 0.205, text="One quiet maid. Fifty-five forgotten lives.\nOne chance to call a place home.", fill="#f7f1e6", font=("Segoe UI", max(10, width // 100)))
        
        panel_left = width * 0.62; panel_top = height * 0.11; panel_right = width * 0.98; panel_bottom = height * 0.97
        self.canvas.create_rectangle(panel_left, panel_top, panel_right, panel_bottom, fill="#101722", outline="#c4a879", width=2)
        self.canvas.create_text((panel_left + panel_right) / 2, panel_top + 30, text="CHOOSE YOUR PATH", fill="#edcf88", font=("Georgia", max(13, width // 65), "bold"))
        
        button_width = panel_right - panel_left - 28
        button_height = min(38, max(30, height * 0.055)) 
        button_gap = min(8, max(5, height * 0.012))
        button_x = panel_left + 14
        button_y = panel_top + height * 0.14
        
        actions = (("NEW STORY", "new"), ("CONTINUE", "continue"), ("CHAPTER SELECT", "chapters"), ("SOUNDTRACK", "soundtrack"), ("SOUNDBOARD", "soundboard"), ("CREDITS", "credits"), ("QUIT", "quit"))
        for index, (label, action) in enumerate(actions):
            self._button(button_x, button_y + index * (button_height + button_gap), button_width, button_height, label, f"menu_{action}", max(9, width // 105))

    def draw(self):
        width, height = self._canvas_size
        self.canvas.delete("all"); self._animated_tags = []
        
        if self.menu or self.current_scene is None: self._draw_menu(width, height); return

        scene = STORY[self.current_scene]
        self._draw_background(scene.backdrop, width, height)
        chapter = CHAPTER_BY_SCENE[self.current_scene]
        
        # Top Bar
        self.canvas.create_rectangle(0, 0, width, 70, fill="#101722", outline="#c4a879", width=1)
        self.canvas.create_text(24, 13, anchor="nw", text=f"ARC  {chapter.arc}", fill="#e8c779", font=("Segoe UI", 9, "bold"))
        self.canvas.create_text(24, 38, anchor="nw", text=f"CHAPTER {chapter.key}  ·  {chapter.title.upper()}", fill="#f1e5ce", font=("Segoe UI", 11, "bold"))
        
        # REPUTATION UI
        rep = self.flags.get("reputation", 0)
        if rep >= 2:
            rep_text, rep_color = "GOOD", "#4ade80"
        elif rep <= -2:
            rep_text, rep_color = "BAD", "#f87171"
        else:
            rep_text, rep_color = "NEUTRAL", "#fbbf24"
            
        self.canvas.create_text(24, 55, anchor="nw", text=f"REPUTATION: {rep_text}", fill=rep_color, font=("Segoe UI", 9, "bold"))
        
        controls = (("CHAPTERS", "control_chapters", 80), ("FX", "control_soundboard", 48), ("VOICE ON" if self.voice_enabled else "VOICE OFF", "control_voice", 78), ("MUSIC", "control_music", 54), ("SAVE", "control_save", 54), ("BACK", "control_back", 54), ("MENU", "control_menu", 54))
        total = sum(button_width for _label, _tag, button_width in controls) + 6 * (len(controls) - 1)
        x = width - total - 14
        for label, tag, button_width in controls:
            self._button(x, 18, button_width, 34, label, tag, 8); x += button_width + 6

        # Characters
        stage_ground = height * 0.72
        cast = scene.cast
        if cast:
            spacing = min(width * 0.30, 320) 
            center = width / 2
            start_x = center - spacing * (len(cast) - 1) / 2
            for index, name in enumerate(cast):
                self._draw_character(name, start_x + index * spacing, stage_ground, width, index)

        # Text Box
        panel_top = height * 0.72 
        self.canvas.create_rectangle(0, panel_top, width, height, fill="#101722", outline="#c4a879", width=2)
        
        if self.temp_lines:
            active_lines = self.temp_lines
            active_index = min(self.temp_index, len(active_lines) - 1)
            line = active_lines[active_index]
        else:
            active_lines = scene.lines
            active_index = min(self.line_index, len(active_lines) - 1)
            line = active_lines[active_index]
            
        final_text = resolve_text(line.text, self.flags)
        
        self.canvas.create_text(34, panel_top + 17, anchor="nw", text=line.speaker.upper(), fill="#d9bd82", font=("Segoe UI", 11, "bold"))
        self.canvas.create_text(34, panel_top + 43, anchor="nw", text=final_text, fill="#f3eee5", font=("Segoe UI", max(12, round(width / 73))), width=width - 68)
        
        ready_for_choice = bool(scene.choices) and not self.temp_lines and self.line_index == len(scene.lines) - 1
        
        if ready_for_choice:
            button_h = min(38, (height - panel_top - 105) / len(scene.choices))
            y = panel_top + 105
            for index, choice in enumerate(scene.choices):
                self._button(34, y + index * (button_h + 7), width - 68, button_h, f"{index + 1}. {choice.text}", f"choice_{index}", 12)
        else:
            if self.temp_lines and self.temp_index == len(self.temp_lines) - 1:
                label = "CONTINUE  >>"
            else:
                label = "RETURN TO TITLE" if (scene.ending and self.line_index == len(scene.lines) - 1 and not self.temp_lines) else "CONTINUE  >"
            self._button(width - 210, height - 53, 176, 35, label, "advance", 10)
            
        self.canvas.create_text(34, height - 21, anchor="w", text="Enter: continue   1–3: choose   Backspace: undo   Ctrl+C: chapters   Ctrl+B: soundboard   Ctrl+V: voice", fill="#aaa9a6", font=("Segoe UI", 8))
        self._speak_current()

def run():
    game = VisualNovel(); game.root.mainloop()

def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--validate-story", action="store_true")
    args = parser.parse_args()
    if args.validate_story: print(f"Story validated: {validate_story()} scenes."); return 0
    run(); return 0

if __name__ == "__main__":
    raise SystemExit(main())
