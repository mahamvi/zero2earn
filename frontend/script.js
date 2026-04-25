const API = "http://127.0.0.1:8000";

let userId = localStorage.getItem("z2e_user_id") || null;
let currentPage = "home";
let latestResume = null;
let currentUser = null;
let isPro = localStorage.getItem("z2e_pro") === "yes";

function setContent(html) {
  document.getElementById("content").innerHTML = html;
}

function safeArr(x) {
  return Array.isArray(x) ? x : [];
}

async function apiGet(path) {
  const res = await fetch(API + path);
  return await res.json();
}

function updateAuthUI() {
  const loginBox = document.getElementById("loginBox");
  const userBox = document.getElementById("userBox");

  if (userId) {
    loginBox.classList.add("hidden");
    userBox.classList.remove("hidden");
    document.getElementById("userMini").innerText =
      currentUser?.name || "User ID: " + userId;
    document.getElementById("proMini").innerText =
      isPro ? "Pro plan active" : "Free plan";
  } else {
    loginBox.classList.remove("hidden");
    userBox.classList.add("hidden");
  }
}

async function login() {
  const form = new URLSearchParams();
  form.append("email", document.getElementById("emailInput").value.trim());
  form.append("password", document.getElementById("passwordInput").value.trim());

  const res = await fetch(API + "/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form
  });

  const data = await res.json();

  if (data.user_id) {
    userId = data.user_id;
    localStorage.setItem("z2e_user_id", userId);
    await loadCurrentUser();
    updateAuthUI();
    showPage("home");
  } else {
    document.getElementById("status").innerText = "Login failed";
  }
}

function logout() {
  localStorage.removeItem("z2e_user_id");
  userId = null;
  currentUser = null;
  updateAuthUI();
  renderWelcome();
}

async function loadCurrentUser() {
  if (!userId) return;
  const d = await apiGet("/api/dashboard/" + userId);
  currentUser = d.user;
}

function setActive(page) {
  document.querySelectorAll(".nav button").forEach(b => b.classList.remove("active"));
  const el = document.getElementById("nav-" + page);
  if (el) el.classList.add("active");
}

function refresh() {
  showPage(currentPage);
}

function showPage(page) {
  currentPage = page;
  setActive(page);

  const titles = {
    home: ["Home", "Your premium earning command center"],
    resume: ["Resume First", "AI resume intelligence and premium rewrite"],
    jobs: ["Jobs", "High-intent job opportunities with AI proposals"],
    micro: ["Micro Jobs", "Fast earning path for first-income momentum"],
    automation: ["Automation", "Daily apply engine, queue health, follow-ups, and forecasts"],
    partners: ["Partners", "College and company revenue system"],
    pricing: ["Plans", "Subscriptions, institutions, and hiring revenue"]
  };

  document.getElementById("pageTitle").innerText = titles[page][0];
  document.getElementById("pageSub").innerText = titles[page][1];

  if (!userId && page !== "pricing" && page !== "partners") {
    renderWelcome();
    return;
  }

  if (page === "home") loadHome();
  if (page === "resume") loadResume();
  if (page === "jobs") loadJobs();
  if (page === "micro") loadMicro();
  if (page === "automation") loadAutomation();
  if (page === "partners") loadPartners();
  if (page === "pricing") loadPricing();
}

function renderWelcome() {
  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>From zero confusion to daily earning command.</h2>
        <p>Login to access your resume engine, jobs, micro-income path, automation, and progress tracker.</p>
        <span class="badge">Resume Intelligence</span>
        <span class="badge blue">Live Jobs</span>
        <span class="badge gold">Micro Income</span>
        <span class="badge purple">College + Company SaaS</span>
      </div>
    </section>
  `);
}

function progressBar(value) {
  const safeValue = Math.max(0, Math.min(100, value || 0));
  return `
    <div class="progress">
      <div class="progress-inner" style="width:${safeValue}%"></div>
    </div>
  `;
}

async function loadHome() {
  const d = await apiGet("/api/dashboard/" + userId);
  currentUser = d.user;
  updateAuthUI();

  const earned = d.metrics.total_earned || 0;
  const goal = d.user.goal_daily || 500;
  const remaining = Math.max(goal - earned, 0);
  const progress = Math.min(100, Math.floor((earned / goal) * 100));

  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>${d.user.name}, Rs.${remaining} away from today’s goal.</h2>
        <p>${d.user.headline || "Complete Resume First to unlock stronger recommendations."}</p>
        ${progressBar(progress)}
        <span class="badge">${d.user.track}</span>
        <span class="badge blue">Stage: ${d.user.stage}</span>
        <span class="badge gold">Goal: Rs.${goal}/day</span>
        <span class="badge purple">${isPro ? "Pro unlocked" : "Free plan"}</span>
      </div>
    </section>

    <div class="grid">
      <div class="metric"><h2>Rs.${earned}</h2><p>Total earned</p></div>
      <div class="metric"><h2>${d.metrics.jobs_applied}</h2><p>Applications</p></div>
      <div class="metric"><h2>${d.metrics.replies}</h2><p>Replies</p></div>
      <div class="metric"><h2>${d.metrics.interviews}</h2><p>Interviews</p></div>
    </div>

    <div class="card">
      <h2>Today’s Money Actions</h2>
      ${d.tasks.map(t => `
        <div class="item">
          <h3>${t.title}</h3>
          <p class="muted">${t.description}</p>
          <span class="badge gold">Reward: Rs.${t.estimated_reward}</span>
          <span class="badge blue">${t.status}</span>
          <br><br>
          <button onclick="completeTask(${t.id})">Complete & Unlock Reward</button>
        </div>
      `).join("")}
    </div>

    <div class="card hero">
      <div class="hero-content">
        <h2>Your Money Path</h2>
        <p>Rs.0 → Rs.500 → Rs.1,000 → Rs.5,000 → Rs.10,000</p>
        <button onclick="showPage('jobs')">Open Jobs</button>
        <button class="secondary" onclick="showPage('micro')">Start Micro Income</button>
      </div>
    </section>
  `);
}

async function completeTask(id) {
  await fetch(API + "/api/tasks/" + id + "/complete", { method: "POST" });
  loadHome();
}

function loadResume() {
  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>Resume Intelligence Engine</h2>
        <p>Upload resume, extract skills, score profile, find missing keywords, generate premium rewrite, and download resume text.</p>
        <span class="badge">ATS scoring</span>
        <span class="badge blue">Skill tags</span>
        <span class="badge red">Missing keywords</span>
        <span class="badge gold">Premium rewrite</span>
      </div>
    </section>

    <div class="card">
      <h2>Upload Resume</h2>
      <input type="file" id="resumeFile" accept=".doc,.docx,.pdf,.txt">
      <button onclick="uploadResume()">Analyze Resume</button>
      <button class="secondary" onclick="optimizeResume()">Optimize</button>
      <button class="soft" onclick="resumeStatus()">Status</button>
    </div>

    <div id="resumeUI">
      <div class="card"><p class="muted">Upload or optimize a resume to see the premium resume dashboard.</p></div>
    </div>
  `);
}

async function uploadResume() {
  const file = document.getElementById("resumeFile").files[0];
  if (!file) return alert("Select resume file first");

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(API + "/api/resume/upload/" + userId, {
    method: "POST",
    body: form
  });

  const d = await res.json();
  latestResume = d;
  renderResumeUI(d);
}

async function optimizeResume() {
  const res = await fetch(API + "/api/resume/optimize/" + userId, { method: "POST" });
  const d = await res.json();
  latestResume = d;
  renderResumeUI(d);
}

async function resumeStatus() {
  const d = await apiGet("/api/resume/status/" + userId);
  latestResume = d;
  renderResumeUI(d);
}

function renderResumeUI(d) {
  const score = d.resume_score || 0;

  document.getElementById("resumeUI").innerHTML = `
    <div class="grid">
      <div class="card">
        <h2>Resume Score</h2>
        <div class="resume-score">${score}</div>
        ${progressBar(score)}
      </div>

      <div class="card">
        <h2>Clean Headline</h2>
        <div class="resume-headline">${d.optimized_headline || d.headline || "Resume profile"}</div>
        <p class="muted">${d.track || ""}</p>
      </div>
    </div>

    <div class="card"><h2>Optimized Summary</h2><p>${d.optimized_summary || d.summary || ""}</p></div>

    <div class="card">
      <h2>Skills</h2>
      ${safeArr(d.skills).map(s => `<span class="badge">${s}</span>`).join("")}
    </div>

    <div class="card">
      <h2>Missing Keywords</h2>
      ${safeArr(d.missing_keywords).map(k => `<span class="badge red">${k}</span>`).join("")}
    </div>

    <div class="card">
      <h2>ATS Keywords</h2>
      ${safeArr(d.ats_keywords).map(k => `<span class="badge blue">${k}</span>`).join("")}
    </div>

    <div class="card">
      <h2>Resume Bullets</h2>
      ${safeArr(d.recommended_bullets).map(b => `<div class="item">${b}</div>`).join("")}
    </div>
  `;
}

async function loadJobs() {
  const d = await apiGet("/api/jobs/" + userId);

  let html = `
    <section class="card hero">
      <div class="hero-content">
        <h2>Money Opportunities</h2>
        <p>Focus on high-reply, fast-action jobs first. Use AI Proposal before applying.</p>
        <span class="badge">Goal: 5 applications today</span>
        <span class="badge blue">AI proposals enabled</span>
      </div>
    </section>
  `;

  html += `<div class="card">`;

  if (!d.jobs || d.jobs.length === 0) {
    html += `<p>No jobs found.</p>`;
  } else {
    d.jobs.slice(0, 12).forEach(j => {
      const link = j.apply_url || j.apply_link || "#";
      html += `
        <div class="job-card">
          <div>
            <div class="job-title">${j.title}</div>
            <div class="job-company">${j.company} | ${j.location || "Remote"}</div>
            <span class="badge gold">Score: ${j.match_score || 0}%</span>
            <span class="badge blue">Win: ${j.win_probability || 0}%</span>
            <span class="badge">${j.source || "Job source"}</span>
          </div>
          <div class="row">
            <button onclick="window.open('${link}','_blank')">Apply Now</button>
            <button class="secondary" onclick="openWingman('${j.id}')">AI Proposal</button>
          </div>
        </div>
      `;
    });
  }

  html += `</div>`;
  setContent(html);
}

async function openWingman(jobId) {
  const d = await apiGet("/api/wingman/" + userId + "?job_id=" + encodeURIComponent(jobId));

  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>AI Proposal</h2>
        <p>${d.title} - ${d.company}</p>
        <span class="badge">Score: ${d.match_score}</span>
        <span class="badge blue">Win: ${d.win_probability}</span>
      </div>
    </section>

    <div class="card">
      <h2>Checklist</h2>
      ${safeArr(d.checklist).map(x => `<div class="item">${x}</div>`).join("")}
    </div>

    <div class="card">
      <h2>Proposal</h2>
      <textarea>${d.proposal || ""}</textarea>
      <button onclick="navigator.clipboard.writeText(document.querySelector('textarea').value)">Copy Proposal</button>
      <button class="secondary" onclick="window.open('${d.portal_url}','_blank')">Open Job</button>
    </div>
  `);
}

async function loadMicro() {
  const d = await apiGet("/api/micro-jobs/" + userId);

  let html = `
    <section class="card hero">
      <div class="hero-content">
        <h2>Instant Money Engine</h2>
        <p>Start earning today while job applications are building momentum.</p>
        <span class="badge gold">Goal: first Rs.100 today</span>
        <span class="badge blue">Beginner friendly</span>
      </div>
    </section>

    <div class="grid">
  `;

  d.items.forEach(m => {
    html += `
      <div class="card">
        <h2>${m.name}</h2>
        <p class="muted">${m.why}</p>
        <span class="badge">${m.category}</span>
        <span class="badge gold">${m.earning_range}</span>
        <span class="badge blue">${m.payout_speed}</span>
        <br><br>
        <button onclick="window.open('${m.url}','_blank')">Start Earning</button>
      </div>
    `;
  });

  html += `</div>`;
  setContent(html);
}

async function loadAutomation() {
  const auto = await apiGet("/api/automation/" + userId + "?limit=20&min_score=20");

  let followups = { items: [] };
  try {
    followups = await apiGet("/api/automation/followups/" + userId);
  } catch (e) {}

  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>Automation Command Center</h2>
        <p>Prepare, submit, track, follow up, forecast, and improve.</p>
        <span class="badge">${auto.mode}</span>
        <span class="badge blue">Min score: ${auto.min_score}</span>
        <span class="badge gold">Queue target: ${auto.recommended_queue_size}</span>
      </div>
    </section>

    <div class="command-grid">
      <div class="card">
        <h2>Today’s Mission</h2>
        <div class="timeline">
          <div class="step"><h3>1. Prepare application queue</h3><p>Build a ready-to-submit queue.</p></div>
          <div class="step"><h3>2. Submit today’s applications</h3><p>Submit 5 prepared applications.</p></div>
          <div class="step"><h3>3. Follow up</h3><p>Due follow-ups: ${safeArr(followups.items).length}</p></div>
          <div class="step"><h3>4. Backup income</h3><p>Complete one microjob or skill-gap task.</p></div>
        </div>
        <button onclick="prepareQueue()">Prepare Queue Now</button>
      </div>

      <div class="card">
        <h2>Queue Health</h2>
        <div class="signal"><h3>Application queue</h3><div class="signal-number">${auto.recommended_queue_size}</div></div>
        <div class="signal"><h3>Follow-ups due</h3><div class="signal-number">${safeArr(followups.items).length}</div></div>
      </div>
    </div>

    <div class="automation-panel">
      <div class="signal"><h3>7-day forecast</h3><div class="signal-number">Rs.${auto.forecast.projected_7d}</div><p>${auto.forecast.message}</p></div>
      <div class="signal"><h3>30-day forecast</h3><div class="signal-number">Rs.${auto.forecast.projected_30d}</div></div>
      <div class="signal"><h3>Streak</h3><div class="signal-number">${auto.streak.streak_days}</div><p>${auto.streak.message}</p></div>
      <div class="signal"><h3>Reply rate</h3><div class="signal-number">${auto.metrics.reply_rate}%</div></div>
    </div>
  `);
}

async function prepareQueue() {
  const form = new URLSearchParams();
  form.append("limit", "10");
  form.append("min_score", "20");

  const res = await fetch(API + "/api/automation/queue/" + userId, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form
  });

  const d = await res.json();
  alert("Prepared: " + d.count);
  loadAutomation();
}

function loadPartners() {
  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>Partnership Engine</h2>
        <p>Built for colleges, companies, training partners, and placement programs.</p>
      </div>
    </section>

    <div class="grid">
      <div class="card"><h2>College Tie-ups</h2><p>Bulk student onboarding and placement dashboards.</p></div>
      <div class="card"><h2>Company Hiring</h2><p>Featured jobs and candidate pipeline.</p></div>
      <div class="card"><h2>Training Partners</h2><p>Upskill users and monetize skill-gap tasks.</p></div>
    </div>
  `);
}

function loadPricing() {
  setContent(`
    <section class="card hero">
      <div class="hero-content">
        <h2>Zero2Earn Revenue System</h2>
        <p>Subscriptions, institutions, company hiring, and featured jobs.</p>
      </div>
    </section>

    <div class="grid">
      <div class="card"><h2>Free</h2><h2>Rs.0</h2><p>Basic jobs and microjobs.</p></div>
      <div class="card"><h2>Pro</h2><h2>Rs.499/month</h2><p>AI proposals, automation, premium resume rewrite.</p><button onclick="isPro=true;localStorage.setItem('z2e_pro','yes');updateAuthUI();alert('Demo Pro unlocked')">Unlock Demo Pro</button></div>
      <div class="card"><h2>College</h2><h2>Custom</h2><p>Bulk student dashboard.</p></div>
      <div class="card"><h2>Company</h2><h2>Custom</h2><p>Hiring dashboard and featured jobs.</p></div>
    </div>
  `);
}

updateAuthUI();

if (userId) {
  loadCurrentUser().then(() => {
    updateAuthUI();
    showPage("home");
  });
} else {
  renderWelcome();
}