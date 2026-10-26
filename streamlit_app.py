from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

import main as story
from game_session import GameSession


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

st.set_page_config(
    page_title=f"{story.APP_NAME}: {story.SUBTITLE}",
    page_icon=str(ASSETS / "game_icon.png"),
    layout="wide",
)
st.markdown(
    """
    <style>
    .stApp { background: #080b10; color: #f3eee5; }
    [data-testid="stSidebar"] { background: #101722; }
    .story-panel { background: rgba(6, 8, 10, .92); border: 1px solid #c4a879;
      border-radius: 12px; padding: 1.25rem 1.5rem; }
    .speaker { color: #d9bd82; font-weight: 700; letter-spacing: .08em; }
    .chapter-label { color: #c4a879; text-transform: uppercase; letter-spacing: .12em; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "game" not in st.session_state:
    st.session_state.game = GameSession()
game: GameSession = st.session_state.game

with st.sidebar:
    st.image(str(ASSETS / "game_icon.png"), width=80)
    st.title("Story")
    if st.button("Start new game", width="stretch"):
        game.new_game()
        st.rerun()
    st.subheader("Chapters")
    for arc in story.ARCS:
        chapters = [chapter for chapter in story.CHAPTERS if chapter.arc == arc]
        with st.expander(arc, expanded=False):
            for chapter in chapters:
                index = story.CHAPTERS.index(chapter)
                if st.button(
                    f"{chapter.key} · {chapter.title}",
                    key=f"chapter-{chapter.key}",
                    disabled=index > game.highest_chapter,
                    width="stretch",
                ):
                    game.start_chapter(index)
                    st.rerun()
    if game.is_in_story:
        st.divider()
        st.download_button(
            "Download save",
            data=game.save_json() if not game.temp_lines else "",
            file_name="fifty-six-lives-save.json",
            mime="application/json",
            disabled=bool(game.temp_lines),
            width="stretch",
        )
        uploaded_save = st.file_uploader("Load save", type=("json",), key="save-upload")
        if uploaded_save is not None and st.button("Load uploaded save", width="stretch"):
            try:
                game.load_json(uploaded_save.getvalue().decode("utf-8"))
                st.success("Save loaded.")
                st.rerun()
            except (UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
                st.error(f"Could not load save: {error}")

st.title(story.APP_NAME)
st.caption(story.SUBTITLE)

if not game.is_in_story:
    cover = ASSETS / "backgrounds" / "garden.png"
    if cover.is_file():
        st.image(str(cover), width="stretch")
    st.info("Start a new game or choose an unlocked chapter from the sidebar.")
else:
    scene = game.scene
    assert scene is not None
    chapter = story.CHAPTER_BY_SCENE[game.current_scene]
    background = ASSETS / "backgrounds" / f"{scene.backdrop}.png"
    if background.is_file():
        st.image(str(background), width="stretch")
    st.markdown(
        f'<p class="chapter-label">Chapter {chapter.key} · {chapter.title}</p>',
        unsafe_allow_html=True,
    )

    if scene.cast:
        columns = st.columns(len(scene.cast))
        for column, character in zip(columns, scene.cast):
            if character in ("Mika", "Mika Amanogawa"):
                names = ["Mika"]
            elif character in ("Mallory", "Mallory Valerius"):
                names = ["Mallory"]
            elif character.startswith("King Galvath"):
                names = ["Galvath"]
            elif character.startswith("Lira"):
                names = ["Lira"]
            elif character.startswith("Gorthak"):
                names = ["Gorthak"]
            elif character == "Shadow":
                names = ["shadow"]
            elif character == "Mika_Evil":
                names = ["Mika_Evil"]
            else:
                names = [character.replace(" ", "_")]
            if character in ("Mika", "Mika Amanogawa") and game.current_scene in {
                "grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"
            }:
                names = ["Mika_sad"]
            elif character in ("Mika", "Mika Amanogawa") and game.current_scene in {
                "ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"
            }:
                names = ["Mika_happy"]
            elif character in ("Mallory", "Mallory Valerius") and game.current_scene in {
                "grief", "lira_maid", "sacrifice"
            }:
                names = ["Mallory_sad"]
            sprite = next(
                (ASSETS / "characters" / f"{name}.png" for name in names
                 if (ASSETS / "characters" / f"{name}.png").is_file()),
                None,
            )
            with column:
                if sprite:
                    st.image(str(sprite), width="stretch")

    line = game.active_line
    if line is not None:
        speaker = html.escape(line.speaker.upper().replace("_EVIL", ""))
        dialogue = html.escape(game.current_text())
        st.markdown(
            f'<div class="story-panel"><div class="speaker">{speaker}</div>'
            f'<p>{dialogue}</p></div>',
            unsafe_allow_html=True,
        )
    if game.choices:
        st.subheader("Choose")
        for index, choice in enumerate(game.choices):
            if st.button(
                choice.text,
                key=f"choice-{game.current_scene}-{index}",
                width="stretch",
            ):
                game.choose(index)
                st.rerun()
    elif st.button("Continue", type="primary", width="stretch"):
        game.advance()
        st.rerun()

st.caption("Music, voice-over, and sound effects from the desktop edition are not included in this web version.")
