const state = { token: null, profile: null, verificationEmail: null, resetEmail: null };
let refreshInFlight = null;
const $ = (selector) => document.querySelector(selector);

function currency(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(value));
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 3600);
}

async function refreshAccessToken() {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const response = await fetch("/auth/refresh", { method: "POST", credentials: "same-origin" });
    if (!response.ok) throw new Error("Your session has expired. Please sign in again.");
    const data = await response.json();
    state.token = data.access_token;
  })();
  try { await refreshInFlight; }
  finally { refreshInFlight = null; }
}

async function api(path, options = {}, retried = false) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
  if (response.status === 401 && state.token && !retried && path !== "/auth/refresh") {
    try {
      await refreshAccessToken();
      return api(path, options, true);
    } catch (error) {
      signOut(false);
      throw error;
    }
  }
  const text = response.status === 204 ? "" : await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (_error) {
    data = null;
  }
  if (!response.ok) {
    const message = data?.detail || data?.message || text || "Something went wrong. Please try again.";
    throw new Error(message);
  }
  return data;
}

function setLoading(form, loading) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = loading;
  if (loading) { button.dataset.label = button.textContent; button.textContent = "Working…"; }
  else if (button.dataset.label) button.textContent = button.dataset.label;
}

function toggleAuth(mode) {
  const isLogin = mode === "login";
  $("#login-panel").classList.toggle("hidden", !isLogin);
  $("#signup-panel").classList.toggle("hidden", isLogin);
  $("#verify-panel").classList.add("hidden");
  $("#forgot-password-panel").classList.add("hidden");
  $("#reset-password-panel").classList.add("hidden");
  $(".tab-list").classList.remove("hidden");
  $("#login-tab").classList.toggle("active", isLogin);
  $("#signup-tab").classList.toggle("active", !isLogin);
  $("#login-tab").setAttribute("aria-selected", String(isLogin));
  $("#signup-tab").setAttribute("aria-selected", String(!isLogin));
}

function showVerification(email) {
  state.verificationEmail = email;
  $("#verification-email").textContent = email;
  $("#login-panel").classList.add("hidden");
  $("#signup-panel").classList.add("hidden");
  $("#verify-panel").classList.remove("hidden");
  $(".tab-list").classList.add("hidden");
  $("#verify-form input").focus();
}

function showForgotPassword() {
  $("#login-panel").classList.add("hidden");
  $("#signup-panel").classList.add("hidden");
  $("#verify-panel").classList.add("hidden");
  $("#reset-password-panel").classList.add("hidden");
  $("#forgot-password-panel").classList.remove("hidden");
  $(".tab-list").classList.add("hidden");
  $("#forgot-password-form input").focus();
}

function showResetPassword(email) {
  state.resetEmail = email;
  $("#reset-email").textContent = email;
  $("#forgot-password-panel").classList.add("hidden");
  $("#reset-password-panel").classList.remove("hidden");
  $("#reset-password-form input").focus();
}

function renderTransactions(entries) {
  $("#transaction-count").textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"}`;
  const target = $("#transactions");
  if (!entries.length) { target.innerHTML = '<div class="empty-state">Your transactions will appear here.</div>'; return; }
  target.innerHTML = entries.map((item) => {
    const isDebit = item.transaction_type === "transfer_out";
    const isDeposit = item.transaction_type === "deposit";
    const title = isDeposit ? "Wallet funding" : `${isDebit ? "Sent to" : "Received from"} ${item.counterparty_email}`;
    const detail = `${item.status} · ${item.description || new Date(item.created_at).toLocaleString()}`;
    const sign = isDebit ? "−" : "+";
    return `<article class="transaction"><div class="transaction-icon ${isDebit ? "out" : ""}">${isDebit ? "↗" : "+"}</div><div class="transaction-main"><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div><div class="transaction-amount ${isDebit ? "debit" : "credit"}">${sign}${currency(item.amount)}</div></article>`;
  }).join("");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;" })[character]);
}

async function loadDashboard() {
  const [profile, wallet, transactions] = await Promise.all([api("/auth/me"), api("/wallet"), api("/wallet/transactions?limit=50")]);
  state.profile = profile;
  $("#user-name").textContent = profile.full_name.split(" ")[0];
  $("#wallet-balance").textContent = currency(wallet.balance);
  $("#wallet-id").textContent = `#${wallet.id.toString().padStart(6, "0")}`;
  renderTransactions(transactions);
}

async function showDashboard() {
  $("#auth-view").classList.add("hidden");
  $("#dashboard-view").classList.remove("hidden");
  $("#logout-button").classList.remove("hidden");
  try { await loadDashboard(); } catch (error) { showToast(error.message, true); }
}

function signOut(revokeServerSession = true) {
  const token = state.token;
  state.token = null;
  $("#dashboard-view").classList.add("hidden");
  $("#auth-view").classList.remove("hidden");
  $("#logout-button").classList.add("hidden");
  if (revokeServerSession) {
    fetch("/auth/logout", { method: "POST", credentials: "same-origin", headers: token ? { Authorization: `Bearer ${token}` } : {} });
  }
}

$("#login-tab").addEventListener("click", () => toggleAuth("login"));
$("#signup-tab").addEventListener("click", () => toggleAuth("signup"));
$("#forgot-password-link").addEventListener("click", showForgotPassword);
document.querySelectorAll(".back-to-login").forEach((button) => button.addEventListener("click", () => toggleAuth("login")));
$("#logout-button").addEventListener("click", () => { signOut(); showToast("Signed out successfully."); });
$("#refresh-button").addEventListener("click", async () => { try { await loadDashboard(); showToast("Wallet refreshed."); } catch (error) { showToast(error.message, true); } });

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try { const data = await api("/auth/login", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(form))) }); state.token = data.access_token; await showDashboard(); showToast("Welcome back."); }
  catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#signup-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try {
    const values = Object.fromEntries(new FormData(form));
    const result = await api("/auth/signup", { method: "POST", body: JSON.stringify(values) });
    showVerification(values.email);
    showToast(result.message + (result.otp ? ` Code: ${result.otp}` : ""));
  } catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#verify-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try { await api("/auth/verify-email-otp", { method: "POST", body: JSON.stringify({ email: state.verificationEmail, otp: new FormData(form).get("otp") }) }); $("#login-form [name='email']").value = state.verificationEmail; $("#login-form [name='password']").focus(); toggleAuth("login"); showToast("Email verified. You can sign in now."); }
  catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#resend-button").addEventListener("click", async (event) => {
  const button = event.currentTarget; button.disabled = true; button.textContent = "Sending…";
  try { const result = await api("/auth/resend-otp", { method: "POST", body: JSON.stringify({ email: state.verificationEmail }) }); showToast(result.message); }
  catch (error) { showToast(error.message, true); } finally { button.disabled = false; button.textContent = "Didn't receive it? Send a new code"; }
});

$("#forgot-password-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try {
    const email = new FormData(form).get("email");
    const result = await api("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
    showResetPassword(email);
    showToast(result.message + (result.otp ? ` Code: ${result.otp}` : ""));
  } catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#reset-password-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try { const values = Object.fromEntries(new FormData(form)); const result = await api("/auth/reset-password", { method: "POST", body: JSON.stringify({ email: state.resetEmail, ...values }) }); $("#login-form [name='email']").value = state.resetEmail; form.reset(); toggleAuth("login"); showToast(result.message); }
  catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#deposit-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try { const values = Object.fromEntries(new FormData(form)); await api("/wallet/add-money", { method: "POST", body: JSON.stringify(values) }); form.reset(); await loadDashboard(); showToast("Funds added to your wallet."); }
  catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

$("#transfer-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const form = event.currentTarget; setLoading(form, true);
  try { const values = Object.fromEntries(new FormData(form)); await api("/wallet/transfer", { method: "POST", body: JSON.stringify(values) }); form.reset(); await loadDashboard(); showToast("Transfer completed successfully."); }
  catch (error) { showToast(error.message, true); } finally { setLoading(form, false); }
});

async function restoreSession() {
  try { await refreshAccessToken(); await showDashboard(); }
  catch { signOut(false); }
}

restoreSession();
