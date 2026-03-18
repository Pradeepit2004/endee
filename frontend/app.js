const API = 'http://localhost:8000';
let sessionId = localStorage.getItem('ragSessionId') || generateId();
let documents = {};
let activeDocId = null;
let currentTab = 'chat';
let quizAnswers = {};
let currentFlashcards = [];
let currentQuiz = [];
let knowledgeNetwork = null;

localStorage.setItem('ragSessionId', sessionId);
document.getElementById('sessionIdDisplay').textContent = sessionId.substring(0, 12) + '...';

function generateId() {
  return Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
}
function showLoading(text = 'Processing...') {
  document.getElementById('loadingText').textContent = text;
  document.getElementById('loadingOverlay').classList.remove('hidden');
}
function hideLoading() { document.getElementById('loadingOverlay').classList.add('hidden'); }
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = `toast ${type}`; t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 3500);
}
function setProgress(pct, text) {
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressText').textContent = text;
}
async function apiPost(endpoint, body) {
  const res = await fetch(API + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'API error'); }
  return res.json();
}
function escapeHtml(text) {
  return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function toggleSidebar() {
  const s = document.getElementById('sidebar');
  const main = document.querySelector('.main-content');
  
  if (s.style.display !== 'none') {
    s.style.display = 'none';
    main.style.width = '100%';
    main.style.marginLeft = '0';
  } else {
    s.style.display = 'flex';
    main.style.width = 'calc(100% - 260px)';
    main.style.marginLeft = '260px';
  }
}
function showTab(tab) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  if (event && event.target) event.target.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
  document.getElementById('welcomeBanner').classList.add('hidden');
  const tabEl = document.getElementById(`tab-${tab}`);
  if (tabEl) tabEl.classList.remove('hidden');
  const titles = { chat:'💬 AI Chat', mindmap:'🗺️ Mind Map', knowledge:'🕸️ Knowledge Graph', tone:'😊 Tone Analyzer', flashcards:'🃏 Flashcards', quiz:'📝 Quiz Generator', timeline:'📅 Timeline', actions:'✅ Action Items', debate:'🥊 Document Debate', email:'📧 Executive Email', facts:'🔍 Facts vs Opinions', contradictions:'⚠️ Contradictions', multidoc:'📚 Multi-Doc Search' };
  document.getElementById('tabTitle').textContent = titles[tab] || tab;
  currentTab = tab;
  if (tab === 'debate') populateDebateDropdowns();
}
async function uploadPDFs(input) {
  const files = Array.from(input.files);
  if (!files.length) return;
  document.getElementById('uploadProgress').classList.remove('hidden');
  document.getElementById('welcomeBanner').classList.add('hidden');
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    setProgress(((i / files.length) * 100), `Uploading ${file.name}...`);
    try {
      const formData = new FormData();
      formData.append('file', file); formData.append('session_id', sessionId);
      const res = await fetch(`${API}/api/documents/upload`, { method: 'POST', body: formData });
      if (!res.ok) { const err = await res.json().catch(() => ({})); showToast(`Failed: ${file.name} — ${err.detail || 'error'}`, 'error'); continue; }
      const data = await res.json();
      documents[data.doc_id] = { docId: data.doc_id, docName: data.doc_name, totalPages: data.total_pages, wordCount: data.word_count };
      if (!activeDocId) setActiveDoc(data.doc_id);
      renderDocList();
      if (data.suggested_questions && data.suggested_questions.length) showSuggestedQuestions(data.suggested_questions);
      if (data.difficulty) showDifficultyBadge(data.difficulty);
      showTab('chat');
      document.querySelectorAll('.nav-btn')[0].classList.add('active');
      showToast(`✅ ${file.name} uploaded!`, 'success');
    } catch (err) { showToast(`Error: ${err.message}`, 'error'); }
  }
  setProgress(100, 'Done!');
  setTimeout(() => document.getElementById('uploadProgress').classList.add('hidden'), 1500);
  input.value = '';
}
function renderDocList() {
  const list = document.getElementById('docList'); list.innerHTML = '';
  Object.values(documents).forEach(doc => {
    const item = document.createElement('div');
    item.className = `doc-item ${doc.docId === activeDocId ? 'active' : ''}`;
    item.innerHTML = `<div class="doc-item-icon">📄</div><div class="doc-item-info"><div class="doc-item-name" title="${escapeHtml(doc.docName)}">${escapeHtml(doc.docName)}</div><div class="doc-item-meta">${doc.totalPages}p · ${(doc.wordCount||0).toLocaleString()}w</div></div><button class="doc-delete" onclick="deleteDoc('${doc.docId}', event)" title="Remove">×</button>`;
    item.addEventListener('click', () => setActiveDoc(doc.docId));
    list.appendChild(item);
  });
}
function setActiveDoc(docId) { activeDocId = docId; renderDocList(); }
async function deleteDoc(docId, event) {
  event.stopPropagation();
  try {
    await fetch(`${API}/api/documents/${sessionId}/${docId}`, { method: 'DELETE' });
    delete documents[docId];
    if (activeDocId === docId) activeDocId = Object.keys(documents)[0] || null;
    renderDocList(); showToast('Document removed', 'info');
    if (!activeDocId) { document.getElementById('welcomeBanner').classList.remove('hidden'); document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden')); }
  } catch (err) { showToast('Error deleting document', 'error'); }
}
function showSuggestedQuestions(questions) {
  const sq = document.getElementById('suggestedQuestions'); const list = document.getElementById('sqList'); list.innerHTML = '';
  questions.forEach(q => { const btn = document.createElement('button'); btn.className = 'sq-btn'; btn.textContent = q; btn.onclick = () => { document.getElementById('questionInput').value = q; sendQuestion(); }; list.appendChild(btn); });
  sq.classList.remove('hidden');
}
function showDifficultyBadge(diff) {
  const badge = document.getElementById('difficultyBadge');
  badge.className = `difficulty-badge ${diff.color}`;
  badge.textContent = `📊 Reading Level: ${diff.level} (Score: ${diff.score} | Grade ${diff.grade_level} | ${diff.word_count.toLocaleString()} words)`;
  badge.classList.remove('hidden');
}
function handleKeyDown(event) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendQuestion(); } }
function handleMultiDocKeyDown(event) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMultiDocQuestion(); } }
async function sendQuestion() {
  const input = document.getElementById('questionInput'); const question = input.value.trim();
  if (!question) return;
  if (document.getElementById('multiDocMode').checked) { document.getElementById('multidocInput').value = question; input.value = ''; showTab('multidoc'); await sendMultiDocQuestion(); return; }
  if (!activeDocId) { showToast('Please upload a document first', 'error'); return; }
  const tutorMode = document.getElementById('tutorMode').checked; const useWeb = document.getElementById('webSearch').checked;
  input.value = ''; addMessage('user', question); addTypingIndicator();
  try {
    const data = await apiPost('/api/documents/ask', { session_id: sessionId, doc_id: activeDocId, question, doc_name: documents[activeDocId]?.docName || '', use_web: useWeb, tutor_mode: tutorMode });
    removeTypingIndicator(); renderAssistantMessage(data, question);
  } catch (err) { removeTypingIndicator(); addMessage('assistant-error', '❌ ' + err.message); }
}
async function sendMultiDocQuestion() {
  const input = document.getElementById('multidocInput'); const question = input.value.trim();
  if (!question) return;
  const docIds = Object.keys(documents);
  if (docIds.length === 0) { showToast('Please upload documents first', 'error'); return; }
  input.value = ''; addMessageToContainer('multidocMessages', 'user', question); addTypingIndicatorTo('multidocMessages');
  try {
    const data = await apiPost('/api/documents/ask-multi', { session_id: sessionId, doc_ids: docIds, question });
    removeTypingIndicatorFrom('multidocMessages'); renderMultiDocAnswer('multidocMessages', data, question);
  } catch (err) { removeTypingIndicatorFrom('multidocMessages'); addMessageToContainer('multidocMessages', 'assistant-error', '❌ ' + err.message); }
}
function addMessage(role, text) { addMessageToContainer('chatMessages', role, text); }
function addMessageToContainer(containerId, role, text) {
  const container = document.getElementById(containerId); const isUser = role === 'user';
  const div = document.createElement('div'); div.className = `message ${isUser ? 'user' : 'assistant'}`;
  div.innerHTML = `<div class="msg-avatar">${isUser ? '👤' : '🧠'}</div><div class="msg-content"><div class="msg-bubble">${escapeHtml(text)}</div></div>`;
  container.appendChild(div); container.scrollTop = container.scrollHeight;
}
function addTypingIndicator() { addTypingIndicatorTo('chatMessages'); }
function addTypingIndicatorTo(containerId) {
  const container = document.getElementById(containerId); const div = document.createElement('div');
  div.className = 'message assistant'; div.id = `typing-${containerId}`;
  div.innerHTML = `<div class="msg-avatar">🧠</div><div class="msg-content"><div class="msg-bubble" style="display:flex;gap:6px;align-items:center;"><span style="animation:spin 1s linear infinite;display:inline-block;">⟳</span>Thinking...</div></div>`;
  container.appendChild(div); container.scrollTop = container.scrollHeight;
}
function removeTypingIndicator() { removeTypingIndicatorFrom('chatMessages'); }
function removeTypingIndicatorFrom(containerId) { const el = document.getElementById(`typing-${containerId}`); if (el) el.remove(); }
function renderAssistantMessage(data, question) {
  const container = document.getElementById('chatMessages'); const div = document.createElement('div'); div.className = 'message assistant';
  const hc = data.hallucination_check; let hallBadge = '';
  if (hc) { const verdict = hc.verdict||'PARTIAL'; const icons={VERIFIED:'✅',HALLUCINATION:'🚨',PARTIAL:'⚠️'}; const labels={VERIFIED:'Source Verified',HALLUCINATION:'Possible Hallucination',PARTIAL:'Partially Verified'}; const score=hc.confidence_score||0; hallBadge=`<div class="hall-badge ${verdict.toLowerCase()}">${icons[verdict]} ${labels[verdict]} (${score}%)</div>`; }
  const conf = data.confidence||'MEDIUM'; const confBadge = `<span class="conf-badge ${conf}">⚡ ${conf} confidence</span>`;
  let sourcesHtml = '';
  if (data.sources && data.sources.length > 0) { const srcItems = data.sources.slice(0,3).map(s=>`<div class="source-item"><span class="source-page">📄 Page ${s.page}</span> — ${escapeHtml(s.text.substring(0,150))}...</div>`).join(''); sourcesHtml=`<div class="sources-section"><div class="sources-title">📍 Source References</div>${srcItems}</div>`; }
  let webHtml = '';
  if (data.hybrid_data && data.hybrid_data.has_web_data) { const wrs=data.hybrid_data.web_results||[]; const links=wrs.slice(0,3).map(r=>`<div class="source-item">🌐 <a href="${r.link}" target="_blank" style="color:var(--accent2)">${escapeHtml(r.title)}</a></div>`).join(''); webHtml=`<div class="sources-section" style="border-color:rgba(0,212,170,0.3)"><div class="sources-title" style="color:var(--accent2)">🌐 Web Sources</div>${links}</div>`; }
  let followupHtml = '';
  if (data.followup_questions && data.followup_questions.length) { const btns=data.followup_questions.map(q=>`<button class="followup-btn" onclick="askFollowup(this,'${q.replace(/'/g,"\\'")}')">${escapeHtml(q)}</button>`).join(''); followupHtml=`<div class="followup-section"><div class="followup-title">💡 Follow-up questions:</div><div class="followup-btns">${btns}</div></div>`; }
  div.innerHTML=`<div class="msg-avatar">🧠</div><div class="msg-content"><div class="msg-bubble">${escapeHtml(data.answer)}</div><div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">${hallBadge}${confBadge}</div>${sourcesHtml}${webHtml}${followupHtml}</div>`;
  container.appendChild(div); container.scrollTop = container.scrollHeight;
}
function renderMultiDocAnswer(containerId, data, question) {
  const container = document.getElementById(containerId); const div = document.createElement('div'); div.className = 'message assistant';
  let bestDocHtml = data.best_document ? `<div class="best-doc-badge">🏆 Best Match: ${escapeHtml(data.best_document)}</div>` : '';
  let sourcesHtml = '';
  if (data.sources && data.sources.length) { const items=data.sources.slice(0,4).map(s=>{const name=s.metadata&&s.metadata.doc_name?s.metadata.doc_name:s.doc_id; return `<div class="source-item"><span class="source-page">📄 ${escapeHtml(name)}</span> — ${escapeHtml(s.content.substring(0,120))}...</div>`}).join(''); sourcesHtml=`<div class="sources-section"><div class="sources-title">📍 Sources</div>${items}</div>`; }
  let followupHtml = '';
  if (data.followup_questions && data.followup_questions.length) { const btns=data.followup_questions.map(q=>`<button class="followup-btn" onclick="askMultiDocFollowup('${q.replace(/'/g,"\\'")}')">${escapeHtml(q)}</button>`).join(''); followupHtml=`<div class="followup-section"><div class="followup-title">💡 Follow-up:</div><div class="followup-btns">${btns}</div></div>`; }
  div.innerHTML=`<div class="msg-avatar">📚</div><div class="msg-content">${bestDocHtml}<div class="msg-bubble">${escapeHtml(data.answer)}</div>${sourcesHtml}${followupHtml}</div>`;
  container.appendChild(div); container.scrollTop = container.scrollHeight;
}
function askFollowup(btn, question) { document.getElementById('questionInput').value = question; btn.closest('.followup-section').remove(); sendQuestion(); }
function askMultiDocFollowup(question) { document.getElementById('multidocInput').value = question; sendMultiDocQuestion(); }
async function loadMindMap() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Generating mind map...');
  try { const data = await apiPost('/api/analysis/mindmap', {session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderMindMap(data); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderMindMap(data) {
  const container = document.getElementById('mindmapContainer'); const branches=data.branches||[]; const W=900,H=600,cx=W/2,cy=H/2,r=200;
  let svg=`<svg viewBox="0 0 ${W} ${H}" class="mindmap-svg" style="width:100%;max-height:70vh"><defs><radialGradient id="centerGrad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#6c63ff"/><stop offset="100%" stop-color="#9c27b0"/></radialGradient></defs>`;
  branches.forEach((branch,i)=>{
    const angle=(i/branches.length)*2*Math.PI-Math.PI/2; const bx=cx+r*Math.cos(angle); const by=cy+r*Math.sin(angle); const color=branch.color||'#6c63ff';
    svg+=`<line x1="${cx}" y1="${cy}" x2="${bx}" y2="${by}" stroke="${color}" stroke-width="2" stroke-opacity="0.6"/>`;
    const subs=branch.subtopics||[];
    subs.forEach((sub,j)=>{ const subAngle=angle+(j-(subs.length-1)/2)*0.5; const sr=r+110; const sx=cx+sr*Math.cos(subAngle); const sy=cy+sr*Math.sin(subAngle); svg+=`<line x1="${bx}" y1="${by}" x2="${sx}" y2="${sy}" stroke="${color}" stroke-width="1" stroke-opacity="0.3" stroke-dasharray="4"/><ellipse cx="${sx}" cy="${sy}" rx="55" ry="18" fill="rgba(26,29,39,0.9)" stroke="${color}" stroke-width="1" stroke-opacity="0.4"/><text x="${sx}" y="${sy+5}" text-anchor="middle" fill="#8892b0" font-size="9" font-family="system-ui">${escapeHtml(sub.substring(0,18))}</text>`; });
    svg+=`<ellipse cx="${bx}" cy="${by}" rx="65" ry="24" fill="${color}" fill-opacity="0.15" stroke="${color}" stroke-width="1.5"/><text x="${bx}" y="${by+5}" text-anchor="middle" fill="${color}" font-size="11" font-weight="600" font-family="system-ui">${escapeHtml(branch.topic.substring(0,20))}</text>`;
  });
  svg+=`<circle cx="${cx}" cy="${cy}" r="55" fill="url(#centerGrad)"/><text x="${cx}" y="${cy+5}" text-anchor="middle" fill="white" font-size="12" font-weight="700" font-family="system-ui">${escapeHtml((data.center||'Document').substring(0,20))}</text></svg>`;
  container.innerHTML=svg;
}
async function loadKnowledgeGraph() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Building knowledge graph...');
  try { const data = await apiPost('/api/analysis/knowledge-graph',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderKnowledgeGraph(data); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderKnowledgeGraph(data) {
  const container=document.getElementById('knowledgeGraph'); container.innerHTML='<div id="knowledgeGraphCanvas" style="width:100%;height:100%"></div>';
  const typeColors={person:'#ff6b6b',concept:'#6c63ff',place:'#00d4aa',organization:'#ffd93d',default:'#8892b0'};
  const nodes=new vis.DataSet((data.nodes||[]).map(n=>({id:n.id,label:n.label,color:{background:typeColors[n.type]||typeColors.default,border:'#2a2d3e',highlight:{background:'#ffffff',border:'#6c63ff'}},font:{color:'#e8eaf6',size:12},shape:n.type==='person'?'circle':'box',borderWidth:2})));
  const edges=new vis.DataSet((data.edges||[]).map((e,i)=>({id:i,from:e.from,to:e.to,label:e.label,color:{color:'#3a3d5e'},font:{color:'#8892b0',size:10,align:'middle'},arrows:{to:{enabled:true,scaleFactor:0.5}}})));
  const options={nodes:{margin:8,widthConstraint:{maximum:120}},edges:{smooth:{type:'curvedCW',roundness:0.2}},physics:{stabilization:{iterations:150},barnesHut:{gravitationalConstant:-4000}},interaction:{hover:true,dragNodes:true,zoomView:true},height:'100%'};
  if (knowledgeNetwork) knowledgeNetwork.destroy();
  knowledgeNetwork=new vis.Network(document.getElementById('knowledgeGraphCanvas'),{nodes,edges},options);
}
async function loadToneAnalysis() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Analyzing tone...');
  try { const data=await apiPost('/api/analysis/tone',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderToneResults(data); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderToneResults(data) {
  const container=document.getElementById('toneResults'); const sentimentPct=((data.sentiment_score+100)/2); const sentimentColor=data.sentiment_score>20?'var(--success)':data.sentiment_score<-20?'var(--error)':'var(--warning)';
  const emotionColors={joy:'#ffd93d',anger:'#ff6b6b',sadness:'#2196F3',fear:'#9c27b0',surprise:'#00bcd4',trust:'#00d4aa'};
  const emotions=data.emotions||{}; const emotionHtml=Object.entries(emotions).map(([e,v])=>`<div class="emotion-item"><span class="emotion-name">${e.charAt(0).toUpperCase()+e.slice(1)}</span><div class="emotion-bar"><div class="emotion-fill" style="width:${v}%;background:${emotionColors[e]||'#6c63ff'}"></div></div></div>`).join('');
  const chapterTones=(data.chapter_tones||[]).map(ct=>`<div class="chapter-tone-item"><span style="color:var(--text-dim)">Page ${ct.page}</span><span class="chapter-tone-badge">${ct.tone}</span></div>`).join('');
  container.innerHTML=`<div class="tone-card"><div class="tone-card-title">Overall Tone</div><div class="tone-main">${data.overall_tone||'Neutral'}</div><div style="font-size:13px;color:var(--text-dim);line-height:1.5">${data.tone_summary||''}</div></div><div class="tone-card"><div class="tone-card-title">Sentiment Score</div><div class="sentiment-bar-container"><div class="sentiment-label"><span>Negative</span><span>${data.sentiment_score>0?'+':''}${data.sentiment_score}</span><span>Positive</span></div><div class="sentiment-bar"><div class="sentiment-fill" style="width:${sentimentPct}%;background:${sentimentColor}"></div></div></div><div style="margin-top:12px"><div class="sentiment-bar-container"><div class="sentiment-label"><span>Formality</span><span>${data.formality_score}/100</span></div><div class="sentiment-bar"><div class="sentiment-fill" style="width:${data.formality_score}%;background:var(--accent)"></div></div></div></div></div><div class="tone-card"><div class="tone-card-title">Emotion Breakdown</div><div class="emotion-grid">${emotionHtml}</div></div><div class="tone-card"><div class="tone-card-title">Writing Style</div><div style="font-size:14px;line-height:1.6;margin-bottom:12px">${data.writing_style||'—'}</div>${chapterTones?`<div class="tone-card-title" style="margin-top:12px">Tone by Page</div><div class="chapter-tone-list">${chapterTones}</div>`:''}</div>`;
}
async function loadFlashcards() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Generating flashcards...');
  try { const data=await apiPost('/api/analysis/flashcards',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); currentFlashcards=data.flashcards||[]; renderFlashcards(currentFlashcards); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderFlashcards(cards) {
  const container=document.getElementById('flashcardsContainer'); container.innerHTML='';
  if (!cards.length) { container.innerHTML='<div class="placeholder-msg">No flashcards generated</div>'; return; }
  cards.forEach((card,i)=>{ const el=document.createElement('div'); el.className='flashcard'; el.onclick=()=>el.classList.toggle('flipped'); el.innerHTML=`<div class="flashcard-inner"><div class="flashcard-front"><div class="card-label">❓ Question ${i+1}</div><div class="card-text">${escapeHtml(card.question||'')}</div><div class="card-topic">📌 ${escapeHtml(card.topic||'General')}</div><div class="card-flip-hint">Click to reveal answer</div></div><div class="flashcard-back"><div class="card-label">✅ Answer</div><div class="card-text">${escapeHtml(card.answer||'')}</div></div></div>`; container.appendChild(el); });
}
async function exportFlashcards() {
  if (!currentFlashcards.length) { showToast('Generate flashcards first','error'); return; }
  try { const res=await fetch(`${API}/api/analysis/flashcards/export-csv`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({flashcards:currentFlashcards})}); const blob=await res.blob(); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='flashcards.csv'; a.click(); URL.revokeObjectURL(url); showToast('Flashcards exported!','success'); }
  catch(err) { showToast('Export error: '+err.message,'error'); }
}
async function loadQuiz() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Generating quiz...');
  try { const data=await apiPost('/api/analysis/quiz',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); currentQuiz=data.quiz||[]; quizAnswers={}; renderQuiz(currentQuiz); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderQuiz(questions) {
  const container=document.getElementById('quizContainer'); container.innerHTML='';
  if (!questions.length) { container.innerHTML='<div class="placeholder-msg">No quiz generated</div>'; return; }
  questions.forEach((q,qi)=>{ const el=document.createElement('div'); el.className='quiz-question'; el.id=`quiz-q-${qi}`; const optionsHtml=(q.options||[]).map((opt,oi)=>`<button class="quiz-option" onclick="answerQuiz(${qi},${oi})" id="opt-${qi}-${oi}"><strong>${String.fromCharCode(65+oi)}.</strong> ${escapeHtml(opt)}</button>`).join(''); el.innerHTML=`<div class="quiz-question-text"><strong>Q${qi+1}.</strong> ${escapeHtml(q.question||'')}</div><div class="quiz-options">${optionsHtml}</div><div class="quiz-explanation" id="explain-${qi}">💡 ${escapeHtml(q.explanation||'')}</div>`; container.appendChild(el); });
  const scoreBtn=document.createElement('button'); scoreBtn.className='action-btn'; scoreBtn.textContent='📊 Show Final Score'; scoreBtn.onclick=showQuizScore; container.appendChild(scoreBtn);
}
function answerQuiz(qi,selectedOi) {
  const q=currentQuiz[qi]; if(quizAnswers[qi]!==undefined) return; quizAnswers[qi]=selectedOi; const correct=q.correct_index;
  for(let oi=0;oi<(q.options||[]).length;oi++){ const btn=document.getElementById(`opt-${qi}-${oi}`); if(!btn) continue; btn.disabled=true; if(oi===correct) btn.classList.add('correct'); else if(oi===selectedOi) btn.classList.add('wrong'); }
  const exp=document.getElementById(`explain-${qi}`); if(exp) exp.style.display='block';
}
function showQuizScore() {
  const total=currentQuiz.length; const correct=Object.entries(quizAnswers).filter(([qi,oi])=>currentQuiz[parseInt(qi)].correct_index===oi).length;
  const pct=Math.round((correct/total)*100); const emoji=pct>=80?'🏆':pct>=60?'👍':'📚';
  const container=document.getElementById('quizContainer'); const existing=document.getElementById('quizScore'); if(existing) existing.remove();
  const scoreDiv=document.createElement('div'); scoreDiv.id='quizScore'; scoreDiv.className='quiz-score'; scoreDiv.innerHTML=`${emoji} Score: ${correct}/${total} (${pct}%)<br><span style="font-size:14px;font-weight:400;color:var(--text-dim)">${pct>=80?'Excellent!':pct>=60?'Good job!':'Keep studying!'}</span>`; container.insertBefore(scoreDiv,container.firstChild); container.scrollTop=0;
}
async function loadTimeline() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Extracting timeline...');
  try { const data=await apiPost('/api/analysis/timeline',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderTimeline(data.timeline||[]); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderTimeline(items) {
  const container=document.getElementById('timelineContainer');
  if (!items.length) { container.innerHTML='<div class="placeholder-msg">No dates/events found in document</div>'; return; }
  const itemsHtml=items.slice(0,25).map(item=>`<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-date">📅 ${escapeHtml(item.date)}</div><div class="timeline-context">${escapeHtml(item.context)}</div></div>`).join('');
  container.innerHTML=`<div class="timeline-wrapper"><div class="timeline-line"></div>${itemsHtml}</div>`;
}
async function loadActionItems() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Extracting action items...');
  try { const data=await apiPost('/api/analysis/action-items',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderActionItems(data.action_items||[]); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderActionItems(items) {
  const container=document.getElementById('actionItemsContainer');
  if (!items.length) { container.innerHTML='<div class="placeholder-msg">No action items found in document</div>'; return; }
  const header=`<div style="font-size:13px;color:var(--text-dim);margin-bottom:16px">Found ${items.length} action items — check off completed tasks</div>`;
  const itemsHtml=items.map((item,i)=>`<div class="action-item" id="action-${i}"><input type="checkbox" class="action-checkbox" onchange="toggleActionItem(${i})"/><div class="action-text">${escapeHtml(item)}</div></div>`).join('');
  container.innerHTML=header+itemsHtml;
}
function toggleActionItem(i) { const el=document.getElementById(`action-${i}`); if(el) el.classList.toggle('completed'); }
function populateDebateDropdowns() {
  const docs=Object.values(documents); const d1=document.getElementById('debateDoc1'); const d2=document.getElementById('debateDoc2');
  [d1,d2].forEach(sel=>{ const curr=sel.value; sel.innerHTML='<option value="">Select Document</option>'; docs.forEach(doc=>{ const opt=document.createElement('option'); opt.value=doc.docId; opt.textContent=doc.docName; sel.appendChild(opt); }); sel.value=curr; });
}
async function loadDebate() {
  const d1=document.getElementById('debateDoc1').value; const d2=document.getElementById('debateDoc2').value;
  if(!d1||!d2) { showToast('Select both documents','error'); return; } if(d1===d2) { showToast('Select two different documents','error'); return; }
  showLoading('Analyzing debate...');
  try { const data=await apiPost('/api/analysis/debate',{session_id:sessionId,doc_id_1:d1,doc_id_2:d2}); hideLoading(); renderDebateResults(data); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderDebateResults(data) {
  const container=document.getElementById('debateResults'); const isD1Winner=data.winner===data.doc1_name; const isD2Winner=data.winner===data.doc2_name;
  const makeArgList=args=>(args||[]).map(a=>`<div class="argument-item"><span class="argument-bullet">▸</span>${escapeHtml(a)}</div>`).join('');
  const makeStrWeakList=(items,type)=>(items||[]).map(i=>`<div style="font-size:12px;color:${type==='str'?'var(--success)':'var(--error)'};margin-bottom:4px">${type==='str'?'✓':'✗'} ${escapeHtml(i)}</div>`).join('');
  container.innerHTML=`<div class="debate-grid"><div class="debate-doc-card ${isD1Winner?'winner':''}"><div class="debate-doc-title">📄 ${escapeHtml(data.doc1_name||'Document 1')}${isD1Winner?'<span class="winner-badge">🏆 WINNER</span>':''}</div><div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">Arguments:</div>${makeArgList(data.doc1_arguments)}<div style="margin-top:12px">${makeStrWeakList(data.doc1_strengths,'str')}${makeStrWeakList(data.doc1_weaknesses,'weak')}</div></div><div class="debate-vs">⚔️</div><div class="debate-doc-card ${isD2Winner?'winner':''}"><div class="debate-doc-title">📄 ${escapeHtml(data.doc2_name||'Document 2')}${isD2Winner?'<span class="winner-badge">🏆 WINNER</span>':''}</div><div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">Arguments:</div>${makeArgList(data.doc2_arguments)}<div style="margin-top:12px">${makeStrWeakList(data.doc2_strengths,'str')}${makeStrWeakList(data.doc2_weaknesses,'weak')}</div></div></div><div class="debate-summary"><div style="font-size:14px;font-weight:700;margin-bottom:8px">🏆 Winner: ${escapeHtml(data.winner||'TIE')}</div><div style="font-size:13px;color:var(--text-dim);margin-bottom:8px">${escapeHtml(data.winner_reason||'')}</div><div style="font-size:13px;line-height:1.6">${escapeHtml(data.comparison_summary||'')}</div></div>`;
}
async function loadEmail() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Drafting executive email...');
  try { const data=await apiPost('/api/analysis/executive-email',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderEmail(data); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderEmail(data) {
  document.getElementById('emailContainer').innerHTML=`<div class="email-card"><div class="email-header"><div class="email-field"><span class="email-field-label">To:</span><span class="email-field-value">${escapeHtml(data.to||'recipient@company.com')}</span></div><div class="email-field"><span class="email-field-label">Subject:</span><span class="email-field-value"><strong>${escapeHtml(data.subject||'')}</strong></span></div></div><div class="email-body">${escapeHtml(data.body||'')}</div><button class="copy-btn" onclick="copyEmail()">📋 Copy Email</button></div>`;
  window._emailData=data;
}
function copyEmail() { if(!window._emailData) return; const text=`To: ${window._emailData.to}\nSubject: ${window._emailData.subject}\n\n${window._emailData.body}`; navigator.clipboard.writeText(text).then(()=>showToast('Email copied!','success')); }
async function loadFactsOpinions() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Analyzing facts and opinions...');
  try { const data=await apiPost('/api/analysis/facts-opinions',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderFactsOpinions(data.items||[]); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderFactsOpinions(items) {
  const container=document.getElementById('factsContainer');
  if (!items.length) { container.innerHTML='<div class="placeholder-msg">No content analyzed</div>'; return; }
  const facts=items.filter(i=>i.type==='FACT').length; const opinions=items.filter(i=>i.type==='OPINION').length;
  const summary=`<div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap"><div style="padding:10px 20px;background:rgba(0,212,170,0.1);border:1px solid var(--success);border-radius:10px;text-align:center"><div style="font-size:24px;font-weight:700;color:var(--success)">${facts}</div><div style="font-size:12px;color:var(--text-dim)">FACTS</div></div><div style="padding:10px 20px;background:rgba(255,107,107,0.1);border:1px solid var(--error);border-radius:10px;text-align:center"><div style="font-size:24px;font-weight:700;color:var(--error)">${opinions}</div><div style="font-size:12px;color:var(--text-dim)">OPINIONS</div></div></div>`;
  const itemsHtml=items.map(item=>`<div class="fact-item ${item.type}"><span class="fact-badge">${item.type}</span><div class="fact-content"><div class="fact-text">${escapeHtml(item.text||'')}</div><div class="fact-reason">${escapeHtml(item.reason||'')}</div></div></div>`).join('');
  container.innerHTML=summary+itemsHtml;
}
async function loadContradictions() {
  if (!activeDocId) { showToast('Select a document first','error'); return; }
  showLoading('Finding contradictions...');
  try { const data=await apiPost('/api/analysis/contradictions',{session_id:sessionId,doc_id:activeDocId}); hideLoading(); renderContradictions(data.contradictions||[]); }
  catch(err) { hideLoading(); showToast('Error: '+err.message,'error'); }
}
function renderContradictions(items) {
  const container=document.getElementById('contradictionsContainer');
  if (!items.length) { container.innerHTML=`<div style="text-align:center;padding:40px"><div style="font-size:40px;margin-bottom:12px">✅</div><div style="font-size:16px;font-weight:600">No contradictions found!</div><div style="color:var(--text-dim);font-size:13px;margin-top:8px">The document appears consistent</div></div>`; return; }
  const header=`<div style="color:var(--error);font-size:13px;margin-bottom:12px">⚠️ Found ${items.length} contradiction(s)</div>`;
  const itemsHtml=items.map((item,i)=>`<div class="contradiction-item"><div class="contradiction-header">⚠️ Contradiction ${i+1}<span class="severity-badge ${item.severity||'MEDIUM'}">${item.severity||'MEDIUM'}</span></div><div class="contradiction-body"><div class="contradiction-statement">📌 ${escapeHtml(item.statement_1||'')}</div><div style="text-align:center;color:var(--error);font-size:12px">↕ contradicts ↕</div><div class="contradiction-statement">📌 ${escapeHtml(item.statement_2||'')}</div><div class="contradiction-explanation">💡 ${escapeHtml(item.explanation||'')}</div></div></div>`).join('');
  container.innerHTML=header+itemsHtml;
}
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('welcomeBanner').classList.remove('hidden');
  fetch(`${API}/api/documents/session/${sessionId}`).then(r=>r.json()).then(data=>{
    if(data.documents&&data.documents.length){ data.documents.forEach(doc=>{ documents[doc.doc_id]={docId:doc.doc_id,docName:doc.doc_name,totalPages:doc.total_pages,wordCount:doc.word_count}; }); if(!activeDocId&&data.documents.length) activeDocId=data.documents[0].doc_id; renderDocList(); }
  }).catch(()=>{});
});

function toggleFullscreen() {
  const btn = document.getElementById('fsBtn');
  const sidebar = document.getElementById('sidebar');
  const app = document.getElementById('app');
  
  if (sidebar.style.display !== 'none') {
    // Hide sidebar - expand content
    sidebar.style.display = 'none';
    btn.textContent = '✖ Exit Fullscreen';
  } else {
    // Show sidebar - normal view
    sidebar.style.display = 'flex';
    btn.textContent = '⛶ Fullscreen';
  }
}

document.addEventListener('fullscreenchange', () => {
  const btn = document.getElementById('fsBtn');
  const sidebar = document.getElementById('sidebar');
  if (!document.fullscreenElement) {
    sidebar.style.width = '260px';
    sidebar.style.overflow = 'auto';
    if (btn) btn.textContent = '⛶ Fullscreen';
  }
});