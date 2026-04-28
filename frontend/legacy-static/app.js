const APP_STATE = {
  proposalMode: localStorage.getItem("proposalMode") || "company",
  selectedReviewFilter: localStorage.getItem("reviewFilter") || "all",
};

const NAV_ITEMS = [
  { key: "home", label: "Home", href: "main.html" },
  { key: "upload", label: "Upload", href: "upload.html" },
  { key: "dashboard", label: "Dashboard", href: "dashboard.html" },
  { key: "review", label: "Review", href: "review.html" },
  { key: "export", label: "Export", href: "export.html" },
];

function getConfig() {
  return window.APP_CONFIG || {};
}

function getStoredSession() {
  try {
    return JSON.parse(localStorage.getItem("datasmithSession") || "null");
  } catch {
    return null;
  }
}

function setStoredSession(session) {
  localStorage.setItem("datasmithSession", JSON.stringify(session));
}

function clearStoredSession() {
  localStorage.removeItem("datasmithSession");
}

function renderNavigation(activePage) {
  const mount = document.querySelector("[data-nav]");
  if (!mount) return;

  const links = NAV_ITEMS.map((item) => {
    const active = item.key === activePage ? "site-nav__link is-active" : "site-nav__link";
    return `<a class="${active}" href="${item.href}">${item.label}</a>`;
  }).join("");

  mount.innerHTML = `
    <header class="site-header">
      <div class="site-header__inner">
        <a class="brand" href="main.html">
          <span class="brand__mark"><iconify-icon icon="lucide:zap"></iconify-icon></span>
          <span class="brand__title">Datasmith AI</span>
        </a>
        <div class="site-nav">
          <nav class="site-nav__links" aria-label="Primary">${links}</nav>
          <div class="nav-actions">
            <span class="nav-user muted" data-user-badge>Guest mode</span>
            <a class="btn btn--secondary" href="login.html" data-auth-link>Login</a>
          </div>
        </div>
      </div>
    </header>
  `;
}

function renderFooter() {
  const mount = document.querySelector("[data-footer]");
  if (!mount) return;

  mount.innerHTML = `
    <footer class="site-footer">
      <div class="site-footer__inner">
        <a class="brand" href="main.html">
          <span class="brand__mark"><iconify-icon icon="lucide:zap"></iconify-icon></span>
          <span class="brand__title">Datasmith AI</span>
        </a>
        <div class="footer-links">
          <a class="subtle-link" href="main.html#workflow">Workflow</a>
          <a class="subtle-link" href="review.html">Confidence Review</a>
          <a class="subtle-link" href="export.html">Export Package</a>
        </div>
        <div class="muted">Tender upload, review, and export flow.</div>
      </div>
    </footer>
  `;
}

function hydrateAuthState() {
  const badge = document.querySelector("[data-user-badge]");
  const authLink = document.querySelector("[data-auth-link]");
  const session = getStoredSession();

  if (badge) {
    badge.textContent = session?.contact_email || session?.company_name || "Guest mode";
  }

  if (authLink) {
    if (session) {
      authLink.textContent = "Logout";
      authLink.href = "#";
      authLink.addEventListener(
        "click",
        (event) => {
          event.preventDefault();
          clearStoredSession();
          window.location.href = "login.html";
        },
        { once: true }
      );
    } else {
      authLink.textContent = "Login";
      authLink.href = "login.html";
    }
  }

  if (document.body.dataset.authRequired === "true" && !session) {
    window.location.href = "login.html";
  }
}

function bindChoiceCards() {
  const cards = [...document.querySelectorAll("[data-mode-card]")];
  const badge = document.querySelector("[data-selected-mode]");
  if (!cards.length) return;

  const update = (mode) => {
    APP_STATE.proposalMode = mode;
    localStorage.setItem("proposalMode", mode);
    cards.forEach((card) => card.classList.toggle("is-selected", card.dataset.modeCard === mode));
    if (badge) {
      badge.textContent =
        mode === "company" ? "Company template selected" : "Tender-defined format selected";
    }
    hydrateModeLabels();
  };

  cards.forEach((card) => card.addEventListener("click", () => update(card.dataset.modeCard)));
  update(APP_STATE.proposalMode);
}

function hydrateModeLabels() {
  document.querySelectorAll("[data-proposal-mode-text]").forEach((node) => {
    node.textContent =
      APP_STATE.proposalMode === "company"
        ? "Company proposal template"
        : "Tender-defined structure";
  });
}

function bindUploadActions() {
  document.querySelectorAll('[data-action="go-processing"]').forEach((button) => {
    button.addEventListener("click", () => {
      localStorage.setItem(
        "latestTenderName",
        "National Digital Infrastructure Expansion Project"
      );
      window.location.href = "processing.html";
    });
  });
}

function bindDashboardLinks() {
  document.querySelectorAll("[data-open-proposal]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      window.location.href = "proposal.html";
    });
  });
}

function bindProposalOutline() {
  const outlineLinks = [...document.querySelectorAll("[data-outline-target]")];
  if (!outlineLinks.length) return;

  outlineLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      outlineLinks.forEach((item) => item.classList.remove("is-active"));
      link.classList.add("is-active");
      const target = document.querySelector(link.dataset.outlineTarget);
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function bindReviewFilters() {
  const filters = [...document.querySelectorAll("[data-review-filter]")];
  const cards = [...document.querySelectorAll("[data-review-card]")];
  if (!filters.length) return;

  const applyFilter = (value) => {
    APP_STATE.selectedReviewFilter = value;
    localStorage.setItem("reviewFilter", value);
    filters.forEach((filter) =>
      filter.classList.toggle("is-active", filter.dataset.reviewFilter === value)
    );
    cards.forEach((card) => {
      const show = value === "all" || card.dataset.reviewCard === value;
      card.classList.toggle("hidden", !show);
    });
  };

  filters.forEach((filter) =>
    filter.addEventListener("click", () => applyFilter(filter.dataset.reviewFilter))
  );
  applyFilter(APP_STATE.selectedReviewFilter);
}

function bindApproveActions() {
  const approve = document.querySelector("[data-approve-review]");
  const requestChanges = document.querySelector("[data-request-changes]");
  if (approve) {
    approve.addEventListener("click", () => {
      window.location.href = "export.html";
    });
  }
  if (requestChanges) {
    requestChanges.addEventListener("click", () => {
      window.location.href = "proposal.html";
    });
  }
}

function bindFeedbackForm() {
  const form = document.querySelector("[data-feedback-form]");
  const status = document.querySelector("[data-feedback-status]");
  if (!form) return;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(form).entries());
    localStorage.setItem("datasmithFeedback", JSON.stringify(payload));
    if (status) {
      status.textContent =
        "Feedback saved locally. This can be connected to the learning loop endpoint next.";
    }
    form.reset();
  });
}

function showAuthMessage(message, tone = "info") {
  const box = document.querySelector("[data-auth-message]");
  if (!box) return;
  box.textContent = message;
  box.className = `auth-message auth-message--${tone}`;
}

function setAuthLoading(form, isLoading, label) {
  const button = form?.querySelector('button[type="submit"]');
  if (!button) return;
  if (!button.dataset.originalLabel) {
    button.dataset.originalLabel = button.innerHTML;
  }
  button.disabled = isLoading;
  button.innerHTML = isLoading ? label : button.dataset.originalLabel;
}

async function onboardCompany(formData) {
  const config = getConfig();
  const baseUrl = config.onboardingBaseUrl || "";
  const endpoint = config.onboardingEndpoint || "/onboard-company";
  if (!baseUrl) {
    throw new Error("Onboarding API base URL is not configured.");
  }

  const response = await fetch(`${baseUrl}${endpoint}`, {
    method: "POST",
    body: formData,
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const message =
      typeof payload === "string"
        ? payload
        : payload?.detail || payload?.message || "Onboarding request failed.";
    throw new Error(message);
  }

  return payload;
}

function bindAuthForms() {
  const tabs = [...document.querySelectorAll("[data-auth-tab]")];
  const panels = [...document.querySelectorAll("[data-auth-panel]")];
  const loginForm = document.querySelector("[data-login-form]");
  const signupForm = document.querySelector("[data-signup-form]");
  if (!tabs.length) return;

  const switchTab = (name) => {
    tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.authTab === name));
    panels.forEach((panel) => panel.classList.toggle("hidden", panel.dataset.authPanel !== name));
  };

  tabs.forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.authTab)));
  switchTab("login");
  showAuthMessage("Use your company email to sign in or create a workspace to begin.", "info");

  loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    const email = String(formData.get("email") || "").trim().toLowerCase();
    const password = String(formData.get("password") || "");
    const stored = getStoredSession();

    showAuthMessage("Signing you in...", "info");
    setAuthLoading(loginForm, true, "Logging in...");

    try {
      if (!stored) {
        throw new Error("No workspace found on this browser yet. Create one first.");
      }
      if (
        stored.contact_email?.toLowerCase() !== email ||
        String(stored.password || "") !== password
      ) {
        throw new Error("Email or password does not match the saved workspace.");
      }
      showAuthMessage("Welcome back. Redirecting to your dashboard...", "success");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 700);
    } catch (error) {
      showAuthMessage(error.message || "Unable to sign in.", "error");
    } finally {
      setAuthLoading(loginForm, false, "Logging in...");
    }
  });

  signupForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const raw = new FormData(signupForm);
    const knowledgeFile = raw.get("knowledge_base");
    const templateFile = raw.get("proposal_template");

    const formData = new FormData();
    formData.append("company_name", String(raw.get("company_name") || ""));
    formData.append("industry", String(raw.get("industry") || ""));
    formData.append("contact_email", String(raw.get("contact_email") || ""));
    formData.append("contact_phone", String(raw.get("contact_phone") || ""));
    formData.append("password", String(raw.get("password") || ""));
    if (knowledgeFile instanceof File && knowledgeFile.size > 0) {
      formData.append("knowledge_base", knowledgeFile);
    }
    if (templateFile instanceof File && templateFile.size > 0) {
      formData.append("proposal_template", templateFile);
    }

    showAuthMessage("Creating your workspace...", "info");
    setAuthLoading(signupForm, true, "Creating workspace...");

    try {
      const payload = await onboardCompany(formData);
      setStoredSession({
        company_name: String(raw.get("company_name") || ""),
        industry: String(raw.get("industry") || ""),
        contact_email: String(raw.get("contact_email") || ""),
        contact_phone: String(raw.get("contact_phone") || ""),
        password: String(raw.get("password") || ""),
        onboardingResponse: payload,
      });
      showAuthMessage("Workspace created successfully. Redirecting to your dashboard...", "success");
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 900);
    } catch (error) {
      showAuthMessage(error.message || "Unable to create workspace.", "error");
    } finally {
      setAuthLoading(signupForm, false, "Creating workspace...");
    }
  });
}

function hydrateTenderName() {
  const name = localStorage.getItem("latestTenderName") || "National Digital Infrastructure Expansion Project";
  document.querySelectorAll("[data-tender-name]").forEach((node) => {
    node.textContent = name;
  });
}

function initFrontend() {
  const page = document.body.dataset.page || "home";
  renderNavigation(page);
  renderFooter();
  bindChoiceCards();
  bindUploadActions();
  bindDashboardLinks();
  bindProposalOutline();
  bindReviewFilters();
  bindApproveActions();
  bindFeedbackForm();
  bindAuthForms();
  hydrateModeLabels();
  hydrateTenderName();
  hydrateAuthState();
}

window.addEventListener("DOMContentLoaded", () => {
  try {
    initFrontend();
  } catch (error) {
    console.error(error);
  }
});
