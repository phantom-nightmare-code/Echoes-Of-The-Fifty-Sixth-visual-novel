const app = document.getElementById("app");
const SAVE_KEY = "fifty-six-worlds-save-v1";
const PROGRESS_KEY = "fifty-six-worlds-progress-v1";
let data;
let state = freshState();

function freshState() {
  return { scene: null, line: 0, flags: { bond: 0, peace: 0, resolve: 0, family_final: 0, reputation: 0 }, highest: 0, temp: null, tempIndex: 0, pending: null };
}

function resolveEnding() {
  const { bond = 0, peace = 0, reputation = 0, family_final = 0 } = state.flags;
  if (reputation <= -2) return bond >= 2 ? "ending_evil_kingdom" : "ending_betrayal";
  if (family_final && bond >= 2) return "ending_home";
  if (peace >= 2) return "ending_peace";
  return "ending_cycle";
}

function enterScene(sceneId) {
  state.scene = sceneId;
  state.line = 0;
  const index = data.chapters.findIndex(chapter => chapter.scene_id === sceneId);
  if (index >= 0) {
    state.highest = Math.max(state.highest, index);
    localStorage.setItem(PROGRESS_KEY, String(state.highest));
  }
}

function activeLine() {
  const scene = data.scenes[state.scene];
  return state.temp ? state.temp[state.tempIndex] : scene.lines[state.line];
}

function resolvedText(line) {
  if (typeof line.text === "string") return line.text;
  const reputation = state.flags.reputation || 0;
  return line.text[reputation >= 2 ? 0 : reputation <= -2 ? 2 : 1];
}

function choices() {
  const scene = data.scenes[state.scene];
  return !state.temp && scene.choices.length && state.line >= scene.lines.length - 1 ? scene.choices : [];
}

function transition(target) {
  if (target === "ending_gate") target = resolveEnding();
  if (target) enterScene(target);
  else state.scene = null;
}

function advance() {
  const scene = data.scenes[state.scene];
  if (state.temp) {
    state.tempIndex++;
    if (state.tempIndex >= state.temp.length) {
      const target = state.pending;
      state.temp = null;
      state.tempIndex = 0;
      state.pending = null;
      transition(target);
    }
  } else if (choices().length) {
    return;
  } else if (state.line < scene.lines.length - 1) {
    state.line++;
  } else if (scene.next_scene) {
    transition(scene.next_scene);
  } else if (scene.ending) {
    state.scene = null;
  }
  render();
}

function choose(index) {
  const choice = choices()[index];
  if (!choice) return;
  Object.entries(choice.effects).forEach(([key, value]) => state.flags[key] = (state.flags[key] || 0) + value);
  if (choice.outcome_lines.length) {
    state.temp = choice.outcome_lines;
    state.tempIndex = 0;
    state.pending = choice.next_scene;
  } else {
    transition(choice.next_scene);
  }
  render();
}

function startChapter(index) {
  if (index > state.highest || index < 0) return;
  enterScene(data.chapters[index].scene_id);
  render();
}

function renderHome() {
  app.innerHTML = `<img class="hero" src="assets/backgrounds/garden.png" alt="Garden"><div class="actions"><button id="new">Start new game</button><button id="continue" ${localStorage.getItem(SAVE_KEY) ? "" : "disabled"}>Continue saved game</button></div><h2 class="scene-title">Chapter select</h2><div id="chapters"></div>`;
  document.getElementById("new").onclick = () => { state = freshState(); enterScene("summoning"); render(); };
  document.getElementById("continue").onclick = load;
  const chapters = document.getElementById("chapters");
  data.arcs.forEach(arc => {
    const title = document.createElement("h3");
    title.className = "arc";
    title.textContent = arc;
    chapters.append(title);
    data.chapters.forEach((chapter, index) => {
      if (chapter.arc !== arc) return;
      const button = document.createElement("button");
      button.textContent = `${chapter.key} · ${chapter.title}`;
      button.disabled = index > state.highest;
      button.onclick = () => startChapter(index);
      chapters.append(button);
    });
  });
}

function renderStory() {
  const scene = data.scenes[state.scene];
  const chapter = data.chapters.find(item => item.scene_id === state.scene);
  const line = activeLine();
  const cast = scene.cast.map(character => {
    let name = character === "Mika_Evil" ? "Mika_Evil" :
      character.startsWith("King Galvath") ? "Galvath" :
      character.startsWith("Mika") ? "Mika" :
      character.startsWith("Mallory") ? "Mallory" :
      character.startsWith("Gorthak") ? "Gorthak" :
      character.startsWith("Lira") ? "Lira" :
      character === "Shadow" ? "shadow" : character;
    if (name === "Mika" && ["grief", "sacrifice", "jealousy", "confrontation", "winter_vigil", "final_battle"].includes(state.scene)) name = "Mika_sad";
    else if (name === "Mika" && ["ending_home", "ending_peace", "reconciliation", "trio", "garden", "return"].includes(state.scene)) name = "Mika_happy";
    else if (name === "Mallory" && ["grief", "lira_maid", "sacrifice"].includes(state.scene)) name = "Mallory_sad";
    return `<img src="assets/characters/${name}.png" alt="${escapeHtml(character)}">`;
  }).join("");
  app.innerHTML = `<p class="scene-title">Chapter ${chapter.key} · ${escapeHtml(chapter.title)}</p>
    <img class="hero" src="assets/backgrounds/${escapeHtml(scene.backdrop)}.png" alt="${escapeHtml(scene.title)}">
    <div class="cast">${cast}</div>
    <section class="dialogue"><div class="speaker">${escapeHtml(line.speaker.replace("_EVIL", "").toUpperCase())}</div><p>${escapeHtml(resolvedText(line))}</p></section>
    <div id="controls"></div>`;
  const controls = document.getElementById("controls");
  const availableChoices = choices();
  if (availableChoices.length) {
    availableChoices.forEach((choice, index) => {
      const button = document.createElement("button");
      button.textContent = choice.text;
      button.onclick = () => choose(index);
      controls.append(button);
    });
  } else {
    controls.innerHTML = `<div class="actions"><button id="next">Continue</button><button id="save">Save</button><button id="menu">Menu</button></div>`;
    document.getElementById("next").onclick = advance;
    document.getElementById("save").onclick = save;
    document.getElementById("menu").onclick = () => { state.scene = null; render(); };
  }
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

function save() {
  if (state.temp) return;
  localStorage.setItem(SAVE_KEY, JSON.stringify(state));
  render();
  alert("Game saved on this device.");
}

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (!data.scenes[saved.scene] || !Number.isInteger(saved.line) ||
        saved.line < 0 || saved.line >= data.scenes[saved.scene].lines.length ||
        !Number.isInteger(saved.highest) || saved.highest < 0 || saved.highest >= data.chapters.length ||
        !saved.flags || typeof saved.flags !== "object") throw new Error("Invalid save.");
    state = { ...freshState(), ...saved, temp: null, tempIndex: 0, pending: null };
    localStorage.setItem(PROGRESS_KEY, String(state.highest));
    render();
  } catch (error) {
    alert(`Could not load save: ${error.message}`);
  }
}

function render() {
  state.scene ? renderStory() : renderHome();
}

fetch("./story.json")
  .then(response => {
    if (!response.ok) throw new Error(`Story data could not be loaded (${response.status}).`);
    return response.json();
  })
  .then(storyData => {
    data = storyData;
    const savedProgress = Number.parseInt(localStorage.getItem(PROGRESS_KEY) || "0", 10);
    if (Number.isInteger(savedProgress) && savedProgress >= 0 && savedProgress < data.chapters.length) {
      state.highest = savedProgress;
    }
    render();
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("./sw.js");
  })
  .catch(error => { app.textContent = error.message; });
