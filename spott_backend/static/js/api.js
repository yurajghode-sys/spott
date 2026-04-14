/**
 * api.js — Spott Frontend ↔ Backend Integration Layer
 * v1.0.0
 *
 * HOW TO USE:
 * Add this ONE line before </body> in index.html:
 *   <script src="http://localhost:5000/static/js/api.js"></script>
 *
 * The script automatically:
 *  - Loads events from the database (replacing hardcoded EVENTS array)
 *  - Wires up login/register/newsletter to the backend
 *  - Hooks into booking/payment/feedback flows
 *  - Manages JWT tokens in localStorage
 */

const SPOTT_API = (function () {

  // ── Configuration ──────────────────────────────────────────────
  const BASE_URL = window.SPOTT_BASE_URL || "http://localhost:5000/api";
  let _token = localStorage.getItem("spott_token") || null;
  let _user  = JSON.parse(localStorage.getItem("spott_user") || "null");

  // ── Core HTTP Request ──────────────────────────────────────────
  async function _req(method, path, body, isForm) {
    const headers = {};
    if (_token) headers["Authorization"] = "Bearer " + _token;
    if (body && !isForm) headers["Content-Type"] = "application/json";

    const opts = { method, headers, credentials: "include" };
    if (body) opts.body = isForm ? body : JSON.stringify(body);

    try {
      const res  = await fetch(BASE_URL + path, opts);
      const data = await res.json();
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      console.error("SPOTT API error:", err);
      return { ok: false, status: 0, data: { error: "Network error. Is the backend running on port 5000?" } };
    }
  }

  // ── Auth Helpers ───────────────────────────────────────────────
  function _setAuth(token, user) {
    _token = token;
    _user  = user;
    localStorage.setItem("spott_token", token);
    localStorage.setItem("spott_user",  JSON.stringify(user));
  }

  function _clearAuth() {
    _token = null;
    _user  = null;
    localStorage.removeItem("spott_token");
    localStorage.removeItem("spott_user");
  }

  function _updateNavbar(user) {
    const displayName = (user.name || "").split(" ")[0] || user.email.split("@")[0];

    const signInBtn = document.getElementById("signInBtn");
    if (signInBtn) {
      signInBtn.textContent = "👤 " + displayName;
      signInBtn.onclick = function () {
        if (typeof openPage === "function") openPage("profilePage");
      };
    }

    const mobileSignIn = document.getElementById("mobileSignIn");
    if (mobileSignIn) mobileSignIn.textContent = "👤 " + displayName;

    const createBtn = document.getElementById("createEventBtn");
    if (createBtn) {
      createBtn.style.display = user.role === "admin" ? "inline-flex" : "none";
    }
  }

  // ── Public helpers ─────────────────────────────────────────────
  function isLoggedIn() { return !!_token; }
  function getUser()    { return _user; }
  function isAdmin()    { return !!(_user && _user.role === "admin"); }

  // ══════════════════════════════════════════════════════════════
  // AUTH METHODS
  // ══════════════════════════════════════════════════════════════
  async function register(name, email, password, phone) {
    const r = await _req("POST", "/auth/register", { name, email, password, phone: phone || "" });
    if (r.ok && r.data.data) {
      _setAuth(r.data.data.token, r.data.data.user);
      _updateNavbar(r.data.data.user);
    }
    return r;
  }

  async function login(email, password) {
    const r = await _req("POST", "/auth/login", { email, password });
    if (r.ok && r.data.data) {
      _setAuth(r.data.data.token, r.data.data.user);
      _updateNavbar(r.data.data.user);
    }
    return r;
  }

  async function logout() {
    await _req("POST", "/auth/logout");
    _clearAuth();
    const signInBtn = document.getElementById("signInBtn");
    if (signInBtn) {
      signInBtn.textContent = "Sign In";
      signInBtn.onclick = function () {
        if (typeof openModal === "function") openModal("authModal");
      };
    }
    const createBtn = document.getElementById("createEventBtn");
    if (createBtn) createBtn.style.display = "none";
  }

  async function getMe()           { return _req("GET", "/auth/me"); }
  async function updateMe(data)    { return _req("PUT", "/auth/me", data); }
  async function toggleSaveEvent(eventId) {
    return _req("POST", "/auth/me/save-event/" + eventId);
  }
  async function subscribeNewsletter(email) {
    return _req("POST", "/auth/newsletter", { email });
  }

  // ══════════════════════════════════════════════════════════════
  // EVENT METHODS
  // ══════════════════════════════════════════════════════════════
  async function getEvents(params) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return _req("GET", "/events" + qs);
  }

  async function getEvent(id)            { return _req("GET", "/events/" + id); }
  async function getTrending()           { return _req("GET", "/events/trending"); }
  async function getCategories()         { return _req("GET", "/events/categories"); }
  async function createEvent(data)       { return _req("POST", "/events", data); }
  async function updateEvent(id, data)   { return _req("PUT", "/events/" + id, data); }
  async function deleteEvent(id)         { return _req("DELETE", "/events/" + id); }
  async function submitReview(eventId, rating, comment) {
    return _req("POST", "/events/" + eventId + "/review", { rating, comment });
  }

  async function uploadEventImage(file) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("folder", "events");
    return _req("POST", "/upload/image", fd, true);
  }

  // ══════════════════════════════════════════════════════════════
  // BOOKING METHODS
  // ══════════════════════════════════════════════════════════════
  async function createBooking(eventId, ticketType, quantity, notes) {
    return _req("POST", "/bookings", {
      event_id: eventId,
      ticket_type: ticketType || "general",
      quantity: quantity || 1,
      notes: notes || "",
    });
  }

  async function getMyBookings(status, page) {
    return _req("GET", "/bookings?status=" + (status || "confirmed") + "&page=" + (page || 1));
  }

  async function getTicket(bookingId)    { return _req("GET", "/bookings/" + bookingId + "/ticket"); }
  async function cancelBooking(id)       { return _req("DELETE", "/bookings/" + id); }

  // ══════════════════════════════════════════════════════════════
  // SEARCH
  // ══════════════════════════════════════════════════════════════
  async function search(q) {
    return _req("GET", "/search?q=" + encodeURIComponent(q));
  }

  // ══════════════════════════════════════════════════════════════
  // ADMIN METHODS
  // ══════════════════════════════════════════════════════════════
  async function adminDashboard()        { return _req("GET", "/admin/dashboard"); }
  async function adminUsers(params)      {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return _req("GET", "/admin/users" + qs);
  }
  async function adminDeleteUser(id)     { return _req("DELETE", "/admin/users/" + id); }
  async function adminUpdateUser(id, d)  { return _req("PUT", "/admin/users/" + id, d); }
  async function adminBookings(params)   {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return _req("GET", "/admin/bookings" + qs);
  }
  async function adminEvents(params)     {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return _req("GET", "/admin/events" + qs);
  }
  async function adminUpdateBooking(id, status) {
    return _req("PUT", "/admin/bookings/" + id, { status });
  }

  // ══════════════════════════════════════════════════════════════
  // USER STATS & SAVED
  // ══════════════════════════════════════════════════════════════
  async function getUserStats()  { return _req("GET", "/users/stats"); }
  async function getSavedEvents(){ return _req("GET", "/users/saved-events"); }

  // ══════════════════════════════════════════════════════════════
  // LOAD EVENTS — Replace hardcoded EVENTS with DB data
  // ══════════════════════════════════════════════════════════════
  async function loadEventsFromAPI(params) {
    const r = await getEvents(Object.assign({ per_page: 50 }, params || {}));
    if (!r.ok || !r.data.data) return;

    const apiEvents = r.data.data.map(function (ev) {
      return {
        id:        ev.id,
        title:     ev.title       || "",
        category:  ev.category    || "",
        date:      ev.date        || "",
        time:      ev.time        || "",
        location:  ev.location    || "",
        price:     ev.price       || "Free",
        type:      ev.type        || "free",
        emoji:     ev.emoji       || "🎉",
        image_url: ev.image_url   || "",
        attendees: [],
        badge:     ev.badge       || ev.type || "free",
        capacity:  ev.capacity    || 0,
        booked:    ev.booked_count|| 0,
        is_full:   ev.is_full     || false,
        seats_left:ev.seats_left  || null,
      };
    });

    if (typeof EVENTS !== "undefined") {
      EVENTS.length = 0;
      apiEvents.forEach(function (e) { EVENTS.push(e); });
    }

    if (typeof renderEvents   === "function") renderEvents();
    if (typeof renderTrending === "function") renderTrending();
    return apiEvents;
  }

  // ══════════════════════════════════════════════════════════════
  // INIT
  // ══════════════════════════════════════════════════════════════
  async function init() {
    // Restore session
    if (_token && _user) {
      _updateNavbar(_user);
      const r = await getMe();
      if (!r.ok) {
        _clearAuth();
      } else {
        _user = r.data.data;
        localStorage.setItem("spott_user", JSON.stringify(_user));
        _updateNavbar(_user);
      }
    } else {
      const createBtn = document.getElementById("createEventBtn");
      if (createBtn) createBtn.style.display = "none";
    }

    await loadEventsFromAPI();
  }

  // Public interface
  return {
    init, isLoggedIn, getUser, isAdmin,
    register, login, logout, getMe, updateMe,
    subscribeNewsletter, toggleSaveEvent,
    getEvents, getEvent, getTrending, getCategories,
    createEvent, updateEvent, deleteEvent, submitReview, uploadEventImage,
    loadEventsFromAPI,
    createBooking, getMyBookings, getTicket, cancelBooking,
    search,
    adminDashboard, adminUsers, adminDeleteUser, adminUpdateUser,
    adminBookings, adminEvents, adminUpdateBooking,
    getUserStats, getSavedEvents,
  };

})();


// ══════════════════════════════════════════════════════════════════
//  WIRE FRONTEND FUNCTIONS → BACKEND
//  These override the mock functions already in index.html
// ══════════════════════════════════════════════════════════════════

// ── Login / Signup Modal ───────────────────────────────────────
window.handleAuth = async function () {
  const email = (document.getElementById("authEmail")    || {}).value?.trim() || "";
  const pass  = (document.getElementById("authPassword") || {}).value || "";
  const name  = (document.getElementById("authName")     || {}).value?.trim() || "";

  if (!email || !pass) {
    if (typeof showToast === "function") showToast("Please fill in all fields.", "⚠️", "error");
    return;
  }

  const btn = document.getElementById("authSubmitBtn");
  if (btn) { btn.textContent = "Loading..."; btn.disabled = true; }

  const isSignup = typeof authMode !== "undefined" && authMode === "signup";
  let r;

  if (isSignup) {
    if (!name) {
      if (typeof showToast === "function") showToast("Name is required to create an account.", "⚠️", "error");
      if (btn) { btn.textContent = "Create Account →"; btn.disabled = false; }
      return;
    }
    r = await SPOTT_API.register(name, email, pass);
  } else {
    r = await SPOTT_API.login(email, pass);
  }

  if (btn) {
    btn.textContent = isSignup ? "Create Account →" : "Sign In →";
    btn.disabled = false;
  }

  if (r.ok) {
    if (typeof closeModal === "function") closeModal("authModal");
    if (typeof showToast  === "function") showToast(r.data.message, "✅", "success");
  } else {
    if (typeof showToast  === "function") showToast(r.data.error || "Authentication failed.", "❌", "error");
  }
};

// ── Quick Register Modal (event page) ─────────────────────────
window.handleRegister = async function () {
  const name  = (document.getElementById("regName")  || {}).value?.trim() || "";
  const email = (document.getElementById("regEmail") || {}).value?.trim() || "";
  const phone = (document.getElementById("regPhone") || {}).value?.trim() || "";

  if (!name || !email) {
    if (typeof showToast === "function") showToast("Please fill in Name and Email.", "⚠️", "error");
    return;
  }

  const tempPass = "Spott@" + Math.random().toString(36).slice(-6);
  const r = await SPOTT_API.register(name, email, tempPass, phone);

  if (r.ok) {
    ["regName", "regEmail", "regPhone"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    if (typeof closeModal === "function") closeModal("registerModal");
    if (typeof showToast  === "function") showToast("You're registered, " + name.split(" ")[0] + "! 🎉", "✅", "success");
  } else {
    if (typeof showToast === "function") showToast(r.data.error || "Registration failed.", "❌", "error");
  }
};

// ── Newsletter Subscribe ───────────────────────────────────────
window.handleSubscribe = async function () {
  const emailEl = document.getElementById("newsletterEmail");
  const email   = emailEl ? emailEl.value.trim() : "";
  if (!email) {
    if (typeof showToast === "function") showToast("Please enter your email.", "⚠️", "error");
    return;
  }

  const btn = document.getElementById("subscribeBtn");
  if (btn) { btn.textContent = "Subscribing..."; btn.disabled = true; }

  const r = await SPOTT_API.subscribeNewsletter(email);

  if (emailEl) emailEl.value = "";
  if (btn) {
    btn.textContent = r.ok ? "✅ Subscribed!" : "Subscribe →";
    if (!r.ok) btn.disabled = false;
  }
  if (typeof showToast === "function") {
    showToast(r.data.message || "Subscribed!", r.ok ? "✅" : "⚠️", r.ok ? "success" : "error");
  }
  if (r.ok) {
    setTimeout(function () {
      if (btn) { btn.textContent = "Subscribe →"; btn.disabled = false; }
    }, 3000);
  }
};

// ── Create / Publish Event ────────────────────────────────────
window.publishEvent = async function () {
  if (!SPOTT_API.isLoggedIn()) {
    if (typeof showToast === "function") showToast("Please sign in first.", "⚠️", "error");
    return;
  }
  if (!SPOTT_API.isAdmin()) {
    if (typeof showToast === "function") showToast("Only admins can create events.", "⚠️", "error");
    return;
  }
  if (typeof ceValidate === "function" && !ceValidate()) return;

  // Gather form data
  const titleEl    = document.getElementById("ceEventName");
  const descEl     = document.getElementById("ceDescription");
  const catEl      = document.getElementById("ceCategory");
  const startEl    = document.getElementById("ceStartDate");
  const venueEl    = document.getElementById("ceVenueInput");
  const priceEl    = document.getElementById("cePrice");
  const ticketEl   = document.getElementById("ceTicketType");
  const capEl      = document.getElementById("ceCapacity");

  const isFree     = ticketEl && ticketEl.value === "free";
  const priceStr   = isFree ? "Free" : ("₹" + (priceEl ? priceEl.value || "0" : "0"));
  const startVal   = startEl ? startEl.value : "";

  // Parse human date from ISO
  let dateStr = "", timeStr = "";
  if (startVal) {
    try {
      const dt = new Date(startVal);
      dateStr = dt.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      timeStr = dt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
    } catch (e) {}
  }

  const payload = {
    title:        titleEl  ? titleEl.value.trim()  : "",
    description:  descEl   ? descEl.value.trim()   : "",
    category:     catEl    ? catEl.value            : "",
    date:         dateStr,
    time:         timeStr,
    datetime_iso: startVal,
    location:     venueEl  ? venueEl.value.trim()  : "",
    price:        priceStr,
    emoji:        "🎉",
    capacity:     capEl    ? parseInt(capEl.value || "0") : 0,
    status:       "published",
  };

  if (!payload.title) {
    if (typeof showToast === "function") showToast("Event title is required.", "⚠️", "error");
    return;
  }

  // Handle image upload if present
  const photoInput = document.getElementById("cePhotoInput");
  if (photoInput && photoInput.files && photoInput.files[0]) {
    const imgR = await SPOTT_API.uploadEventImage(photoInput.files[0]);
    if (imgR.ok) payload.image_url = imgR.data.data.url;
  }

  const r = await SPOTT_API.createEvent(payload);

  if (r.ok) {
    if (typeof EVENTS !== "undefined" && r.data.data) {
      EVENTS.unshift(Object.assign({}, r.data.data, { attendees: [], badge: r.data.data.type }));
    }
    if (typeof closeModal    === "function") closeModal("createEventModal");
    if (typeof renderEvents  === "function") renderEvents();
    if (typeof resetCeForm   === "function") resetCeForm();
    if (typeof showToast     === "function") showToast('"' + payload.title + '" is now live! 🎉', "🚀", "success");
    setTimeout(function () {
      const feat = document.getElementById("featured");
      if (feat) feat.scrollIntoView({ behavior: "smooth" });
    }, 400);
  } else {
    if (typeof showToast === "function") showToast(r.data.error || "Failed to create event.", "❌", "error");
  }
};

// ── Payment / Booking Flow ────────────────────────────────────
window._spottCurrentEventId = null;
window._spottSelectedTicket = "general";

window.processPayment = async function () {
  if (!SPOTT_API.isLoggedIn()) {
    if (typeof closePage   === "function") closePage("paymentsPage");
    if (typeof openModal   === "function") openModal("authModal");
    if (typeof showToast   === "function") showToast("Please sign in to book.", "⚠️", "error");
    return;
  }

  const eventId    = window._spottCurrentEventId;
  const ticketType = window._spottSelectedTicket || "general";

  if (eventId) {
    const r = await SPOTT_API.createBooking(eventId, ticketType, 1);
    if (typeof closePage === "function") closePage("paymentsPage");
    if (r.ok) {
      if (typeof openModal  === "function") openModal("paySuccessModal");
      if (typeof showToast  === "function") showToast("Booking confirmed! 🎉", "✅", "success");
    } else {
      if (typeof showToast  === "function") showToast(r.data.error || "Booking failed.", "❌", "error");
    }
  } else {
    // Demo mode (no event selected)
    if (typeof closePage === "function") closePage("paymentsPage");
    if (typeof openModal === "function") openModal("paySuccessModal");
  }
};

// ── Feedback / Review Submission ──────────────────────────────
window.submitFeedback = async function () {
  if (typeof currentRating === "undefined" || !currentRating) {
    if (typeof showToast === "function") showToast("Please select a star rating.", "⚠️", "error");
    return;
  }

  const comment = (document.getElementById("feedbackComment") || {}).value?.trim() || "";
  const eventId = window._spottCurrentEventId;

  if (eventId && SPOTT_API.isLoggedIn()) {
    await SPOTT_API.submitReview(eventId, currentRating, comment);
  }

  if (typeof closePage  === "function") closePage("feedbackPage");
  if (typeof showToast  === "function") showToast("Thanks for your " + currentRating + "★ review! 🎉", "⭐", "success");
};

// ── Bookmark / Toggle Save ─────────────────────────────────────
var _origToggleSave = window.toggleSave;
window.toggleSave = async function (eventId, btn) {
  if (!SPOTT_API.isLoggedIn()) {
    if (typeof showToast === "function") showToast("Sign in to save events. 🔒", "⚠️", "error");
    return;
  }
  const r = await SPOTT_API.toggleSaveEvent(String(eventId));
  if (r.ok) {
    const saved = r.data.data && r.data.data.saved;
    if (btn) btn.classList.toggle("saved", saved);
    if (typeof showToast === "function") {
      showToast(saved ? "Event saved! 🔖" : "Removed from saved.", saved ? "🔖" : "✅", "success");
    }
  }
  // Also call original local handler if it exists
  if (typeof _origToggleSave === "function") _origToggleSave(eventId, btn);
};

// ── Patch openRegModal to track current event ─────────────────
var _origOpenRegModal = window.openRegModal;
window.openRegModal = function (ev) {
  if (ev && ev.id) window._spottCurrentEventId = ev.id;
  if (typeof _origOpenRegModal === "function") _origOpenRegModal(ev);
};

// ── Patch selectTicket to track ticket type ───────────────────
var _origSelectTicket = window.selectTicket;
window.selectTicket = function (type) {
  window._spottSelectedTicket = type;
  if (typeof _origSelectTicket === "function") _origSelectTicket(type);
};

// ── Global search with API suggestions ───────────────────────
document.addEventListener("DOMContentLoaded", function () {
  var searchInput = document.getElementById("globalSearch");
  if (searchInput) {
    var _debounce = null;
    searchInput.addEventListener("input", function () {
      clearTimeout(_debounce);
      var q = this.value.trim();
      var sugg = document.getElementById("searchSuggestions");

      if (q.length < 2) {
        if (sugg) sugg.innerHTML = "";
        return;
      }
      _debounce = setTimeout(async function () {
        var r = await SPOTT_API.search(q);
        if (r.ok && sugg && r.data.data) {
          var suggestions = r.data.data.suggestions || [];
          sugg.innerHTML = suggestions.map(function (s) {
            return '<div class="suggestion-item" onclick="pickSuggestion(\'' + s.replace(/'/g, "\\'") + '\')">' + s + "</div>";
          }).join("");
        }

        // Also filter rendered events
        if (r.ok && r.data.data && r.data.data.results) {
          var ids = r.data.data.results.map(function (e) { return e.id; });
          if (typeof EVENTS !== "undefined" && ids.length) {
            // Show matching events in grid
            if (typeof renderEvents === "function") {
              // Temporarily filter
              var origEvents = EVENTS.slice();
              EVENTS.length = 0;
              r.data.data.results.forEach(function (ev) {
                EVENTS.push(Object.assign({}, ev, { attendees: [], badge: ev.badge || ev.type }));
              });
              renderEvents();
              // Restore after 30 seconds of inactivity
              clearTimeout(window._spottSearchRestore);
              window._spottSearchRestore = setTimeout(function () {
                EVENTS.length = 0;
                origEvents.forEach(function (e) { EVENTS.push(e); });
                renderEvents();
              }, 30000);
            }
          }
        }
      }, 350);
    });

    // On clear, restore
    searchInput.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        this.value = "";
        var sugg = document.getElementById("searchSuggestions");
        if (sugg) sugg.innerHTML = "";
        if (typeof renderEvents === "function") renderEvents();
      }
    });
  }

  // ── Initialise API ───────────────────────────────────────────
  SPOTT_API.init();
});

console.log("%c🎉 Spott API Integration Ready", "color:#ff007f;font-weight:bold;font-size:14px;");
console.log("%cBackend: " + (window.SPOTT_BASE_URL || "http://localhost:5000/api"), "color:#329fff;");
