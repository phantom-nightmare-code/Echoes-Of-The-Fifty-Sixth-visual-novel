"""A self-contained visual novel adaptation of the supplied Vallhelm story."""

from __future__ import annotations

import argparse
import array
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

APP_NAME = "Fifty-Six Lives"
SAVE_VERSION = 4
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
            Line("Narration", "The grand hall of Vallhelm is suffocatingly silent, save for the crackling hum of the ancient summoning circle etched into the marble floor. The Demon Lord's armies are a day's march away, and the kingdom's last hope rests on a forbidden, desperate ritual."),
            Line("Narration", "A flash of blinding, golden light erupts from the center of the runes. The shockwave knocks the royal mages off their feet. When the smoke clears, the entire court gasps in unison."),
            Line("Narration", "Instead of a towering, armored warrior, a young woman stands in the center of the circle. She is wearing a simple, black-and-white maid's uniform, holding a feather duster like a sword."),
            Line("Mika", "Whoa! What the—? Where am I? This is definitely not the hotel hallway I was just cleaning. Why is everyone staring at me like I just grew a second head?"),
            Line("King Galvath", "A servant! The prophecy promised a champion to save us from the abyss, and the heavens send us a scullery maid with a duster! This is a mockery of everything we stand for!"),
        ),
        (
            Choice(
                text="Step forward and offer to help her", 
                next_scene="first_impression", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mallory", "Father, please! Silence! The circle responded to her. The magic recognized her soul. We cannot dismiss her just because she doesn't look like a knight."),
                    Line("Mika", "Thanks for the save. I'm Mika, by the way. Nice to meet someone here who isn't immediately yelling at me."),
                    Line("Mallory", "I am Mallory. And I have a feeling we are going to need each other if we are going to survive this."),
                )
            ),
            Choice(
                text="Stand your ground and demand respect", 
                next_scene="first_impression", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika", "I can hear you, you know. I'm standing right here. And for the record, I've handled worse messes than a few angry soldiers. Have you ever cleaned up after a royal banquet?"),
                    Line("Narration", "The court gasps at her defiance. The King's face turns crimson with rage, and the guards tighten their grip on their weapons."),
                    Line("Mallory", "Silence! The circle responded to her. We cannot dismiss her just because she doesn't look like a knight. Stand down!"),
                )
            ),
        ),
    ),
    "first_impression": Scene(
        "The Wrong Hero", "throne", ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "The court's disappointment sharpens into suspicion. A seasoned captain of the guard steps forward, pointing his spear directly at Mika's untouched sleeves."),
            Line("King Galvath", "If the ritual brought a servant, then it has failed us. We need a champion who can wield a blade, not someone to dust the throne room while the kingdom burns."),
            Line("Mika", "I'm right here, you know. I have a name. It's Mika. And honestly, I'm just as confused as you are."),
        ),
        (
            Choice(
                text="Apologize and try to explain", 
                next_scene="coffee", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika", "Look, I don't know how I got here, but I'm not your enemy. I was just doing my job, and now I'm here. I just want to go home."),
                    Line("Narration", "The King hesitates, his expression softening slightly at her calm, rational tone."),
                    Line("Mallory", "Let us speak in the gardens, away from this hostility. Please, follow me."),
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
            Line("Narration", "Mallory walks Mika out of the echoing throne room and into the quiet, sprawling palace gardens. The night air is cool and carries the sweet scent of night-blooming jasmine."),
            Line("Narration", "They sit on a stone bench near a gently bubbling fountain. The distant sound of the panicked court fades away, replaced by the chirping of crickets."),
            Line("Mallory", "I apologize for my father. He is terrified. We all are. The Demon Lord's shadow looms over us, and we are desperate. But I am not ready to give up on you yet."),
        ),
        (
            Choice(
                text="Offer to help her anyway", 
                next_scene="market", 
                effects={"bond": 1, "reputation": 1},
                outcome_lines=(
                    Line("Mika", "It's okay. I'm used to people underestimating me. Let me see what I can do to help. I might not be a knight, but I'm a fast learner."),
                    Line("Mallory", "You are a rare soul, Mika. Thank you."),
                )
            ),
            Choice(
                text="Demand to be sent home immediately", 
                next_scene="market", 
                effects={"resolve": 1, "reputation": -1},
                outcome_lines=(
                    Line("Mika", "I don't care about your war or your prophecies. I want to go home. Now. Find a way to send me back."),
                    Line("Mallory", "I... I don't know how to send you back. The ritual only works one way."),
                    Line("Mika", "Then find a way. Or I'll find it myself."),
                )
            ),
        ),
    ),
    "market": Scene(
        "The City Market", "garden", ("Mallory", "Mika"),
        (
            Line("Narration", "Before the sun rises, Mallory disguises herself in a heavy cloak and takes Mika into the lower city. The streets are damp with morning fog, and the market is bustling, but a thick layer of fear hangs in the air."),
            Line("Mika", "The people are scared. I used to clean rooms for people who never looked me in the eye. It's strange, being the one everyone is staring at now."),
            Line("Narration", "A small child, distracted by the commotion, bumps into Mika, dropping a woven basket of apples. The fruit scatters across the muddy cobblestones."),
        ),
        (
            Choice(
                text="Help the child gather the apples", 
                next_scene="knight_mistake", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Oh! Careful there, little one. Let me help you. Don't want these delicious apples getting bruised."), 
                    Line("Mallory", "You care for them already. You have a gentle heart, Mika."),
                )
            ),
            Choice(
                text="Ignore the child and keep walking", 
                next_scene="knight_mistake", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Watch where you're going. I don't have time for this."), 
                    Line("Mallory", "That was cold, Mika. These are my people."),
                )
            ),
        ),
    ),
    "knight_mistake": Scene(
        "The Knight's Mistake", "throne", ("Mika", "Mallory", "Lira"),
        (
            Line("Narration", "Back at the palace, tensions boil over. A frightened, young guard, believing Mika's intervention at the market was demonic manipulation, lunges at her with a spear."),
            Line("Narration", "Mika doesn't flinch. She pivots on her heel, sidestepping the thrust by a hair's breadth, grabs the wooden shaft of the spear, and snaps it in two with a sharp twist of her wrist."),
            Line("Lira", "Enough! Stand down, soldier! Stand down! She could have broken your arm. Instead, she disarmed you without drawing a drop of blood."),
        ),
        (
            Choice(
                text="Forgive the guard", 
                next_scene="archive", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I know what fear makes people do. It's okay. Let's just make sure it doesn't happen again."), 
                    Line("Lira", "You have my respect, Maid. I am Lira, Captain of the Royal Guard."),
                )
            ),
            Choice(
                text="Threaten the guard", 
                next_scene="archive", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "If he tries that again, I won't be so gentle. Tell your men to stay out of my way."), 
                    Line("Lira", "Watch your tongue, Maid. You are not in charge here."),
                )
            ),
        ),
    ),
    "archive": Scene(
        "The Ancient Record", "archive", ("King Galvath", "Mallory", "Mika"),
        (
            Line("Narration", "King Galvath, humbled but still suspicious, summons the three women to the restricted section of the royal archives. The room smells of old paper, ozone, and dust."),
            Line("Narration", "He opens a massive, ancient tome bound in dragon leather. The pages glow with a faint, ethereal light."),
            Line("King Galvath", "This book names you, Mika. It describes fifty-five lives before this one. Each time, your memories were wiped clean. You are a cosmic pawn."),
            Line("Mika", "Fifty-five lives? You mean I've done this before? I've died before? Fifty-five times?"),
        ),
        (
            Choice(
                text="Accept the responsibility", 
                next_scene="training", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Then let this life belong to me. I will help you, but I choose what home means. No more wiping my memories."), 
                    Line("Mallory", "Thank you, Mika. We will stand by you."),
                )
            ),
            Choice(
                text="Refuse the prophecy", 
                next_scene="training", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I am not a pawn. I won't be your sacrifice. Find someone else to do your dirty work."), 
                    Line("Mallory", "Please, Mika. We need you. The whole world needs you."),
                )
            ),
        ),
    ),
    "training": Scene(
        "Sparring with Lira", "throne", ("Mika", "Lira"), 
        (
            Line("Narration", "The training yard is filled with the harsh clang of steel. Lira is a whirlwind of precision and grace, her sword cutting through the air. Mika, however, is struggling to adjust to the weight of a real blade."), 
            Line("Lira", "Your strength is incredible, Mika, but your footwork is sloppy! You fight like you're holding a mop!"), 
            Line("Mika", "A mop can be pretty dangerous if you know how to swing it! I once fought off a drunk noble with a bucket of soapy water!"),
        ), 
        (
            Choice(
                text="Help Lira up", 
                next_scene="garden", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Lira laughs, a genuine, warm sound. She lunges again, but Mika anticipates it. She sweeps Lira's leg with the flat of her blade, knocking the captain into the dirt."), 
                    Line("Mika", "Good match, Captain."), 
                    Line("Lira", "You are full of surprises, Maid. Perhaps you really are the hero the prophecy spoke of."),
                )
            ), 
            Choice(
                text="Gloat over her", 
                next_scene="garden", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika disarms Lira with a swift strike, sending her sword clattering to the ground."), 
                    Line("Mika", "Not so tough now, are you, Captain?"), 
                    Line("Lira", "Don't push your luck, Maid. I was going easy on you."),
                )
            ),
        )
    ),
    "garden": Scene(
        "A Quiet Afternoon", "garden", ("Mallory", "Mika"), 
        (
            Line("Narration", "Days pass in relative peace, a calm before the inevitable storm. Mallory leads Mika to a hidden garden behind the palace walls, overgrown with wild roses and ivy."), 
            Line("Mallory", "The palace garden is peaceful. No one will bother you here. This was my mother's favorite place."), 
            Line("Mika", "It's beautiful. A quiet place, a warm drink, and no urgent prophecy. I could get used to this."),
        ), 
        (
            Choice(
                text="Open up to Mallory", 
                next_scene="goblin_warning", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika smiles softly, the first genuine smile she has shown since arriving. They spend hours talking about her world, her small apartment, her love of cleaning, and the peaceful, mundane life she left behind."), 
                    Line("Mika", "I used to think my life was boring. Just waking up, going to work, coming home. But now... I'd give anything for one boring Tuesday."), 
                    Line("Mallory", "You make this place feel like home too, Mika."),
                )
            ), 
            Choice(
                text="Keep your distance", 
                next_scene="goblin_warning", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika stares at the roses, refusing to meet Mallory's eyes."), 
                    Line("Mika", "I'm not here to make friends, Mallory. I'm here because I have to be."), 
                    Line("Mallory", "I see. I'm sorry for prying."),
                )
            ),
        )
    ),
    "goblin_warning": Scene(
        "Tracks at the Orchard", "farm", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The royal orchard on the outskirts of the city is in ruins. The wooden fence is cut from the inside. Wet footprints lead toward the goblin road, but none lead back."), 
            Line("Mika", "This wasn't an attack from the outside. Look at the cut. Someone from the city cut this from the inside and dragged the scouts out."), 
            Line("Lira", "We should report this to the King immediately. This is high treason."),
        ), 
        (
            Choice(
                text="Investigate quietly", 
                next_scene="raid", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "If we report this, the King will just send an army. Then the real traitor wins. We need to find out who benefits before we call anyone an enemy. We need evidence."), 
                    Line("Mallory", "Agreed. We do this your way, Mika."),
                )
            ), 
            Choice(
                text="Report to the King", 
                next_scene="raid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Let the army handle it. That's what they're paid for, right?"), 
                    Line("Lira", "As you wish. I will inform His Majesty immediately."),
                )
            ),
        )
    ),
    "raid": Scene(
        "The Goblin Raid", "farm", ("Mika", "Gorthak", "Mallory"), 
        (
            Line("Narration", "A goblin band storms the countryside, setting fire to the wheat fields. Mika shields Mallory, raising her broken spear to fight. But as the smoke clears, she notices the raiders are not warriors, but refugees."), 
            Line("Gorthak", "Our village has nothing left! The blight took our crops, and the king's soldiers poisoned our wells! We came for food, not a war with your people!"), 
            Line("Mallory", "Mika, what should we do? If we attack, we prove we're monsters. If we don't, they'll take everything."),
        ), 
        (
            Choice(
                text="Hear them out", 
                next_scene="treaty", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika drops her weapon to the mud. The silence that follows is deafening. Gorthak stares at her, bewildered by her courage."), 
                    Line("Mika", "Put down your weapons. All of you. We can settle this without bloodshed."), 
                    Line("Gorthak", "Why should we trust you? You are human."), 
                    Line("Mika", "Because I'm the only one here who has seen enough death. Fifty-five lifetimes of it. I'm not looking for more."),
                )
            ), 
            Choice(
                text="Attack", 
                next_scene="treaty", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika charges forward, her broken spear flashing in the firelight. The goblins scatter, terrified by her ferocity."), 
                    Line("Mika", "Drive them back! Show them what happens when they threaten Vallhelm!"), 
                    Line("Gorthak", "We will remember this, human! We will remember!"),
                )
            ),
        )
    ),
    "treaty": Scene(
        "A Language of Understanding", "throne", ("Gorthak", "Mika", "Mallory"), 
        (
            Line("Narration", "Once the danger passes, Mika forces both sides to sit at the negotiating table. The tension in the throne room is thick enough to cut with a knife."), 
            Line("Gorthak", "Give our people a fair chance, and we will stand between Vallhelm and its enemies. We are warriors, not thieves."), 
            Line("King Galvath", "You expect me to ally with goblins? They have raided our lands for generations! My father died fighting them!"),
        ), 
        (
            Choice(
                text="Push for peace", 
                next_scene="goblin_home", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "And you expect me to fight for a kingdom that would let children starve over a grudge? A treaty is only worth something if we keep choosing to honor it."), 
                    Line("Mallory", "Mika is right, Father. The real enemy is at our borders. We need Gorthak's army."), 
                    Line("Gorthak", "You are a strange human, Mika. You fight like a demon, but you speak like an angel."),
                )
            ), 
            Choice(
                text="Suggest a truce", 
                next_scene="goblin_home", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'm not saying we hold hands and sing songs. I'm saying we accept a temporary truce until the Demon Lord is defeated."), 
                    Line("King Galvath", "A temporary measure. Nothing more. Do not expect me to break bread with them."), 
                    Line("Gorthak", "Cautious. But acceptable."),
                )
            ),
        )
    ),
    "goblin_home": Scene(
        "A Village at the Edge", "farm", ("Gorthak", "Mika", "Mallory"), 
        (
            Line("Narration", "Mika follows Gorthak to Crag-Vale, a goblin village nestled in the jagged mountains. It is a ruin of empty granaries, poisoned wells, and crying children. The smell of rot is overwhelming."), 
            Line("Gorthak", "We did not raid your farms until the blight took ours. We were desperate. We are dying."), 
            Line("Mika", "Then we have been fighting over the same wound. Someone poisoned your wells, cut our fences, and killed our scouts. They wanted this war."),
        ), 
        (
            Choice(
                text="Sympathize", 
                next_scene="shadow", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "A sudden whistle cuts through the air. An arrow strikes the ground between them, vibrating with force. Its shaft bears the king's seal."), 
                    Line("Mika", "Look at the shaft. It bears the king's seal. But he wouldn't... this is a forgery. We'll fix this, Gorthak. I promise."), 
                    Line("Gorthak", "Thank you, Mika. You are different from the others."),
                )
            ), 
            Choice(
                text="Demand answers", 
                next_scene="shadow", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "A sudden whistle cuts through the air. An arrow strikes the ground between them, vibrating with force."), 
                    Line("Mika", "Who did this? Who poisoned your wells? Tell me what you know!"), 
                    Line("Gorthak", "We don't know! We are not your enemy, but you are making it very hard to remember that!"),
                )
            ),
        )
    ),
    "shadow": Scene(
        "The Demon Lord's Shadow", "battle", ("Mika", "Mallory", "Gorthak"), 
        (
            Line("Narration", "The Demon Lord's forces gather at the border. A massive army of dark knights, wraiths, and fire-breathing beasts stretches across the horizon, blotting out the sun."), 
            Line("Narration", "Knights, mages, and goblins stand shoulder to shoulder, preparing to defend Vallhelm together. The air smells of ozone, ash, and fear."), 
            Line("Mallory", "You do not have to face the whole army by yourself. We are with you. Vallhelm is with you."),
        ), 
        (
            Choice(
                text="Lead together", 
                next_scene="war_council", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I know. I just need to remember that when the fighting starts. Fear makes people do terrible things. But it can also make them brave."), 
                    Line("Gorthak", "My people will hold the left flank. Show them the strength of a champion, Maid. We fight as one!"),
                )
            ), 
            Choice(
                text="Lead alone", 
                next_scene="war_council", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I can handle this. I've done it before. Just make sure the civilians are safe."), 
                    Line("Mallory", "Be careful, Mika. Please. Don't do anything reckless."),
                )
            ),
        )
    ),
    "war_council": Scene(
        "The Empty Place at Council", "throne", ("King Galvath", "Mallory", "Mika", "Gorthak"), 
        (
            Line("Narration", "Before the war council can agree on a plan, the king's maps are found covered in black ash. Every road leads to the same ruined valley, a death trap."), 
            Line("King Galvath", "The enemy is steering us toward the north. It's a trap. We have no choice but to spring it."), 
            Line("Mallory", "Then we choose the ground together. Mika is not a weapon we point at it. We fight as one, or we don't fight at all."),
        ), 
        (
            Choice(
                text="Plan together", 
                next_scene="sacrifice", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "If we're walking into a trap, we make sure we spring it on our terms. We use the valley's terrain to our advantage."), 
                    Line("Mallory", "Smart. We'll coordinate the mages to provide cover."),
                )
            ), 
            Choice(
                text="Charge in", 
                next_scene="sacrifice", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "We attack now. We don't give them time to fortify their positions."), 
                    Line("King Galvath", "Reckless! You will get us all killed!"),
                )
            ),
        )
    ),
    "sacrifice": Scene(
        "The Cost of Victory", "battle", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The battle is brutal. The valley runs red. The allied forces are pushed to the brink, but they hold the line. The battle breaks the enemy's advance, but at a terrible cost."), 
            Line("Narration", "Mika spends everything she has to keep Mallory and the defenders alive. She channels the raw, unrefined magic of the summoning circle."), 
            Line("Mika", "[shake]Mallory! Get behind me![/shake]"),
        ), 
        (
            Choice(
                text="Hold on for them", 
                next_scene="grief", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "A blinding flash of light erupts from Mika's body, consuming the remaining shadow beasts. The blast levels the valley. When the light fades, Mika collapses into the mud."), 
                    Line("Mallory", "Mika! Stay with us. Please. Don't close your eyes! I can't lose you!"), 
                    Line("Narration", "The light fades from Mika's eyes. She smiles softly, knowing she saved them."),
                )
            ), 
            Choice(
                text="Let go", 
                next_scene="grief", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika lets out a final, exhausted sigh, closing her eyes as the magic consumes her."), 
                    Line("Mika", "I'm sorry... I couldn't hold on..."), 
                    Line("Narration", "She is gone. The cycle has claimed another life."),
                )
            ),
        )
    ),
    "grief": Scene(
        "After the Battle", "infirmary", ("Mallory", "Lira"), 
        (
            Line("Narration", "Vallhelm mourns. The kingdom is saved, but the champion is gone. The capital is draped in black banners."), 
            Line("Lira", "You should not have to hold all this grief alone, Your Highness. You haven't left her side in days. You need to eat."), 
            Line("Mallory", "I promised her she wouldn't be alone. I failed her. I couldn't protect her. She died for us."),
        ), 
        (
            Choice(
                text="Comfort her", 
                next_scene="lira_maid", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Lira", "She protected us. And she would want you to keep living. She wouldn't want you to waste away in this room. Let me help you."), 
                    Line("Mallory", "Then stay beside me. And when Mika comes home, we will tell her together."),
                )
            ), 
            Choice(
                text="Leave her be", 
                next_scene="lira_maid", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Lira", "As you wish, Your Highness. I will be outside if you need me."), 
                    Line("Mallory", "...")
                )
            ),
        )
    ),
    "lira_maid": Scene(
        "The New Maid", "infirmary", ("Mallory", "Lira"), 
        (
            Line("Narration", "Grief makes the days blur. To keep the palace running and to keep Mallory from drowning in sorrow, Lira asks to serve as her personal maid until Mika can return."), 
            Line("Mallory", "It is not a replacement. I need help, and I trust you. You are my anchor in this storm."), 
            Line("Lira", "I will wear the apron, Your Highness. But I will never pretend to be Mika. She is one of a kind."),
        ), 
        (
            Choice(
                text="Accept Lira", 
                next_scene="return", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mallory laughs for the first time in weeks, though it is tinged with sadness. She pins Mika's pale ribbon beside the appointment order."), 
                    Line("Mallory", "I know. She would be furious if we replaced her. She'd probably throw a bucket of soapy water at us."), 
                    Line("Lira", "I'll do my best to keep your spirits up."),
                )
            ), 
            Choice(
                text="Resent Lira", 
                next_scene="return", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mallory", "It hurts, Lira. Every time I see you in that apron, it hurts."), 
                    Line("Lira", "I'm sorry, Your Highness. I never meant to cause you pain."),
                )
            ),
        )
    ),
    "return": Scene(
        "The Return", "dawn", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "At the garden memorial, Mallory and Lira speak to Mika as if she can still hear them. A soft, golden glow gathers around the fragments of her soul."), 
            Line("Mika", "Mallory...? Lira...? I'm all right. I could feel how much you wanted me back."), 
            Line("Mallory", "You are home. This time, you do not have to be alone. We're here."),
        ), 
        (
            Choice(
                text="Embrace them", 
                next_scene="jealousy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "It was dark. So dark. But I heard your voice calling me. It was like a lighthouse."), 
                    Line("Mika", "I missed you. Both of you. So much."), 
                    Line("Mallory", "We missed you too, Mika. Welcome back."),
                )
            ), 
            Choice(
                text="Be distant", 
                next_scene="jealousy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Thanks. For bringing me back. I guess."), 
                    Line("Mallory", "Mika? What's wrong? Did something happen in the dark?"), 
                    Line("Mika", "I don't want to talk about it right now."),
                )
            ),
        )
    ),
    "jealousy": Scene(
        "The Place Beside the Princess", "moon", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "A servant mistakenly calls Lira the princess's 'new maid' in passing. Mika's smile falters. Lira is wearing the very apron Mika used to fold each morning."), 
            Line("Mika", "You found someone to take my place before I even came back. I was gone for five minutes. Well, a few weeks."), 
            Line("Mallory", "Mika, please. Tell me what you heard. It's not what you think. Lira was just helping me survive."),
        ), 
        (
            Choice(
                text="Talk it out", 
                next_scene="confrontation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I saved this world. I died for it. Why does it feel as if I have already been erased from it?"), 
                    Line("Mika", "I was scared. I'm still scared. But I don't want to push you away."), 
                    Line("Mallory", "I'm so sorry, Mika. I never meant to make you feel that way."),
                )
            ), 
            Choice(
                text="Lash out", 
                next_scene="confrontation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "You're all the same. Fifty-five times I've died for people, and fifty-five times I've been replaced the second I closed my eyes."), 
                    Line("Mallory", "Mika, please! It's not like that!"), 
                    Line("Mika", "Then what is it like? Because it looks exactly like that from where I'm standing."),
                )
            ),
        )
    ),
    "confrontation": Scene(
        "The Words Left Unsaid", "archive", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Mika, Mallory, and Lira retreat to the archive to talk. A window slams shut though there is no wind. An ink-black handprint appears on the inside of the glass, smoking slightly."), 
            Line("Mika", "When I heard 'new maid,' it felt like the last place in the world that was mine disappeared. Like I was just a ghost."), 
            Line("Lira", "I wanted to keep your place warm. I never wanted to stand in it. I'm sorry, Mika."),
        ), 
        (
            Choice(
                text="Unite", 
                next_scene="reconciliation", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I know you didn't mean to hurt me. But it did hurt. I've lost everyone fifty-five times over. I'm terrified of being forgotten."), 
                    Line("Mika", "Something in this palace wants us to doubt each other. It's feeding on our fear. We can't let it win."), 
                    Line("Mallory", "Together. We face it together."),
                )
            ), 
            Choice(
                text="Blame them", 
                next_scene="reconciliation", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "This is your fault. Both of you. You made me feel like I was nothing."), 
                    Line("Mallory", "Mika! That's not fair and you know it!"), 
                    Line("Mika", "Fair? Nothing about this is fair."),
                )
            ),
        )
    ),
    "reconciliation": Scene(
        "The Ribbon Returned", "garden", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Lira places Mika's pale ribbon on the table instead of putting it on. She waits for Mika to decide what it means, a gesture of ultimate respect."), 
            Line("Mallory", "I want both of you here. Not as copies of one another—as yourselves. You both mean the world to me."), 
            Line("Mika", "I was scared. I still am. But I don't want fear choosing for me."),
        ), 
        (
            Choice(
                text="Tie the ribbon", 
                next_scene="trio", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika picks up the ribbon and ties it back into her hair. The garden lanterns flare to life one by one, pushing back the darkness."), 
                    Line("Mika", "I'm not going anywhere. And I'm not going to let a little jealousy ruin this. We're a team."), 
                    Line("Lira", "Agreed. We are stronger together."),
                )
            ), 
            Choice(
                text="Leave it", 
                next_scene="trio", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I need time. I'm not ready to just pretend everything is okay."), 
                    Line("Mallory", "Okay. Take all the time you need. We'll be here when you're ready."),
                )
            ),
        )
    ),
    "trio": Scene(
        "Three Places at the Table", "garden", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Mika returns to the household by choice. Mallory keeps Lira as her maid and Mika takes charge of the palace staff; Lira remains the princess's trusted guard and closest confidante."), 
            Line("Lira", "No one here needs to disappear for someone else to belong. We're a team. A weird, chaotic team."), 
            Line("Mika", "Then let us keep the table wide enough for all of us."),
        ), 
        (
            Choice(
                text="Celebrate", 
                next_scene="assassination", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "For the first time in weeks, the palace feels like a place of warmth, rather than a fortress under siege."), 
                    Line("Mika", "Let's eat! I'm starving!"), 
                    Line("Mallory", "I'll have the chefs prepare a feast!"),
                )
            ), 
            Choice(
                text="Stay quiet", 
                next_scene="assassination", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Okay. Sounds good."), 
                    Line("Lira", "... Is everything alright, Mika?"), 
                    Line("Mika", "Yeah. Just tired. Let's get some rest."),
                )
            ),
        )
    ),
    "assassination": Scene(
        "A Threat in the Garden", "moon", ("Lira", "Mika", "Mallory"), 
        (
            Line("Narration", "A hidden faction tries to strike at the royal family during a moonlit walk. Lira spots the glint of a blade first, a flash of silver in the bushes."), 
            Line("Lira", "Mika, down! Assassin on the east wall!"), 
            Line("Narration", "Mika throws herself in front of Mallory, catching a poisoned dart on her armored sleeve. The three women fight back-to-back, a perfect unit."),
        ), 
        (
            Choice(
                text="Protect them", 
                next_scene="conspiracy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Stay behind me! I won't let them touch you!"), 
                    Line("Lira", "The palace is safer when we trust each other enough to share the watch."), 
                    Line("Mallory", "Thank you, Mika. You saved my life."),
                )
            ), 
            Choice(
                text="Offensive", 
                next_scene="conspiracy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "I'll hunt them down. They won't get far."), 
                    Line("Lira", "Careful! It could be a trap!"), 
                    Line("Narration", "Mika charges into the darkness, determined to end the threat permanently."),
                )
            ),
        )
    ),
    "conspiracy": Scene(
        "The Hand Behind the Knife", "archive", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The trail leads below the old archive. A locked door opens from the other side. Standing there is Councilman Vane, holding a glowing, dark artifact, his eyes clouded with dark magic."), 
            Line("Mika", "You. You're the one who poisoned the wells. You killed our scouts. Why?"), 
            Line("Vane", "For the glory of Vallhelm! The Demon Lord promised me power beyond imagination!"),
        ), 
        (
            Choice(
                text="Arrest", 
                next_scene="healing", 
                effects={"peace": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika disarms Vane with a swift strike, pinning him to the ground."), 
                    Line("Mika", "Take him away. Let him rot in the dungeons for his crimes."), 
                    Line("Mallory", "Justice will be served. Thank you, Mika."),
                )
            ), 
            Choice(
                text="Execute", 
                next_scene="healing", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika's blade flashes in the dim light. Vane falls to the ground, the dark artifact shattering into dust."), 
                    Line("Mika", "You die now. Traitors don't deserve a trial."), 
                    Line("Lira", "Mika, no... It wasn't your place to execute him."),
                )
            ),
        )
    ),
    "healing": Scene(
        "The Healing Kitchen", "infirmary", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "The conspirators are stopped, but the battle leaves Mika's old wounds burning. She tries to hide the tremor in her hands from the others."), 
            Line("Mallory", "You don't have to be useful to deserve rest. Let me bandage that."), 
            Line("Lira", "Then tonight, we keep watch while you heal. You've earned a moment of peace."),
        ), 
        (
            Choice(
                text="Accept help", 
                next_scene="prophecy", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mallory gently cleans Mika's wounds, humming a soft lullaby. Mika finally allows herself to relax, leaning into Mallory's touch."), 
                    Line("Mika", "Thank you. Both of you. For making me feel human again."), 
                    Line("Mallory", "Always, Mika. Always."),
                )
            ), 
            Choice(
                text="Push away", 
                next_scene="prophecy", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "Leave me. I can take care of myself."), 
                    Line("Lira", "... As you wish. We'll be right outside if you need us."), 
                    Line("Narration", "Mika sits alone in the dark, wincing as she tries to bandage her own wounds."),
                )
            ),
        )
    ),
    "prophecy": Scene(
        "The Prophecy Unfolds", "archive", ("Lira", "Mika", "Mallory"), 
        (
            Line("Narration", "The old book reveals one final warning: a darkness older than the Demon Lord is drawing near. The true enemy approaches."), 
            Line("Lira", "I found a way to focus the magic without asking Mika to carry it all. We can channel it together. A shared burden."), 
            Line("Mallory", "Then we face the storm as a family, with the whole kingdom behind us."),
        ), 
        (
            Choice(
                text="Accept", 
                next_scene="winter_vigil", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "Fifty-five times I did this alone. Not this time. Let's do it together."), 
                    Line("Mallory", "Yes. Together."), 
                    Line("Narration", "The ground trembles. The black winter has arrived."),
                )
            ), 
            Choice(
                text="Alone", 
                next_scene="winter_vigil", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "No. I'll do it. I'm the champion, aren't I? I'm the one who has to make the sacrifice."), 
                    Line("Lira", "Stubborn fool. You don't have to carry this alone."), 
                    Line("Narration", "The ground trembles. The black winter has arrived."),
                )
            ),
        )
    ),
    "winter_vigil": Scene(
        "The Longest Night", "winter", ("Mika", "Mallory", "Lira", "Gorthak"), 
        (
            Line("Narration", "On the eve of the black winter, the four keep watch at the garden fountain. The sky is an inky void, devoid of stars."), 
            Line("Shadow", "[shake]Fifty-five times you died alone. The fifty-sixth will end the pattern. You will break.[/shake]"), 
            Line("Mika", "You're wrong. This time, I have people who know my name."),
        ), 
        (
            Choice(
                text="Strong", 
                next_scene="storm", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "The shadow smiles with Mika's own face and vanishes beneath the ice."), 
                    Line("Mika", "I have people who know my name. I am not alone."), 
                    Line("Mallory", "We are here. We will always be here."),
                )
            ), 
            Choice(
                text="Doubt", 
                next_scene="storm", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "The shadow smiles with Mika's own face and vanishes beneath the ice."), 
                    Line("Mika", "Maybe I will break. Maybe this is the time I finally fail."), 
                    Line("Lira", "Don't say that. We need you to be strong."),
                )
            ),
        )
    ),
    "storm": Scene(
        "The Gathering Storm", "winter", ("Mallory", "Mika", "Lira"), 
        (
            Line("Narration", "Winter turns the sky black. Beyond the walls, a vast shadow opens over Vallhelm. The final battle is at hand."), 
            Line("Mika", "Fifty-six lives, and I finally know what I want to protect."), 
            Line("Mallory", "Whatever happens out there... I love you, Mika. I should have said it sooner."),
        ), 
        (
            Choice(
                text="Love you too", 
                next_scene="final_battle", 
                effects={"bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Mika", "I love you too. Let's end this. Together."), 
                    Line("Mallory", "Let's go."), 
                    Line("Narration", "They charge into the darkness, side by side."),
                )
            ), 
            Choice(
                text="Silent", 
                next_scene="final_battle", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Mika", "..."), 
                    Line("Mallory", "Mika? Please, say something."), 
                    Line("Mika", "There's no time for words. We have a battle to win."),
                )
            ),
        )
    ),
    "final_battle": Scene(
        "The Final Battle", "battle", ("Mika", "Mallory", "Lira", "Shadow"), 
        (
            Line("Narration", "The sky cracks open. The ancient shadow descends, a massive entity of writhing darkness and glowing red eyes."), 
            Line("Shadow", "[color=#ff0000]You are nothing but a servant. You cannot defeat me.[/color]"), 
            Line("Mika", "I am a servant. But I am also a hero. And this is my home!"),
        ), 
        (
            Choice(
                text="Together", 
                next_scene="ending_gate", 
                effects={"family_final": 1, "bond": 1, "reputation": 1}, 
                outcome_lines=(
                    Line("Narration", "Mika raises her weapon, channeling all her power into a single strike. Mallory and Lira stand beside her, combining their magic."), 
                    Line("Mika", "[shake]Together![/shake]"), 
                    Line("Shadow", "Impossible!"),
                )
            ), 
            Choice(
                text="Sacrifice", 
                next_scene="ending_gate", 
                effects={"resolve": 1, "reputation": -1}, 
                outcome_lines=(
                    Line("Narration", "Mika pushes Mallory and Lira out of the way, charging directly into the shadow."), 
                    Line("Mika", "[shake]I'll do it alone![/shake]"), 
                    Line("Mallory", "No! Mika!"),
                )
            ),
        )
    ),
    "ending_home": Scene(
        "A New Dawn", "dawn", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Together, they break the ancient shadow. The entity shatters into a million pieces of light. Mika falls to her knees, exhausted."), 
            Line("Mallory", "You came back. You are loved, Mika. You are home."), 
            Line("Mika", "As long as a fragment of me remains, I will always find my way back to you. This time, I am staying home. Forever."), 
            Line("Lira", "The dawn is breaking. We actually did it."),
        ), 
        ending=True
    ),
    "ending_peace": Scene(
        "The Kingdom United", "dawn", ("Gorthak", "Mika", "Mallory"), 
        (
            Line("Narration", "The goblin alliance turns the tide. Together, the people of Vallhelm shatter the darkness and keep their promise of peace."), 
            Line("Gorthak", "Today we fought as neighbors. Let us live that way tomorrow."), 
            Line("Mika", "I used to think protecting people meant standing in front of them. Now I know it can mean standing beside them."), 
            Line("Narration", "A new era of unity begins. Goblins and humans rebuild the kingdom together, and Mika stands at the center of it all."),
        ), 
        ending=True
    ),
    "ending_cycle": Scene(
        "The Fifty-Sixth Return", "dawn", ("Mika", "Mallory", "Lira"), 
        (
            Line("Narration", "Mika meets the darkness alone and wins, though the familiar cycle claims its price once more."), 
            Line("Narration", "In the quiet that follows, Mallory and Lira refuse to let her go. Their voices guide her back to the garden."), 
            Line("Mika", "I will try again. Next time, I will let you stand beside me."), 
            Line("Mallory", "I'll be waiting for you. Always."),
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
        self.volume = 0.5
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
            base_freqs = {"Mika": 600, "Mallory": 500, "Lira": 550, "King Galvath": 200, "Gorthak": 150, "Shadow": 100, "Narration": 350}
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
        
        # --- WINDOW ICON ---
        if HAS_PIL:
            try:
                base_dir = Path(__file__).resolve().parent
                icon_path = None
                for folder in ["assets/characters", "assets", ""]:
                    p = base_dir / folder / "Mika.png" if folder else base_dir / "Mika.png"
                    if p.exists():
                        icon_path = p
                        break
                
                if icon_path:
                    icon_img = Image.open(icon_path)
                    icon_img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    self._icon_photo = ImageTk.PhotoImage(icon_img)
                    self.root.iconphoto(True, self._icon_photo)
            except Exception: pass
        # -------------------

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
        self.root.bind("<h>", lambda _event: self.toggle_immersive())
        for key, index in (("1", 0), ("2", 1), ("3", 2)):
            self.root.bind(key, lambda _event, choice_index=index: self.choose(choice_index))
            
        self.draw()
        self.root.after(220, self._animate_idle)

    def toggle_immersive(self):
        self.immersive_mode = not self.immersive_mode
        self.draw()

    def _trigger_shake(self, duration=20, intensity=10):
        self.shake_timer = duration
        self.shake_intensity = intensity

    def _trigger_flash(self):
        self.canvas.create_rectangle(0, 0, self._canvas_size[0], self._canvas_size[1], fill="#ffffff", stipple="gray50", tags="flash")
        self.root.after(100, lambda: self.canvas.delete("flash"))

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
        self._enter_scene("summoning"); self.line_index = 0; self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.play_scene_sfx("summoning"); self.draw()

    def show_menu(self):
        self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self.menu = True; self._last_spoken = None
        self.immersive_mode = False
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
            text.insert("end", f"【{speaker}】\n{clean_txt}\n\n", "speaker")
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
        cue = {"summoning": "summon", "first_impression": "wind", "coffee": "garden", "market": "footsteps", "knight_mistake": "sword", "archive": "pages", "training": "sword", "garden": "garden", "goblin_warning": "footsteps", "raid": "sword", "treaty": "hope", "goblin_home": "wind", "shadow": "wind", "war_council": "heartbeat", "sacrifice": "heartbeat", "grief": "heartbeat", "lira_maid": "pages", "return": "hope", "jealousy": "heartbeat", "confrontation": "heartbeat", "reconciliation": "hope", "trio": "garden", "assassination": "sword", "conspiracy": "footsteps", "healing": "garden", "prophecy": "pages", "winter_vigil": "wind", "storm": "wind", "final_battle": "sword", "ending_home": "hope", "ending_peace": "hope", "ending_cycle": "heartbeat"}
        sound_key = cue.get(scene_id)
        if sound_key: self.soundboard.play(sound_key)

    def play_effect(self, key: str):
        if self.sfx_enabled: self.soundboard.play(key)
        self.draw()

    def _start_typing(self, speaker, full_text):
        # Parse Custom Tags
        self._is_shaking_text = "[shake]" in full_text
        full_text = full_text.replace("[shake]", "").replace("[/shake]", "")
        
        self._text_color = "#f3eee5"
        if "[color=" in full_text:
            match = re.search(r"\[color=(.*?)\](.*?)\[/color\]", full_text)
            if match:
                self._text_color = match.group(1)
                full_text = re.sub(r"\[color=.*?\]|\[/color\]", "", full_text)
                
        # Trigger Screen FX
        if speaker == "Shadow" or "Mika" in speaker and "sacrifice" in self.current_scene:
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
        if (width, height) != self._canvas_size: self._canvas_size = (width, height); self.draw()

    def _on_click(self, event):
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
                if tag.startswith("menu_"):
                    clicked_button = True
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
                    clicked_button = True
                    action = tag[8:]
                    if action == "save": self.save_game()
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
                    elif action == "skip": 
                        self.is_typing = False
                        self.display_text = self.full_text
                        self.advance()
                        self.advance()
                    return
                if tag == "advance": self.advance(); return

        if not self.menu and not clicked_button and not self.chapter_select and not self.soundboard_visible and not self.soundtrack_visible and not self.credits:
            self.advance()

    def _enter_scene(self, scene_id: str):
        self.current_scene = scene_id
        chapter_index = next(index for index, chapter in enumerate(CHAPTERS) if chapter.scene_id == scene_id)
        self.highest_chapter = max(self.highest_chapter, chapter_index)
        
        # Initialize offsets for slide-in
        scene = STORY[scene_id]
        for i, name in enumerate(scene.cast):
            self._char_offsets[name] = -250 if i == 0 else 250

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

    def _animate_idle(self):
        previous_offset = self._idle_offset
        self._idle_offset += self._idle_direction
        if self._idle_offset <= 0: self._idle_offset = 0; self._idle_direction = 1
        elif self._idle_offset >= 2: self._idle_offset = 2; self._idle_direction = -1
        
        # Slide-in Animation
        for name in list(self._char_offsets.keys()):
            if self._char_offsets[name] < 0:
                self._char_offsets[name] = min(0, self._char_offsets[name] + 25)
            elif self._char_offsets[name] > 0:
                self._char_offsets[name] = max(0, self._char_offsets[name] - 25)

        # Apply screen shake
        dx = dy = 0
        if self.shake_timer > 0:
            dx = random.randint(-self.shake_intensity, self.shake_intensity)
            dy = random.randint(-self.shake_intensity, self.shake_intensity)
            self.shake_timer -= 1

        for tag in self._animated_tags:
            self.canvas.move(tag, dx, dy - (previous_offset - self._idle_offset))

        # Shake Text effect
        if self.text_id and self._is_shaking_text:
            tx = random.randint(-3, 3)
            ty = random.randint(-3, 3)
            self.canvas.move(self.text_id, tx, ty)

        self.root.after(220, self._animate_idle)

    def save_game(self):
        if self.current_scene is None or self.menu or self.temp_lines: return
        path = save_path(); data = {"version": SAVE_VERSION, "current_scene": self.current_scene, "line_index": self.line_index, "flags": self.flags, "highest_chapter": self.highest_chapter}
        try: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError: return

    def load_game(self):
        path = save_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            scene_id = data["current_scene"]; line_index = data["line_index"]; flags = data["flags"]
            if not 0 <= line_index < len(STORY[scene_id].lines): raise ValueError()
            highest_chapter = data.get("highest_chapter", 0)
        except Exception: return
        
        self.undo_stack.clear(); self._enter_scene(scene_id); self.line_index = line_index; self.flags = flags; self.highest_chapter = max(highest_chapter, self.highest_chapter)
        self.temp_lines = None; self.temp_index = 0; self.pending_next_scene = None
        self.menu = False; self.credits = False; self.chapter_select = False; self.soundboard_visible = False; self.soundtrack_visible = False; self._last_spoken = None
        self.history.clear()
        self.play_scene_sfx(scene_id); self.draw()

    def _button(self, x, y, width, height, label, tag, font_size=15):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill="#1a2938", outline="#a78b58", width=1, tags=(tag,))
        self.canvas.create_text(x + width / 2, y + height / 2, text=label, fill="#f4ead6", font=("Segoe UI", font_size, "bold"), tags=(tag,), width=width - 8)

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
            except Exception: return
        
        self.canvas.create_image(0, 0, image=self._bg_cache[cache_key], anchor="nw")
        overlay = Image.new("RGBA", (width, height), (16, 23, 34, 120))
        self._bg_cache[("overlay", width, height)] = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(0, 0, image=self._bg_cache[("overlay", width, height)], anchor="nw")

    def _draw_character(self, name: str, x: float, ground: float, width: int, index: int):
        sprite_tag = f"sprite_{index}"
        self._animated_tags.append(sprite_tag)
        
        # Add slide-in offset
        x += self._char_offsets.get(name, 0)
        
        filename_map = {"Mika": "Mika", "Mallory": "Mallory", "King Galvath": "Galvath", "Lira": "Lira", "Gorthak": "Gorthak", "Shadow": "shadow"}
        base_name = filename_map.get(name, name)
        expression = ""
        if name == "Mika" and self.current_scene in {"grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"}: expression = "_sad"
        elif name == "Mika" and self.current_scene in {"ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"}: expression = "_happy"
        elif name == "Mallory" and self.current_scene in {"grief", "lira_maid", "sacrifice"}: expression = "_sad"

        base_dir = Path(__file__).resolve().parent
        def find_file(fn):
            for folder in ["assets/characters", "assets", "characters", "images", "sprites", ""]:
                p = base_dir / folder / fn if folder else base_dir / fn
                if p.exists(): return p
            return None

        img_path = find_file(f"{base_name}{expression}.png") or find_file(f"{base_name}.png")
        
        if not img_path:
            self.canvas.create_rectangle(x-100, ground-250, x+100, ground, fill="#1a2938", outline="#a78b58", width=2, tags=(sprite_tag,))
            self.canvas.create_text(x, ground-125, text=name, fill="#edcf88", font=("Georgia", 20, "bold"), tags=(sprite_tag,))
            self.canvas.create_text(x, ground-100, text="[Portrait Missing]", fill="#c5c0bd", font=("Segoe UI", 10), tags=(sprite_tag,))
            self.canvas.create_text(x, ground + 15, text=name, fill="#eee5d4", font=("Segoe UI", 11, "bold"), tags=(sprite_tag,))
            return

        if not HAS_PIL: return

        if self._character_width_ratio is None:
            ref = find_file("Mallory.png")
            if ref is None: return
            try:
                with Image.open(ref) as r:
                    bbox = r.convert("RGBA").getchannel("A").getbbox()
                    if bbox: mallory_ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
                    else: return
            except OSError: return

            max_ratio = 0
            for fn in ("Galvath.png", "Gorthak.png", "Lira.png", "Mika.png", "shadow.png"):
                p = find_file(fn)
                if p:
                    try:
                        with Image.open(p) as c:
                            bbox = c.convert("RGBA").getchannel("A").getbbox()
                            if bbox: max_ratio = max(max_ratio, (bbox[3]-bbox[1]) / (bbox[2]-bbox[0]))
                    except OSError: pass
            if max_ratio == 0: return
            self._character_width_ratio = min(mallory_ratio, 1 / max_ratio)

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
            except Exception: return

        tk_image = self._image_cache[cache_key]
        ground -= self._idle_offset
        self.canvas.create_image(x, ground, image=tk_image, anchor="s", tags=(sprite_tag,))
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
                button_top = 120
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
        
        # Top Bar (Hide in immersive mode)
        if not self.immersive_mode:
            self.canvas.create_rectangle(0, 0, width, 70, fill="#101722", outline="#c4a879", width=1)
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
                ("BACK", "control_back", 45), 
                ("MENU", "control_menu", 45)
            )
            total = sum(button_width for _label, _tag, button_width in controls) + 6 * (len(controls) - 1)
            x = width - total - 14
            for label, tag, button_width in controls:
                self.canvas.create_rectangle(x, 18, x + button_width, 34 + 18, fill="#1a2938", outline="#a78b58", width=1, tags=(tag,))
                self.canvas.create_text(x + button_width / 2, 18 + 34 / 2, text=label, fill="#4ade80" if self.auto_play and label == "AUTO" else "#f4ead6", font=("Segoe UI", 8, "bold"), tags=(tag,), width=button_width - 8)
                x += button_width + 6

        stage_ground = height * 0.72
        cast = scene.cast
        if cast:
            spacing = min(width * 0.30, 320) 
            center = width / 2
            start_x = center - spacing * (len(cast) - 1) / 2
            for index, name in enumerate(cast):
                self._draw_character(name, start_x + index * spacing, stage_ground, width, index)

        panel_top = height * 0.72
        
        if self.temp_lines:
            active_lines = self.temp_lines
            active_index = min(self.temp_index, len(active_lines) - 1)
            line = active_lines[active_index]
        else:
            active_lines = scene.lines
            active_index = min(self.line_index, len(active_lines) - 1)
            line = active_lines[active_index]
            
        final_text = resolve_text(line.text, self.flags)
        
        ready_for_choice = bool(scene.choices) and not self.temp_lines and self.line_index == len(scene.lines) - 1
        font_size = max(12, round(width / 73))
        choice_gap = 6
        choice_button_h = 0
        choice_y = 0
        if ready_for_choice:
            choice_button_h = min(34, max(18, (height - panel_top - 120 - choice_gap * (len(scene.choices) - 1)) / len(scene.choices)))
            choice_y = height - 38 - len(scene.choices) * choice_button_h - (len(scene.choices) - 1) * choice_gap
            self.is_typing = False
            self.display_text = re.sub(r"\[.*?\]", "", final_text)
            while True:
                measure_id = self.canvas.create_text(34, 0, anchor="nw", text=self.display_text, font=("Segoe UI", font_size), width=width - 68)
                text_bbox = self.canvas.bbox(measure_id)
                self.canvas.delete(measure_id)
                text_height = text_bbox[3] - text_bbox[1] if text_bbox else 0
                available_height = choice_y - 10 - (panel_top + 43)
                if text_height <= available_height or font_size <= 12:
                    break
                font_size -= 1
            if text_height > available_height:
                panel_top = max(0, min(panel_top, choice_y - 10 - 43 - text_height))
        else:
            self.display_text = ""

        if not self.immersive_mode:
            self.canvas.create_rectangle(0, panel_top, width, height, fill="#101722", outline="#c4a879", width=2)
        else:
            self.canvas.create_rectangle(0, panel_top, width, height, fill="#101722", stipple="gray50", outline="")

        self.canvas.create_text(34, panel_top + 17, anchor="nw", text=line.speaker.upper(), fill="#d9bd82", font=("Segoe UI", 11, "bold"))
        self.text_id = self.canvas.create_text(34, panel_top + 43, anchor="nw", text="", fill=self._text_color, font=("Segoe UI", font_size), width=width - 68)

        if ready_for_choice:
            self.canvas.itemconfigure(self.text_id, text=self.display_text)
            for index, choice in enumerate(scene.choices):
                self._button(34, choice_y + index * (choice_button_h + choice_gap), width - 68, choice_button_h, f"{index + 1}. {choice.text}", f"choice_{index}", 12)
        else:
            if self.temp_lines and self.temp_index == len(self.temp_lines) - 1:
                label = "CONTINUE  >>"
            else:
                label = "RETURN TO TITLE" if (scene.ending and self.line_index == len(scene.lines) - 1 and not self.temp_lines) else "CONTINUE  >"
            
            if not self.immersive_mode:
                self._button(width - 210, height - 53, 176, 35, label, "advance", 10)
            
            if not self.history or self.history[-1] != (line.speaker, final_text):
                self.history.append((line.speaker, final_text))
            
            if self._last_spoken != (self.current_scene, self.line_index, self.temp_index):
                self._last_spoken = (self.current_scene, self.line_index, self.temp_index)
                self._start_typing(line.speaker, final_text)
            else:
                self.canvas.itemconfigure(self.text_id, text=self.display_text)

        if not self.immersive_mode:
            self.canvas.create_text(34, height - 21, anchor="w", text="Click anywhere to advance   •   Press H for Immersive Mode   •   Space: continue   •   Backspace: undo", fill="#aaa9a6", font=("Segoe UI", 8))

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
