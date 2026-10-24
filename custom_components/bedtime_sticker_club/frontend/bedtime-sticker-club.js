// Native family and Parent Controls cards for Bedtime Sticker Club.

const DOMAIN = "bedtime_sticker_club";
const STICKERS = ["⭐", "🌈", "🚀", "🦄", "🦖", "🐱", "🦋", "⚽"];
const AVATAR_CHOICES = [
  "🦊", "🦖", "🦄", "🐱", "🐶", "🐻", "🐼", "🐸", "🐵", "🐰", "🐯", "🐨",
  "🦁", "🐷", "🐮", "🐔", "🐢", "🐙", "🦋", "🐝", "🐬", "🐧", "🦉", "🐲",
  "⭐", "🌈", "🚀", "⚽", "🎨", "🌻", "🍓", "🎵", "🦕", "🐳", "🦩", "🐺",
];

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
    const editor = document.createElement("bedtime-card-editor");
    editor.cardType = this.cardType;
    return editor;
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
      .child.size-compact { padding:10px; border-width:2px; border-radius:18px }
      .child.size-large { padding:22px; border-radius:30px }
      .child.size-compact .name { font-size:20px }
      .child.size-large .name { font-size:28px }
      .identity { display:flex; align-items:center; gap:12px; min-width:0 }
      .avatar { box-sizing:border-box; width:58px; height:58px; min-width:58px; min-height:58px;
        flex:none; display:grid; place-items:center; padding:0; border:0; overflow:hidden;
        border-radius:20px; color:inherit; background:var(--tint,#f0e6ff); font-size:37px;
        line-height:1; text-align:center; cursor:pointer }
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
      .calendar-controls { display:flex; gap:8px; margin-top:10px }
      .calendar { margin-top:10px; border-top:2px dashed #e7e2ed; padding-top:10px }
      .calendar-title { display:flex; align-items:center; justify-content:space-between; margin:4px 0 10px;
        font-weight:850 }
      .calendar-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:4px }
      .weekday { text-align:center; color:var(--muted); font-size:11px; font-weight:800 }
      .calendar-day { min-width:0; min-height:52px; display:grid; align-content:start; gap:3px;
        padding:4px 2px; text-align:center; font-size:12px }
      .calendar-day.selected { outline:3px solid var(--accent,#7541bf); outline-offset:1px }
      .calendar-row { display:flex; justify-content:center; gap:1px; white-space:nowrap;
        font-size:10px; line-height:1.2 }
      .calendar-detail { margin-top:10px; padding:12px; border-radius:14px; background:#f6f3f8;
        color:var(--ink); font-size:13px }
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
      .picker-backdrop { position:fixed; inset:0; z-index:1000; display:grid; place-items:center;
        padding:16px; background:#211b2d88 }
      .picker-dialog { width:min(100%,480px); max-height:90vh; overflow:auto; display:grid;
        gap:12px; padding:20px; border-radius:24px; background:#fffefb; box-shadow:0 10px 48px #0005 }
      .picker-emoji { display:grid; grid-template-columns:repeat(6,minmax(48px,1fr)); gap:6px }
      .picker-emoji button { min-height:48px; padding:2px; text-align:center; font-size:25px }
      .picker-dialog input[type=text] { min-height:48px; padding:10px; border:1px solid #90889b;
        border-radius:10px; color:var(--ink); font:inherit }
      .avatar-image { display:block; width:100%; height:100%; object-fit:cover; border-radius:inherit }
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
    if (this.constructor === BedtimeCalendarCard) return this.renderCalendar();
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
  static cardType = "bedtime-sticker-family";

  static getStubConfig() { return {type: `custom:${this.cardType}`}; }

  constructor() {
    super();
    this._routineOverrides = new Map();
    this._avatarObjects = new Map();
    this._expandedCalendars = new Set();
    this._selectedCalendarDays = new Map();
  }

  renderFamily() {
    this.shell("Bedtime Sticker Club 🌟");
    const connected = this._hass.connected !== false && this._hass.connection?.connected !== false;
    const routineEntity = this._hass.states["sensor.bedtime_routine"];
    const day = routineEntity?.attributes.routine_date;
    if (day && day !== this._routineDay) {
      this._routineOverrides.clear();
      this._routineDay = day;
    }
    const automaticRoutine = routineEntity?.attributes.active_routine || "bedtime";
    const message = this.element("p", connected
      ? automaticRoutine === "morning"
        ? "Before school · Four little tasks to start the day."
        : "Tonight’s routine · Three little tasks, one happy sticker."
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
        && state.attributes.routine === "bedtime"
        && !state.attributes.archived)
      .sort((a, b) => a.attributes.display_order - b.attributes.display_order);
    if (!profiles.length) {
      grid.append(this.element("p", "Add a child in Parent Controls to create their checklist."));
    }
    for (const state of profiles) {
      const childId = state.attributes.child_id;
      const morning = Object.values(this._hass.states).find((candidate) =>
        candidate.attributes.child_id === childId && candidate.attributes.routine === "morning");
      grid.append(this.renderChild(state, morning, connected, automaticRoutine));
    }
    this._page.append(grid);
    if (this._error) this._page.append(this.element("p", this._error, "error"));
  }

  renderChild(state, morningState, connected, automaticRoutine) {
    const attributes = state.attributes;
    const routine = this._routineOverrides.get(attributes.child_id) || automaticRoutine;
    const selected = routine === "morning" && morningState ? morningState : state;
    const routineAttributes = selected.attributes;
    const card = this.element("article", undefined, "child");
    card.classList.add(`size-${attributes.card_size || "standard"}`);
    card.style.setProperty("--accent", attributes.accent || "#7541bf");
    card.style.setProperty("--tint", attributes.tint || "#f0e6ff");
    const identity = this.element("header", undefined, "identity");
    const avatar = this.button(attributes.avatar || "🙂", async () => {
      this.showAvatarPicker(attributes);
    }, "avatar");
    avatar.setAttribute("aria-label", `Change ${attributes.child_name}'s avatar`);
    avatar.setAttribute("aria-haspopup", "dialog");
    const avatarImage = this._avatarObjects.get(attributes.child_id)?.filename || attributes.avatar_image;
    if (avatarImage) {
      avatar.textContent = "";
      const image = this.element("img");
      image.className = "avatar-image";
      image.alt = "";
      avatar.append(image);
      this.loadAvatar(attributes.child_id, avatarImage).then((url) => {
        if (url && image.isConnected) image.src = url;
        else if (image.isConnected) avatar.textContent = attributes.avatar || "🙂";
      }).catch(() => {
        if (image.isConnected) avatar.textContent = attributes.avatar || "🙂";
      });
    }
    identity.append(avatar);
    const name = this.element("div");
    name.append(this.element("div", attributes.child_name, "name"));
    name.append(this.element("div", `My ${routineAttributes.routine} checklist`, "muted"));
    identity.append(name);
    card.append(identity);
    if (morningState) {
      const toggle = this.button(
        `Switch to ${routine === "morning" ? "bedtime" : "morning"}`,
        () => {
          this._routineOverrides.set(attributes.child_id, routine === "morning" ? "bedtime" : "morning");
          this.render();
        },
      );
      card.append(toggle);
    }
    const definitions = routineAttributes.task_definitions || [];
    const completed = Number(routineAttributes.completed || 0);
    card.append(this.element("p", `${completed} of ${definitions.length} done`, "muted"));
    const tasks = this.element("div", undefined, "tasklist");
    for (const task of definitions) {
      const done = Boolean(routineAttributes.tasks?.[task.id]);
      const button = this.button("", () => this.call("set_task", {
        child_id: attributes.child_id,
        task: task.id,
        completed: !done,
        routine_date: routineAttributes.routine_date,
        routine,
      }), `${done ? "done " : ""}row`);
      button.disabled = !connected || state.state === "unavailable";
      button.append(this.element("span", task.icon || "✓"));
      button.append(this.element("span", task.label, "label"));
      button.append(this.element("span", done ? "✓" : "", "check"));
      tasks.append(button);
    }
    card.append(tasks);
    const award = routineAttributes.stickers?.[routineAttributes.routine_date];
    if (routineAttributes.earned || award?.earned) {
      card.append(this.element("p", "You earned a sticker! Pick your favorite ↓", "sticker"));
      const picker = this.element("div", undefined, "stickers");
      for (const sticker of STICKERS) {
        const button = this.button(sticker, () => this.call("choose_sticker", {
          child_id: attributes.child_id,
          routine_date: routineAttributes.routine_date,
          routine,
          sticker,
        }), award?.emoji === sticker ? "chosen" : "");
        button.disabled = !connected;
        button.setAttribute("aria-label", `Choose sticker ${sticker}`);
        picker.append(button);
      }
      card.append(picker);
    }
    const total = routineAttributes.lifetime_total ?? selected.state;
    card.append(this.element("p", `🏆 ${total} ${routine}${Number(total) === 1 ? "" : "s"} completed`, "muted"));
    const calendarEnabled = this.constructor !== BedtimeChildChecklistCard
      || (this._config?.calendar || "collapsible") === "collapsible";
    const calendarOpen = this._expandedCalendars.has(attributes.child_id);
    if (calendarEnabled) card.append(this.button(`${calendarOpen ? "Hide" : "Show"} sticker calendar`, () => {
      if (calendarOpen) this._expandedCalendars.delete(attributes.child_id);
      else this._expandedCalendars.add(attributes.child_id);
      this.render();
    }));
    if (calendarEnabled && calendarOpen && morningState) {
      card.append(renderCalendar(this, [{bedtime: state, morning: morningState}], attributes.month,
        this._selectedCalendarDays.get(attributes.child_id), (day) => {
          this._selectedCalendarDays.set(attributes.child_id, day);
          this.render();
        }));
    }
    return card;
  }

  async authenticatedFetch(path, options = {}) {
    if (this._hass.fetchWithAuth) return this._hass.fetchWithAuth(path, options);
    const token = this._hass.auth?.data?.access_token || this._hass.auth?.accessToken;
    if (!token) throw new Error("Reconnect Home Assistant before uploading or loading an avatar.");
    return fetch(path, {
      ...options,
      headers: {"Authorization": `Bearer ${token}`, ...(options.headers || {})},
    });
  }

  async loadAvatar(childId, filename) {
    const cached = this._avatarObjects.get(childId);
    if (cached?.filename === filename) return cached.url;
    const response = await this.authenticatedFetch(`/api/${DOMAIN}/avatars/${encodeURIComponent(childId)}`);
    if (!response.ok) return null;
    const previous = this._avatarObjects.get(childId);
    if (previous) URL.revokeObjectURL(previous.url);
    const url = URL.createObjectURL(await response.blob());
    this._avatarObjects.set(childId, {filename, url});
    return url;
  }

  showAvatarPicker(profile) {
    const backdrop = this.element("div", undefined, "picker-backdrop");
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) backdrop.remove();
    });
    const dialog = this.element("section", undefined, "picker-dialog");
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", `Choose ${profile.child_name}'s avatar`);
    const title = this.element("h2", `Choose ${profile.child_name}’s avatar`);
    dialog.append(title);
    dialog.append(this.element("p", "Choose an emoji or upload a square-cropped image.", "muted"));
    const emojiGrid = this.element("div", undefined, "picker-emoji");
    for (const emoji of AVATAR_CHOICES) {
      const choice = this.button(emoji, async () => {
        await this.call("set_avatar", {child_id: profile.child_id, avatar: emoji});
        const previous = this._avatarObjects.get(profile.child_id);
        if (previous) URL.revokeObjectURL(previous.url);
        this._avatarObjects.delete(profile.child_id);
        backdrop.remove();
      });
      choice.setAttribute("aria-label", `Use ${emoji} as ${profile.child_name}'s avatar`);
      emojiGrid.append(choice);
    }
    dialog.append(emojiGrid);
    const customLabel = this.element("label", "Enter another emoji");
    const custom = this.input(profile.avatar, "text", "Enter another emoji");
    custom.maxLength = 16;
    customLabel.append(custom);
    dialog.append(customLabel);
    dialog.append(this.button("Save emoji", async () => {
      if ([...custom.value].length > 0) {
        await this.call("set_avatar", {child_id: profile.child_id, avatar: custom.value});
        backdrop.remove();
      }
    }));
    const upload = this.element("input");
    upload.type = "file";
    upload.accept = "image/jpeg,image/png,image/webp";
    upload.setAttribute("aria-label", "Upload a photo avatar");
    const uploadButton = this.button("Upload image", () => upload.click());
    upload.addEventListener("change", async () => {
      const file = upload.files?.[0];
      if (!file) return;
      if (file.size > 5 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
        this._error = "Choose a JPEG, PNG, or WebP image no larger than 5 MiB.";
        this.render();
        return;
      }
      uploadButton.disabled = true;
      uploadButton.textContent = "Uploading…";
      try {
        const result = await this.authenticatedFetch(
          `/api/${DOMAIN}/avatars/${encodeURIComponent(profile.child_id)}`,
          {method: "POST", headers: {"Content-Type": file.type}, body: file},
        );
        if (!result.ok) throw new Error((await result.text()) || "Home Assistant could not save the avatar.");
        const body = await result.json();
        const previous = this._avatarObjects.get(profile.child_id);
        if (previous) URL.revokeObjectURL(previous.url);
        this._avatarObjects.delete(profile.child_id);
        await this.loadAvatar(profile.child_id, body.avatar_image);
        this._error = null;
        backdrop.remove();
        this.render();
      } catch (error) {
        uploadButton.disabled = false;
        uploadButton.textContent = "Upload image";
        const message = this.element("p", error.message, "error");
        dialog.append(message);
      }
    });
    dialog.append(upload, uploadButton);
    dialog.append(this.button("Cancel", () => backdrop.remove()));
    backdrop.append(dialog);
    this.shadowRoot.append(backdrop);
    custom.focus();
  }
}

class BedtimeChildChecklistCard extends BedtimeFamilyCard {
  static cardType = "bedtime-sticker-child-card";

  static getStubConfig() {
    return {
      type: `custom:${this.cardType}`,
      routine: "auto",
      size: "inherit",
      calendar: "collapsible",
    };
  }

  setConfig(config) {
    super.setConfig(config);
    if (config.routine !== undefined && !["auto", "bedtime", "morning"].includes(config.routine)) {
      throw new Error("routine must be auto, bedtime, or morning.");
    }
    if (config.size !== undefined && !["inherit", "compact", "standard", "large"].includes(config.size)) {
      throw new Error("size must be inherit, compact, standard, or large.");
    }
    if (config.calendar !== undefined && !["collapsible", "hidden"].includes(config.calendar)) {
      throw new Error("calendar must be collapsible or hidden.");
    }
  }

  render() {
    if (!this._hass) return;
    this.shell("Bedtime checklist");
    const state = Object.values(this._hass.states).find((candidate) =>
      candidate.attributes.child_id === this._config.child_id
      && candidate.attributes.routine === "bedtime");
    if (!state) {
      this._body.textContent = "Choose a child in the card settings.";
      return;
    }
    const attributes = state.attributes;
    if (attributes.archived) {
      this._body.textContent = `${attributes.child_name}'s profile is archived.`;
      return;
    }
    const morning = Object.values(this._hass.states).find((candidate) =>
      candidate.attributes.child_id === attributes.child_id
      && candidate.attributes.routine === "morning");
    const autoRoutine = this._hass.states["sensor.bedtime_routine"]?.attributes.active_routine || "bedtime";
    if (this._config.routine && this._config.routine !== "auto" && !this._routineOverrides.has(attributes.child_id)) {
      this._routineOverrides.set(attributes.child_id, this._config.routine);
    }
    const originalSize = attributes.card_size;
    const size = this._config.size || "inherit";
    const stateForCard = {
      ...state,
      attributes: {
        ...attributes,
        card_size: size === "inherit" ? originalSize : size,
      },
    };
    this._body.textContent = "";
    this._page.append(this.renderChild(stateForCard, morning, this._hass.connected !== false, autoRoutine));
  }
}

class BedtimeCalendarCard extends BedtimeCard {
  static cardType = "bedtime-sticker-calendar";

  static getStubConfig() { return {type: `custom:${this.cardType}`}; }

  constructor() {
    super();
    this._selectedDay = null;
  }

  setConfig(config) {
    super.setConfig(config);
    if (config.child_ids !== undefined
      && (!Array.isArray(config.child_ids) || !config.child_ids.every((id) => typeof id === "string"))) {
      throw new Error("child_ids must be a list of child profile IDs.");
    }
  }

  renderCalendar() {
    this.shell("Family sticker calendar");
    const states = Object.values(this._hass.states);
    const selectedIds = this._config.child_ids;
    const profiles = states
      .filter((state) => state.entity_id.startsWith("sensor.bedtime_")
        && state.attributes.routine === "bedtime"
        && (selectedIds ? selectedIds.includes(state.attributes.child_id) : !state.attributes.archived))
      .sort((a, b) => a.attributes.display_order - b.attributes.display_order)
      .map((bedtime) => ({
        bedtime,
        morning: states.find((state) => state.attributes.child_id === bedtime.attributes.child_id
          && state.attributes.routine === "morning"),
      })).filter((profile) => profile.morning);
    if (!profiles.length) {
      this._body.textContent = "Choose an active child to show their sticker calendar.";
      return;
    }
    const month = profiles[0].bedtime.attributes.month;
    this._body.textContent = monthTitle(month);
    this._page.append(renderCalendar(this, profiles, month, this._selectedDay, (day) => {
      this._selectedDay = day;
      this.render();
    }));
  }
}

function monthTitle(month) {
  const [year, number] = month.split("-").map(Number);
  return new Date(Date.UTC(year, number - 1, 1)).toLocaleDateString("en-US", {
    month: "long", year: "numeric", timeZone: "UTC",
  });
}

function renderCalendar(owner, profiles, month, selectedDay, selectDay) {
  const section = owner.element("section", undefined, "calendar");
  section.append(owner.element("div", monthTitle(month), "calendar-title"));
  const grid = owner.element("div", undefined, "calendar-grid");
  for (const weekday of ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) {
    grid.append(owner.element("div", weekday, "weekday"));
  }
  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  for (let blank = 0; blank < firstWeekday; blank++) grid.append(document.createElement("span"));
  for (let number = 1; number <= daysInMonth; number++) {
    const day = `${month}-${String(number).padStart(2, "0")}`;
    const button = owner.button(String(number), () => selectDay(day),
      `calendar-day${selectedDay === day ? " selected" : ""}`);
    const descriptions = [];
    for (const profile of profiles) {
      const {bedtime, morning} = profile;
      const morningSticker = morning.attributes.stickers?.[day];
      const bedtimeSticker = bedtime.attributes.stickers?.[day];
      const description = `${bedtime.attributes.child_name}: morning `
        + `${morningSticker?.earned ? morningSticker.emoji : "no sticker"}; bedtime `
        + `${bedtimeSticker?.earned ? bedtimeSticker.emoji : "no sticker"}`;
      descriptions.push(description);
      const row = owner.element("span",
        `${bedtime.attributes.avatar || "🙂"}${morningSticker?.earned ? morningSticker.emoji : "·"}`
          + `${bedtimeSticker?.earned ? bedtimeSticker.emoji : "·"}`,
        "calendar-row",
      );
      row.title = description;
      row.setAttribute("aria-label", description);
      button.append(row);
    }
    button.setAttribute("aria-label", `${day}. ${descriptions.join(". ")}`);
    grid.append(button);
  }
  section.append(grid);
  if (selectedDay) {
    const details = owner.element("section", undefined, "calendar-detail");
    details.append(owner.element("h3", `Sticker details · ${selectedDay}`));
    let hasReward = false;
    for (const {bedtime, morning} of profiles) {
      const morningSticker = morning.attributes.stickers?.[selectedDay];
      const bedtimeSticker = bedtime.attributes.stickers?.[selectedDay];
      hasReward ||= Boolean(morningSticker?.earned || bedtimeSticker?.earned);
      details.append(owner.element("p",
        `${bedtime.attributes.avatar || "🙂"} ${bedtime.attributes.child_name}: `
        + `morning ${morningSticker?.earned ? morningSticker.emoji : "no sticker"}; `
        + `bedtime ${bedtimeSticker?.earned ? bedtimeSticker.emoji : "no sticker"}.`,
      ));
    }
    if (!hasReward) details.append(owner.element("p", "No stickers were earned on this day."));
    if (owner._hass.user?.is_admin && selectedDay <= profiles[0].bedtime.attributes.routine_date) {
      details.append(owner.button("Correct this day", () => {
        window.history.pushState(null, "", `/bedtime-club/parents?routine_date=${encodeURIComponent(selectedDay)}`);
        window.dispatchEvent(new Event("location-changed"));
      }));
    }
    section.append(details);
  }
  return section;
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
      const size = this.element("select");
      for (const value of ["compact", "standard", "large"]) {
        const option = this.element("option", value[0].toUpperCase() + value.slice(1));
        option.value = value;
        size.append(option);
      }
      size.value = profile.size || "standard";
      const actions = this.element("div", undefined, "toolbar");
      actions.append(this.button("Save name", () => this.save("profile_update", {
        child_id: profile.id, name: name.value, size: size.value,
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
      row.append(name, size, actions);
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
    this.renderMorningTasks(data);
  }

  renderMorningTasks(data) {
    const section = this.element("section", undefined, "admin");
    section.append(this.element("h2", "Shared morning tasks"));
    const draft = this._drafts.get("default:morning")
      || structuredClone(data.default_morning_tasks || []);
    this._drafts.set("default:morning", draft);
    for (const row of this.taskRows(draft, "default:morning")) section.append(row);
    const controls = this.element("div", undefined, "toolbar");
    controls.append(this.button("Add morning task", () => {
      draft.push({id: `task_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`, label: "New morning task", icon: "✓"});
      this.render();
    }));
    const timing = this.effectiveDay();
    controls.append(timing, this.button("Save morning defaults", () => this.save("default_tasks", {
      routine: "morning", tasks: draft, effective_day: timing.value,
    })));
    section.append(controls);
    for (const profile of data.profiles.filter((item) => item.active)) {
      const customized = profile.task_overrides?.morning;
      const key = `${profile.id}:morning`;
      const override = this._drafts.get(key)
        || (customized ? structuredClone(customized) : null);
      if (customized) this._drafts.set(key, override);
      section.append(this.element("h3", `${profile.name}’s morning tasks`));
      section.append(this.button(customized ? "Reset to shared morning tasks" : "Customize morning tasks", () => {
        if (customized) this.save("child_tasks", {
          child_id: profile.id, routine: "morning", tasks: null, effective_day: "tomorrow",
        });
        else {
          this._drafts.set(key, structuredClone(data.default_morning_tasks || []));
          this.render();
        }
      }));
      if (!override) continue;
      for (const row of this.taskRows(override, key)) section.append(row);
      const settings = this.element("div", undefined, "toolbar");
      settings.append(this.button("Add child morning task", () => {
        override.push({id: `task_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`, label: "New morning task", icon: "✓"});
        this.render();
      }));
      const effective = this.effectiveDay();
      settings.append(effective, this.button("Save child morning tasks", () => this.save("child_tasks", {
        child_id: profile.id, routine: "morning", tasks: override, effective_day: effective.value,
      })));
      section.append(settings);
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
    const requestedDate = new URL(window.location.href).searchParams.get("routine_date");
    if (requestedDate && requestedDate !== this._parentRequestedDate) {
      this._parentRequestedDate = requestedDate;
      this._correctionDay = requestedDate;
    }
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
      for (const routine of ["bedtime", "morning"]) {
        entry.append(this.element("h3", `${routine[0].toUpperCase()}${routine.slice(1)}`));
        for (const task of this.tasksForProfile(profile, data, routine)) {
          const label = this.element("label", `${task.icon} ${task.label} `);
          const checkbox = this.element("input");
          checkbox.type = "checkbox";
          checkbox.checked = Boolean(daily?.tasks?.[routine]?.[task.id]);
          checkbox.addEventListener("change", () => this.save("correct_task", {
            child_id: profile.id, routine, routine_date: date.value,
            task: task.id, completed: checkbox.checked,
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
        sticker.value = daily?.rewards?.[routine]?.emoji || "⭐";
        const earned = this.element("input");
        earned.type = "checkbox";
        earned.checked = Boolean(daily?.rewards?.[routine]?.earned);
        const awardLabel = this.element("label", ` Parent-set ${routine} sticker earned `);
        awardLabel.append(earned);
        entry.append(sticker, awardLabel, this.button(`Save ${routine} reward`, () => this.save("set_reward", {
          child_id: profile.id, routine, routine_date: date.value,
          sticker: sticker.value, earned: earned.checked,
        })));
      }
      section.append(entry);
    }
    this._page.append(section);
  }

  tasksForProfile(profile, data, routine = "bedtime") {
    return profile.task_overrides?.[routine]
      || (routine === "bedtime" ? data.default_tasks : data.default_morning_tasks);
  }
}

class BedtimeCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
  }

  setConfig(config) {
    this._config = {...(config || {})};
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  element(tag, label, value) {
    const node = document.createElement(tag);
    if (label) node.textContent = label;
    if (value !== undefined) node.value = value;
    return node;
  }

  addField(container, labelText, field) {
    const label = this.element("label", labelText);
    label.append(field);
    container.append(label);
  }

  select(options, value, onChange, multiple = false) {
    const control = this.element("select");
    control.multiple = multiple;
    for (const [optionValue, labelText] of options) {
      const option = this.element("option", labelText, optionValue);
      option.value = optionValue;
      option.selected = multiple ? value.includes(optionValue) : optionValue === value;
      control.append(option);
    }
    control.addEventListener("change", onChange);
    return control;
  }

  changed(patch) {
    this._config = {...this._config, ...patch};
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: {config: this._config}, bubbles: true, composed: true,
    }));
  }

  render() {
    if (!this._hass || !this.cardType) return;
    this.shadowRoot.replaceChildren();
    const style = document.createElement("style");
    style.textContent = "label {display:grid;gap:8px;margin:12px 0} input,select {min-height:42px;padding:8px;font:inherit} p {color:var(--secondary-text-color)}";
    this.shadowRoot.append(style);
    const body = document.createElement("section");
    if (this.cardType === "bedtime-sticker-child-card") {
      const profiles = Object.values(this._hass.states)
        .filter((state) => state.attributes.routine === "bedtime"
          && state.entity_id.startsWith("sensor.bedtime_"))
        .sort((a, b) => a.attributes.display_order - b.attributes.display_order);
      const options = profiles.map((state) => [state.attributes.child_id, state.attributes.child_name]);
      const child = this.select(options, this._config.child_id || options[0]?.[0], (event) => {
        this.changed({child_id: event.target.value});
      });
      this.addField(body, "Child", child);
      this.addField(body, "Routine", this.select(
        [["auto", "Automatic"], ["morning", "Morning"], ["bedtime", "Bedtime"]],
        this._config.routine || "auto",
        (event) => this.changed({routine: event.target.value}),
      ));
      this.addField(body, "Size", this.select(
        [["inherit", "Use child size"], ["compact", "Compact"], ["standard", "Standard"], ["large", "Large"]],
        this._config.size || "inherit",
        (event) => this.changed({size: event.target.value}),
      ));
      this.addField(body, "Calendar", this.select(
        [["collapsible", "Expandable"], ["hidden", "Hidden"]],
        this._config.calendar || "collapsible",
        (event) => this.changed({calendar: event.target.value}),
      ));
      if (!options.length) body.append(this.element("p", "Add a child profile before configuring a checklist card."));
    } else if (this.cardType === "bedtime-sticker-calendar") {
      const profiles = Object.values(this._hass.states)
        .filter((state) => state.attributes.routine === "bedtime"
          && state.entity_id.startsWith("sensor.bedtime_"))
        .sort((a, b) => a.attributes.display_order - b.attributes.display_order);
      const activeIds = profiles.filter((state) => !state.attributes.archived)
        .map((state) => state.attributes.child_id);
      const value = this._config.child_ids || activeIds;
      const select = this.select(profiles.map((state) => [
        state.attributes.child_id,
        `${state.attributes.child_name}${state.attributes.archived ? " (archived)" : ""}`,
      ]), value, (event) => {
        const selected = [...event.target.selectedOptions].map((option) => option.value);
        const patch = selected.length === activeIds.length
          && activeIds.every((id) => selected.includes(id))
          ? {child_ids: undefined}
          : {child_ids: selected};
        this.changed(patch);
      }, true);
      select.size = Math.min(Math.max(profiles.length, 3), 8);
      this.addField(body, "Children (select one or more; blank means all active children)", select);
    } else {
      body.append(this.element("p", "Shows the live family checklist for every active child."));
    }
    this.shadowRoot.append(body);
  }

  async getConfig() { return this._config || {}; }
}

customElements.define("bedtime-sticker-family", BedtimeFamilyCard);
customElements.define("bedtime-sticker-child-card", BedtimeChildChecklistCard);
customElements.define("bedtime-sticker-parent-controls", BedtimeParentCard);
customElements.define("bedtime-card-editor", BedtimeCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "bedtime-sticker-family",
  name: "Bedtime Sticker Club family dashboard",
  description: "The family's bedtime checklists and stickers.",
  preview: true,
});
window.customCards.push({
  type: "bedtime-sticker-child-card",
  name: "Bedtime Sticker Club child checklist",
  description: "A configurable morning or bedtime checklist for one child.",
  preview: true,
});
customElements.define("bedtime-sticker-calendar", BedtimeCalendarCard);
window.customCards.push({
  type: "bedtime-sticker-calendar",
  name: "Bedtime Sticker Club calendar",
  description: "A shared morning and bedtime sticker calendar for selected children.",
  preview: true,
});
