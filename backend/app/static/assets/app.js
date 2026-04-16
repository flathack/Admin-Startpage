const state = {
  token: localStorage.getItem("startpage.sessionToken") || "",
  user: null,
  dashboard: { headline: "", widgets: [] },
  integrations: [],
  activeIntegration: null,
  activeNav: "dashboard",
  activeAdNode: "ad-users-computers",
  adTreeExpanded: true,
  connector: null,
  sessionExpiresAt: "",
  rolloutJobs: [],
  rolloutSummary: null,
};

const NAV_STRUCTURE = [
  { id: "dashboard", label: "Dashboard", icon: "■", permission: "startpage.dashboard.view" },
  {
    id: "ad",
    label: "ActiveDirectory",
    icon: "◎",
    permission: "ad.view",
    children: [
      { id: "ad-users-computers", label: "AD Users & Computers" },
      { id: "ad-reports", label: "Auswertungen" },
      { id: "ad-dns", label: "DNS" },
      { id: "ad-dhcp", label: "DHCP" },
    ],
  },
  { id: "nutanix", label: "Nutanix", icon: "◈", permission: "nutanix.view" },
  { id: "endpoint", label: "Endpoint Central", icon: "◌", permission: "endpoint.view" },
  { id: "citrix", label: "Citrix", icon: "◍", permission: "citrix.view" },
  { id: "rollout", label: "Rollout", icon: "▣", permission: "rollout.view" },
];

const VIEW_META = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Persoenliche Startseite mit Widgets, Schnellzugriffen und einem klaren Ueberblick.",
  },
  ad: {
    title: "ActiveDirectory",
    subtitle: "Tree-basierter Zugriff auf AD Users & Computers, Auswertungen, DNS und DHCP.",
  },
  nutanix: {
    title: "Nutanix",
    subtitle: "Cluster- und VM-nahe Informationen in einer fokussierten Arbeitsansicht.",
  },
  endpoint: {
    title: "Endpoint Central",
    subtitle: "Agent-, Inventar- und Patch-nahe Informationen fuer Clients und Server.",
  },
  citrix: {
    title: "Citrix",
    subtitle: "On-Prem Maschinen- und Connector-nahe Informationen fuer den Citrix-Betrieb.",
  },
  rollout: {
    title: "Rollout",
    subtitle: "Rollout-nahe Operations-Sicht als Bruecke zum Rollout-Monitor.",
  },
};

const elements = {
  loginView: document.querySelector("#loginView"),
  loginForm: document.querySelector("#loginForm"),
  loginMessage: document.querySelector("#loginMessage"),
  usernameInput: document.querySelector("#usernameInput"),
  passwordInput: document.querySelector("#passwordInput"),
  appView: document.querySelector("#appView"),
  healthBadges: document.querySelector("#healthBadges"),
  sidebarNav: document.querySelector("#sidebarNav"),
  sidebarUserLabel: document.querySelector("#sidebarUserLabel"),
  connectorStatusBox: document.querySelector("#connectorStatusBox"),
  welcomeMeta: document.querySelector("#welcomeMeta"),
  welcomeTitle: document.querySelector("#welcomeTitle"),
  workspaceSubtitle: document.querySelector("#workspaceSubtitle"),
  searchInput: document.querySelector("#searchInput"),
  refreshIntegrationsButton: document.querySelector("#refreshIntegrationsButton"),
  logoutButton: document.querySelector("#logoutButton"),
  contentPrimary: document.querySelector("#contentPrimary"),
  contentSecondary: document.querySelector("#contentSecondary"),
};

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) {
    headers.set("X-Session-Token", state.token);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) {
      resetClientState();
    }
    const message = payload.detail || payload.message || "Anfrage fehlgeschlagen.";
    throw new Error(message);
  }
  return payload;
}

function resetClientState() {
  localStorage.removeItem("startpage.sessionToken");
  state.token = "";
  state.user = null;
  state.dashboard = { headline: "", widgets: [] };
  state.integrations = [];
  state.activeIntegration = null;
  state.activeNav = "dashboard";
  state.activeAdNode = "ad-users-computers";
  state.adTreeExpanded = true;
  state.sessionExpiresAt = "";
  elements.appView.classList.add("hidden");
  elements.loginView.classList.remove("hidden");
}

function setMessage(message, type = "") {
  elements.loginMessage.textContent = message;
  elements.loginMessage.className = `message ${type}`.trim();
}

function integrationStatusClass(status) {
  return `status-${status || "unknown"}`;
}

function renderHealth(data) {
  state.connector = data.connector || null;
  elements.healthBadges.innerHTML = "";
  [
    `Status: ${data.status}`,
    data.mockAuth ? "Mock Auth aktiv" : "LDAP aktiv",
    data.mockIntegrations ? "Mock Integrationen aktiv" : "Live Integrationen aktiv",
    "Docker Backend",
    "Portainer Layout",
  ].forEach((label) => {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = label;
    elements.healthBadges.appendChild(badge);
  });
  renderConnectorStatus();
}

function renderConnectorStatus() {
  elements.connectorStatusBox.innerHTML = "";
  if (!state.connector) {
    elements.connectorStatusBox.innerHTML = "<div class='placeholder-block'>Kein Connector-Status verfuegbar.</div>";
    return;
  }

  const rows = [
    ["Aktiviert", String(state.connector.enabled)],
    ["Erreichbar", String(state.connector.reachable)],
    ["Modus", state.connector.mode || "unknown"],
    ["URL", state.connector.baseUrl || "-"],
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "meta-row";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    elements.connectorStatusBox.appendChild(row);
  });

  const note = document.createElement("div");
  note.className = "note-card";
  note.textContent = state.connector.message || "Kein Hinweis verfuegbar.";
  elements.connectorStatusBox.appendChild(note);

  (state.connector.capabilities || []).forEach((capability) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = capability;
    elements.connectorStatusBox.appendChild(chip);
  });
}

function hasPermission(permission) {
  if (!state.user || !permission) {
    return false;
  }
  const domain = permission.split(".")[0];
  return state.user.permissions.includes(permission) || state.user.permissions.includes(`${domain}.*`);
}

function availableNavItems() {
  return NAV_STRUCTURE.filter((item) => hasPermission(item.permission));
}

function integrationById(systemId) {
  return state.integrations.find((integration) => integration.id === systemId) || null;
}

function buildSummaryCard(title, value, description) {
  return `
    <div class="summary-card">
      <strong>${value}</strong>
      <h4>${title}</h4>
      <p>${description}</p>
    </div>
  `;
}

function renderSidebar() {
  if (!state.user) {
    return;
  }

  elements.sidebarUserLabel.textContent = state.user.displayName || state.user.username;
  elements.sidebarNav.innerHTML = "";

  availableNavItems().forEach((item) => {
    const wrapper = document.createElement("div");
    wrapper.className = "sidebar-section";

    const button = document.createElement("button");
    button.type = "button";
    button.className = `nav-item ${state.activeNav === item.id ? "active" : ""}`.trim();
    button.dataset.navId = item.id;
    button.innerHTML = `
      <span class="nav-item-main">
        <span class="nav-icon">${item.icon}</span>
        <span>${item.label}</span>
      </span>
      ${item.children ? `<span>${state.adTreeExpanded ? "▾" : "▸"}</span>` : ""}
    `;
    wrapper.appendChild(button);

    if (item.children && state.adTreeExpanded) {
      const tree = document.createElement("div");
      tree.className = "sidebar-tree";
      item.children.forEach((child) => {
        const treeButton = document.createElement("button");
        treeButton.type = "button";
        treeButton.className = `tree-item ${state.activeAdNode === child.id ? "active" : ""}`.trim();
        treeButton.dataset.treeId = child.id;
        treeButton.textContent = child.label;
        tree.appendChild(treeButton);
      });
      wrapper.appendChild(tree);
    }

    elements.sidebarNav.appendChild(wrapper);
  });
}

function renderUserContext() {
  if (!state.user) {
    return "";
  }
  const sessionInfo = state.sessionExpiresAt ? new Date(state.sessionExpiresAt).toLocaleString("de-DE") : "-";
  return `
    <div class="info-card">
      <div class="meta-row"><span>Display Name</span><strong>${state.user.displayName}</strong></div>
      <div class="meta-row"><span>Benutzer</span><strong>${state.user.username}</strong></div>
      <div class="meta-row"><span>E-Mail</span><strong>${state.user.email || "-"}</strong></div>
      <div class="meta-row"><span>DN</span><strong>${state.user.distinguishedName}</strong></div>
      <div class="meta-row"><span>Session gueltig bis</span><strong>${sessionInfo}</strong></div>
    </div>
    <div class="info-card">
      <h4>Rollen</h4>
      <div class="chip-list">${state.user.roles.map((role) => `<span class="chip">${role}</span>`).join("")}</div>
    </div>
    <div class="info-card">
      <h4>AD Gruppen</h4>
      <div class="chip-list">${state.user.adGroups.map((group) => `<span class="chip">${group}</span>`).join("")}</div>
    </div>
  `;
}

function renderDashboardView() {
  const filterValue = elements.searchInput.value.trim().toLowerCase();
  const widgets = state.dashboard.widgets.filter((widget) => {
    if (!filterValue) {
      return true;
    }
    return `${widget.title} ${widget.category} ${widget.description}`.toLowerCase().includes(filterValue);
  });

  const visibleModules = availableNavItems().filter((item) => item.id !== "dashboard");

  elements.contentPrimary.innerHTML = `
    <section class="workspace-section">
      <div class="section-header">
        <div>
          <p class="eyebrow">Persoenliche Startseite</p>
          <h3 class="section-title">Widgets und Schnellzugriffe</h3>
        </div>
        <button id="saveDashboardButton" type="button">Aenderungen speichern</button>
      </div>
      <div class="summary-grid">
        ${buildSummaryCard("Widgets", String(state.dashboard.widgets.length), "Persoenliche Eintraege fuer deine Startseite.")}
        ${buildSummaryCard("Module", String(visibleModules.length), "Freigaben aus Rollen und AD-Gruppen.")}
        ${buildSummaryCard("Integrationen", String(state.integrations.length), "Fuer diesen Benutzer sichtbare Integrationen.")}
      </div>
      <div class="widget-list">
        ${widgets.map((widget, index) => `
          <div class="widget-card">
            <div>
              <p class="eyebrow">${widget.category}</p>
              <h4>${widget.title}</h4>
              <p>${widget.description || "Keine Beschreibung hinterlegt."}</p>
              <p><a href="${widget.url}" target="_blank" rel="noreferrer">${widget.url}</a></p>
            </div>
            <div class="widget-actions">
              <button type="button" data-action="remove-widget" data-index="${index}" class="secondary">Entfernen</button>
            </div>
          </div>
        `).join("") || `<div class="placeholder-block">Keine Widgets vorhanden oder aktueller Filter ohne Treffer.</div>`}
      </div>
      <div class="form-card">
        <div>
          <p class="eyebrow">Neues Widget</p>
          <h4>Quicklink hinzufuegen</h4>
        </div>
        <form id="widgetForm" class="form-stack">
          <div class="form-grid">
            <input id="widgetTitle" placeholder="Titel" required>
            <input id="widgetCategory" placeholder="Kategorie" required>
            <input id="widgetUrl" placeholder="URL" required>
            <input id="widgetDescription" placeholder="Beschreibung">
          </div>
          <button type="submit">Widget hinzufuegen</button>
        </form>
      </div>
    </section>
  `;

  elements.contentSecondary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">Aktiver Kontext</p>
        <h3 class="section-title">Benutzer und Freigaben</h3>
      </div>
      ${renderUserContext()}
    </section>
  `;
}

function renderAdView() {
  const adDetail = state.activeIntegration && state.activeIntegration.id === "ad" ? state.activeIntegration : integrationById("ad");
  const views = {
    "ad-users-computers": {
      title: "AD Users & Computers",
      note: "Der tree ist vorbereitet und fuehrt spaeter in echte LDAP- oder Connector-basierte Detailansichten.",
      items: adDetail?.items || [],
    },
    "ad-reports": {
      title: "Auswertungen",
      note: "Auswertungen werden spaeter aus AD-Reports und Rollout-Monitor-Logik gespeist.",
      items: [
        { label: "Locked Users", value: "geplant" },
        { label: "Inactive Accounts", value: "geplant" },
        { label: "Password Expiry", value: "geplant" },
      ],
    },
    "ad-dns": {
      title: "DNS",
      note: "DNS wird im AD-Kontext vorbereitet und spaeter ueber Connector oder Services integriert.",
      items: [
        { label: "Lookup Zones", value: "spaeter" },
        { label: "Host Records", value: "spaeter" },
      ],
    },
    "ad-dhcp": {
      title: "DHCP",
      note: "DHCP bleibt unter dem AD-Baum und wird spaeter ueber Windows-nahe Dienste angebunden.",
      items: [
        { label: "Scopes", value: "spaeter" },
        { label: "Reservations", value: "spaeter" },
      ],
    },
  };

  const active = views[state.activeAdNode];
  elements.contentPrimary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">ActiveDirectory Tree</p>
        <h3 class="section-title">${active.title}</h3>
      </div>
      <div class="note-card">${active.note}</div>
      <div class="detail-list">
        ${active.items.map((item) => `<div class="detail-row"><span>${item.label}</span><strong>${item.value}</strong></div>`).join("") || `<div class="placeholder-block">Keine Daten vorhanden.</div>`}
      </div>
    </section>
  `;

  elements.contentSecondary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">AD Kontext</p>
        <h3 class="section-title">Session und Connector</h3>
      </div>
      <div class="info-card">
        <p>${adDetail?.message || "AD-Kontext noch nicht geladen."}</p>
        <div class="chip-list">${Object.entries(adDetail?.meta || {}).map(([key, value]) => `<span class="chip">${key}: ${value}</span>`).join("")}</div>
      </div>
      ${renderUserContext()}
    </section>
  `;
}

function renderIntegrationModule(systemId, extraMarkup = "") {
  const detail = state.activeIntegration && state.activeIntegration.id === systemId ? state.activeIntegration : integrationById(systemId);
  elements.contentPrimary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">${detail?.source || "modul"}</p>
        <h3 class="section-title">${detail?.title || systemId}</h3>
      </div>
      <div class="note-card">${detail?.message || "Noch keine Details geladen."}</div>
      <div class="detail-list">
        ${(detail?.items || []).map((item) => `<div class="detail-row"><span>${item.label}</span><strong>${item.value}</strong></div>`).join("") || `<div class="placeholder-block">Keine Detaildaten vorhanden.</div>`}
      </div>
    </section>
  `;

  elements.contentSecondary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">Metadaten</p>
        <h3 class="section-title">Status und Kontext</h3>
      </div>
      <div class="info-card">
        <div class="chip-list">
          <span class="chip ${integrationStatusClass(detail?.status)}">${detail?.status || "unknown"}</span>
          ${Object.entries(detail?.meta || {}).map(([key, value]) => `<span class="chip">${key}: ${value}</span>`).join("")}
        </div>
      </div>
      ${extraMarkup}
    </section>
  `;
}

function renderRolloutView() {
  const vsphere = integrationById("vsphere");
  const canCreate = hasPermission("rollout.create");
  const canManage = hasPermission("rollout.manage");
  elements.contentPrimary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">Rollout</p>
        <h3 class="section-title">Operations-Hub fuer Rollout und Infrastruktur</h3>
      </div>
      <div class="summary-grid">
        ${buildSummaryCard("Jobs", String(state.rolloutSummary?.jobCount || 0), "Persistierte Rollout-Jobs im Web-Backend.")}
        ${buildSummaryCard("Aktiv", String(state.rolloutSummary?.runningCount || 0), "Laufende oder vorbereitete Rollout-Workflows.")}
        ${buildSummaryCard("Fehler", String(state.rolloutSummary?.errorCount || 0), "Jobs mit technischem oder fachlichem Fehlerstatus.")}
      </div>
      ${canCreate ? `
      <div class="form-card">
        <div>
          <p class="eyebrow">Neuer Rollout-Job</p>
          <h4>Job fuer Web-Rollout anlegen</h4>
        </div>
        <form id="rolloutJobForm" class="form-stack">
          <div class="form-grid">
            <input id="rolloutHostname" placeholder="Hostname" required>
            <input id="rolloutTemplate" placeholder="Template" required>
            <input id="rolloutCluster" placeholder="Cluster" required>
            <input id="rolloutNetwork" placeholder="Netzwerk" required>
          </div>
          <input id="rolloutTags" placeholder="Tags, komma-getrennt">
          <button type="submit">Rollout-Job anlegen</button>
        </form>
      </div>` : ""}
      <div class="info-card">
        <h4>Rollout-Jobs</h4>
        <div class="detail-list">
          ${state.rolloutJobs.map((job) => `
            <div class="widget-card">
              <div>
                <p class="eyebrow">${job.jobId}</p>
                <h4>${job.hostname}</h4>
                <p>${job.template} auf ${job.cluster} / ${job.network}</p>
                <p>Status: ${job.status} | Progress: ${job.progress}%</p>
                <p>${job.clientMessage || "Noch keine Ausfuehrungsdaten vorhanden."}</p>
              </div>
              <div class="widget-actions">
                ${canManage ? `<button type="button" class="secondary" data-action="restart-rollout" data-job-id="${job.jobId}">Reset</button>` : ""}
              </div>
            </div>
          `).join("") || `<div class="placeholder-block">Noch keine Rollout-Jobs vorhanden.</div>`}
        </div>
      </div>
      <div class="info-card">
        <h4>Naechste Rollout-Schritte</h4>
        <ol class="list-clean">
          <li>Job-Startlogik mit Nutanix-Clone-Service verbinden</li>
          <li>Share-Kommunikation fuer WinPE und Runtime-Dateien anbinden</li>
          <li>ReRollout-, Delete- und Continue-Workflows portieren</li>
        </ol>
      </div>
    </section>
  `;

  elements.contentSecondary.innerHTML = `
    <section class="workspace-section">
      <div>
        <p class="eyebrow">Infrastruktur</p>
        <h3 class="section-title">vSphere Kontext</h3>
      </div>
      <div class="detail-list">
        ${(vsphere?.items || []).map((item) => `<div class="detail-row"><span>${item.label}</span><strong>${item.value}</strong></div>`).join("") || `<div class="placeholder-block">Keine vSphere-Daten vorhanden.</div>`}
      </div>
      <div class="info-card">
        <h4>Persistenz</h4>
        <p>${state.rolloutSummary?.tasksDirectory || "Kein Tasks-Verzeichnis bekannt."}</p>
      </div>
    </section>
  `;
}

function renderCurrentView() {
  const meta = VIEW_META[state.activeNav] || VIEW_META.dashboard;
  elements.welcomeTitle.textContent = meta.title;
  elements.workspaceSubtitle.textContent = meta.subtitle;

  if (state.activeNav === "dashboard") {
    renderDashboardView();
    return;
  }
  if (state.activeNav === "ad") {
    renderAdView();
    return;
  }
  if (state.activeNav === "nutanix") {
    renderIntegrationModule("nutanix");
    return;
  }
  if (state.activeNav === "endpoint") {
    renderIntegrationModule("endpoint");
    return;
  }
  if (state.activeNav === "citrix") {
    renderIntegrationModule("citrix", `
      <div class="info-card">
        <h4>Connector Hinweis</h4>
        <p>Citrix bleibt an den Windows Connector gekoppelt, damit Delivery-Controller- und PowerShell-nahe Pfade sauber getrennt bleiben.</p>
      </div>
    `);
    return;
  }
  if (state.activeNav === "rollout") {
    renderRolloutView();
  }
}

function renderApp() {
  elements.loginView.classList.add("hidden");
  elements.appView.classList.remove("hidden");
  elements.welcomeMeta.textContent = `Angemeldet als ${state.user.username}`;
  renderSidebar();
  renderCurrentView();
}

async function loadIntegrations(selectDefault = false) {
  const payload = await request("/api/integrations/overview");
  state.integrations = payload.systems || [];
  if (selectDefault) {
    if (state.activeNav === "ad") {
      await selectIntegration("ad");
      return;
    }
    if (["nutanix", "endpoint", "citrix"].includes(state.activeNav)) {
      await selectIntegration(state.activeNav);
      return;
    }
  }
  renderCurrentView();
}

async function loadRolloutJobs() {
  if (!hasPermission("rollout.view")) {
    state.rolloutJobs = [];
    state.rolloutSummary = null;
    return;
  }
  const payload = await request("/api/rollout/jobs");
  state.rolloutJobs = payload.jobs || [];
  state.rolloutSummary = payload.summary || null;
}

async function selectIntegration(systemId) {
  state.activeIntegration = await request(`/api/integrations/${systemId}`);
  renderCurrentView();
}

async function login(username, password) {
  const payload = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  state.token = payload.sessionToken;
  state.user = payload.user;
  state.dashboard = payload.dashboard;
  state.sessionExpiresAt = payload.expiresAt || "";
  state.activeNav = "dashboard";
  state.activeAdNode = "ad-users-computers";
  localStorage.setItem("startpage.sessionToken", state.token);
  setMessage("Anmeldung erfolgreich.", "success");
  renderApp();
  await loadIntegrations(false);
  await loadRolloutJobs();
}

async function bootstrapSession() {
  const health = await request("/api/health");
  renderHealth(health);
  if (!state.token) {
    return;
  }

  try {
    const payload = await request("/api/me");
    state.user = payload.user;
    state.dashboard = payload.dashboard;
    state.sessionExpiresAt = payload.expiresAt || "";
    state.activeNav = "dashboard";
    renderApp();
    await loadIntegrations(false);
    await loadRolloutJobs();
  } catch (_error) {
    resetClientState();
  }
}

elements.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage("Anmeldung wird ausgefuehrt...");
  try {
    await login(elements.usernameInput.value, elements.passwordInput.value);
  } catch (error) {
    setMessage(error.message, "error");
  }
});

elements.searchInput.addEventListener("input", () => {
  renderCurrentView();
});

elements.logoutButton.addEventListener("click", async () => {
  try {
    await request("/api/auth/logout", { method: "POST" });
  } catch (_error) {
    // Client-State trotzdem lokal zuruecksetzen.
  }
  resetClientState();
  window.location.reload();
});

elements.refreshIntegrationsButton.addEventListener("click", async () => {
  try {
    await loadIntegrations(true);
    await loadRolloutJobs();
  } catch (error) {
    window.alert(error.message);
  }
});

elements.sidebarNav.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const treeButton = target.closest("[data-tree-id]");
  if (treeButton instanceof HTMLElement) {
    state.activeNav = "ad";
    state.activeAdNode = treeButton.dataset.treeId;
    if (!state.activeIntegration || state.activeIntegration.id !== "ad") {
      await selectIntegration("ad");
    } else {
      renderSidebar();
      renderCurrentView();
    }
    renderSidebar();
    return;
  }

  const navButton = target.closest("[data-nav-id]");
  if (!(navButton instanceof HTMLElement)) {
    return;
  }

  const navId = navButton.dataset.navId;
  if (navId === "ad") {
    state.activeNav = "ad";
    state.adTreeExpanded = !state.adTreeExpanded || state.activeNav !== "ad";
    await selectIntegration("ad");
    renderSidebar();
    return;
  }

  state.activeNav = navId;
  renderSidebar();
  if (["nutanix", "endpoint", "citrix"].includes(navId)) {
    await selectIntegration(navId);
    return;
  }
  renderCurrentView();
});

elements.contentPrimary.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.id !== "widgetForm") {
    if (!(form instanceof HTMLFormElement) || form.id !== "rolloutJobForm") {
      return;
    }
    event.preventDefault();
    const hostname = form.querySelector("#rolloutHostname")?.value?.trim() || "";
    const template = form.querySelector("#rolloutTemplate")?.value?.trim() || "";
    const cluster = form.querySelector("#rolloutCluster")?.value?.trim() || "";
    const network = form.querySelector("#rolloutNetwork")?.value?.trim() || "";
    const tagsRaw = form.querySelector("#rolloutTags")?.value?.trim() || "";
    request("/api/rollout/jobs", {
      method: "POST",
      body: JSON.stringify({
        hostname,
        template,
        cluster,
        network,
        tags: tagsRaw.split(",").map((item) => item.trim()).filter(Boolean),
      }),
    })
      .then(async () => {
        form.reset();
        await loadRolloutJobs();
        renderCurrentView();
      })
      .catch((error) => {
        window.alert(error.message);
      });
    return;
  }
  event.preventDefault();
  const title = form.querySelector("#widgetTitle")?.value?.trim() || "";
  const category = form.querySelector("#widgetCategory")?.value?.trim() || "";
  const url = form.querySelector("#widgetUrl")?.value?.trim() || "";
  const description = form.querySelector("#widgetDescription")?.value?.trim() || "";
  state.dashboard.widgets.unshift({
    id: `${Date.now()}`,
    title,
    category,
    url,
    description,
  });
  form.reset();
  renderCurrentView();
});

elements.contentPrimary.addEventListener("click", async (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  if (target.dataset.action === "remove-widget") {
    const index = Number(target.dataset.index);
    if (!Number.isNaN(index)) {
      state.dashboard.widgets.splice(index, 1);
      renderCurrentView();
    }
    return;
  }

  if (target.id === "saveDashboardButton") {
    try {
      const payload = await request("/api/me/dashboard", {
        method: "PUT",
        body: JSON.stringify(state.dashboard),
      });
      state.dashboard = payload.dashboard;
      renderCurrentView();
    } catch (error) {
      window.alert(error.message);
    }
    return;
  }

  if (target.dataset.action === "restart-rollout") {
    request(`/api/rollout/jobs/${target.dataset.jobId}/restart`, {
      method: "POST",
    })
      .then(async () => {
        await loadRolloutJobs();
        renderCurrentView();
      })
      .catch((error) => {
        window.alert(error.message);
      });
  }
});

bootstrapSession().catch((error) => {
  setMessage(error.message, "error");
});
