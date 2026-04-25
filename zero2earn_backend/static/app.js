let USER_ID = null;
let DASH = null;
let JOBS = [];
let FILTERED_JOBS = [];
let AUTO = null;
let RESUME = null;

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const e = (str) => String(str ?? '').replace(/[&<>"]/g, s => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[s]));
const ea = (str) => e(str).replace(/'/g, '&#39;');

window.addEventListener('DOMContentLoaded', () => {
  $('#login-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const r = await fetch('/api/login', { method: 'POST', body: new FormData(ev.target) });
    if (!r.ok) return alert('Login failed');
    const d = await r.json();
    USER_ID = d.user_id;
    $('#auth').classList.add('hidden');
    $('#app').classList.remove('hidden');
    await refreshAll();
  });
  const signupForm = $('#signup-form');
  if (signupForm) {
    signupForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const r = await fetch('/api/signup', { method: 'POST', body: new FormData(ev.target) });
      if (!r.ok) {
        const msg = await r.text();
        return alert('Signup failed: ' + msg);
      }
      const d = await r.json();
      USER_ID = d.user_id;
      $('#auth').classList.add('hidden');
      $('#app').classList.remove('hidden');
      await refreshAll();
      switchTab('resume');
    });
  }
  $$('.tab-btn').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  $('#refresh-all').addEventListener('click', refreshAll);
  $('#close-modal').addEventListener('click', closeWingman);
  $('#wingman-modal').addEventListener('click', (ev) => { if (ev.target.id === 'wingman-modal') closeWingman(); });
});

function closeWingman() { $('#wingman-modal').classList.add('hidden'); $('#wingman-content').innerHTML = ''; }
function switchTab(tab) { $$('.tab-btn').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab)); $$('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === tab)); $('#screen-title').textContent = tab === 'rm' ? 'Revenue Mode' : tab.charAt(0).toUpperCase() + tab.slice(1).replace('-', ' '); }
async function refreshAll() { await Promise.all([loadDashboard(), loadResumeLayer(), loadJobs(), loadMicroJobs(), loadSkills(), loadIncome(), loadApplications(), loadAutomation()]); renderCoach(); renderRM(); }


async function loadResumeLayer() {
  if (!USER_ID || !$('#resume')) return;
  $('#resume').innerHTML = `<div class="card"><h3>Resume First Engine</h3><div class="muted">Loading resume layer...</div></div>`;
  try {
    const r = await fetch(`/api/resume/status/${USER_ID}`);
    if (!r.ok) throw new Error('resume status failed');
    RESUME = await r.json();
    renderResumeLayer();
  } catch (err) {
    $('#resume').innerHTML = `<div class="card"><h3>Resume First Engine</h3><div class="muted">Resume layer could not load. Use AI Coach to paste or upload resume, then refresh.</div></div>`;
  }
}

function renderResumeLayer() {
  const has = !!RESUME?.has_resume;
  $('#resume').innerHTML = `
    <div class="section-title"><h3>Resume First Engine</h3><span class="pill">${has ? 'Ready for matching' : 'Start here'}</span></div>
    <div class="grid metrics">
      <div class="card"><div class="muted">Resume status</div><div class="metric-value">${has ? 'ON' : 'OFF'}</div><div class="muted">${e(RESUME.next_step || '')}</div></div>
      <div class="card"><div class="muted">Track</div><div class="metric-value" style="font-size:22px">${e(RESUME.track || 'General remote')}</div></div>
      <div class="card"><div class="muted">Skills found</div><div class="metric-value">${(RESUME.skills || []).length}</div></div>
      <div class="card"><div class="muted">Resume length</div><div class="metric-value">${RESUME.resume_length || 0}</div></div>
    </div>
    <div class="two">
      <div class="card">
        <h3>Step 1: Paste resume</h3>
        <form id="resume-first-paste" class="grid">
          <textarea name="text" placeholder="Paste any user's resume here. Jobs, Wingman, Skills and Automation will adapt to this resume."></textarea>
          <button class="btn good" type="submit">Analyze resume and personalize jobs</button>
        </form>
        <form id="resume-first-upload" class="grid" enctype="multipart/form-data" style="margin-top:14px">
          <input type="file" name="file" accept=".pdf,.docx,.txt" />
          <button class="btn secondary" type="submit">Upload resume</button>
        </form>
      </div>
      <div class="card">
        <h3>Step 2: Optimize profile</h3>
        <div class="muted">Headline</div>
        <div style="margin:8px 0 14px"><strong>${e(RESUME.headline || 'No headline yet')}</strong></div>
        <div class="muted">Summary</div>
        <div style="margin-top:8px">${e(RESUME.summary || 'Paste or upload resume first.')}</div>
        <div style="margin-top:12px">${(RESUME.skills || []).map(s => `<span class="tag">${e(s)}</span>`).join('')}</div>
        <div class="actions" style="margin-top:14px">
          <button class="btn" onclick="optimizeResumeNow()">Optimize resume layer</button>
          <button class="btn secondary" onclick="switchTab('jobs')">Show matched jobs</button>
        </div>
      </div>
    </div>`;
  $('#resume-first-paste').addEventListener('submit', async ev => {
    ev.preventDefault();
    await fetch(`/api/resume/paste/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) });
    await afterResumeChanged('Resume analyzed. Jobs are now personalized.');
  });
  $('#resume-first-upload').addEventListener('submit', async ev => {
    ev.preventDefault();
    await fetch(`/api/resume/upload/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) });
    await afterResumeChanged('Resume uploaded. Jobs are now personalized.');
  });
}

async function optimizeResumeNow() {
  const r = await fetch(`/api/resume/optimize/${USER_ID}`, { method: 'POST' });
  if (!r.ok) return alert('Upload or paste resume first');
  const d = await r.json();
  alert(`Resume optimized. Score: ${d.resume_score}. Open Jobs to see relevant matches.`);
  await afterResumeChanged();
}

async function afterResumeChanged(msg) {
  await loadDashboard();
  await loadResumeLayer();
  await loadJobs();
  await loadSkills();
  await loadAutomation();
  renderCoach();
  renderRM();
  if (msg) alert(msg);
}

async function loadDashboard() {
  const r = await fetch(`/api/dashboard/${USER_ID}`); if (!r.ok) return;
  DASH = await r.json(); $('#user-track').textContent = DASH.user.track; const m = DASH.metrics; const t = DASH.tracking || {};
  $('#home').innerHTML = `
    <div class="grid metrics">
      <div class="card"><div class="muted">Total earned</div><div class="metric-value">₹${m.total_earned}</div></div>
      <div class="card"><div class="muted">Applications submitted</div><div class="metric-value">${m.jobs_applied}</div><div class="muted">Prepared: ${m.prepared || 0}</div></div>
      <div class="card"><div class="muted">Reply rate</div><div class="metric-value">${m.reply_rate || 0}%</div><div class="muted">Interviews: ${m.interviews || 0}</div></div>
      <div class="card"><div class="muted">Today's command</div><div class="metric-value">₹${m.today_target}</div><div class="muted">${m.pending_tasks} tasks left</div></div>
    </div>
    <div class="split">
      <div class="card"><div class="section-title"><h3>Today's command</h3><span class="pill">${e(DASH.user.track)}</span></div><div class="grid">${DASH.tasks.map(t => `<div class="task"><div><div><strong>${e(t.title)}</strong></div><div class="muted">${e(t.description)}</div><div class="muted">Est. ₹${t.estimated_reward || 0}</div></div><div>${t.status === 'done' ? '<span class="pill">Done</span>' : `<button class="btn secondary" onclick="completeTask(${t.id})">Complete</button>`}</div></div>`).join('')}</div></div>
      <div class="card"><div class="section-title"><h3>Automation insights</h3><span class="pill">Daily Mode</span></div><div class="grid">${(AUTO?.commands || t.insights || []).map(x => `<div><strong>${e(x)}</strong></div>`).join('')}<div class="muted">Avg application score: ${t.avg_score || 0}</div></div></div>
    </div>
    <div class="card" style="margin-top:16px"><div class="section-title"><h3>Alerts</h3><span class="pill">Live</span></div><div class="grid">${DASH.alerts.map(a => `<div><strong>${e(a.message)}</strong><div class="muted">${e(a.created_at)}</div></div>`).join('')}</div></div>`;
}
async function completeTask(id) { await fetch(`/api/tasks/${id}/complete`, { method: 'POST' }); await loadDashboard(); renderRM(); }

async function loadJobs() { const r = await fetch(`/api/jobs/${USER_ID}`); if (!r.ok) return; const d = await r.json(); JOBS = d.jobs || []; FILTERED_JOBS = [...JOBS]; renderJobsPanel(); }
function renderJobsPanel() {
  $('#jobs').innerHTML = `<div class="section-title"><h3>Resume-matched Live Jobs + Apply Engine</h3><div class="actions"><button class="btn secondary" onclick="switchTab('resume')">Resume First</button><button class="btn" id="refresh-jobs-btn">Refresh live jobs</button></div></div><div class="card filter-card"><div class="job-filters"><input id="job-search" placeholder="Search title, company, keyword"/><select id="job-source"><option value="">All sources</option><option value="Remotive">Remotive</option><option value="RemoteOK">RemoteOK</option><option value="Arbeitnow">Arbeitnow</option></select><select id="job-level"><option value="">All levels</option><option value="entry">Entry</option><option value="mid">Mid</option><option value="senior">Senior</option><option value="general">General</option></select><select id="job-category"><option value="">All categories</option><option value="tech">Tech</option><option value="writing">Writing</option><option value="operations">Operations</option><option value="support">Support</option><option value="design">Design</option><option value="marketing">Marketing</option><option value="general">General</option></select><select id="job-min-score"><option value="0">Any score</option><option value="50">50+</option><option value="60">60+</option><option value="70">70+</option><option value="80">80+</option></select></div><div class="actions" style="margin-top:12px"><button class="btn good" onclick="prepareApplyBatch()">Prepare Top 10</button><button class="btn secondary" onclick="openTopPortals()">Open Top 5 Portals</button></div></div><div id="apply-engine-panel"></div><div class="section-title"><h3>Recommended jobs</h3><span class="pill" id="jobs-count">${FILTERED_JOBS.length} jobs</span></div><div class="grid" id="jobs-list"></div>`;
  $('#refresh-jobs-btn').onclick = loadJobs;
  ['job-search','job-source','job-level','job-category','job-min-score'].forEach(id => $('#' + id).addEventListener('input', applyLocalFilters));
  renderJobList();
}
function applyLocalFilters() { const q = $('#job-search').value.toLowerCase(), source = $('#job-source').value, level = $('#job-level').value, cat = $('#job-category').value, min = parseInt($('#job-min-score').value || '0',10); FILTERED_JOBS = JOBS.filter(j => (!q || `${j.title} ${j.company} ${j.description}`.toLowerCase().includes(q)) && (!source || j.source === source) && (!level || j.level === level) && (!cat || j.category === cat) && (j.match_score >= min)); renderJobList(); }
function renderJobList() { $('#jobs-count').textContent = `${FILTERED_JOBS.length} jobs`; $('#jobs-list').innerHTML = FILTERED_JOBS.map(renderJob).join('') || '<div class="card muted">No jobs match filters.</div>'; }
function renderJob(job) { const applyUrl = (job.apply_url && job.apply_url !== '#') ? job.apply_url : job.portal_links.linkedin; return `<div class="card job-card"><div class="actions"><span class="pill">${e(job.source)}</span><span class="pill">Score ${job.match_score}%</span><span class="pill">Win ${job.win_probability}%</span><span class="pill">${e(job.level)}</span></div><div><strong>${e(job.title)}</strong></div><div class="muted">${e(job.company)} · ${e(job.location || 'Remote')}</div><div class="muted">${e(job.salary_hint || 'Not listed')}</div><div class="actions"><span class="tag">${e(job.category || 'general')}</span>${(job.matched_skills || []).map(s => `<span class="tag">${e(s)}</span>`).join('')}</div><div class="muted">${(job.reasons || []).map(e).join(' • ')}</div>${(job.missing_skills || []).length ? `<div class="muted">Need ${e(job.missing_skills.join(', '))}</div>` : ''}<div class="actions"><a class="btn" href="${applyUrl}" target="_blank">Open portal</a><button class="btn secondary" onclick="openWingman('${String(job.id).replace(/'/g, "\\'")}')">Wingman</button><button class="btn good" onclick="applyWithWingman('${String(job.id).replace(/'/g, "\\'")}')">Apply with Wingman</button></div><div class="portal-links"><a href="${job.portal_links.linkedin}" target="_blank">LinkedIn</a><a href="${job.portal_links.indeed_india}" target="_blank">Indeed India</a><a href="${job.portal_links.naukri}" target="_blank">Naukri</a><a href="${job.portal_links.foundit}" target="_blank">Foundit</a><a href="${job.portal_links.internshala}" target="_blank">Internshala</a></div></div>`; }
async function openWingman(jobId) { const r = await fetch(`/api/wingman/${USER_ID}?job_id=${encodeURIComponent(jobId)}`); if (!r.ok) return alert('Wingman failed for this job'); const w = await r.json(); renderWingman(w, false); }
async function applyWithWingman(jobId) { const r = await fetch(`/api/wingman/${USER_ID}?job_id=${encodeURIComponent(jobId)}`); if (!r.ok) return alert('Wingman failed for this job'); const w = await r.json(); await copyText(w.proposal); renderWingman(w, true); window.open(w.portal_url, '_blank', 'noopener,noreferrer'); }
function renderWingman(w, applying) { const blob = encodeURIComponent(JSON.stringify(w)); $('#wingman-content').innerHTML = `<div class="three"><div class="card"><div class="muted">Match score</div><div class="metric-value">${w.match_score}%</div></div><div class="card"><div class="muted">Win probability</div><div class="metric-value">${w.win_probability}%</div></div><div class="card"><div class="muted">Portal</div><a class="btn" href="${w.portal_url}" target="_blank">Open source portal</a></div></div>${applying ? '<div class="card" style="margin-top:16px"><strong>Proposal copied.</strong><div class="muted">Paste it into the portal, submit, then mark applied.</div></div>' : ''}<div class="two" style="margin-top:16px"><div class="card"><h4>Why this fits</h4>${w.reasons.map(x => `<div class="tag">${e(x)}</div>`).join('')}<h4>Missing</h4>${(w.missing || []).length ? w.missing.map(x => `<div class="tag warn">${e(x)}</div>`).join('') : '<div class="muted">No major gap detected</div>'}</div><div class="card"><h4>Checklist</h4>${w.checklist.map(x => `<div class="muted">• ${e(x)}</div>`).join('')}</div></div><div class="card" style="margin-top:16px"><div class="section-title"><h4>Proposal</h4><button class="btn secondary" onclick="copyProposal()">Copy</button></div><textarea id="proposal-box">${e(w.proposal)}</textarea><div class="actions" style="margin-top:12px"><button class="btn secondary" onclick="saveApplication('${blob}','prepared')">Save prepared</button><button class="btn good" onclick="saveApplication('${blob}','applied')">Mark applied</button></div></div>`; $('#wingman-modal').classList.remove('hidden'); }
async function copyText(text) { try { await navigator.clipboard.writeText(text); } catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); } }
async function copyProposal() { const box = $('#proposal-box'); if (!box) return; await copyText(box.value); alert('Proposal copied'); }
async function saveApplication(blob, status='applied') { const w = JSON.parse(decodeURIComponent(blob)); const job = JOBS.find(j => String(j.id) === String(w.job_id)); const fd = new FormData(); fd.append('job_id', w.job_id); fd.append('title', w.title); fd.append('company', w.company); fd.append('source', job?.source || 'Live'); fd.append('apply_url', w.portal_url); fd.append('proposal', $('#proposal-box')?.value || w.proposal); fd.append('score', w.match_score); fd.append('status', status); await fetch(`/api/applications/${USER_ID}`, { method: 'POST', body: fd }); alert(`Application saved as ${status}`); closeWingman(); await loadApplications(); await loadDashboard(); await loadAutomation(); }
async function prepareApplyBatch() { const r = await fetch(`/api/apply-engine/plan/${USER_ID}?limit=10&min_score=55`); if (!r.ok) return alert('Could not prepare batch'); const d = await r.json(); $('#apply-engine-panel').innerHTML = `<div class="card"><div class="section-title"><h3>Prepared application queue</h3><span class="pill">${d.count} jobs</span></div><div class="grid">${d.items.map(w => { const blob = encodeURIComponent(JSON.stringify(w)); return `<div class="task"><div><strong>${e(w.title)}</strong><div class="muted">${e(w.company)} · Score ${w.match_score}% · Win ${w.win_probability}%</div></div><div class="actions"><button class="btn secondary" onclick="copyBatchProposal('${blob}')">Copy proposal</button><a class="btn" href="${w.portal_url}" target="_blank">Open</a><button class="btn good" onclick="saveApplication('${blob}','applied')">Mark applied</button></div></div>`; }).join('')}</div></div>`; }
async function copyBatchProposal(blob) { const w = JSON.parse(decodeURIComponent(blob)); await copyText(w.proposal); alert('Proposal copied'); }
function openTopPortals() { FILTERED_JOBS.slice(0, 5).forEach((j, idx) => { const url = (j.apply_url && j.apply_url !== '#') ? j.apply_url : j.portal_links.linkedin; setTimeout(() => window.open(url, '_blank', 'noopener,noreferrer'), idx * 350); }); }

async function loadAutomation() { if (!USER_ID) return; if ($('#automation')) $('#automation').innerHTML = `<div class="card"><h3>Automation Engine</h3><div class="muted">Loading daily execution plan...</div></div>`; try { const r = await fetch(`/api/automation/${USER_ID}`); if (!r.ok) throw new Error('automation failed'); AUTO = await r.json(); renderAutomation(); } catch (err) { if ($('#automation')) $('#automation').innerHTML = `<div class="card"><h3>Automation Engine</h3><div class="muted">Automation could not load. First analyze a resume, then open Jobs and prepare applications.</div><div class="actions" style="margin-top:12px"><button class="btn" onclick="switchTab('resume')">Start with Resume</button><button class="btn secondary" onclick="switchTab('jobs')">Open Jobs</button></div></div>`; } }
function renderAutomation() { if (!$('#automation') || !AUTO) return; const f = AUTO.forecast || {}, s = AUTO.streak || {}; $('#automation').innerHTML = `<div class="section-title"><h3>Automation Engine</h3><span class="pill">${e(AUTO.mode)}</span></div><div class="grid metrics"><div class="card"><div class="muted">Queue size</div><div class="metric-value">${AUTO.recommended_queue_size}</div></div><div class="card"><div class="muted">High-score jobs</div><div class="metric-value">${AUTO.high_score_jobs}</div></div><div class="card"><div class="muted">Streak</div><div class="metric-value">${s.streak_days || 0}d</div><div class="muted">${e(s.message || '')}</div></div><div class="card"><div class="muted">30-day forecast</div><div class="metric-value">₹${f.projected_30d || 0}</div></div></div><div class="two"><div class="card"><h3>Daily execution commands</h3><div class="grid">${(AUTO.commands || []).map(x => `<div class="task"><div><strong>${e(x)}</strong></div></div>`).join('')}</div><div class="actions" style="margin-top:12px"><button class="btn good" onclick="automationQueue()">Auto-prepare queue</button><button class="btn secondary" onclick="switchTab('applications')">Review Applications</button></div></div><div class="card"><h3>Income forecast</h3><div class="muted">${e(f.message || '')}</div><div style="margin-top:10px"><span class="tag">7 days ₹${f.projected_7d || 0}</span><span class="tag">30 days ₹${f.projected_30d || 0}</span></div></div></div><div class="card" style="margin-top:16px"><div class="section-title"><h3>Follow-ups due</h3><span class="pill">${(AUTO.followups_due || []).length}</span></div><div class="grid">${(AUTO.followups_due || []).length ? AUTO.followups_due.map(renderFollowup).join('') : '<div class="muted">No follow-ups due. Keep submitting and tracking.</div>'}</div></div><div class="card" style="margin-top:16px"><h3>Top automation queue candidates</h3><div class="grid">${(AUTO.top_jobs || []).map(j => `<div class="task"><div><strong>${e(j.title)}</strong><div class="muted">${e(j.company)} · Score ${j.score}% · Win ${j.win_probability}%</div></div><a class="btn" target="_blank" href="${j.apply_url || '#'}">Open</a></div>`).join('')}</div></div>`; }
function renderFollowup(x) { const blob = encodeURIComponent(x.message || ''); return `<div class="task"><div><strong>${e(x.title)}</strong><div class="muted">${e(x.company)} · ${e(x.status)} · due ${e(x.follow_up_date)}</div></div><div class="actions"><button class="btn secondary" onclick="copyFollowup('${blob}')">Copy follow-up</button><a class="btn" href="${x.apply_url}" target="_blank">Open</a><button class="btn good" onclick="markFollowupSent(${x.id})">Sent</button></div></div>`; }
async function automationQueue() { const fd = new FormData(); fd.append('limit', '10'); fd.append('min_score', '55'); const r = await fetch(`/api/automation/queue/${USER_ID}`, { method: 'POST', body: fd }); if (!r.ok) return alert('Queue failed'); const d = await r.json(); alert(`Prepared ${d.count} new applications`); await loadApplications(); await loadDashboard(); await loadAutomation(); }
async function copyFollowup(blob) { await copyText(decodeURIComponent(blob)); alert('Follow-up copied'); }
async function markFollowupSent(id) { await fetch(`/api/automation/followup-sent/${USER_ID}/${id}`, { method: 'POST' }); await loadAutomation(); await loadApplications(); }

async function loadSkills() { if (!USER_ID) return; const r = await fetch(`/api/skills/${USER_ID}`); if (!r.ok) return; const d = await r.json(), plans = d.plans || [], top = d.top_jobs || []; $('#skills').innerHTML = `<div class="section-title"><h3>Skill Gap → Learning Path Engine</h3><span class="pill">Resume-first</span></div><div class="two"><div class="card"><h3>Top skill gaps to fix</h3><div class="grid">${plans.length ? plans.map(p => `<div class="skill-plan"><div class="actions"><span class="pill">${e(p.category)}</span><span class="pill">${e(p.time)}</span></div><h4>${e(p.name)}</h4><div class="muted">${e(p.why)}</div><div style="margin-top:8px"><strong>Mini project:</strong> ${e(p.project)}</div><div class="muted" style="margin-top:8px">Resume line: ${e(p.resume_line)}</div><div class="portal-links" style="margin-top:10px">${(p.resources || []).map(res => `<a href="${res.url}" target="_blank">${e(res.title)}</a>`).join('')}</div><div class="actions" style="margin-top:10px"><button class="btn secondary" onclick="addSkillTask('${ea(p.id)}')">Add to today</button></div></div>`).join('') : '<div class="muted">No urgent skill gap detected yet. Upload/paste a resume and refresh jobs.</div>'}</div></div><div class="card"><h3>Jobs affected by gaps</h3><div class="grid">${top.length ? top.map(j => `<div class="task"><div><strong>${e(j.title)}</strong><div class="muted">${e(j.company)} · Score ${j.score}%</div><div>${(j.missing_skills || []).map(s => `<span class="tag warn">Need ${e(s)}</span>`).join('')}</div></div></div>`).join('') : '<div class="muted">No job data yet.</div>'}</div></div></div>`; }
async function addSkillTask(skill) { const fd = new FormData(); fd.append('skill', skill); await fetch(`/api/skills/add-to-today/${USER_ID}`, { method: 'POST', body: fd }); await loadDashboard(); switchTab('home'); }
async function loadMicroJobs() { const r = await fetch(`/api/micro-jobs/${USER_ID}`); if (!r.ok) return; const d = await r.json(); $('#micro').innerHTML = `<div class="section-title"><h3>First ₹100 / ₹500 micro-income engine</h3></div><div class="grid">${d.items.map(x => `<div class="card micro-card"><div class="actions"><span class="pill">${e(x.category)}</span><span class="pill">${e(x.payout_speed)}</span></div><div><strong>${e(x.name)}</strong></div><div class="muted">${e(x.earning_range)} · ${e(x.country_fit)}</div><div class="muted">${e(x.why)}</div><div class="actions"><a class="btn" href="${x.url}" target="_blank">Open portal</a><button class="btn secondary" onclick="addMicro('${e(x.id)}')">Add to today</button></div></div>`).join('')}</div>`; }
async function addMicro(id) { const fd = new FormData(); fd.append('portal_id', id); await fetch(`/api/micro-jobs/add-to-today/${USER_ID}`, { method: 'POST', body: fd }); await loadDashboard(); switchTab('home'); }
async function loadIncome() { const r = await fetch(`/api/income/${USER_ID}`); if (!r.ok) return; const d = await r.json(); $('#income').innerHTML = `<div class="two"><div class="card"><h3>Add income</h3><form id="income-form" class="grid"><input name="amount" type="number" placeholder="Amount in ₹" required/><input name="source" placeholder="Source" required/><textarea name="notes" placeholder="Notes"></textarea><button class="btn" type="submit">Save income</button></form></div><div class="card"><h3>Recent income</h3><div class="grid">${d.items.map(x => `<div class="income-card"><strong>₹${x.amount}</strong><div>${e(x.source)}</div><div class="muted">${e(x.notes || '')}</div><div class="muted">${e(x.created_at)}</div></div>`).join('')}</div></div></div>`; $('#income-form').addEventListener('submit', async ev => { ev.preventDefault(); await fetch(`/api/income/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) }); ev.target.reset(); await loadIncome(); await loadDashboard(); renderRM(); }); }
async function loadApplications() { const r = await fetch(`/api/applications/${USER_ID}`); if (!r.ok) return; const d = await r.json(); const m = d.metrics || {}; $('#applications').innerHTML = `<div class="section-title"><h3>Tracking Engine</h3><span class="pill">Feedback loop</span></div><div class="grid metrics"><div class="card"><div class="muted">Prepared</div><div class="metric-value">${m.prepared || 0}</div></div><div class="card"><div class="muted">Applied+</div><div class="metric-value">${(m.applied||0)+(m.viewed||0)+(m.replied||0)+(m.interview||0)+(m.hired||0)+(m.rejected||0)}</div></div><div class="card"><div class="muted">Reply rate</div><div class="metric-value">${m.reply_rate || 0}%</div></div><div class="card"><div class="muted">Interview rate</div><div class="metric-value">${m.interview_rate || 0}%</div></div></div><div class="card" style="margin-bottom:16px"><h3>Auto insights</h3>${(m.insights || []).map(x => `<div class="muted">• ${e(x)}</div>`).join('')}</div><div class="section-title"><h3>Applications</h3><span class="pill">Update every response</span></div><div class="grid">${(d.items || []).map(renderApplication).join('') || '<div class="card muted">No applications yet. Use Jobs → Prepare Top 10.</div>'}</div>`; }
function renderApplication(x) { const statuses = ['prepared','applied','viewed','replied','interview','hired','rejected']; return `<div class="card app-card"><div class="actions"><span class="pill">${e(x.status)}</span><span class="pill">Score ${x.score}%</span>${x.follow_up_date ? `<span class="pill">Follow-up ${e(x.follow_up_date)}</span>` : ''}</div><div><strong>${e(x.title)}</strong></div><div class="muted">${e(x.company)} · ${e(x.source)}</div><div class="actions"><a class="btn" href="${x.apply_url}" target="_blank">Open portal</a>${statuses.map(s => `<button class="btn ${s === x.status ? 'good' : 'secondary'}" onclick="updateAppStatus(${x.id},'${s}')">${s}</button>`).join('')}</div>${x.response_date ? `<div class="muted">Response: ${e(x.response_date)}</div>` : ''}${x.rejection_reason ? `<div class="muted">Reason: ${e(x.rejection_reason)}</div>` : ''}<div class="muted">Created: ${e(x.created_at)}</div></div>`; }
async function updateAppStatus(id, status) { const fd = new FormData(); fd.append('status', status); if (status === 'rejected') { const reason = prompt('Rejection reason / note?') || ''; fd.append('rejection_reason', reason); } await fetch(`/api/applications/${USER_ID}/${id}/status`, { method: 'POST', body: fd }); await loadApplications(); await loadDashboard(); await loadAutomation(); renderRM(); }
function renderCoach() { if (!DASH) return; $('#coach').innerHTML = `<div class="two"><div class="card"><h3>Paste resume</h3><form id="resume-paste-form" class="grid"><textarea name="text" placeholder="Paste resume text here"></textarea><button class="btn" type="submit">Analyze pasted text</button></form><form id="resume-upload-form" class="grid" enctype="multipart/form-data" style="margin-top:14px"><input type="file" name="file" accept=".pdf,.docx,.txt"/><button class="btn secondary" type="submit">Upload and analyze</button></form></div><div class="card"><h3>Profile optimizer</h3><form id="profile-save-form" class="grid"><input name="headline" value="${ea(DASH.user.headline || '')}"/><textarea name="summary">${e(DASH.user.summary || '')}</textarea><div>${(DASH.user.skills || []).map(s => `<span class="tag">${e(s)}</span>`).join('')}</div><button class="btn good" type="submit">Save profile</button></form></div></div>`; $('#resume-paste-form').addEventListener('submit', async ev => { ev.preventDefault(); await fetch(`/api/resume/paste/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) }); await afterResumeChanged('Resume analyzed'); }); $('#resume-upload-form').addEventListener('submit', async ev => { ev.preventDefault(); await fetch(`/api/resume/upload/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) }); await afterResumeChanged('Resume uploaded and analyzed'); }); $('#profile-save-form').addEventListener('submit', async ev => { ev.preventDefault(); await fetch(`/api/profile/save/${USER_ID}`, { method: 'POST', body: new FormData(ev.target) }); await loadDashboard(); await loadJobs(); await loadSkills(); await loadAutomation(); alert('Profile saved'); }); }
function renderRM() { if (!DASH) return; const earned = DASH.metrics.total_earned, target = DASH.metrics.today_target, gap = Math.max(target - earned, 0), t = DASH.tracking || {}, f = AUTO?.forecast || {}; $('#rm').innerHTML = `<div class="three"><div class="card"><div class="muted">Daily target</div><div class="metric-value">₹${target}</div></div><div class="card"><div class="muted">Total earned</div><div class="metric-value">₹${earned}</div></div><div class="card"><div class="muted">30-day forecast</div><div class="metric-value">₹${f.projected_30d || 0}</div></div></div><div class="card" style="margin-top:16px"><h3>Automation command</h3><div class="grid"><div class="task"><div><strong>1. Auto-prepare queue</strong><div class="muted">Use Automation → Auto-prepare queue for top-fit jobs.</div></div></div><div class="task"><div><strong>2. Submit prepared applications</strong><div class="muted">Prepared: ${t.prepared || 0}. Move them to applied after portal submission.</div></div></div><div class="task"><div><strong>3. Send due follow-ups</strong><div class="muted">Follow-ups keep old applications alive.</div></div></div></div></div>`; }
