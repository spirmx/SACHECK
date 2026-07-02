const iconPaths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  board: '<path d="M4 4h5v16H4zM15 4h5v9h-5z"/><path d="M15 17h5v3h-5z"/>',
  layers: '<path d="m12 3-9 5 9 5 9-5-9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M16 3v4M8 3v4M3 10h18"/>',
  spark: '<path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z"/><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  arrow: '<path d="M5 12h14M14 7l5 5-5 5"/>',
  bolt: '<path d="m13 2-9 12h8l-1 8 9-12h-8l1-8Z"/>',
  brain: '<path d="M9.5 4.5A3 3 0 0 0 5 7v1a3 3 0 0 0-1 5.8V15a3 3 0 0 0 4 2.8A3 3 0 0 0 12 20V6a3 3 0 0 0-2.5-1.5Z"/><path d="M14.5 4.5A3 3 0 0 1 19 7v1a3 3 0 0 1 1 5.8V15a3 3 0 0 1-4 2.8A3 3 0 0 1 12 20V6a3 3 0 0 1 2.5-1.5Z"/>',
  trend: '<path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
  file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a5 5 0 0 1 10 0v2M16 4a3 3 0 0 1 0 6M17 14a4 4 0 0 1 4 4v2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
};

const svgIcon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`;

const category = {
  Word: { color: '#6aa9ff', letter: 'W' },
  Excel: { color: '#53dda1', letter: 'X' },
  Slide: { color: '#ff9a62', letter: 'P' },
  PDF: { color: '#ff6e7c', letter: 'PDF' },
  Figma: { color: '#c58aff', letter: 'F' },
  Miro: { color: '#f7d266', letter: 'M' },
  Web: { color: '#4de8e1', letter: '</>' },
  Data: { color: '#65c7ff', letter: 'DB' },
  Link: { color: '#f26bb5', letter: '↗' },
};

let tasks = [
  { id: 1, title: 'สรุป Requirement ระบบ Claims', type: 'Word', status: 'waiting', due: 'Today, 14:00', note: 'รวบรวม scope จากทีม BA และ stakeholder', progress: 15, members: ['HT','PM'], priority: 96 },
  { id: 2, title: 'วิเคราะห์ Renewal Conversion', type: 'Excel', status: 'waiting', due: 'Tomorrow', note: 'เทียบ cohort Q1 และ Q2 พร้อม insight', progress: 5, members: ['HT'], priority: 89 },
  { id: 3, title: 'Customer Journey — Motor', type: 'Miro', status: 'waiting', due: '03 Jul', note: 'Map pain point จาก quotation ถึง issued', progress: 20, members: ['UX','BA'], priority: 84 },
  { id: 4, title: 'Redesign Agent Dashboard', type: 'Figma', status: 'doing', due: 'Today, 17:30', note: 'High fidelity + interactive prototype', progress: 68, members: ['HT','UX','FE'], priority: 98 },
  { id: 5, title: 'Pricing API Integration', type: 'Web', status: 'doing', due: '04 Jul', note: 'เชื่อม pricing response และ error states', progress: 54, members: ['FE','BE'], priority: 91 },
  { id: 6, title: 'Executive Monthly Report', type: 'Slide', status: 'doing', due: '05 Jul', note: 'KPI, trend และ strategic recommendation', progress: 42, members: ['HT','PM'], priority: 87 },
  { id: 7, title: 'Policy Wording Review', type: 'PDF', status: 'done', due: '30 Jun', note: 'Reviewed และส่ง Legal เรียบร้อย', progress: 100, members: ['LG'], priority: 72 },
  { id: 8, title: 'Lead Source Data Cleanup', type: 'Data', status: 'done', due: '29 Jun', note: 'Normalize source และ campaign mapping', progress: 100, members: ['DA','HT'], priority: 70 },
  { id: 9, title: 'Sales Script V3', type: 'Word', status: 'done', due: '28 Jun', note: 'Final version พร้อม objection handling', progress: 100, members: ['SA'], priority: 66 },
];

function createScaleMock(seed, targetSize = 1250) {
  const titles = [
    'Policy migration review', 'Agent onboarding flow', 'Claims exception audit',
    'Renewal cohort analysis', 'Quotation UX improvement', 'Commission reconciliation',
    'Customer feedback synthesis', 'Campaign performance report', 'Pricing rule validation',
    'Sales journey optimization', 'Partner API mapping', 'Executive insight brief',
  ];
  const notes = [
    'ตรวจข้อมูลและสรุปประเด็นที่ต้องตัดสินใจ', 'จัดโครงสร้างพร้อม next action สำหรับทีม',
    'วิเคราะห์ผลกระทบ ความเสี่ยง และ dependency', 'เตรียม prototype พร้อม validation checklist',
  ];
  const types = Object.keys(category).filter(type => type !== 'Link');
  const dueDates = ['Today, 16:00', 'Tomorrow', '03 Jul', '05 Jul', '08 Jul', '12 Jul', 'No deadline'];
  const owners = [['HT'], ['BA','HT'], ['UX'], ['DA','PM'], ['FE','BE'], ['SA']];
  const output = [...seed];
  for (let index = output.length; index < targetSize; index += 1) {
    const band = index % 10;
    const status = band < 4 ? 'waiting' : band < 8 ? 'doing' : 'done';
    const type = types[(index * 7) % types.length];
    const progress = status === 'done' ? 100 : status === 'doing' ? 30 + ((index * 13) % 61) : (index * 5) % 24;
    output.push({
      id: 10000 + index,
      title: `${titles[index % titles.length]} #${String(index + 1).padStart(4, '0')}`,
      type,
      status,
      due: dueDates[(index * 3) % dueDates.length],
      note: notes[index % notes.length],
      progress,
      members: owners[index % owners.length],
      priority: 40 + ((index * 37) % 60),
    });
  }
  return output;
}

tasks = createScaleMock(tasks);

const templates = [
  { id: 1, title: 'Business Requirement Document', type: 'Word', description: 'BRD structure พร้อม scope, flow และ acceptance criteria', used: 32 },
  { id: 2, title: 'Monthly Performance Model', type: 'Excel', description: 'KPI dashboard, variance และ automated summary', used: 48 },
  { id: 3, title: 'Executive Storytelling Deck', type: 'Slide', description: 'Deck สำหรับผู้บริหาร เน้น insight และ decision', used: 21 },
  { id: 4, title: 'UX Discovery Board', type: 'Miro', description: 'Persona, journey, pain point และ opportunity map', used: 17 },
  { id: 5, title: 'Product UI Starter Kit', type: 'Figma', description: 'Component, token และ responsive foundation', used: 39 },
  { id: 6, title: 'Analysis Notebook', type: 'Data', description: 'Structure สำหรับ exploratory data analysis', used: 14 },
];

let events = [
  { id: 1, date: '2026-07-01', time: '09:30', title: 'Daily Product Sync', type: 'Meeting', color: '#5b8cff' },
  { id: 2, date: '2026-07-01', time: '14:00', title: 'Claims Requirement Review', type: 'Deadline', color: '#ff6e7c' },
  { id: 3, date: '2026-07-03', time: '10:30', title: 'UX Critique', type: 'Meeting', color: '#9b7cff' },
  { id: 4, date: '2026-07-06', time: '16:00', title: 'Sprint Planning', type: 'Meeting', color: '#4de8e1' },
  { id: 5, date: '2026-07-08', time: '11:00', title: 'Pricing API Demo', type: 'Milestone', color: '#53dda1' },
  { id: 6, date: '2026-07-15', time: '09:00', title: 'Monthly Report Due', type: 'Deadline', color: '#ff9a62' },
];

const state = {
  screen: 'overview',
  boardFilter: 'All',
  boardSearch: '',
  boardSort: 'priority',
  boardLimits: { waiting: 18, doing: 18, done: 18 },
  templateFilter: 'All',
  selectedDate: '2026-07-01',
  commandIndex: 0,
};
const screenTitles = { overview: 'Command Center', board: 'Work Board', templates: 'Template Library', calendar: 'Calendar', intelligence: 'Intelligence' };
const statusMeta = {
  waiting: { label: 'Waiting', subtitle: 'Ready to start', color: '#5b8cff' },
  doing: { label: 'Doing', subtitle: 'In active motion', color: '#ffae66' },
  done: { label: 'Success', subtitle: 'Completed work', color: '#53dda1' },
};

const host = document.querySelector('#screenHost');
const commandBackdrop = document.querySelector('#commandBackdrop');
const commandInput = document.querySelector('#commandInput');
const commandResults = document.querySelector('#commandResults');
const modalBackdrop = document.querySelector('#modalBackdrop');
const modalCard = document.querySelector('#modalCard');
const numberFormat = new Intl.NumberFormat('en-US');
const formatCount = value => numberFormat.format(value);

function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = svgIcon(el.dataset.icon); });
}

function metricCard(label, value, icon, accent, trend, progress) {
  return `<article class="metric-card glass" style="--accent:${accent}">
    <div class="metric-top"><span>${label}</span><span class="nav-icon">${svgIcon(icon)}</span></div>
    <div class="metric-main"><strong>${value}</strong><span class="trend">${trend}</span></div>
    <div class="microbar"><i style="--value:${progress}%"></i></div>
  </article>`;
}

function miniTask(task) {
  return `<div class="mini-task" style="--type:${category[task.type]?.color || '#8da3b8'}" data-task-id="${task.id}">
    <strong>${task.title}</strong><small>${task.type} · ${task.due}</small>
  </div>`;
}

function renderOverview() {
  const counts = Object.fromEntries(['waiting','doing','done'].map(s => [s, tasks.filter(t => t.status === s).length]));
  const completion = Math.round(counts.done / tasks.length * 100);
  const top = [...tasks].filter(t => t.status !== 'done').sort((a,b) => b.priority - a.priority).slice(0,3);
  host.innerHTML = `<div class="screen overview-screen stagger">
    <div class="hero-grid" style="--i:0">
      <section class="hero glass">
        <span class="eyebrow"><i></i> LIVE WORKSPACE · WEDNESDAY, 01 JULY</span>
        <h2>สวัสดี Hoyturbro,<br><span>วันนี้พร้อมสร้างอะไรที่ดีขึ้น?</span></h2>
        <p>SA Intelligence จัดลำดับงานจาก deadline, impact และ momentum แล้ว งานที่ควรโฟกัสที่สุดคือ Agent Dashboard ก่อน 17:30 น.</p>
        <div class="hero-actions"><button class="secondary-btn" data-go="board">เปิด Focus Board ${svgIcon('arrow')}</button><button class="ghost-btn" data-open-command>ถาม SA Intelligence</button></div>
        <div class="live-strip">${[12,18,9,24,15,29,19,25,11,21,16,27].map((_,i)=>`<i style="--n:${i}"></i>`).join('')}</div>
      </section>
      <aside class="brief-card glass">
        <div class="brief-head"><div><span class="eyebrow">INTELLIGENCE BRIEF</span><br><strong>Workspace momentum</strong></div><div class="ai-orb">✦</div></div>
        <div class="brief-score"><strong>87</strong><small>▲ 12% this week</small></div>
        <p>จังหวะงานอยู่ในระดับดีมาก แต่มี 2 งานที่ deadline ชนกันช่วงบ่าย แนะนำล็อก focus block 13:00–15:00</p>
        <div class="signal-list">
          <div class="signal" style="--signal:var(--green)"><i></i><span>Flow efficiency</span><b>92%</b></div>
          <div class="signal" style="--signal:var(--orange)"><i></i><span>Deadline pressure</span><b>Medium</b></div>
          <div class="signal" style="--signal:var(--violet)"><i></i><span>Creative energy</span><b>High</b></div>
        </div>
      </aside>
    </div>

    <div class="metric-grid" style="--i:1">
      ${metricCard('TOTAL WORK', formatCount(tasks.length), 'folder', '#65c7ff', 'large workspace', 78)}
      ${metricCard('WAITING', formatCount(counts.waiting), 'clock', '#5b8cff', `${tasks.filter(t=>t.status==='waiting'&&t.priority>=90).length} high priority`, 46)}
      ${metricCard('IN MOTION', formatCount(counts.doing), 'bolt', '#ff9a62', '+18% velocity', 68)}
      ${metricCard('COMPLETION', completion + '%', 'check', '#53dda1', '+12% vs last week', completion)}
    </div>

    <div class="overview-lower" style="--i:2">
      <section class="flow-panel glass">
        <div class="section-label"><div><h2>Work Flow</h2><p>Live snapshot across every status</p></div><button data-go="board">View full board →</button></div>
        <div class="mini-board">
          ${['waiting','doing','done'].map(status => `<div class="mini-column" style="--column:${statusMeta[status].color}"><div class="mini-column-head"><span>${statusMeta[status].label}</span><b>${counts[status]}</b></div>${tasks.filter(t=>t.status===status).slice(0,2).map(miniTask).join('')}</div>`).join('')}
        </div>
      </section>
      <aside class="focus-panel glass">
        <div class="section-label"><div><h2>Focus Queue</h2><p>Ranked by SA Intelligence</p></div><button data-go="intelligence">Why? →</button></div>
        <div class="focus-list">${top.map((t,i)=>`<div class="focus-item" style="--rank:${i===0?'#ff6e7c':i===1?'#ff9a62':'#5b8cff'}"><span class="focus-rank">0${i+1}</span><div><strong>${t.title}</strong><small>${t.type} · ${t.due}</small></div><b>${t.priority}</b></div>`).join('')}</div>
      </aside>
    </div>
  </div>`;
  wireCommonActions();
}

function taskCard(task) {
  const c = category[task.type] || { color:'#8da3b8' };
  return `<article class="task-card" draggable="true" data-task-id="${task.id}" style="--type:${c.color};--column:${statusMeta[task.status].color}">
    <span class="task-glow"></span>
    <div class="task-top"><span class="task-type">${task.type}</span><button class="task-menu" aria-label="Task options">•••</button></div>
    <h3>${task.title}</h3><p>${task.note}</p>
    <div class="task-progress"><i style="--progress:${task.progress}%"></i></div>
    <div class="task-meta"><span class="task-date ${task.due.includes('Today')?'urgent':''}">${svgIcon('clock')} ${task.due}</span><span class="member-stack">${task.members.map((m,i)=>`<span style="--avatar:${['#5b8cff','#9b7cff','#f26bb5'][i%3]}">${m}</span>`).join('')}</span></div>
  </article>`;
}

function resetBoardLimits() {
  state.boardLimits = { waiting: 18, doing: 18, done: 18 };
}

function sortBoardTasks(list) {
  const copy = [...list];
  if (state.boardSort === 'name') return copy.sort((a, b) => a.title.localeCompare(b.title));
  if (state.boardSort === 'type') return copy.sort((a, b) => a.type.localeCompare(b.type) || b.priority - a.priority);
  return copy.sort((a, b) => b.priority - a.priority || a.title.localeCompare(b.title));
}

function renderBoard() {
  const types = ['All', ...new Set(tasks.map(t=>t.type))];
  const query = state.boardSearch.trim().toLocaleLowerCase();
  const filteredByType = state.boardFilter === 'All' ? tasks : tasks.filter(t=>t.type === state.boardFilter);
  const visible = sortBoardTasks(query
    ? filteredByType.filter(t => `${t.title} ${t.type} ${t.note} ${t.due} ${t.status}`.toLocaleLowerCase().includes(query))
    : filteredByType);
  const renderedCount = ['waiting','doing','done'].reduce((total, status) => total + Math.min(state.boardLimits[status], visible.filter(t=>t.status===status).length), 0);
  host.innerHTML = `<div class="screen board-screen stagger">
    <div class="board-toolbar" style="--i:0">
      <div class="board-toolbar-head"><div class="section-label"><div><h2>Visual Work Board</h2><p>ออกแบบสำหรับ 1,000+ งาน · aggregate ทั้งหมด แต่ render เท่าที่จำเป็น</p></div></div><div class="scale-badge"><i></i><strong>${formatCount(tasks.length)}</strong><span>indexed</span><b>${renderedCount} rendered</b></div><button class="primary-btn" data-quick-add>＋ New work</button></div>
      <div class="board-control-row">
        <form class="board-search" id="boardSearchForm"><span>${svgIcon('search')}</span><input name="query" value="${state.boardSearch.replaceAll('"','&quot;')}" placeholder="Search across ${formatCount(tasks.length)} tasks..."><button type="submit">Search</button></form>
        <label class="sort-control"><span>Sort</span><select id="boardSort"><option value="priority" ${state.boardSort==='priority'?'selected':''}>Smart priority</option><option value="name" ${state.boardSort==='name'?'selected':''}>Name</option><option value="type" ${state.boardSort==='type'?'selected':''}>Type</option></select></label>
        ${state.boardSearch ? '<button class="filter-pill" data-clear-search>Clear search</button>' : ''}
      </div>
      <div class="filter-pills board-type-filters">${types.map(t=>`<button class="filter-pill ${state.boardFilter===t?'active':''}" data-board-filter="${t}">${t}</button>`).join('')}</div>
      <div class="result-summary"><span>${formatCount(visible.length)} matching work items</span><small>คอลัมน์เลื่อนแยกกันเพื่อคงความเร็วและตำแหน่งการทำงาน</small></div>
    </div>
    <div class="kanban" style="--i:1">${['waiting','doing','done'].map(status => {
      const allInStatus = visible.filter(t=>t.status===status);
      const list = allInStatus.slice(0, state.boardLimits[status]);
      return `<section class="kanban-column" data-status="${status}" style="--column:${statusMeta[status].color}">
        <header class="kanban-head"><div class="kanban-title"><i></i><div><strong>${statusMeta[status].label}</strong><small>${statusMeta[status].subtitle}</small></div></div><b>${formatCount(allInStatus.length)}</b></header>
        <div class="task-stack">${list.map(taskCard).join('') || '<div class="empty-drop">Drop work here</div>'}</div>
        <footer class="column-footer"><span>Showing ${formatCount(list.length)} of ${formatCount(allInStatus.length)}</span>${list.length < allInStatus.length ? `<button data-load-more="${status}">Load 18 more ↓</button>` : '<b>All loaded ✓</b>'}</footer>
      </section>`;
    }).join('')}</div>
  </div>`;
  host.querySelectorAll('[data-board-filter]').forEach(btn => btn.addEventListener('click', () => { state.boardFilter = btn.dataset.boardFilter; resetBoardLimits(); renderBoard(); }));
  host.querySelector('[data-quick-add]').addEventListener('click', openQuickAdd);
  host.querySelector('#boardSearchForm').addEventListener('submit', event => { event.preventDefault(); state.boardSearch = new FormData(event.currentTarget).get('query') || ''; resetBoardLimits(); renderBoard(); });
  host.querySelector('#boardSort').addEventListener('change', event => { state.boardSort = event.currentTarget.value; resetBoardLimits(); renderBoard(); });
  host.querySelector('[data-clear-search]')?.addEventListener('click', () => { state.boardSearch = ''; resetBoardLimits(); renderBoard(); });
  host.querySelectorAll('[data-load-more]').forEach(btn => btn.addEventListener('click', () => { state.boardLimits[btn.dataset.loadMore] += 18; renderBoard(); }));
  wireDragDrop();
}

function wireDragDrop() {
  host.querySelectorAll('.task-card').forEach(card => {
    card.addEventListener('dragstart', e => { card.classList.add('dragging'); e.dataTransfer.setData('text/plain', card.dataset.taskId); });
    card.addEventListener('dragend', () => card.classList.remove('dragging'));
  });
  host.querySelectorAll('.kanban-column').forEach(col => {
    col.addEventListener('dragover', e => { e.preventDefault(); col.classList.add('drag-over'); });
    col.addEventListener('dragleave', () => col.classList.remove('drag-over'));
    col.addEventListener('drop', e => {
      e.preventDefault(); col.classList.remove('drag-over');
      const task = tasks.find(t => t.id === Number(e.dataTransfer.getData('text/plain')));
      if (!task || task.status === col.dataset.status) return;
      const previous = task.status; task.status = col.dataset.status;
      task.progress = task.status === 'done' ? 100 : task.status === 'doing' ? Math.max(35, task.progress) : Math.min(20, task.progress);
      renderBoard();
      toast(`${task.title}`, `${statusMeta[previous].label} → ${statusMeta[task.status].label}`);
      if (task.status === 'done') launchConfetti();
    });
  });
}

function renderTemplates() {
  const filters = ['All', ...new Set(templates.map(t=>t.type))];
  const visible = state.templateFilter === 'All' ? templates : templates.filter(t=>t.type===state.templateFilter);
  host.innerHTML = `<div class="screen template-screen stagger">
    <div class="template-toolbar" style="--i:0"><div><div class="section-label"><div><h2>Template Library</h2><p>Reusable intelligence — เริ่มงานใหม่โดยไม่เริ่มจากศูนย์</p></div></div><div class="filter-pills">${filters.map(t=>`<button class="filter-pill ${state.templateFilter===t?'active':''}" data-template-filter="${t}">${t}</button>`).join('')}</div></div><button class="secondary-btn" data-template-new>＋ Add Template</button></div>
    <div class="template-grid" style="--i:1">${visible.map(t=>{ const c=category[t.type]; return `<article class="template-card glass" style="--type:${c.color}"><div class="template-visual"><span class="template-letter">${c.letter}</span></div><h3>${t.title}</h3><p>${t.description}</p><div class="template-foot"><small>Used ${t.used} times · ${t.type} / Template</small><button class="use-template" data-use-template="${t.id}">Use template →</button></div></article>`; }).join('')}</div>
  </div>`;
  host.querySelectorAll('[data-template-filter]').forEach(btn => btn.addEventListener('click',()=>{ state.templateFilter=btn.dataset.templateFilter; renderTemplates(); }));
  host.querySelectorAll('[data-use-template]').forEach(btn => btn.addEventListener('click',()=>useTemplate(Number(btn.dataset.useTemplate))));
  host.querySelector('[data-template-new]').addEventListener('click', () => toast('Prototype action', 'ใน Desktop app ปุ่มนี้จะเปิด File Picker / Add Link'));
}

function useTemplate(id) {
  const t = templates.find(x=>x.id===id); if (!t) return;
  tasks.unshift({ id: Date.now(), title: `New ${t.title}`, type:t.type, status:'waiting', due:'No deadline', note:`Created from ${t.title}`, progress:0, members:['HT'], priority:76 });
  t.used += 1;
  toast('Template ready', `สร้างงานใหม่ใน Waiting / ${t.type}`);
  setTimeout(()=>navigate('board'), 450);
}

function calendarDays(year, month) {
  const first = new Date(year, month, 1); const start = new Date(year, month, 1-first.getDay());
  return Array.from({length:42}, (_,i)=>{ const d=new Date(start); d.setDate(start.getDate()+i); return d; });
}

function ymd(date) { return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`; }

function renderCalendar() {
  const days = calendarDays(2026,6);
  const selectedEvents = events.filter(e=>e.date===state.selectedDate).sort((a,b)=>a.time.localeCompare(b.time));
  const selectedObj = new Date(state.selectedDate+'T12:00:00');
  host.innerHTML = `<div class="screen calendar-screen stagger">
    <div class="calendar-toolbar" style="--i:0"><div><span class="eyebrow">WORK RHYTHM</span><h2 style="margin:5px 0 0;font-size:18px">July 2026</h2></div><div class="filter-pills"><button class="filter-pill">‹</button><button class="filter-pill active">Today</button><button class="filter-pill">›</button><button class="secondary-btn" data-add-event>＋ Add Event</button></div></div>
    <div class="calendar-layout" style="--i:1">
      <section class="calendar-card glass"><div class="calendar-weekdays">${['SUN','MON','TUE','WED','THU','FRI','SAT'].map(d=>`<span>${d}</span>`).join('')}</div><div class="calendar-grid">${days.map(d=>{const key=ymd(d), dayEvents=events.filter(e=>e.date===key); return `<button class="calendar-day ${d.getMonth()!==6?'muted':''} ${key==='2026-07-01'?'today':''} ${key===state.selectedDate?'selected':''}" data-date="${key}"><span class="day-number">${d.getDate()}</span>${dayEvents.slice(0,2).map(e=>`<span class="event-dot" style="--event:${e.color}">${e.time} ${e.title}</span>`).join('')}</button>`;}).join('')}</div></section>
      <aside class="agenda-panel glass"><span class="agenda-date">${selectedObj.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'})}</span><h3>Day agenda</h3><div class="timeline">${selectedEvents.length?selectedEvents.map(e=>`<div class="timeline-item"><time>${e.time}</time><div class="agenda-event" style="--event:${e.color}"><strong>${e.title}</strong><small>${e.type}</small></div></div>`).join(''):'<p style="color:var(--muted);font-size:9px">วันนี้ยังว่าง — เหมาะกับ focus block</p>'}</div></aside>
    </div>
  </div>`;
  host.querySelectorAll('[data-date]').forEach(btn=>btn.addEventListener('click',()=>{state.selectedDate=btn.dataset.date;renderCalendar();}));
  host.querySelector('[data-add-event]').addEventListener('click', openEventModal);
}

function renderIntelligence() {
  host.innerHTML = `<div class="screen intelligence-screen stagger">
    <div class="section-label" style="--i:0"><div><span class="eyebrow"><i></i> CONTEXT ENGINE ONLINE</span><h2 style="font-size:20px;margin-top:7px">SA Intelligence</h2><p>ระบบวิเคราะห์งานจาก priority, deadline, context และพฤติกรรมการทำงาน</p></div><button data-open-command>Ask anything →</button></div>
    <div class="intel-grid" style="--i:1">
      <section class="intel-card large glass"><div class="intel-head"><strong>Workload radar</strong><span>● LIVE MODEL</span></div><div class="radar-wrap"><div class="radar"><i class="radar-sweep"></i><i class="radar-dot" style="--x:66%;--y:29%;--dot:#ff6e7c"></i><i class="radar-dot" style="--x:31%;--y:62%;--dot:#4de8e1"></i><i class="radar-dot" style="--x:58%;--y:72%;--dot:#9b7cff"></i><i class="radar-dot" style="--x:42%;--y:37%;--dot:#f7d266"></i></div></div><p style="color:var(--muted);font-size:9px;line-height:1.8">จุดสีแดงคือ deadline pressure ของ Agent Dashboard ส่วนจุดม่วงคือ creative workload ที่กำลังเพิ่มขึ้น ระบบแนะนำลด context switching ช่วงบ่าย</p></section>
      <section class="intel-card glass"><div class="intel-head"><strong>Smart predictions</strong><span>87% confidence</span></div><div class="prediction-list">
        <div class="prediction" style="--p:#ff6e7c"><span class="prediction-icon">${svgIcon('bolt')}</span><div><strong>Deadline collision</strong><small>2 งานอาจชนกันช่วง 14:00–17:30</small></div><b>HIGH</b></div>
        <div class="prediction" style="--p:#53dda1"><span class="prediction-icon">${svgIcon('trend')}</span><div><strong>Flow opportunity</strong><small>จัดกลุ่ม Figma + Miro ลดเวลาได้ 24 นาที</small></div><b>+18%</b></div>
        <div class="prediction" style="--p:#9b7cff"><span class="prediction-icon">${svgIcon('brain')}</span><div><strong>Best focus window</strong><small>พลังสร้างสรรค์สูงสุด 13:10–15:20</small></div><b>NOW</b></div>
      </div></section>
      <section class="intel-card glass"><div class="intel-head"><strong>7-day velocity</strong><span>+12.4%</span></div><div class="activity-chart">${[42,66,54,82,70,91,76].map((h,i)=>`<i class="chart-bar" style="--h:${h}%"><span>${['M','T','W','T','F','S','S'][i]}</span></i>`).join('')}</div></section>
    </div>
  </div>`;
  wireCommonActions();
}

function renderScreen() {
  ({overview:renderOverview, board:renderBoard, templates:renderTemplates, calendar:renderCalendar, intelligence:renderIntelligence}[state.screen] || renderOverview)();
}

function navigate(screen) {
  state.screen = screen;
  document.querySelectorAll('.nav-item').forEach(btn=>btn.classList.toggle('active',btn.dataset.screen===screen));
  document.querySelector('#pageTitle').textContent = screenTitles[screen];
  document.querySelector('#breadcrumb').textContent = screenTitles[screen].toUpperCase();
  document.querySelector('#sidebar').classList.remove('open');
  renderScreen();
  document.querySelector('.screen-host').scrollTop = 0;
}

function wireCommonActions() {
  host.querySelectorAll('[data-go]').forEach(btn=>btn.addEventListener('click',()=>navigate(btn.dataset.go)));
  host.querySelectorAll('[data-open-command]').forEach(btn=>btn.addEventListener('click',openCommand));
}

function modal(content) { modalCard.innerHTML=content; modalBackdrop.hidden=false; modalCard.querySelectorAll('[data-close-modal]').forEach(b=>b.addEventListener('click',closeModal)); }
function closeModal() { modalBackdrop.hidden=true; modalCard.innerHTML=''; }

function openQuickAdd() {
  modal(`<div class="modal-head"><div><h2>Create new work</h2><p>เพิ่มงานลง Waiting แล้วจัดลำดับด้วย SA Intelligence</p></div><button class="modal-close" data-close-modal>×</button></div>
    <form id="quickAddForm"><div class="form-grid">
      <div class="field full"><label>WORK TITLE</label><input name="title" required placeholder="เช่น วิเคราะห์ Renewal Conversion" autofocus></div>
      <div class="field"><label>TYPE</label><select name="type">${Object.keys(category).map(t=>`<option>${t}</option>`).join('')}</select></div>
      <div class="field"><label>DEADLINE</label><input name="due" value="Tomorrow"></div>
      <div class="field full"><label>CONTEXT / NOTE</label><textarea name="note" placeholder="รายละเอียดที่ช่วยให้ระบบเข้าใจงาน..."></textarea></div>
    </div><div class="modal-actions"><button type="button" class="ghost-btn" data-close-modal>Cancel</button><button class="primary-btn" type="submit">Create smart work</button></div></form>`);
  modalCard.querySelector('#quickAddForm').addEventListener('submit',e=>{e.preventDefault();const d=new FormData(e.currentTarget);tasks.unshift({id:Date.now(),title:d.get('title'),type:d.get('type'),status:'waiting',due:d.get('due')||'No deadline',note:d.get('note')||'New work item',progress:0,members:['HT'],priority:78});closeModal();toast('Work created',`${d.get('title')} อยู่ใน Waiting แล้ว`);navigate('board');});
}

function openEventModal() {
  modal(`<div class="modal-head"><div><h2>Add calendar event</h2><p>สร้าง event เพื่อเห็น workload และ reminder ใน timeline</p></div><button class="modal-close" data-close-modal>×</button></div>
    <form id="eventForm"><div class="form-grid">
      <div class="field full"><label>EVENT NAME</label><input name="title" required placeholder="Event name"></div>
      <div class="field"><label>DATE</label><input type="date" name="date" value="${state.selectedDate}" required></div>
      <div class="field"><label>TIME</label><input type="time" name="time" value="09:00" required></div>
      <div class="field"><label>TYPE</label><select name="type"><option>Meeting</option><option>Deadline</option><option>Milestone</option><option>Focus block</option></select></div>
      <div class="field"><label>COLOR</label><select name="color"><option value="#5b8cff">Blue</option><option value="#9b7cff">Violet</option><option value="#53dda1">Green</option><option value="#ff6e7c">Red</option><option value="#ff9a62">Orange</option></select></div>
    </div><div class="modal-actions"><button type="button" class="ghost-btn" data-close-modal>Cancel</button><button class="primary-btn" type="submit">Save event</button></div></form>`);
  modalCard.querySelector('#eventForm').addEventListener('submit',e=>{e.preventDefault();const d=new FormData(e.currentTarget);events.push({id:Date.now(),title:d.get('title'),date:d.get('date'),time:d.get('time'),type:d.get('type'),color:d.get('color')});state.selectedDate=d.get('date');closeModal();toast('Event saved',`${d.get('time')} · ${d.get('title')}`);renderCalendar();});
}

function commandItems(query='') {
  const q=query.toLowerCase().trim();
  const nav = Object.entries(screenTitles).map(([screen,title])=>({title:`เปิด ${title}`,subtitle:'Navigate',icon:screen==='intelligence'?'spark':screen==='calendar'?'calendar':'grid',color:'#4de8e1',action:()=>navigate(screen)}));
  const taskItems = tasks.filter(t=>!q || `${t.title} ${t.type} ${t.status} ${t.note}`.toLowerCase().includes(q.replace('งานด่วน','today').replace('กำลังทำ','doing'))).slice(0,6).map(t=>({title:t.title,subtitle:`${statusMeta[t.status].label} · ${t.type} · ${t.due}`,icon:'file',color:category[t.type]?.color||'#8da3b8',action:()=>{state.boardFilter=t.type;navigate('board');toast('Smart filter',`แสดงงานประเภท ${t.type}`);}}));
  const actions = [
    {title:'สร้างงานใหม่',subtitle:'Quick action',icon:'plus',color:'#53dda1',action:openQuickAdd},
    {title:'สรุปงานที่ควรโฟกัส',subtitle:'Ask SA Intelligence',icon:'brain',color:'#9b7cff',action:()=>{navigate('intelligence');toast('Briefing ready','วิเคราะห์ workload ล่าสุดแล้ว');}},
  ];
  if (!q) return [...actions,...nav.slice(0,5),...taskItems.slice(0,3)];
  const navMatches=nav.filter(x=>`${x.title} ${x.subtitle}`.toLowerCase().includes(q));
  return [...taskItems,...navMatches,...actions.filter(x=>x.title.includes(query))].slice(0,9);
}

function renderCommands() {
  const items=commandItems(commandInput.value); state.commandIndex=Math.min(state.commandIndex,Math.max(0,items.length-1));
  commandResults.innerHTML=items.length?items.map((x,i)=>`<button class="command-result ${i===state.commandIndex?'selected':''}" data-command-index="${i}" style="--result:${x.color}"><span class="command-result-icon">${svgIcon(x.icon)}</span><span><strong>${x.title}</strong><small>${x.subtitle}</small></span><em>↵</em></button>`).join(''):'<div style="padding:35px;text-align:center;color:var(--muted);font-size:9px">ไม่พบผลลัพธ์ ลองค้นด้วยชื่อ ประเภท หรือสถานะงาน</div>';
  commandResults.querySelectorAll('[data-command-index]').forEach(btn=>btn.addEventListener('click',()=>executeCommand(items[Number(btn.dataset.commandIndex)])));
}

function executeCommand(item) { if(!item)return; closeCommand(); item.action(); }
function openCommand() { commandBackdrop.hidden=false; commandInput.value='';state.commandIndex=0;renderCommands();setTimeout(()=>commandInput.focus(),50); }
function closeCommand() { commandBackdrop.hidden=true; }

function toast(title, message) {
  const el=document.createElement('div');el.className='toast';el.innerHTML=`<i>✓</i><div><strong>${title}</strong><small>${message}</small></div>`;document.querySelector('#toastStack').appendChild(el);setTimeout(()=>{el.style.opacity='0';el.style.transform='translateX(25px)';setTimeout(()=>el.remove(),250)},3200);
}

function launchConfetti() {
  const layer=document.querySelector('#confettiLayer'); const colors=['#4de8e1','#5b8cff','#9b7cff','#f26bb5','#f7d266','#53dda1'];
  for(let i=0;i<60;i++){const p=document.createElement('i');p.className='confetti';p.style.cssText=`left:${45+Math.random()*10}%;top:${35+Math.random()*8}%;--c:${colors[i%colors.length]};--tx:${(Math.random()-.5)*700}px;--ty:${200+Math.random()*500}px;--r:${Math.random()*900}deg;animation-delay:${Math.random()*.15}s`;layer.appendChild(p);setTimeout(()=>p.remove(),1800);}
}

function showNotifications() {
  const panel=document.querySelector('#notificationPanel'); panel.hidden=!panel.hidden;
  panel.innerHTML=`<h3>Notifications</h3><div class="notice" style="--n:#ff6e7c"><span class="notice-icon">${svgIcon('clock')}</span><div><strong>Deadline in 4 hours</strong><small>Claims Requirement Review · 14:00</small></div></div><div class="notice" style="--n:#9b7cff"><span class="notice-icon">${svgIcon('spark')}</span><div><strong>Focus window detected</strong><small>Best creative block starts 13:10</small></div></div><div class="notice" style="--n:#53dda1"><span class="notice-icon">${svgIcon('check')}</span><div><strong>Weekly momentum +12%</strong><small>You completed 3 high-impact tasks</small></div></div>`;
}

document.querySelectorAll('[data-screen]').forEach(btn=>btn.addEventListener('click',()=>navigate(btn.dataset.screen)));
document.querySelector('#quickAddBtn').addEventListener('click',openQuickAdd);
document.querySelector('#searchTrigger').addEventListener('click',openCommand);
document.querySelector('#briefingBtn').addEventListener('click',()=>navigate('intelligence'));
document.querySelector('#notificationBtn').addEventListener('click',showNotifications);
document.querySelector('#menuToggle').addEventListener('click',()=>document.querySelector('#sidebar').classList.toggle('open'));
modalBackdrop.addEventListener('click',e=>{if(e.target===modalBackdrop)closeModal();});
commandBackdrop.addEventListener('click',e=>{if(e.target===commandBackdrop)closeCommand();});
commandInput.addEventListener('input',()=>{state.commandIndex=0;renderCommands();});
commandInput.addEventListener('keydown',e=>{const items=commandItems(commandInput.value);if(e.key==='ArrowDown'){e.preventDefault();state.commandIndex=Math.min(items.length-1,state.commandIndex+1);renderCommands();}if(e.key==='ArrowUp'){e.preventDefault();state.commandIndex=Math.max(0,state.commandIndex-1);renderCommands();}if(e.key==='Enter'){e.preventDefault();executeCommand(items[state.commandIndex]);}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand();}if(e.key==='Escape'){closeCommand();closeModal();document.querySelector('#notificationPanel').hidden=true;}});
document.addEventListener('mousemove',e=>{const glow=document.querySelector('#cursorGlow');glow.style.left=e.clientX+'px';glow.style.top=e.clientY+'px';});
document.addEventListener('click',e=>{if(!e.target.closest('#notificationPanel,#notificationBtn'))document.querySelector('#notificationPanel').hidden=true;});

hydrateIcons();
navigate('overview');
setTimeout(()=>toast('SA Intelligence online','Mock workspace พร้อมให้ทดลองแล้ว'),700);
