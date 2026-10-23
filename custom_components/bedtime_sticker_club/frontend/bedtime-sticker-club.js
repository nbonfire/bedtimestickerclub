// Native family and Parent Controls cards for Bedtime Sticker Club.

const DOMAIN = "bedtime_sticker_club";
const STICKERS = ["⭐", "🌈", "🚀", "🦄", "🦖", "🐱", "🦋", "⚽"];

class BedtimeCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rendered = false;
  }

  setConfig(config) {
    this._config = config || {};
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot?.activeElement) return;
    this.render();
  }

  static getConfigElement() {
    return document.createElement("bedtime-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  getCardSize() {
    return 4;
  }

  shell(title) {
    this.shadowRoot.replaceChildren();
    const style = document.createElement("style");
    style.textContent = `
      :host { --ink:#24203b; --muted:#625b74; display:block; color:var(--ink);
        font-family:ui-rounded,"Avenir Next",system-ui,sans-serif }
      * { box-sizing:border-box }
      .page { border-radius:24px; padding:clamp(12px,2.5vw,24px); background:#fff4da }
      .heading { display:flex; gap:12px; justify-content:space-between; align-items:center;
        font-size:clamp(25px,4vw,38px); font-weight:900; line-height:1.15 }
      .sub { margin:8px 0 18px; color:var(--muted); font-size:15px; line-height:1.5 }
      .children { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr)); gap:14px; align-items:start }
      .child { background:#fffefb; border:3px solid var(--accent,#7541bf); border-radius:24px;
        box-shadow:3px 4px 0 color-mix(in srgb,var(--accent,#7541bf) 18%,transparent); padding:16px; min-width:0 }
      .identity { display:flex; align-items:center; gap:12px; min-width:0 }
      .avatar { width:56px; height:56px; flex:none; display:grid; place-items:center;
        border:0; border-radius:18px; color:inherit; background:var(--tint,#f0e6ff);
        font-size:36px; cursor:pointer }
      .avatar:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible { outline:3px solid #222; outline-offset:2px }
      .name { font-size:24px; font-weight:850; overflow-wrap:anywhere }
      .muted { color:var(--muted); font-size:13px }
      .tasklist { display:grid; gap:8px; margin-top:14px }
      button { min-height:48px; border:2px solid #e7e2ed; border-radius:14px; padding:8px 11px;
        color:var(--ink); background:#fff; font:inherit; cursor:pointer; text-align:left }
      button.done { border-color:var(--accent,#7541bf); background:var(--tint,#f0e6ff) }
      button:disabled { cursor:default; opacity:.55 }
      .row { display:flex; align-items:center; gap:9px }
      .row .label { flex:1; line-height:1.3; overflow-wrap:anywhere }
      .check { width:26px; height:26px; border:2px solid #aaa2b6; border-radius:8px;
        flex:none; display:grid; place-items:center }
      .done .check { color:white; background:var(--accent,#7541bf); border-color:var(--accent,#7541bf) }
      .sticker { text-align:center; font-size:14px; font-weight:750; color:var(--accent,#7541bf) }
      .stickers { display:grid; grid-template-columns:repeat(4,minmax(48px,1fr)); gap:7px; margin-top:8px }
      .stickers button { min-height:48px; padding:3px; text-align:center; font-size:26px }
      .stickers .chosen { border-color:var(--accent,#7541bf); background:var(--tint,#f0e6ff) }
      .head-actions { display:flex; flex:none; gap:6px }
      .icon-button { width:48px; min-width:48px; padding:0; text-align:center; font-size:21px }
      .admin { display:grid; gap:12px; padding:16px; border-radius:18px; background:white }
      .profile { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:8px; align-items:center }
      .toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center }
      .toolbar input,.toolbar select,.profile input,.task-row input { min-height:48px; min-width:0;
        border:1px solid #90889b; border-radius:10px; padding:9px; color:var(--ink); background:white; font:inherit }
      .toolbar input,.task-row input { flex:1 }
      .task-row { display:flex; flex-wrap:wrap; gap:6px; align-items:center }
      .task-row button,.profile button { min-height:44px }
      h2,h3 { margin:6px 0; font-size:19px }
      .error { color:#9c3918; font-weight:700 }
      @media(max-width:400px) { .child { padding:12px } .name { font-size:21px } }
    `;
    this.shadowRoot.append(style);
    const page = document.createElement("section");
    page.className = "page";
    const header = document.createElement("header");
    header.className = "heading";
    header.textContent = title;
    page.append(header);
    this._body = document.createElement("div");
    this._body.className = "sub";
    page.append(this._body);
    this.shadowRoot.append(page);
    this._page = page;
    this._rendered = true;
  }

  element(tag, text, className) {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  }

  button(label, onClick, className) {
    const item = this.element("button", label, className);
    item.type = "button";
    item.addEventListener("click", onClick);
    return item;
  }

  async call(service, data) {
    try {
      await this._hass.callService(DOMAIN, service, data);
    } catch (error) {
      this._error = error.message || "Home Assistant could not save that change.";
      this.render();
    }
  }

  render() {
    if (!this._hass) return;
    if (this.constructor === BedtimeFamilyCard) return this.renderFamily();
    if (this.constructor === BedtimeParentCard) return this.renderParents();
  }

  async parent(action, data = {}) {
    if (!this._hass.user?.is_admin) throw new Error("Sign in with a Home Assistant administrator account.");
    const sensor = Object.values(this._hass.states).find((state) =>
      state.entity_id.startsWith("sensor.bedtime_") && state.entity_id !== "sensor.bedtime_routine");
    return this._hass.callWS({
      type: `${DOMAIN}/admin`,
      entry_id: this._config.entry_id || sensor?.attributes.integration_entry_id,
      action, data,
    });
  }
}

class BedtimeFamilyCard extends BedtimeCard {
  renderFamily() {
    this.shell("Bedtime Sticker Club 🌟");
    const connected = this._hass.connected !== false && this._hass.connection?.connected !== false;
    const message = this.element("p", connected
      ? "Tonight’s routine · Three little tasks, one happy sticker."
      : "Connection lost. Your saved stickers are safe. Reconnecting…", "sub");
    const actions = this.shadowRoot.querySelector("header");
    if (this._hass.user?.is_admin) {
      const settings = this.button("⚙", () => {
        window.history.pushState(null, "", "/bedtime-club/parents");
        window.dispatchEvent(new Event("location-changed"));
      }, "icon-button");
      settings.setAttribute("aria-label", "Parent controls");
      actions.append(settings);
    }
    this._body.replaceWith(message);
    const grid = this.element("div", undefined, "children");
    const profiles = Object.values(this._hass.states)
      .filter((state) => state.entity_id.startsWith("sensor.bedtime_")
        && state.entity_id !== "sensor.bedtime_routine"
        && !state.attributes.archived)
      .sort((a, b) => a.attributes.display_order - b.attributes.display_order);
    if (!profiles.length) {
      grid.append(this.element("p", "Add a child in Parent Controls to create their checklist."));
    }
    for (const state of profiles) grid.append(this.renderChild(state, connected));
    this._page.append(grid);
    if (this._error) this._page.append(this.element("p", this._error, "error"));
  }

  renderChild(state, connected) {
    const attributes = state.attributes;
    const card = this.element("article", undefined, "child");
    card.style.setProperty("--accent", attributes.accent || "#7541bf");
    card.style.setProperty("--tint", attributes.tint || "#f0e6ff");
    const identity = this.element("header", undefined, "identity");
    const avatar = this.button(attributes.avatar || "🙂", async () => {
      const next = prompt(`Choose ${attributes.child_name}’s emoji avatar`, attributes.avatar || "🙂");
      if (next) await this.call("set_avatar", {child_id: attributes.child_id, avatar: next});
    }, "avatar");
    avatar.setAttribute("aria-label", `Change ${attributes.child_name}'s avatar`);
    identity.append(avatar);
    const name = this.element("div");
    name.append(this.element("div", attributes.child_name, "name"));
    name.append(this.element("div", "My bedtime checklist", "muted"));
    identity.append(name);
    card.append(identity);
    const definitions = attributes.task_definitions || [];
    const completed = Number(attributes.completed || 0);
    card.append(this.element("p", `${completed} of ${definitions.length} done`, "muted"));
    const tasks = this.element("div", undefined, "tasklist");
    for (const task of definitions) {
      const done = Boolean(attributes.tasks?.[task.id]);
      const button = this.button("", () => this.call("set_task", {
        child_id: attributes.child_id,
        task: task.id,
        completed: !done,
        routine_date: attributes.routine_date,
      }), `${done ? "done " : ""}row`);
      button.disabled = !connected || state.state === "unavailable";
      button.append(this.element("span", task.icon || "✓"));
      button.append(this.element("span", task.label, "label"));
      button.append(this.element("span", done ? "✓" : "", "check"));
      tasks.append(button);
    }
    card.append(tasks);
    const award = attributes.stickers?.[attributes.routine_date];
    if (attributes.earned || award?.earned) {
      card.append(this.element("p", "You earned a sticker! Pick your favorite ↓", "sticker"));
      const picker = this.element("div", undefined, "stickers");
      for (const sticker of STICKERS) {
        const button = this.button(sticker, () => this.call("choose_sticker", {
          child_id: attributes.child_id,
          routine_date: attributes.routine_date,
          sticker,
        }), award?.emoji === sticker ? "chosen" : "");
        button.disabled = !connected;
        button.setAttribute("aria-label", `Choose sticker ${sticker}`);
        picker.append(button);
      }
      card.append(picker);
    }
    card.append(this.element("p", `🏆 ${attributes.lifetime_total ?? state.state} bedtime${(attributes.lifetime_total ?? Number(state.state)) === 1 ? "" : "s"} completed`, "muted"));
    return card;
  }
}

class BedtimeParentCard extends BedtimeCard {
  constructor() {
    super();
    this._drafts = new Map();
  }

  async renderParents() {
    if (!this._hass.user?.is_admin) {
      this.shell("Parent Controls");
      this._body.textContent = "Sign in with a Home Assistant administrator account to manage the family checklist.";
      return;
    }
    if (!this._parentData || !this._parentLoaded || this._refresh) {
      if (!this._refresh) {
        this._refresh = this.parent("read").then((data) => {
          this._parentData = data;
          this._parentLoaded = Date.now();
        }).catch((error) => { this._error = error.message; }).finally(() => { this._refresh = null; });
      }
      await this._refresh;
    }
    if (!this._parentData) {
      this.shell("Parent Controls");
      this._body.textContent = this._error || "Parent settings are loading…";
      return;
    }
    this.shell("Parent Controls ⚙");
    this._body.textContent = "Manage profiles, bedtime tasks, reminders, and this month’s rewards.";
    const data = this._parentData;
    this.renderSchedule(data);
    this.renderProfiles(data);
    this.renderDefaults(data);
    this.renderCorrections(data);
    if (this._error) this._page.append(this.element("p", this._error, "error"));
  }

  input(value, type = "text", label = "") {
    const input = this.element("input");
    input.type = type;
    input.value = value ?? "";
    if (label) input.setAttribute("aria-label", label);
    return input;
  }

  async save(action, data) {
    try {
      await this.parent(action, data);
      this._parentLoaded = 0;
      this._error = null;
      this._parentData = null;
      this.render();
    } catch (error) {
      this._error = error.message || "Home Assistant could not save that change.";
      this.render();
    }
  }

  renderSchedule(data) {
    const section = this.element("section", undefined, "admin");
    section.append(this.element("h2", "Schedule"));
    const row = this.element("div", undefined, "toolbar");
    const fields = [
      ["dinner_time", "Dinner"], ["bedtime_time", "Bedtime"],
      ["routine_switch_time", "Routine switch"],
    ].map(([key, label]) => {
      const labelNode = this.element("label", label);
      const value = this.input(data.schedule[key].slice(0, 5), "time", label);
      labelNode.append(value);
      row.append(labelNode);
      return [key, value];
    });
    row.append(this.button("Save schedule", () => this.save("schedule", {
      schedule: Object.fromEntries(fields.map(([key, input]) => [key, `${input.value}:00`])),
    })));
    section.append(row);
    this._page.append(section);
  }

  renderProfiles(data) {
    const section = this.element("section", undefined, "admin");
    section.append(this.element("h2", "Children"));
    for (const profile of data.profiles) {
      const row = this.element("div", undefined, "profile");
      const name = this.input(profile.name, "text", `${profile.name}'s name`);
      const actions = this.element("div", undefined, "toolbar");
      actions.append(this.button("Save name", () => this.save("profile_update", {
        child_id: profile.id, name: name.value,
      })));
      const currentPosition = data.profiles.indexOf(profile);
      if (currentPosition > 0) actions.append(this.button("↑", () => this.save("profile_move", {
        child_id: profile.id, position: currentPosition - 1,
      })));
      if (currentPosition < data.profiles.length - 1) actions.append(this.button("↓", () => this.save("profile_move", {
        child_id: profile.id, position: currentPosition + 1,
      })));
      actions.append(this.button(profile.active ? "Archive" : "Restore", () => this.save(
        profile.active ? "profile_archive" : "profile_restore", {child_id: profile.id},
      )));
      row.append(name, actions);
      section.append(row);
    }
    const add = this.element("div", undefined, "toolbar");
    const name = this.input("", "text", "New child's name");
    add.append(name, this.button("Add child", () => this.save("profile_create", {name: name.value})));
    section.append(add);
    this._page.append(section);
  }

  renderDefaults(data) {
    const section = this.element("section", undefined, "admin");
    section.append(this.element("h2", "Shared bedtime tasks"));
    const draft = this._drafts.get("default") || structuredClone(data.default_tasks);
    this._drafts.set("default", draft);
    const rows = this.taskRows(draft, "default");
    for (const row of rows) section.append(row);
    const add = this.element("div", undefined, "toolbar");
    add.append(this.button("Add task", () => {
      draft.push({id: `task_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`, label: "New task", icon: "✓"});
      this.render();
    }));
    const timing = this.effectiveDay();
    add.append(timing);
    add.append(this.button("Save default tasks", () => this.save("default_tasks", {
      tasks: draft, effective_day: timing.value,
    })));
    section.append(add);
    for (const profile of data.profiles.filter((item) => item.active)) {
      const customized = profile.task_overrides?.bedtime;
      const override = this._drafts.get(profile.id)
        || (customized ? structuredClone(customized) : null);
      if (customized) this._drafts.set(profile.id, override);
      const heading = this.element("h3", `${profile.name}’s tasks`);
      section.append(heading);
      section.append(this.button(customized ? "Reset to shared tasks" : "Customize tasks", () => {
        if (customized) this.save("child_tasks", {
          child_id: profile.id, tasks: null, effective_day: "tomorrow",
        });
        else {
          this._drafts.set(profile.id, structuredClone(data.default_tasks));
          this.render();
        }
      }));
      if (override) {
        for (const row of this.taskRows(override, profile.id)) section.append(row);
        const controls = this.element("div", undefined, "toolbar");
        controls.append(this.button("Add child task", () => {
          override.push({id: `task_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`, label: "New task", icon: "✓"});
          this.render();
        }));
        const effective = this.effectiveDay();
        controls.append(effective);
        controls.append(this.button("Save child tasks", () => this.save("child_tasks", {
          child_id: profile.id, tasks: override, effective_day: effective.value,
        })));
        section.append(controls);
      }
    }
    this._page.append(section);
  }

  taskRows(tasks, key) {
    return tasks.map((task, index) => {
      const row = this.element("div", undefined, "task-row");
      const icon = this.input(task.icon, "text", `Icon for ${task.label}`);
      const label = this.input(task.label, "text", "Task label");
      icon.style.maxWidth = "70px";
      row.append(icon, label);
      const draft = this._drafts.get(key);
      row.append(this.button("↑", () => {
        if (index > 0) [draft[index - 1], draft[index]] = [draft[index], draft[index - 1]];
        this.render();
      }));
      row.append(this.button("↓", () => {
        if (index < tasks.length - 1) [draft[index + 1], draft[index]] = [draft[index], draft[index + 1]];
        this.render();
      }));
      row.append(this.button("Remove", () => {
        draft.splice(index, 1);
        this.render();
      }));
      const update = () => { task.label = label.value; task.icon = icon.value; };
      label.addEventListener("input", update);
      icon.addEventListener("input", update);
      return row;
    });
  }

  effectiveDay() {
    const select = this.element("select");
    select.setAttribute("aria-label", "When should checklist changes take effect?");
    for (const [value, label] of [["tomorrow", "Tomorrow"], ["today", "Today"]]) {
      const option = this.element("option", label);
      option.value = value;
      select.append(option);
    }
    return select;
  }

  renderCorrections(data) {
    const section = this.element("section", undefined, "admin");
    section.append(this.element("h2", "This month’s corrections"));
    this._correctionDay ||= data.today;
    const date = this.input(this._correctionDay, "date", "Routine day to correct");
    date.max = data.today;
    date.addEventListener("change", () => {
      this._correctionDay = date.value;
      this._parentData = null;
      this._parentLoaded = 0;
      this.render();
    });
    section.append(date);
    for (const profile of data.profiles) {
      const daily = data.days[profile.id]?.[date.value];
      const entry = this.element("details");
      const summary = this.element("summary", `${profile.name} · ${profile.active ? "active" : "archived"}`);
      entry.append(summary);
      for (const task of this.tasksForProfile(profile, data)) {
        const label = this.element("label", `${task.icon} ${task.label} `);
        const checkbox = this.element("input");
        checkbox.type = "checkbox";
        checkbox.checked = Boolean(daily?.tasks?.bedtime?.[task.id]);
        checkbox.addEventListener("change", () => this.save("correct_task", {
          child_id: profile.id, routine_date: date.value, task: task.id,
          completed: checkbox.checked,
        }));
        label.append(checkbox);
        entry.append(label);
      }
      const sticker = this.element("select");
      for (const emoji of STICKERS) {
        const option = this.element("option", emoji);
        option.value = emoji;
        sticker.append(option);
      }
      sticker.value = daily?.rewards?.bedtime?.emoji || "⭐";
      const earned = this.element("input");
      earned.type = "checkbox";
      earned.checked = Boolean(daily?.rewards?.bedtime?.earned);
      const awardLabel = this.element("label", " Parent-set sticker earned ");
      awardLabel.append(earned);
      entry.append(sticker, awardLabel, this.button("Save reward override", () => this.save("set_reward", {
        child_id: profile.id, routine_date: date.value,
        sticker: sticker.value, earned: earned.checked,
      })));
      section.append(entry);
    }
    this._page.append(section);
  }

  tasksForProfile(profile, data) {
    return profile.task_overrides?.bedtime || data.default_tasks;
  }
}

class BedtimeCardEditor extends HTMLElement {
  setConfig(config) { this._config = config || {}; }
  set hass(hass) { this._hass = hass; }
  connectedCallback() {
    if (this._built) return;
    this._built = true;
    const field = document.createElement("ha-selector");
    field.selector = {text: {}}
    field.label = "Bedtime Sticker Club card settings are managed on the Parent Controls page.";
    this.append(field);
  }
  async getConfig() { return this._config || {}; }
}

customElements.define("bedtime-sticker-family", BedtimeFamilyCard);
customElements.define("bedtime-sticker-parent-controls", BedtimeParentCard);
customElements.define("bedtime-card-editor", BedtimeCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bedtime-sticker-family",
  name: "Bedtime Sticker Club family dashboard",
  description: "The family's bedtime checklists and stickers.",
  preview: true,
});
