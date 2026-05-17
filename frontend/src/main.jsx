// import React, { useEffect, useMemo, useState } from 'react';
// import { createRoot } from 'react-dom/client';
// import './styles.css';
// import {
//   checkProposalFormat,
//   generateProposal,
//   loginCompany,
//   normalizeCompanySession,
//   onboardCompany,
//   uploadPdf,
// } from './api';

// const ROUTES = ['home', 'onboarding', 'upload', 'processing', 'dashboard', 'proposal', 'review', 'export'];
// const STORAGE_KEYS = {
//   session: 'datasmithSession',
//   docState: 'datasmithDocState',
//   proposalResult: 'datasmithProposalResult',
//   feedback: 'datasmithFeedback',
//   proposalMode: 'proposalMode',
// };

// function normalizeFormatSource(value) {
//   return value === 'tender' ? 'tender' : 'template';
// }

// function getFormatSourceLabel(value) {
//   return normalizeFormatSource(value) === 'tender' ? 'Tender document' : 'Onboarded template';
// }

// function getProposalFormatStatus(docState) {
//   if (!docState?.doc_id) {
//     return 'No tender uploaded';
//   }

//   if (docState?.proposalFound) {
//     return docState?.hasTables ? 'This tender has a table-format response form' : 'Tender response format detected';
//   }

//   return 'No format detected';
// }
// const REVIEW_ITEMS = [
//   {
//     id: 1,
//     tone: 'done',
//     category: 'high',
//     title: 'Company profile aligned',
//     text: 'Registered entity details, sector, and credential summary are already aligned to the tender narrative.',
//     status: 'Ready',
//   },
//   {
//     id: 2,
//     tone: 'warning',
//     category: 'review',
//     title: 'Past performance narrative',
//     text: 'Similar project references were found, but the wording still needs a reviewer pass before submission.',
//     status: 'Needs review',
//   },
//   {
//     id: 3,
//     tone: 'danger',
//     category: 'missing',
//     title: 'Commercial annexure values',
//     text: 'Tender-specific pricing fields are still blank and should be completed manually.',
//     status: 'Missing input',
//   },
// ];

// function getInitialRoute() {
//   const hash = window.location.hash.replace('#/', '').replace('#', '');
//   return ROUTES.includes(hash) ? hash : 'home';
// }

// function getStoredJson(key, fallback = null) {
//   try {
//     return JSON.parse(localStorage.getItem(key) || 'null') || fallback;
//   } catch {
//     return fallback;
//   }
// }

// function setStoredJson(key, value) {
//   if (value === null || value === undefined) {
//     localStorage.removeItem(key);
//     return;
//   }

//   localStorage.setItem(key, JSON.stringify(value));
// }

// function getProposalSections(payload) {
//   const candidates = [
//     payload?.sections,
//     payload?.proposal_sections,
//     payload?.proposal_json?.sections,
//     Array.isArray(payload?.proposal_json) ? payload.proposal_json : null,
//   ];

//   const firstArray = candidates.find((value) => Array.isArray(value));
//   if (!firstArray) {
//     return [];
//   }

//   return firstArray
//     .map((item, index) => {
//       if (typeof item === 'string') {
//         return item;
//       }

//       if (typeof item?.title === 'string') {
//         return item.title;
//       }

//       if (typeof item?.heading === 'string') {
//         return item.heading;
//       }

//       if (typeof item?.name === 'string') {
//         return item.name;
//       }

//       return `Section ${index + 1}`;
//     })
//     .filter(Boolean);
// }

// function sanitizeProposalResult(nextValue) {
//   if (!nextValue) {
//     return null;
//   }

//   const { downloadUrl, raw, ...persisted } = nextValue;
//   return persisted;
// }

// function revokeProposalDownloadUrl(proposalResult) {
//   if (proposalResult?.downloadUrl?.startsWith('blob:')) {
//     URL.revokeObjectURL(proposalResult.downloadUrl);
//   }
// }

// function App() {
//   const [route, setRoute] = useState(getInitialRoute());
//   const [session, setSession] = useState(() => getStoredJson(STORAGE_KEYS.session));
//   const [proposalMode, setProposalMode] = useState(() => normalizeFormatSource(localStorage.getItem(STORAGE_KEYS.proposalMode)));
//   const [docState, setDocState] = useState(() => getStoredJson(STORAGE_KEYS.docState, {}));
//   const [proposalResult, setProposalResult] = useState(() => getStoredJson(STORAGE_KEYS.proposalResult));
//   const [feedback, setFeedback] = useState(() => getStoredJson(STORAGE_KEYS.feedback, {}));

//   const navigate = (nextRoute) => {
//     setRoute(nextRoute);
//     window.location.hash = `/${nextRoute}`;
//   };

//   const guardedNavigate = (nextRoute) => {
//     if (!session && !['home', 'onboarding'].includes(nextRoute)) {
//       navigate('onboarding');
//       return;
//     }
//     navigate(nextRoute);
//   };

//   const clearWorkflowState = () => {
//     revokeProposalDownloadUrl(proposalResult);
//     setDocState({});
//     setProposalResult(null);
//     setFeedback({});
//     localStorage.removeItem(STORAGE_KEYS.docState);
//     localStorage.removeItem(STORAGE_KEYS.proposalResult);
//     localStorage.removeItem(STORAGE_KEYS.feedback);
//   };

//   const saveSession = (nextSession) => {
//     const currentCompanyId = session?.company_id;
//     const nextCompanyId = nextSession?.company_id;

//     if (currentCompanyId && nextCompanyId && currentCompanyId !== nextCompanyId) {
//       clearWorkflowState();
//     }

//     setSession(nextSession);
//     setStoredJson(STORAGE_KEYS.session, nextSession);
//   };

//   const saveDocState = (nextState) => {
//     setDocState(nextState);
//     setStoredJson(STORAGE_KEYS.docState, nextState);
//   };

//   const saveProposalResult = (nextValue) => {
//     revokeProposalDownloadUrl(proposalResult);
//     setProposalResult(nextValue);
//     setStoredJson(STORAGE_KEYS.proposalResult, sanitizeProposalResult(nextValue));
//   };

//   const saveFeedback = (nextValue) => {
//     setFeedback(nextValue);
//     setStoredJson(STORAGE_KEYS.feedback, nextValue);
//   };

//   const logout = () => {
//     clearWorkflowState();
//     localStorage.removeItem(STORAGE_KEYS.session);
//     setSession(null);
//     navigate('onboarding');
//   };

//   const sharedProps = {
//     session,
//     saveSession,
//     proposalMode,
//     setProposalMode: (mode) => {
//       const nextMode = normalizeFormatSource(mode);
//       setProposalMode(nextMode);
//       localStorage.setItem(STORAGE_KEYS.proposalMode, nextMode);
//     },
//     docState,
//     saveDocState,
//     proposalResult,
//     saveProposalResult,
//     feedback,
//     saveFeedback,
//     navigate,
//     guardedNavigate,
//   };

//   const page = useMemo(() => {
//     const pages = {
//       home: <HomePage {...sharedProps} />,
//       onboarding: <OnboardingPage {...sharedProps} />,
//       upload: <UploadPage {...sharedProps} />,
//       processing: <ProcessingPage {...sharedProps} />,
//       dashboard: <DashboardPage {...sharedProps} />,
//       proposal: <ProposalPage {...sharedProps} />,
//       review: <ReviewPage {...sharedProps} />,
//       export: <ExportPage {...sharedProps} />,
//     };
//     return pages[route] || pages.home;
//   }, [route, session, proposalMode, docState, proposalResult, feedback]);

//   return (
//     <div className="shell">
//       <Nav route={route} session={session} navigate={guardedNavigate} logout={logout} />
//       {page}
//       <Footer navigate={navigate} />
//     </div>
//   );
// }

// function Nav({ route, session, navigate, logout }) {
//   const items = [
//     ['home', 'Overview'],
//     ['dashboard', 'Dashboard'],
//     ['upload', 'Intake'],
//     ['processing', 'Processing'],
//     ['review', 'Review'],
//     ['export', 'Export'],
//   ];

//   return (
//     <header className="site-header">
//       <div className="site-header__inner">
//         <button className="brand brand-button" onClick={() => navigate('home')}>
//           <span className="brand__mark">D</span>
//           <span>
//             <span className="brand__eyebrow">Tender Operations</span>
//             <span className="brand__title">Datasmith AI</span>
//           </span>
//         </button>
//         <div className="site-nav">
//           <nav className="site-nav__links" aria-label="Primary">
//             {items.map(([key, label]) => (
//               <button
//                 key={key}
//                 className={`site-nav__link ${route === key ? 'is-active' : ''}`}
//                 onClick={() => navigate(key)}
//               >
//                 {label}
//               </button>
//             ))}
//           </nav>
//           <div className="nav-actions">
//             <label className="nav-search" aria-label="Search workspace">
//               <span className="nav-search__icon">/</span>
//               <input type="text" placeholder="Search tenders, drafts, or tasks" />
//             </label>
//             <div className="nav-user">
//               <span className="nav-user__label">Workspace</span>
//               <strong>{session?.company_name || 'Guest mode'}</strong>
//             </div>
//             {session ? (
//               <button className="btn btn--secondary" onClick={logout}>Logout</button>
//             ) : (
//               <button className="btn btn--secondary" onClick={() => navigate('onboarding')}>Log In</button>
//             )}
//           </div>
//         </div>
//       </div>
//     </header>
//   );
// }

// function Footer({ navigate }) {
//   return (
//     <footer className="site-footer">
//       <div className="site-footer__inner">
//         <div>
//           <div className="footer-title">Datasmith AI</div>
//           <div className="muted">A focused workspace for tender intake, review, drafting, and export.</div>
//         </div>
//         <div className="footer-links">
//           <button className="subtle-link" onClick={() => navigate('onboarding')}>Onboarding</button>
//           <button className="subtle-link" onClick={() => navigate('processing')}>AI Processing</button>
//           <button className="subtle-link" onClick={() => navigate('proposal')}>Draft Editor</button>
//         </div>
//       </div>
//     </footer>
//   );
// }

// function HomePage({ navigate, session, proposalMode, docState }) {
//   const sections = [
//     {
//       title: 'Access',
//       name: 'Workspace Setup',
//       text: 'Create a company workspace, sign in securely, and move into the operating dashboard.',
//       items: ['Secure sign-in', 'Workspace setup', 'Team context', 'Dashboard access'],
//       route: 'onboarding',
//     },
//     {
//       title: 'Intake',
//       name: 'Tender Upload',
//       text: 'Add the tender package, capture source documents, and prepare the submission for analysis.',
//       items: ['Document intake', 'File tracking', 'Requirement capture', 'Submission context'],
//       route: 'upload',
//     },
//     {
//       title: 'Format',
//       name: 'Response Structure',
//       text: 'Choose whether the response follows the tender format or your internal proposal standard.',
//       items: ['Tender-led structure', 'Company template', `Current mode: ${getFormatSourceLabel(proposalMode)}`],
//       route: 'upload',
//     },
//     {
//       title: 'Analysis',
//       name: 'Document Processing',
//       text: 'Review structure, surface requirements, and prepare a draft with reusable company information.',
//       items: ['Structure review', 'Requirement extraction', 'Company knowledge', 'Draft preparation'],
//       route: 'processing',
//     },
//     {
//       title: 'Validation',
//       name: 'Content Review',
//       text: 'Separate approved content, items needing review, and unresolved gaps before sign-off.',
//       items: ['Ready content', 'Needs review', 'Missing information'],
//       route: 'review',
//     },
//     {
//       title: 'Delivery',
//       name: 'Draft And Export',
//       text: 'Refine the draft, confirm approvals, package exports, and capture operator feedback.',
//       items: ['Draft editor', 'Approvals', 'Editable export', 'Feedback'],
//       route: 'export',
//     },
//   ];
//   const workflowStages = [
//     { title: '1. Access', desc: 'Authenticate and open the workspace.', state: session ? 'Ready' : 'Pending' },
//     { title: '2. Intake', desc: docState?.fileName || 'Tender file not uploaded yet.', state: docState?.fileName ? 'Captured' : 'Waiting' },
//     { title: '3. Structure', desc: `${getFormatSourceLabel(proposalMode)} selected.`, state: 'Active' },
//     { title: '4. Processing', desc: 'Extract sections, requirements, and draft content.', state: 'Queued' },
//     { title: '5. Review', desc: 'Validate ready content and resolve missing inputs.', state: 'Queued' },
//     { title: '6. Export', desc: 'Approve the final draft and prepare submission files.', state: 'Queued' },
//   ];

//   return (
//     <main className="page-main">
//       <section className="hero hero--dashboard">
//         <div className="hero-copy">
//           <div className="eyebrow-chip">Datasmith AI Workspace</div>
//           <h1>Run the full tender response workflow from a focused blue workspace.</h1>
//           <p>
//             Your original workflow stays intact, but the interface now pushes toward a more product-like dashboard:
//             sharper hierarchy, clearer task states, and less generic presentation.
//           </p>
//           <div className="hero-actions">
//             <button className="btn btn--primary" onClick={() => navigate(session ? 'dashboard' : 'onboarding')}>
//               {session ? 'Open Dashboard' : 'Start Onboarding'}
//             </button>
//             <button className="btn btn--ghost" onClick={() => navigate('upload')}>Open Tender Intake</button>
//           </div>
//           <div className="hero-metrics">
//             <MiniMetric label="Workspace" value={session ? 'Active' : 'Setup required'} />
//             <MiniMetric label="Tender file" value={docState?.fileName || 'No upload yet'} />
//             <MiniMetric label="Response mode" value={getFormatSourceLabel(proposalMode)} />
//           </div>
//         </div>

//         <div className="workflow-board">
//           <div className="workflow-board__header">Workflow Status</div>
//           <div className="workflow-list">
//             {workflowStages.map((stage) => (
//               <FlowPill
//                 key={stage.title}
//                 tone={stage.state === 'Pending' || stage.state === 'Waiting' ? 'soft' : stage.state === 'Captured' || stage.state === 'Active' ? 'brand' : 'success'}
//                 title={stage.title}
//                 subtitle={stage.desc}
//                 badge={stage.state}
//               />
//             ))}
//           </div>
//         </div>
//       </section>

//       <section className="page-section">
//         <PageHead
//           title="Workflow Modules"
//           text="Every screen below still follows the workflow you gave, but it now feels more like a real operations product."
//         />
//         <div className="section-grid">
//           {sections.map((section) => (
//             <button key={section.name} className="section-card" onClick={() => navigate(section.route)}>
//               <div className="section-card__eyebrow">{section.title}</div>
//               <h3>{section.name}</h3>
//               <p>{section.text}</p>
//               <div className="tag-row">
//                 {section.items.map((item) => <span key={item} className="tag">{item}</span>)}
//               </div>
//             </button>
//           ))}
//         </div>
//       </section>

//       <section className="page-section page-section--compact">
//         <div className="dashboard-table-card">
//           <div className="table-card__head">
//             <div>
//               <div className="stack-panel__eyebrow">Current Workflow</div>
//               <h2 className="panel-title">Tender response journey</h2>
//             </div>
//             <button className="btn btn--ghost" onClick={() => navigate(session ? 'dashboard' : 'onboarding')}>
//               {session ? 'Open Operations' : 'Create Workspace'}
//             </button>
//           </div>
//           <div className="workflow-table">
//             {workflowStages.map((stage) => (
//               <div key={stage.title} className="workflow-row">
//                 <div className="workflow-row__title">{stage.title}</div>
//                 <div className="workflow-row__desc">{stage.desc}</div>
//                 <StatusToken tone={stage.state === 'Pending' || stage.state === 'Waiting' ? 'draft' : stage.state === 'Active' || stage.state === 'Captured' ? 'review' : 'done'} label={stage.state} />
//               </div>
//             ))}
//           </div>
//         </div>
//       </section>
//     </main>
//   );
// }

// function OnboardingPage({ saveSession, navigate, session }) {
//   const [mode, setMode] = useState(session ? 'login' : 'signup');
//   const [status, setStatus] = useState({ type: 'info', text: 'Create or access your workspace to continue into the dashboard.' });
//   const [loading, setLoading] = useState(false);

//   async function handleLogin(event) {
//     event.preventDefault();
//     setLoading(true);
//     setStatus({ type: 'info', text: 'Checking workspace details...' });
//     const form = new FormData(event.currentTarget);
//     const email = String(form.get('email') || '').trim().toLowerCase();
//     const password = String(form.get('password') || '');

//     try {
//       const payload = await loginCompany({ email, password });
//       const nextSession = {
//         ...normalizeCompanySession(payload),
//         contact_email: email,
//         industry: payload.industry || '',
//         contact_phone: payload.contact_phone || '',
//         password,
//         knowledge_base_name: payload.knowledge_base_name || 'Knowledge base pending',
//         proposal_template_name: payload.proposal_template_name || 'Template pending',
//       };

//       saveSession(nextSession);
//       setStatus({ type: 'success', text: 'Workspace found. Redirecting to the dashboard...' });
//       setTimeout(() => navigate('dashboard'), 600);
//     } catch (error) {
//       setStatus({ type: 'error', text: error.message || 'Unable to sign in right now.' });
//     } finally {
//       setLoading(false);
//     }
//   }

//   async function handleSignup(event) {
//     event.preventDefault();
//     setLoading(true);
//     setStatus({ type: 'info', text: 'Creating your workspace...' });
//     const form = new FormData(event.currentTarget);
//     const nextSession = {
//       company_id: `CMP-${Date.now().toString().slice(-6)}`,
//       company_name: String(form.get('company_name') || ''),
//       industry: String(form.get('industry') || ''),
//       contact_email: String(form.get('contact_email') || ''),
//       contact_phone: String(form.get('contact_phone') || ''),
//       password: String(form.get('password') || ''),
//       knowledge_base: form.get('knowledge_base'),
//       proposal_template: form.get('proposal_template'),
//       knowledge_base_name: form.get('knowledge_base')?.name || 'Knowledge base pending',
//       proposal_template_name: form.get('proposal_template')?.name || 'Template pending',
//     };

//     try {
//       const payload = await onboardCompany(nextSession);
//       saveSession({
//         ...normalizeCompanySession(payload, nextSession),
//         industry: payload.industry || nextSession.industry,
//         contact_phone: payload.contact_phone || nextSession.contact_phone,
//         password: nextSession.password,
//         knowledge_base_name: payload.knowledge_base_name || nextSession.knowledge_base_name,
//         proposal_template_name: payload.proposal_template_name || nextSession.proposal_template_name,
//       });
//       setStatus({ type: 'success', text: 'Workspace created successfully. Redirecting to the dashboard...' });
//       setTimeout(() => navigate('dashboard'), 700);
//     } catch (error) {
//       setStatus({ type: 'error', text: error.message || 'Unable to create workspace right now.' });
//     } finally {
//       setLoading(false);
//     }
//   }

//   return (
//     <main className="auth-page">
//       <section className="auth-shell auth-shell--elevated">
//         <aside className="auth-hero auth-hero--flow">
//           <div className="auth-hero__eyebrow">Workspace Access</div>
//           <h1 className="page-title">Set up the company workspace before work begins.</h1>
//           <p className="page-subtitle">
//             Keep access simple: returning users sign in, new teams create a workspace, and both land in the same
//             operating view for intake and review.
//           </p>
//           <div className="auth-points">
//             <div className="auth-point">
//               <div className="auth-point__icon">01</div>
//               <div>
//                 <strong>Access your workspace</strong>
//                 <p className="muted">Sign in to an existing account or create a new company workspace.</p>
//               </div>
//             </div>
//             <div className="auth-point">
//               <div className="auth-point__icon">02</div>
//               <div>
//                 <strong>Store company context</strong>
//                 <p className="muted">Keep core contact, knowledge base, and template details in one place.</p>
//               </div>
//             </div>
//             <div className="auth-point">
//               <div className="auth-point__icon">03</div>
//               <div>
//                 <strong>Continue to operations</strong>
//                 <p className="muted">Move directly into tender intake, processing, review, and export.</p>
//               </div>
//             </div>
//           </div>
//         </aside>

//         <section className="auth-card auth-card--clean">
//           <div className="auth-tabs">
//             <button className={`auth-tab ${mode === 'login' ? 'is-active' : ''}`} onClick={() => setMode('login')}>Log In</button>
//             <button className={`auth-tab ${mode === 'signup' ? 'is-active' : ''}`} onClick={() => setMode('signup')}>Create Workspace</button>
//           </div>
//           <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>

//           {mode === 'login' ? (
//             <form className="auth-form" onSubmit={handleLogin}>
//               <TextField label="Email" name="email" type="email" placeholder="you@company.com" />
//               <TextField label="Password" name="password" type="password" placeholder="Enter your password" />
//               <button className="btn btn--primary auth-submit" disabled={loading}>{loading ? 'Logging in...' : 'Log In To Workspace'}</button>
//             </form>
//           ) : (
//             <form className="auth-form" onSubmit={handleSignup}>
//               <div className="field-grid">
//                 <TextField label="Company name" name="company_name" placeholder="ABC Infra Pvt Ltd" />
//                 <TextField label="Industry" name="industry" placeholder="Infrastructure / Consulting / Energy" />
//               </div>
//               <div className="field-grid">
//                 <TextField label="Contact email" name="contact_email" type="email" placeholder="ops@company.com" />
//                 <TextField label="Contact phone" name="contact_phone" placeholder="+91 98765 43210" />
//               </div>
//               <TextField label="Password" name="password" type="password" placeholder="Create a strong password" />
//               <div className="field-grid">
//                 <FileField label="Knowledge base" name="knowledge_base" />
//                 <FileField label="Proposal template" name="proposal_template" />
//               </div>
//               <button className="btn btn--primary auth-submit" disabled={loading}>{loading ? 'Creating workspace...' : 'Create Workspace'}</button>
//             </form>
//           )}
//         </section>
//       </section>
//     </main>
//   );
// }

// function UploadPage({ session, docState, saveDocState, proposalMode, setProposalMode, guardedNavigate, saveProposalResult, saveFeedback }) {
//   const [fileName, setFileName] = useState(docState?.fileName || '');
//   const [selectedFile, setSelectedFile] = useState(null);
//   const [status, setStatus] = useState({ type: 'info', text: 'Choose the tender document to begin intake.' });

//   async function handleUpload(event) {
//     event.preventDefault();
//     if (!selectedFile || !fileName) {
//       setStatus({ type: 'error', text: 'Choose a tender PDF first.' });
//       return;
//     }

//     if (!session?.company_id) {
//       setStatus({ type: 'error', text: 'Create or access a workspace before uploading a tender.' });
//       return;
//     }

//     setStatus({ type: 'info', text: 'Uploading tender document...' });

//     try {
//       const payload = await uploadPdf({ companyId: session.company_id, file: selectedFile });
//       saveProposalResult(null);
//       saveFeedback({});
//       const proposalFound = Boolean(payload?.proposal_found);
//       const formatSource = proposalFound ? 'tender' : 'template';
//       setProposalMode(formatSource);
//       const nextState = {
//         fileName,
//         fileUrl: payload?.file_url || payload?.tender_file_url || '',
//         doc_id: payload?.doc_id || payload?.id || `DOC-${Date.now().toString().slice(-6)}`,
//         uploadSummary: payload?.message || `Tender captured with ${payload?.total_chunks || 0} extracted chunks.`,
//         selectedMode: formatSource,
//         totalChunks: payload?.total_chunks || 0,
//         textChunks: payload?.text_chunks || 0,
//         tableChunks: payload?.table_chunks || 0,
//         hasTables: Boolean(payload?.has_tables ?? payload?.table_chunks > 0),
//         proposalFound,
//         proposalSections: getProposalSections(payload),
//         raw: payload,
//       };
//       saveDocState(nextState);
//       setStatus({ type: 'success', text: 'Tender captured. Moving to processing...' });
//       setTimeout(() => guardedNavigate('processing'), 650);
//     } catch (error) {
//       setStatus({ type: 'error', text: error.message || 'Unable to upload tender right now.' });
//     }
//   }

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Tender Intake"
//         text="Upload the source tender, confirm the response structure, and prepare the file for processing."
//       />

//       <section className="upload-shell">
//         <div className="steppers">
//           <StepCard index="1" title="Upload documents" text="Tender PDF and annexures" active />
//           <StepCard index="2" title="Parse documents" text="Detect sections and tables" />
//           <StepCard index="3" title="Extract information" text="Map compliance and requirements" />
//           <StepCard index="4" title="Generate summary" text="Prepare the AI handoff" />
//         </div>

//         <div className="upload-grid">
//           <form className="dropzone dropzone--tall" onSubmit={handleUpload}>
//             <div className="dropzone__icon">PDF</div>
//             <h2 className="panel-title">Upload tender document</h2>
//             <p className="section-subtitle">Add the primary tender PDF to initialize the working file and document context.</p>
//             <div className="field">
//               <label>
//                 Tender PDF
//                 <input
//                   type="file"
//                   accept=".pdf"
//                   required
//                   onChange={(event) => {
//                     const file = event.target.files?.[0] || null;
//                     setSelectedFile(file);
//                     setFileName(file?.name || '');
//                   }}
//                 />
//               </label>
//             </div>
//             <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>
//             <button className="btn btn--primary" type="submit">Continue To Processing</button>
//           </form>

//           <aside className="stack-panel">
//             <div className="stack-panel__section">
//               <div className="stack-panel__eyebrow">Response Structure</div>
//               <h3>Format source is selected after upload</h3>
//               <div className="info-note">
//                 Once parsing finishes, the next screen enables the tender format only when a response form is detected.
//               </div>
//             </div>

//             <div className="stack-panel__section">
//               <div className="stack-panel__eyebrow">Parsed outcome preview</div>
//               <div className="preview-list">
//                 <PreviewItem label="Uploaded file" value={fileName || 'No file chosen yet'} />
//                 <PreviewItem label="Format source" value={getFormatSourceLabel(proposalMode)} />
//                 <PreviewItem label="Document ID" value={docState?.doc_id || 'Will be assigned after upload'} />
//                 <PreviewItem label="Next step" value="Document processing" />
//               </div>
//             </div>
//           </aside>
//         </div>
//       </section>
//     </main>
//   );
// }

// function ProcessingPage({ session, docState, proposalMode, setProposalMode, saveDocState, saveProposalResult, guardedNavigate }) {
//   const [status, setStatus] = useState({ type: 'info', text: 'Review the extraction stages and generate the first draft.' });
//   const [loading, setLoading] = useState(false);
//   const [formatSource, setFormatSource] = useState(() => {
//     if (docState?.proposalFound) {
//       return normalizeFormatSource(docState?.selectedMode || 'tender');
//     }

//     return 'template';
//   });

//   useEffect(() => {
//     const nextSource = docState?.proposalFound
//       ? normalizeFormatSource(docState?.selectedMode || 'tender')
//       : 'template';

//     setFormatSource(nextSource);
//     setProposalMode(nextSource);
//   }, [docState?.doc_id, docState?.proposalFound, docState?.selectedMode, setProposalMode]);

//   useEffect(() => {
//     if (!docState?.doc_id) {
//       return undefined;
//     }

//     let active = true;

//     checkProposalFormat({ docId: docState.doc_id })
//       .then((payload) => {
//         if (!active) {
//           return;
//         }

//         const proposalFound = Boolean(payload?.proposal_found);
//         const nextSource = proposalFound ? normalizeFormatSource(docState?.selectedMode || 'tender') : 'template';
//         const nextState = {
//           ...docState,
//           proposalFound,
//           hasTables: Boolean(payload?.has_tables),
//           selectedMode: nextSource,
//         };

//         saveDocState(nextState);
//         setProposalMode(nextSource);
//         setFormatSource(nextSource);
//       })
//       .catch(() => {
//         // Format detection is already available from upload; this re-check is best-effort.
//       });

//     return () => {
//       active = false;
//     };
//   }, [docState?.doc_id]);

//   function handleFormatSourceChange(nextSource) {
//     const normalizedSource = docState?.proposalFound ? normalizeFormatSource(nextSource) : 'template';
//     setFormatSource(normalizedSource);
//     setProposalMode(normalizedSource);
//     saveDocState({
//       ...docState,
//       selectedMode: normalizedSource,
//     });
//   }

//   async function handleGenerate() {
//     if (!docState?.fileName) {
//       setStatus({ type: 'error', text: 'Upload a tender first so the processing flow has input.' });
//       return;
//     }

//     if (!session?.company_id || !docState?.doc_id) {
//       setStatus({ type: 'error', text: 'Workspace or document details are missing.' });
//       return;
//     }

//     const effectiveFormatSource = docState?.proposalFound ? formatSource : 'template';
//     setLoading(true);
//     setStatus({ type: 'info', text: 'Generating proposal...' });

//     try {
//       const payload = await generateProposal({
//         companyId: session.company_id,
//         docId: docState.doc_id,
//         formatSource: effectiveFormatSource,
//       });
//       const sections = docState?.proposalSections?.length
//         ? docState.proposalSections
//         : [
//             'Executive summary aligned to tender objectives',
//             'Eligibility and compliance checklist',
//             'Past experience and delivery capability',
//             'Team structure and implementation approach',
//           ];
//       const nextDocState = {
//         ...docState,
//         selectedMode: effectiveFormatSource,
//       };

//       saveDocState(nextDocState);
//       setProposalMode(effectiveFormatSource);

//       if (payload?.downloadUrl) {
//         const link = document.createElement('a');
//         link.href = payload.downloadUrl;
//         link.download = payload.filename || 'generated_proposal.docx';
//         document.body.appendChild(link);
//         link.click();
//         link.remove();
//       }

//       saveProposalResult({
//         title: payload?.filename || 'generated_proposal.docx',
//         companyNarrative: effectiveFormatSource === 'tender'
//           ? 'The backend detected a proposal structure in the tender and generated the draft against that format.'
//           : 'The backend generated the draft using the company template for this workspace.',
//         proposalMode: effectiveFormatSource,
//         tenderName: docState.fileName,
//         docId: docState.doc_id,
//         companyId: session.company_id,
//         sections,
//         downloadUrl: payload.downloadUrl,
//         filename: payload.filename,
//       });
//       setStatus({ type: 'success', text: 'Draft prepared. Opening the proposal workspace...' });
//       setTimeout(() => guardedNavigate('proposal'), 650);
//     } catch (error) {
//       setStatus({ type: 'error', text: error.message || 'Unable to generate the draft right now.' });
//     } finally {
//       setLoading(false);
//     }
//   }

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Document Processing"
//         text="Track the core extraction stages and generate the first response draft from the tender package."
//       />

//       <section className="processing-layout">
//         <div className="processing-column">
//           <div className="processing-shell">
//             <div className="processing-shell__header">Processing Stages</div>
//             <div className="processing-track">
//               <ProcessNode title="Identify Tender Structure" text="Review sections, annexures, mandatory forms, and formatting rules." />
//               <ProcessNode title="Extract Tender Data" text="Capture fields, milestones, evaluation criteria, and submission deadlines." />
//               <ProcessNode title="Match Company Knowledge" text="Bring in reusable credentials, references, and prior response material." />
//               <ProcessNode title="Prepare Draft Content" text="Assemble the first draft for reviewer validation." />
//             </div>
//           </div>
//         </div>

//         <aside className="side-rail">
//           <div className="timeline-card">
//             <div className="stack-panel__eyebrow">Current input</div>
//             <PreviewItem label="Tender file" value={docState?.fileName || 'No upload yet'} />
//             <PreviewItem label="Format source" value={getFormatSourceLabel(proposalMode)} />
//             <PreviewItem label="Document ID" value={docState?.doc_id || 'Document not captured yet'} />
//             <PreviewItem label="Detected format" value={getProposalFormatStatus(docState)} />
//           </div>
//           <div className="timeline-card">
//             <div className="stack-panel__eyebrow">Proposal format</div>
//             <div className="format-source-group" role="radiogroup" aria-label="Proposal format source">
//               <label className={`format-source-option ${formatSource === 'tender' ? 'is-selected' : ''} ${!docState?.proposalFound ? 'is-disabled' : ''}`}>
//                 <input
//                   type="radio"
//                   name="format_source"
//                   value="tender"
//                   checked={formatSource === 'tender'}
//                   disabled={!docState?.proposalFound || loading}
//                   onChange={() => handleFormatSourceChange('tender')}
//                 />
//                 <span>Use response format from the tender document itself</span>
//               </label>
//               <label className={`format-source-option ${formatSource === 'template' ? 'is-selected' : ''}`}>
//                 <input
//                   type="radio"
//                   name="format_source"
//                   value="template"
//                   checked={formatSource === 'template'}
//                   disabled={loading}
//                   onChange={() => handleFormatSourceChange('template')}
//                 />
//                 <span>Use my onboarded proposal template</span>
//               </label>
//             </div>
//           </div>
//           <div className="timeline-card">
//             <div className="stack-panel__eyebrow">Review states</div>
//             <div className="confidence-row">
//               <ConfidenceChip tone="success" title="High Confidence" />
//               <ConfidenceChip tone="warning" title="Needs Review" />
//               <ConfidenceChip tone="danger" title="Missing Information" />
//             </div>
//           </div>
//           <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>
//           {loading ? (
//             <div className="loading-note" role="status" aria-live="polite">
//               <span className="spinner" aria-hidden="true" />
//               <span>Generating proposal...</span>
//             </div>
//           ) : null}
//           <div className="inline-actions">
//             <button className="btn btn--primary" onClick={handleGenerate} disabled={loading}>
//               {loading ? 'Generating proposal...' : 'Generate Proposal'}
//             </button>
//             <button className="btn btn--ghost" onClick={() => guardedNavigate('review')} disabled={loading}>Open Review</button>
//           </div>
//         </aside>
//       </section>
//     </main>
//   );
// }

// function DashboardPage({ session, docState, proposalMode, guardedNavigate, proposalResult }) {
//   const queue = [
//     {
//       name: docState?.fileName || 'New tender package',
//       owner: session?.company_name || 'Workspace',
//       stage: docState?.fileName ? 'Processing ready' : 'Awaiting upload',
//       progress: proposalResult ? 'Draft available' : docState?.fileName ? 'Queued for generation' : 'No document',
//       due: proposalResult ? 'Review next' : 'Upload required',
//     },
//     {
//       name: 'Compliance review',
//       owner: 'Review team',
//       stage: 'Validation',
//       progress: 'Needs review',
//       due: 'Before export',
//     },
//     {
//       name: 'Commercial annexures',
//       owner: 'Bid manager',
//       stage: 'Pending input',
//       progress: 'Missing values',
//       due: 'Open',
//     },
//   ];

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Workspace Dashboard"
//         text="Operate the proposal workflow from one place: intake, generation, validation, and release."
//         action={<button className="btn btn--primary" onClick={() => guardedNavigate('upload')}>New Tender</button>}
//       />

//       <section className="kpi-grid">
//         <Metric label="Company" value={session?.company_name || 'Workspace'} text={session?.contact_email || 'No workspace email yet'} />
//         <Metric label="Industry" value={session?.industry || 'Not set'} text={session?.contact_phone || 'Contact pending'} />
//         <Metric label="Tender" value={docState?.fileName || 'No upload yet'} text={docState?.doc_id || 'Document ID pending'} />
//         <Metric label="Format source" value={getFormatSourceLabel(proposalMode)} text={getProposalFormatStatus(docState)} />
//       </section>

//       <section className="dashboard-showcase">
//         <article className="dashboard-main">
//           <div className="dashboard-main__header">
//             <div>
//               <div className="stack-panel__eyebrow">Operations Queue</div>
//               <h2 className="panel-title">Tender response tracking</h2>
//             </div>
//             <span className="status-pill status-pill--review">{proposalResult ? 'Draft available' : 'Waiting for generation'}</span>
//           </div>

//           <div className="progress-band">
//             <ProgressStep title="Onboard" active />
//             <ProgressStep title="Upload" active={Boolean(docState?.fileName)} />
//             <ProgressStep title="Process" active={Boolean(proposalResult)} />
//             <ProgressStep title="Review" />
//             <ProgressStep title="Export" />
//           </div>

//           <div className="dashboard-table">
//             <div className="dashboard-table__head">
//               <span>Workflow Item</span>
//               <span>Owner</span>
//               <span>Stage</span>
//               <span>Status</span>
//               <span>Next Move</span>
//             </div>
//             {queue.map((item) => (
//               <div key={item.name} className="dashboard-table__row">
//                 <strong>{item.name}</strong>
//                 <span>{item.owner}</span>
//                 <span>{item.stage}</span>
//                 <StatusToken tone={item.progress.includes('Draft') ? 'done' : item.progress.includes('Missing') ? 'danger' : item.progress.includes('Needs') ? 'warning' : 'review'} label={item.progress} />
//                 <span>{item.due}</span>
//               </div>
//             ))}
//           </div>

//           <div className="quick-grid">
//             <QuickAction title="Upload tender" text="Bring in the latest tender document and choose the structure path." onClick={() => guardedNavigate('upload')} />
//             <QuickAction title="Open draft" text="Review the draft workspace and continue refining the response." onClick={() => guardedNavigate('proposal')} />
//             <QuickAction title="Run review" text="Inspect ready content, flagged sections, and missing inputs." onClick={() => guardedNavigate('review')} />
//           </div>
//         </article>

//         <aside className="dashboard-aside">
//           <div className="sidebar-card sidebar-card--accent">
//             <div className="stack-panel__eyebrow">Primary Action</div>
//             <h3>Move the current response forward</h3>
//             <p>Use the next action below to continue the workflow without losing context.</p>
//             <button className="btn btn--primary" onClick={() => guardedNavigate(docState?.fileName ? 'processing' : 'upload')}>
//               {docState?.fileName ? 'Open Processing' : 'Start Intake'}
//             </button>
//           </div>
//           <div className="sidebar-card">
//             <div className="stack-panel__eyebrow">Workspace Focus</div>
//             <ul className="plain-list">
//               <li>Keep workspace details current before each response cycle</li>
//               <li>Use a consistent intake structure across tender submissions</li>
//               <li>Review flagged sections before approving the draft</li>
//               <li>Track export readiness and unresolved commercial inputs</li>
//             </ul>
//           </div>
//         </aside>
//       </section>
//     </main>
//   );
// }

// function ProposalPage({ proposalResult, docState, guardedNavigate }) {
//   const outline = proposalResult?.sections?.length
//     ? proposalResult.sections
//     : [
//         'Executive Summary',
//         'Eligibility And Compliance',
//         'Technical Approach',
//         'Past Performance',
//         'Commercial Inputs',
//       ];

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Draft Editor"
//         text="Review the draft, refine key sections, and move the response toward approval."
//       />

//       <section className="proposal-workspace">
//         <aside className="proposal-sidebar">
//           <div className="sidebar-card">
//             <div className="stack-panel__eyebrow">Draft outline</div>
//             <div className="outline-list">
//               {outline.map((item) => <div key={item} className="outline-link">{item}</div>)}
//             </div>
//           </div>
//           <div className="sidebar-card">
//             <div className="stack-panel__eyebrow">Draft metadata</div>
//             <PreviewItem label="Tender" value={docState?.fileName || 'Not uploaded'} />
//             <PreviewItem label="Draft state" value={proposalResult ? 'Draft ready' : 'Awaiting generation'} />
//           </div>
//         </aside>

//         <article className="editor-card editor-card--rich">
//           <div className="proposal-banner">
//             <div>
//               <div className="stack-panel__eyebrow">Proposal Draft</div>
//               <h2 className="panel-title">Refine sections, confirm content quality, and prepare for release</h2>
//             </div>
//             <div className="inline-actions">
//               <button className="btn btn--ghost" onClick={() => guardedNavigate('review')}>Open Review</button>
//               <button className="btn btn--primary" onClick={() => guardedNavigate('export')}>Approve Draft</button>
//             </div>
//           </div>

//           <div className="doc-content">
//             <section className="content-block">
//               <h3>Executive Summary</h3>
//               <p>{proposalResult?.companyNarrative || 'Generate a draft to populate this section.'}</p>
//               <div className="suggestion">
//                 Suggested insertion: tailor the executive summary to the tender owner, delivery horizon, and differentiators.
//               </div>
//             </section>

//             <section className="content-block">
//               <h3>Eligibility And Compliance</h3>
//               <div className="callout">
//                 Compliance-aligned content is grouped here so reviewers can verify requirements quickly.
//               </div>
//             </section>

//             <section className="content-block">
//               <h3>Technical Approach</h3>
//               <p>
//                 Use this workspace to shape delivery approach, methodology, and staffing into a more polished final response,
//                 while keeping review and approval close at hand.
//               </p>
//             </section>

//             <section className="content-block">
//               <h3>Commercial Inputs</h3>
//               <div className="review-block">
//                 Missing-value placeholders should remain clearly visible so the reviewer knows what still needs manual input.
//               </div>
//             </section>
//           </div>
//         </article>
//       </section>
//     </main>
//   );
// }

// function ReviewPage({ guardedNavigate }) {
//   const [filter, setFilter] = useState('all');
//   const filtered = REVIEW_ITEMS.filter((item) => filter === 'all' || item.category === filter);

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Review And Approval"
//         text="Separate approved content, flagged sections, and missing inputs before release."
//       />

//       <section className="review-shell">
//         <div className="review-filter-row">
//           <FilterButton label="All" active={filter === 'all'} onClick={() => setFilter('all')} />
//           <FilterButton label="High confidence" active={filter === 'high'} onClick={() => setFilter('high')} />
//           <FilterButton label="Needs review" active={filter === 'review'} onClick={() => setFilter('review')} />
//           <FilterButton label="Missing info" active={filter === 'missing'} onClick={() => setFilter('missing')} />
//         </div>

//         <div className="review-grid review-grid--full">
//           {filtered.map((item) => (
//             <article key={item.id} className="review-card">
//               <div className="review-card__head">
//                 <h3>{item.title}</h3>
//                 <span className={`status-pill status-pill--${item.tone}`}>{item.status}</span>
//               </div>
//               <div className={`issue-strip issue-strip--${item.tone === 'danger' ? 'critical' : item.tone === 'done' ? 'ok' : 'warning'}`}>
//                 {item.text}
//               </div>
//             </article>
//           ))}
//         </div>

//         <section className="approval-band">
//           <div>
//             <div className="stack-panel__eyebrow">Approval</div>
//             <h2 className="panel-title">Confirm the draft, request revisions, or move directly to export.</h2>
//           </div>
//           <div className="inline-actions">
//             <button className="btn btn--ghost" onClick={() => guardedNavigate('proposal')}>Request Changes</button>
//             <button className="btn btn--primary" onClick={() => guardedNavigate('export')}>Approve And Continue</button>
//           </div>
//         </section>
//       </section>
//     </main>
//   );
// }

// function ExportPage({ feedback, saveFeedback, guardedNavigate, proposalResult }) {
//   const [message, setMessage] = useState(Object.keys(feedback || {}).length ? 'Saved feedback is available below.' : 'Feedback has not been saved yet.');

//   function handleFeedback(event) {
//     event.preventDefault();
//     const nextFeedback = Object.fromEntries(new FormData(event.currentTarget).entries());
//     saveFeedback(nextFeedback);
//     setMessage('Feedback saved successfully.');
//     event.currentTarget.reset();
//   }

//   return (
//     <main className="page-main page-section">
//       <PageHead
//         title="Export And Feedback"
//         text="Prepare the submission package and capture notes that improve the next response cycle."
//       />

//       <section className="export-grid export-grid--wide">
//         <article className="export-card">
//           <div className="stack-panel__eyebrow">Export</div>
//           <h2 className="panel-title">Download editable proposal package</h2>
//           <div className="export-hero">
//             <div className="export-hero__card">
//               <strong>Download Editable Proposal</strong>
//               <span>Word (.docx), Excel (.xlsx), and final submission bundle</span>
//             </div>
//             <div className="tag-row">
//               <span className="tag">Word (.docx)</span>
//               <span className="tag">Excel (.xlsx)</span>
//               <span className="tag">Version history saved</span>
//             </div>
//           </div>
//           <div className="inline-actions">
//             <button className="btn btn--ghost" onClick={() => guardedNavigate('proposal')}>Back To Draft</button>
//             <button
//               className="btn btn--primary"
//               onClick={() => {
//                 if (proposalResult?.downloadUrl) {
//                   const link = document.createElement('a');
//                   link.href = proposalResult.downloadUrl;
//                   link.download = proposalResult.filename || 'generated_proposal.docx';
//                   link.click();
//                 }
//               }}
//               disabled={!proposalResult?.downloadUrl}
//             >
//               {proposalResult?.downloadUrl ? 'Download Proposal' : 'Prepare Export'}
//             </button>
//           </div>
//         </article>

//         <article className="export-card">
//           <div className="stack-panel__eyebrow">Feedback</div>
//           <h2 className="panel-title">Capture edits and improve the next response cycle</h2>
//           <div className="learning-ladder">
//             <div className="learning-step">Reviewer notes are recorded</div>
//             <div className="learning-step">Draft patterns are refined</div>
//             <div className="learning-step">Future responses become faster and cleaner</div>
//           </div>
//           <form className="auth-form" onSubmit={handleFeedback}>
//             <TextField label="What needed manual work?" name="manual_work_area" placeholder="Financial tables, annexures, reviewer comments..." />
//             <div className="field">
//               <label>
//                 What should improve next time?
//                 <textarea name="feedback_notes" placeholder="Add notes for the next response cycle..." />
//               </label>
//             </div>
//             <button className="btn btn--primary">Save Feedback</button>
//           </form>
//           <div className="info-note">{message}</div>
//         </article>
//       </section>
//     </main>
//   );
// }

// function PageHead({ title, text, action }) {
//   return (
//     <div className="page-head">
//       <div>
//         <h1 className="page-title">{title}</h1>
//         <p className="page-subtitle">{text}</p>
//       </div>
//       {action}
//     </div>
//   );
// }

// function TextField({ label, name, type = 'text', placeholder }) {
//   return (
//     <div className="field">
//       <label>
//         {label}
//         <input name={name} type={type} placeholder={placeholder} required />
//       </label>
//     </div>
//   );
// }

// function FileField({ label, name }) {
//   return (
//     <div className="field">
//       <label>
//         {label}
//         <input name={name} type="file" required />
//       </label>
//     </div>
//   );
// }

// function MiniMetric({ label, value }) {
//   return (
//     <div className="mini-metric">
//       <span>{label}</span>
//       <strong>{value}</strong>
//     </div>
//   );
// }

// function FlowPill({ title, subtitle, tone, badge }) {
//   return (
//     <div className={`flow-pill flow-pill--${tone}`}>
//       <div className="flow-pill__top">
//         <strong>{title}</strong>
//         {badge ? <span className="flow-pill__badge">{badge}</span> : null}
//       </div>
//       <span>{subtitle}</span>
//     </div>
//   );
// }

// function StatusToken({ label, tone = 'review' }) {
//   return <span className={`status-token status-token--${tone}`}>{label}</span>;
// }

// function StepCard({ index, title, text, active = false }) {
//   return (
//     <div className={`step ${active ? 'is-active' : ''}`}>
//       <div className="step__index">{index}</div>
//       <strong>{title}</strong>
//       <p className="muted">{text}</p>
//     </div>
//   );
// }

// function ChoiceCard({ title, text, selected, onClick }) {
//   return (
//     <button className={`choice-card ${selected ? 'is-selected' : ''}`} onClick={onClick} type="button">
//       <div className="choice-card__top">
//         <h3>{title}</h3>
//         <span className="choice-mark" />
//       </div>
//       <p>{text}</p>
//     </button>
//   );
// }

// function PreviewItem({ label, value }) {
//   return (
//     <div className="preview-item">
//       <span>{label}</span>
//       <strong>{value}</strong>
//     </div>
//   );
// }

// function ProcessNode({ title, text }) {
//   return (
//     <div className="process-node">
//       <div className="process-node__accent" />
//       <div>
//         <strong>{title}</strong>
//         <p>{text}</p>
//       </div>
//     </div>
//   );
// }

// function ConfidenceChip({ title, tone }) {
//   return <div className={`confidence-chip confidence-chip--${tone}`}>{title}</div>;
// }

// function Metric({ label, value, text }) {
//   return (
//     <article className="metric-card">
//       <div className="metric-icon">#</div>
//       <div>
//         <div className="kpi-label">{label}</div>
//         <div className="kpi-number">{value}</div>
//         <p>{text}</p>
//       </div>
//     </article>
//   );
// }

// function ProgressStep({ title, active = false }) {
//   return (
//     <div className={`progress-step ${active ? 'is-active' : ''}`}>
//       <span className="progress-step__dot" />
//       <strong>{title}</strong>
//     </div>
//   );
// }

// function QuickAction({ title, text, onClick }) {
//   return (
//     <button className="quick-link quick-link--block" onClick={onClick}>
//       <span>
//         <strong>{title}</strong>
//         <span className="muted quick-link__text">{text}</span>
//       </span>
//     </button>
//   );
// }

// function FilterButton({ label, active, onClick }) {
//   return (
//     <button className={`review-filter ${active ? 'is-active' : ''}`} onClick={onClick}>
//       {label}
//     </button>
//   );
// }

// createRoot(document.getElementById('root')).render(<App />);
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import {
  checkProposalFormat,
  generateProposal,
  getProcurementOrchestration,
  loginCompany,
  normalizeCompanySession,
  onboardCompany,
  uploadPdf,
} from './api';

const ROUTES = ['home', 'onboarding', 'upload', 'processing', 'dashboard', 'proposal', 'review', 'export'];
const STORAGE_KEYS = {
  session: 'datasmithSession',
  docState: 'datasmithDocState',
  proposalResult: 'datasmithProposalResult',
  orchestrationResult: 'datasmithOrchestrationResult',
  feedback: 'datasmithFeedback',
  proposalMode: 'proposalMode',
};

function normalizeFormatSource(value) {
  return value === 'tender' ? 'tender' : 'template';
}

function getFormatSourceLabel(value) {
  return normalizeFormatSource(value) === 'tender' ? 'Tender document' : 'Onboarded template';
}

function getProposalFormatStatus(docState) {
  if (!docState?.doc_id) return 'No tender uploaded';
  if (docState?.proposalFound) {
    return docState?.hasTables ? 'Table-format response form detected' : 'Tender response format detected';
  }
  return 'No format detected';
}

const REVIEW_ITEMS = [
  {
    id: 1,
    tone: 'done',
    category: 'high',
    title: 'Company profile aligned',
    text: 'Registered entity details, sector, and credential summary are already aligned to the tender narrative.',
    status: 'Ready',
  },
  {
    id: 2,
    tone: 'warning',
    category: 'review',
    title: 'Past performance narrative',
    text: 'Similar project references were found, but the wording still needs a reviewer pass before submission.',
    status: 'Needs review',
  },
  {
    id: 3,
    tone: 'danger',
    category: 'missing',
    title: 'Commercial annexure values',
    text: 'Tender-specific pricing fields are still blank and should be completed manually.',
    status: 'Missing input',
  },
];

function getInitialRoute() {
  const hash = window.location.hash.replace('#/', '').replace('#', '');
  return ROUTES.includes(hash) ? hash : 'home';
}

function getStoredJson(key, fallback = null) {
  try {
    return JSON.parse(localStorage.getItem(key) || 'null') || fallback;
  } catch {
    return fallback;
  }
}

function setStoredJson(key, value) {
  if (value === null || value === undefined) {
    localStorage.removeItem(key);
    return;
  }
  localStorage.setItem(key, JSON.stringify(value));
}

function getProposalSections(payload) {
  const candidates = [
    payload?.sections,
    payload?.proposal_sections,
    payload?.proposal_json?.sections,
    Array.isArray(payload?.proposal_json) ? payload.proposal_json : null,
  ];
  const firstArray = candidates.find((value) => Array.isArray(value));
  if (!firstArray) return [];
  return firstArray
    .map((item, index) => {
      if (typeof item === 'string') return item;
      if (typeof item?.title === 'string') return item.title;
      if (typeof item?.heading === 'string') return item.heading;
      if (typeof item?.name === 'string') return item.name;
      return `Section ${index + 1}`;
    })
    .filter(Boolean);
}

function sanitizeProposalResult(nextValue) {
  if (!nextValue) return null;
  const { downloadUrl, raw, ...persisted } = nextValue;
  return persisted;
}

function revokeProposalDownloadUrl(proposalResult) {
  if (proposalResult?.downloadUrl?.startsWith('blob:')) {
    URL.revokeObjectURL(proposalResult.downloadUrl);
  }
}

function App() {
  const [route, setRoute] = useState(getInitialRoute());
  const [session, setSession] = useState(() => getStoredJson(STORAGE_KEYS.session));
  const [proposalMode, setProposalMode] = useState(() => normalizeFormatSource(localStorage.getItem(STORAGE_KEYS.proposalMode)));
  const [docState, setDocState] = useState(() => getStoredJson(STORAGE_KEYS.docState, {}));
  const [proposalResult, setProposalResult] = useState(() => getStoredJson(STORAGE_KEYS.proposalResult));
  const [orchestrationResult, setOrchestrationResult] = useState(() => getStoredJson(STORAGE_KEYS.orchestrationResult));
  const [feedback, setFeedback] = useState(() => getStoredJson(STORAGE_KEYS.feedback, {}));

  const navigate = useCallback((nextRoute) => {
    setRoute(nextRoute);
    window.location.hash = `/${nextRoute}`;
  }, []);

  const guardedNavigate = useCallback((nextRoute) => {
    if (!session && !['home', 'onboarding'].includes(nextRoute)) {
      navigate('onboarding');
      return;
    }
    navigate(nextRoute);
  }, [session, navigate]);

  const clearWorkflowState = useCallback(() => {
    setDocState({});
    setProposalResult((prev) => {
      revokeProposalDownloadUrl(prev);
      return null;
    });
    setFeedback({});
    setOrchestrationResult(null);
    localStorage.removeItem(STORAGE_KEYS.docState);
    localStorage.removeItem(STORAGE_KEYS.proposalResult);
    localStorage.removeItem(STORAGE_KEYS.orchestrationResult);
    localStorage.removeItem(STORAGE_KEYS.feedback);
  }, []);

  const saveSession = useCallback((nextSession) => {
    setSession((currentSession) => {
      const currentCompanyId = currentSession?.company_id;
      const nextCompanyId = nextSession?.company_id;
      if (currentCompanyId && nextCompanyId && currentCompanyId !== nextCompanyId) {
        clearWorkflowState();
      }
      return nextSession;
    });
    setStoredJson(STORAGE_KEYS.session, nextSession);
  }, [clearWorkflowState]);

  const saveDocState = useCallback((nextState) => {
    setDocState(nextState);
    setStoredJson(STORAGE_KEYS.docState, nextState);
  }, []);

  const saveProposalResult = useCallback((nextValue) => {
    setProposalResult((prev) => {
      revokeProposalDownloadUrl(prev);
      return nextValue;
    });
    setStoredJson(STORAGE_KEYS.proposalResult, sanitizeProposalResult(nextValue));
  }, []);

  const saveOrchestrationResult = useCallback((nextValue) => {
    setOrchestrationResult(nextValue);
    setStoredJson(STORAGE_KEYS.orchestrationResult, nextValue);
  }, []);

  const saveFeedback = useCallback((nextValue) => {
    setFeedback(nextValue);
    setStoredJson(STORAGE_KEYS.feedback, nextValue);
  }, []);

  const logout = useCallback(() => {
    clearWorkflowState();
    localStorage.removeItem(STORAGE_KEYS.session);
    setSession(null);
    navigate('onboarding');
  }, [clearWorkflowState, navigate]);

  const setProposalModeStable = useCallback((mode) => {
    const nextMode = normalizeFormatSource(mode);
    setProposalMode(nextMode);
    localStorage.setItem(STORAGE_KEYS.proposalMode, nextMode);
  }, []);

  const sharedProps = {
    session,
    saveSession,
    proposalMode,
    setProposalMode: setProposalModeStable,
    docState,
    saveDocState,
    proposalResult,
    saveProposalResult,
    orchestrationResult,
    saveOrchestrationResult,
    feedback,
    saveFeedback,
    navigate,
    guardedNavigate,
  };

  const page = useMemo(() => {
    const pages = {
      home: <HomePage {...sharedProps} />,
      onboarding: <OnboardingPage {...sharedProps} />,
      upload: <UploadPage {...sharedProps} />,
      processing: <ProcessingPage {...sharedProps} />,
      dashboard: <DashboardPage {...sharedProps} />,
      proposal: <ProposalPage {...sharedProps} />,
      review: <ReviewPage {...sharedProps} />,
      export: <ExportPage {...sharedProps} />,
    };
    return pages[route] || pages.home;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route, session, proposalMode, docState, proposalResult, orchestrationResult, feedback]);

  return (
    <div className="shell">
      <Nav route={route} session={session} navigate={guardedNavigate} logout={logout} />
      {page}
      <Footer navigate={navigate} />
    </div>
  );
}

function Nav({ route, session, navigate, logout }) {
  const items = [
    ['home', 'Overview'],
    ['dashboard', 'Dashboard'],
    ['upload', 'Intake'],
    ['processing', 'Processing'],
    ['review', 'Review'],
    ['export', 'Export'],
  ];

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <button className="brand brand-button" onClick={() => navigate('home')}>
          <span className="brand__mark">D</span>
          <span>
            <span className="brand__eyebrow">Tender Operations</span>
            <span className="brand__title">Datasmith AI</span>
          </span>
        </button>
        <div className="site-nav">
          <nav className="site-nav__links" aria-label="Primary">
            {items.map(([key, label]) => (
              <button
                key={key}
                className={`site-nav__link ${route === key ? 'is-active' : ''}`}
                onClick={() => navigate(key)}
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="nav-actions">
            <label className="nav-search" aria-label="Search workspace">
              <span className="nav-search__icon">/</span>
              <input type="text" placeholder="Search tenders, drafts, or tasks" />
            </label>
            <div className="nav-user">
              <span className="nav-user__label">Workspace</span>
              <strong>{session?.company_name || 'Guest mode'}</strong>
            </div>
            {session ? (
              <button className="btn btn--secondary" onClick={logout}>Logout</button>
            ) : (
              <button className="btn btn--secondary" onClick={() => navigate('onboarding')}>Log In</button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

function Footer({ navigate }) {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div>
          <div className="footer-title">Datasmith AI</div>
          <div className="muted">A focused workspace for tender intake, review, drafting, and export.</div>
        </div>
        <div className="footer-links">
          <button className="subtle-link" onClick={() => navigate('onboarding')}>Onboarding</button>
          <button className="subtle-link" onClick={() => navigate('processing')}>AI Processing</button>
          <button className="subtle-link" onClick={() => navigate('proposal')}>Draft Editor</button>
        </div>
      </div>
    </footer>
  );
}

function HomePage({ navigate, session, proposalMode, docState }) {
  const sections = [
    {
      title: 'Access',
      name: 'Workspace Setup',
      text: 'Create a company workspace, sign in securely, and move into the operating dashboard.',
      items: ['Secure sign-in', 'Workspace setup', 'Team context', 'Dashboard access'],
      route: 'onboarding',
    },
    {
      title: 'Intake',
      name: 'Tender Upload',
      text: 'Add the tender package, capture source documents, and prepare the submission for analysis.',
      items: ['Document intake', 'File tracking', 'Requirement capture', 'Submission context'],
      route: 'upload',
    },
    {
      title: 'Format',
      name: 'Response Structure',
      text: 'Choose whether the response follows the tender format or your internal proposal standard.',
      items: ['Tender-led structure', 'Company template', `Current mode: ${getFormatSourceLabel(proposalMode)}`],
      route: 'upload',
    },
    {
      title: 'Analysis',
      name: 'Document Processing',
      text: 'Review structure, surface requirements, and prepare a draft with reusable company information.',
      items: ['Structure review', 'Requirement extraction', 'Company knowledge', 'Draft preparation'],
      route: 'processing',
    },
    {
      title: 'Validation',
      name: 'Content Review',
      text: 'Separate approved content, items needing review, and unresolved gaps before sign-off.',
      items: ['Ready content', 'Needs review', 'Missing information'],
      route: 'review',
    },
    {
      title: 'Delivery',
      name: 'Draft And Export',
      text: 'Refine the draft, confirm approvals, package exports, and capture operator feedback.',
      items: ['Draft editor', 'Approvals', 'Editable export', 'Feedback'],
      route: 'export',
    },
  ];

  const workflowStages = [
    { title: '1. Access', desc: 'Authenticate and open the workspace.', state: session ? 'Ready' : 'Pending' },
    { title: '2. Intake', desc: docState?.fileName || 'Tender file not uploaded yet.', state: docState?.fileName ? 'Captured' : 'Waiting' },
    { title: '3. Structure', desc: `${getFormatSourceLabel(proposalMode)} selected.`, state: 'Active' },
    { title: '4. Processing', desc: 'Extract sections, requirements, and draft content.', state: 'Queued' },
    { title: '5. Review', desc: 'Validate ready content and resolve missing inputs.', state: 'Queued' },
    { title: '6. Export', desc: 'Approve the final draft and prepare submission files.', state: 'Queued' },
  ];

  return (
    <main className="page-main">
      <section className="hero hero--dashboard">
        <div className="hero-copy">
          <div className="eyebrow-chip">Datasmith AI Workspace</div>
          <h1>Run the full tender response workflow from a focused blue workspace.</h1>
          <p>
            Your original workflow stays intact, but the interface now pushes toward a more product-like dashboard:
            sharper hierarchy, clearer task states, and less generic presentation.
          </p>
          <div className="hero-actions">
            <button className="btn btn--primary" onClick={() => navigate(session ? 'dashboard' : 'onboarding')}>
              {session ? 'Open Dashboard' : 'Start Onboarding'}
            </button>
            <button className="btn btn--ghost" onClick={() => navigate('upload')}>Open Tender Intake</button>
          </div>
          <div className="hero-metrics">
            <MiniMetric label="Workspace" value={session ? 'Active' : 'Setup required'} />
            <MiniMetric label="Tender file" value={docState?.fileName || 'No upload yet'} />
            <MiniMetric label="Response mode" value={getFormatSourceLabel(proposalMode)} />
          </div>
        </div>

        <div className="workflow-board">
          <div className="workflow-board__header">Workflow Status</div>
          <div className="workflow-list">
            {workflowStages.map((stage) => (
              <FlowPill
                key={stage.title}
                tone={
                  stage.state === 'Pending' || stage.state === 'Waiting'
                    ? 'soft'
                    : stage.state === 'Captured' || stage.state === 'Active'
                    ? 'brand'
                    : 'success'
                }
                title={stage.title}
                subtitle={stage.desc}
                badge={stage.state}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="page-section">
        <PageHead
          title="Workflow Modules"
          text="Every screen below still follows the workflow you gave, but it now feels more like a real operations product."
        />
        <div className="section-grid">
          {sections.map((section) => (
            <button key={section.name} className="section-card" onClick={() => navigate(section.route)}>
              <div className="section-card__eyebrow">{section.title}</div>
              <h3>{section.name}</h3>
              <p>{section.text}</p>
              <div className="tag-row">
                {section.items.map((item) => <span key={item} className="tag">{item}</span>)}
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="page-section page-section--compact">
        <div className="dashboard-table-card">
          <div className="table-card__head">
            <div>
              <div className="stack-panel__eyebrow">Current Workflow</div>
              <h2 className="panel-title">Tender response journey</h2>
            </div>
            <button className="btn btn--ghost" onClick={() => navigate(session ? 'dashboard' : 'onboarding')}>
              {session ? 'Open Dashboard' : 'Set Up Workspace'}
            </button>
          </div>
          <div className="workflow-track">
            {workflowStages.map((stage) => (
              <div key={stage.title} className="workflow-row">
                <strong className="workflow-row__title">{stage.title}</strong>
                <span className="workflow-row__desc">{stage.desc}</span>
                <span className={`status-pill status-pill--${
                  stage.state === 'Pending' || stage.state === 'Waiting' ? 'review'
                  : stage.state === 'Captured' || stage.state === 'Active' ? 'done'
                  : 'review'
                }`}>{stage.state}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function OnboardingPage({ session, saveSession, navigate }) {
  const [mode, setMode] = useState('login');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ type: 'info', text: 'Sign in to an existing workspace or create a new one.' });
  const signupFilesRef = useRef({});

  async function handleLogin(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    setLoading(true);
    setStatus({ type: 'info', text: 'Signing in...' });
    try {
      const payload = await loginCompany({ email: data.email, password: data.password });
      const nextSession = normalizeCompanySession(payload, { contact_email: data.email });
      saveSession(nextSession);
      setStatus({ type: 'success', text: `Welcome back${nextSession.company_name ? ', ' + nextSession.company_name : ''}. Redirecting...` });
      setTimeout(() => navigate('dashboard'), 700);
    } catch (error) {
      setStatus({ type: 'error', text: error.message || 'Login failed. Check credentials and try again.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleSignup(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget).entries());
    // Attach File objects from ref (FormData won't capture file inputs as File unless named correctly)
    data.knowledge_base = signupFilesRef.current.knowledge_base;
    data.proposal_template = signupFilesRef.current.proposal_template;
    setLoading(true);
    setStatus({ type: 'info', text: 'Creating workspace...' });
    try {
      const payload = await onboardCompany(data);
      const nextSession = normalizeCompanySession(payload, {
        company_name: data.company_name,
        contact_email: data.contact_email,
      });
      saveSession(nextSession);
      setStatus({ type: 'success', text: 'Workspace created. Redirecting to dashboard...' });
      setTimeout(() => navigate('dashboard'), 700);
    } catch (error) {
      setStatus({ type: 'error', text: error.message || 'Unable to create workspace right now.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-shell auth-shell--elevated">
        <aside className="auth-hero auth-hero--flow">
          <div className="auth-hero__eyebrow">Workspace Access</div>
          <h1 className="page-title">Set up the company workspace before work begins.</h1>
          <p className="page-subtitle">
            Keep access simple: returning users sign in, new teams create a workspace, and both land in the same
            operating view for intake and review.
          </p>
          <div className="auth-points">
            <div className="auth-point">
              <div className="auth-point__icon">01</div>
              <div>
                <strong>Access your workspace</strong>
                <p className="muted">Sign in to an existing account or create a new company workspace.</p>
              </div>
            </div>
            <div className="auth-point">
              <div className="auth-point__icon">02</div>
              <div>
                <strong>Store company context</strong>
                <p className="muted">Keep core contact, knowledge base, and template details in one place.</p>
              </div>
            </div>
            <div className="auth-point">
              <div className="auth-point__icon">03</div>
              <div>
                <strong>Continue to operations</strong>
                <p className="muted">Move directly into tender intake, processing, review, and export.</p>
              </div>
            </div>
          </div>
        </aside>

        <section className="auth-card auth-card--clean">
          <div className="auth-tabs">
            <button className={`auth-tab ${mode === 'login' ? 'is-active' : ''}`} onClick={() => setMode('login')}>Log In</button>
            <button className={`auth-tab ${mode === 'signup' ? 'is-active' : ''}`} onClick={() => setMode('signup')}>Create Workspace</button>
          </div>
          <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>

          {mode === 'login' ? (
            <form className="auth-form" onSubmit={handleLogin}>
              <TextField label="Email" name="email" type="email" placeholder="you@company.com" />
              <TextField label="Password" name="password" type="password" placeholder="Enter your password" />
              <button className="btn btn--primary auth-submit" disabled={loading}>
                {loading ? 'Logging in…' : 'Log In To Workspace'}
              </button>
            </form>
          ) : (
            <form className="auth-form" onSubmit={handleSignup}>
              <div className="field-grid">
                <TextField label="Company name" name="company_name" placeholder="ABC Infra Pvt Ltd" />
                <TextField label="Industry" name="industry" placeholder="Infrastructure / Consulting / Energy" />
              </div>
              <div className="field-grid">
                <TextField label="Contact email" name="contact_email" type="email" placeholder="ops@company.com" />
                <TextField label="Contact phone" name="contact_phone" placeholder="+91 98765 43210" />
              </div>
              <TextField label="Password" name="password" type="password" placeholder="Create a strong password" />
              <div className="field-grid">
                <FileField
                  label="Knowledge base"
                  name="knowledge_base"
                  onChange={(file) => { signupFilesRef.current.knowledge_base = file; }}
                />
                <FileField
                  label="Proposal template"
                  name="proposal_template"
                  onChange={(file) => { signupFilesRef.current.proposal_template = file; }}
                />
              </div>
              <button className="btn btn--primary auth-submit" disabled={loading}>
                {loading ? 'Creating workspace…' : 'Create Workspace'}
              </button>
            </form>
          )}
        </section>
      </section>
    </main>
  );
}

function UploadPage({ session, docState, saveDocState, proposalMode, setProposalMode, guardedNavigate, saveProposalResult, saveFeedback }) {
  const [fileName, setFileName] = useState(docState?.fileName || '');
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState({ type: 'info', text: 'Choose the tender document to begin intake.' });

  async function handleUpload(event) {
    event.preventDefault();
    if (!selectedFile) {
      setStatus({ type: 'error', text: 'Choose a tender PDF first.' });
      return;
    }
    if (!session?.company_id) {
      setStatus({ type: 'error', text: 'Create or access a workspace before uploading a tender.' });
      return;
    }
    setStatus({ type: 'info', text: 'Uploading tender document…' });
    try {
      const payload = await uploadPdf({ companyId: session.company_id, file: selectedFile });
      saveProposalResult(null);
      saveFeedback({});
      const proposalFound = Boolean(payload?.proposal_found);
      const formatSource = proposalFound ? 'tender' : 'template';
      setProposalMode(formatSource);
      const nextState = {
        fileName,
        fileUrl: payload?.file_url || payload?.tender_file_url || '',
        doc_id: payload?.doc_id || payload?.id || `DOC-${Date.now().toString().slice(-6)}`,
        uploadSummary: payload?.message || `Tender captured with ${payload?.total_chunks || 0} extracted chunks.`,
        selectedMode: formatSource,
        totalChunks: payload?.total_chunks || 0,
        textChunks: payload?.text_chunks || 0,
        tableChunks: payload?.table_chunks || 0,
        hasTables: Boolean(payload?.has_tables ?? (payload?.table_chunks > 0)),
        proposalFound,
        proposalSections: getProposalSections(payload),
        raw: payload,
      };
      saveDocState(nextState);
      setStatus({ type: 'success', text: 'Tender captured. Moving to processing…' });
      setTimeout(() => guardedNavigate('processing'), 650);
    } catch (error) {
      setStatus({ type: 'error', text: error.message || 'Unable to upload tender right now.' });
    }
  }

  return (
    <main className="page-main page-section">
      <PageHead
        title="Tender Intake"
        text="Upload the source tender, confirm the response structure, and prepare the file for processing."
      />

      <section className="upload-shell">
        <div className="steppers">
          <StepCard index="1" title="Upload documents" text="Tender PDF and annexures" active />
          <StepCard index="2" title="Parse documents" text="Detect sections and tables" />
          <StepCard index="3" title="Extract information" text="Map compliance and requirements" />
          <StepCard index="4" title="Generate summary" text="Prepare the AI handoff" />
        </div>

        <div className="upload-grid">
          <form className="dropzone dropzone--tall" onSubmit={handleUpload}>
            <div className="dropzone__icon">PDF</div>
            <h2 className="panel-title">Upload tender document</h2>
            <p className="section-subtitle">Add the primary tender PDF to initialize the working file and document context.</p>
            <div className="field">
              <label>
                Tender PDF
                <input
                  type="file"
                  accept=".pdf"
                  required
                  onChange={(event) => {
                    const file = event.target.files?.[0] || null;
                    setSelectedFile(file);
                    setFileName(file?.name || '');
                  }}
                />
              </label>
            </div>
            <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>
            <button className="btn btn--primary" type="submit">Continue To Processing</button>
          </form>

          <aside className="stack-panel">
            <div className="stack-panel__section">
              <div className="stack-panel__eyebrow">Response Structure</div>
              <h3>Format source is selected after upload</h3>
              <div className="info-note">
                Once parsing finishes, the next screen enables the tender format only when a response form is detected.
              </div>
            </div>

            <div className="stack-panel__section">
              <div className="stack-panel__eyebrow">Parsed outcome preview</div>
              <div className="preview-list">
                <PreviewItem label="Uploaded file" value={fileName || 'No file chosen yet'} />
                <PreviewItem label="Format source" value={getFormatSourceLabel(proposalMode)} />
                <PreviewItem label="Document ID" value={docState?.doc_id || 'Will be assigned after upload'} />
                <PreviewItem label="Next step" value="Document processing" />
              </div>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

function ProcessingPage({ session, docState, proposalMode, setProposalMode, saveDocState, saveProposalResult, saveOrchestrationResult, guardedNavigate }) {
  const [status, setStatus] = useState({ type: 'info', text: 'Review the extraction stages and generate the first draft.' });
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [formatSource, setFormatSource] = useState(() => {
    if (docState?.proposalFound) {
      return normalizeFormatSource(docState?.selectedMode || 'tender');
    }
    return 'template';
  });

  useEffect(() => {
    const nextSource = docState?.proposalFound
      ? normalizeFormatSource(docState?.selectedMode || 'tender')
      : 'template';
    setFormatSource(nextSource);
    setProposalMode(nextSource);
  }, [docState?.doc_id, docState?.proposalFound, docState?.selectedMode, setProposalMode]);

  useEffect(() => {
    if (!docState?.doc_id) return undefined;
    let active = true;
    checkProposalFormat({ docId: docState.doc_id })
      .then((payload) => {
        if (!active) return;
        const proposalFound = Boolean(payload?.proposal_found);
        const nextSource = proposalFound ? normalizeFormatSource(docState?.selectedMode || 'tender') : 'template';
        const nextState = { ...docState, proposalFound, hasTables: Boolean(payload?.has_tables), selectedMode: nextSource };
        saveDocState(nextState);
        setProposalMode(nextSource);
        setFormatSource(nextSource);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [docState?.doc_id]);

  function handleFormatSourceChange(nextSource) {
    const normalizedSource = docState?.proposalFound ? normalizeFormatSource(nextSource) : 'template';
    setFormatSource(normalizedSource);
    setProposalMode(normalizedSource);
    saveDocState({ ...docState, selectedMode: normalizedSource });
  }

  async function handleGenerate() {
    if (!docState?.fileName) {
      setStatus({ type: 'error', text: 'Upload a tender first so the processing flow has input.' });
      return;
    }
    if (!session?.company_id || !docState?.doc_id) {
      setStatus({ type: 'error', text: 'Workspace or document details are missing.' });
      return;
    }
    const effectiveFormatSource = docState?.proposalFound ? formatSource : 'template';
    setLoading(true);
    setStatus({ type: 'info', text: 'Generating proposal…' });
    try {
      const payload = await generateProposal({
        companyId: session.company_id,
        docId: docState.doc_id,
        formatSource: effectiveFormatSource,
      });
      const sections = docState?.proposalSections?.length
        ? docState.proposalSections
        : [
            'Executive summary aligned to tender objectives',
            'Eligibility and compliance checklist',
            'Past experience and delivery capability',
            'Team structure and implementation approach',
          ];
      const nextDocState = { ...docState, selectedMode: effectiveFormatSource };
      saveDocState(nextDocState);
      setProposalMode(effectiveFormatSource);

      const result = {
        title: payload?.filename || 'generated_proposal.docx',
        companyNarrative: effectiveFormatSource === 'tender'
          ? 'The backend detected a proposal structure in the tender and generated the draft against that format.'
          : 'The backend generated the draft using the company template for this workspace.',
        proposalMode: effectiveFormatSource,
        tenderName: docState.fileName,
        docId: docState.doc_id,
        companyId: session.company_id,
        sections,
        downloadUrl: payload.downloadUrl,
        filename: payload.filename,
        blob: payload.blob,
      };
      try {
        const orchestration = await getProcurementOrchestration({ docId: docState.doc_id });
        saveOrchestrationResult(orchestration);
        result.orchestrationSummary = orchestration?.summary;
      } catch {
        saveOrchestrationResult(null);
      }

      saveProposalResult(result);
      setPreviewData(result);
      setStatus({ type: 'success', text: 'Draft ready. Vendor RFQs, compliance scoring, reuse intelligence, and deadline alerts are now orchestrated.' });
      setShowPreview(true);
    } catch (error) {
      setStatus({ type: 'error', text: error.message || 'Unable to generate the draft right now.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-main page-section">
      <PageHead
        title="Document Processing"
        text="Track the core extraction stages and generate the first response draft from the tender package."
      />

      <section className="processing-layout">
        <div className="processing-column">
          <div className="processing-shell">
            <div className="processing-shell__header">Processing Stages</div>
            <div className="processing-track">
              <ProcessNode title="Identify Tender Structure" text="Review sections, annexures, mandatory forms, and formatting rules." />
              <ProcessNode title="Extract Tender Data" text="Capture fields, milestones, evaluation criteria, and submission deadlines." />
              <ProcessNode title="Match Company Knowledge" text="Bring in reusable credentials, references, and prior response material." />
              <ProcessNode title="Prepare Draft Content" text="Assemble the first draft for reviewer validation." />
            </div>
          </div>
        </div>

        <aside className="side-rail">
          <div className="timeline-card">
            <div className="stack-panel__eyebrow">Current input</div>
            <PreviewItem label="Tender file" value={docState?.fileName || 'No upload yet'} />
            <PreviewItem label="Format source" value={getFormatSourceLabel(proposalMode)} />
            <PreviewItem label="Document ID" value={docState?.doc_id || 'Document not captured yet'} />
            <PreviewItem label="Detected format" value={getProposalFormatStatus(docState)} />
          </div>
          <div className="timeline-card">
            <div className="stack-panel__eyebrow">Proposal format</div>
            <div className="format-source-group" role="radiogroup" aria-label="Proposal format source">
              <label className={`format-source-option ${formatSource === 'tender' ? 'is-selected' : ''} ${!docState?.proposalFound ? 'is-disabled' : ''}`}>
                <input
                  type="radio"
                  name="format_source"
                  value="tender"
                  checked={formatSource === 'tender'}
                  disabled={!docState?.proposalFound || loading}
                  onChange={() => handleFormatSourceChange('tender')}
                />
                <span>Use response format from the tender document itself</span>
              </label>
              <label className={`format-source-option ${formatSource === 'template' ? 'is-selected' : ''}`}>
                <input
                  type="radio"
                  name="format_source"
                  value="template"
                  checked={formatSource === 'template'}
                  disabled={loading}
                  onChange={() => handleFormatSourceChange('template')}
                />
                <span>Use my onboarded proposal template</span>
              </label>
            </div>
          </div>
          <div className="timeline-card">
            <div className="stack-panel__eyebrow">Review states</div>
            <div className="confidence-row">
              <ConfidenceChip tone="success" title="High Confidence" />
              <ConfidenceChip tone="warning" title="Needs Review" />
              <ConfidenceChip tone="danger" title="Missing Information" />
            </div>
          </div>
          <div className={`auth-message auth-message--${status.type}`}>{status.text}</div>
          {loading ? (
            <div className="loading-note" role="status" aria-live="polite">
              <span className="spinner" aria-hidden="true" />
              <span>Generating proposal…</span>
            </div>
          ) : null}
          <div className="inline-actions">
            <button className="btn btn--primary" onClick={handleGenerate} disabled={loading}>
              {loading ? 'Generating…' : 'Generate Proposal'}
            </button>
            <button className="btn btn--ghost" onClick={() => guardedNavigate('review')} disabled={loading}>
              Open Review
            </button>
          </div>
        </aside>
      </section>

      {/* ── Proposal Preview Panel ── */}
      {showPreview && previewData && (
        <ProposalPreviewPanel
          previewData={previewData}
          onViewDraft={() => guardedNavigate('proposal')}
          onDownload={() => {
            if (previewData.downloadUrl) {
              const link = document.createElement('a');
              link.href = previewData.downloadUrl;
              link.download = previewData.filename || 'generated_proposal.docx';
              document.body.appendChild(link);
              link.click();
              link.remove();
            }
          }}
          onDismiss={() => setShowPreview(false)}
        />
      )}
    </main>
  );
}

/* ── Proposal Preview Panel Component ── */
function ProposalPreviewPanel({ previewData, onViewDraft, onDownload, onDismiss }) {
  return (
    <section className="preview-panel" aria-label="Generated proposal preview">
      <div className="preview-panel__header">
        <div>
          <div className="stack-panel__eyebrow">Generated Proposal</div>
          <h2 className="panel-title">{previewData.title}</h2>
        </div>
        <div className="inline-actions">
          <button className="btn btn--ghost" onClick={onDismiss} aria-label="Dismiss preview">Dismiss</button>
          <button className="btn btn--ghost" onClick={onDownload} disabled={!previewData.downloadUrl}>
            ↓ Download .docx
          </button>
          <button className="btn btn--primary" onClick={onViewDraft}>Open Draft Editor →</button>
        </div>
      </div>

      <div className="preview-panel__body">
        {/* Left: doc outline */}
        <div className="preview-panel__sidebar">
          <div className="stack-panel__eyebrow" style={{ marginBottom: '0.75rem' }}>Document outline</div>
          <div className="outline-list">
            {previewData.sections.map((section, i) => (
              <div key={i} className="outline-link outline-link--numbered">
                <span className="outline-link__num">{String(i + 1).padStart(2, '0')}</span>
                <span>{section}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '1.2rem' }}>
            <div className="stack-panel__eyebrow" style={{ marginBottom: '0.6rem' }}>Metadata</div>
            <div className="preview-list">
              <PreviewItem label="Tender" value={previewData.tenderName} />
              <PreviewItem label="Format" value={getFormatSourceLabel(previewData.proposalMode)} />
              <PreviewItem label="Doc ID" value={previewData.docId} />
            </div>
          </div>
        </div>

        {/* Right: doc preview */}
        <div className="preview-panel__doc">
          <div className="doc-preview">
            <div className="doc-preview__page">
              <div className="doc-preview__watermark">DRAFT</div>
              <div className="doc-preview__titlepage">
                <div className="doc-preview__co-label">Proposal prepared by</div>
                <div className="doc-preview__co-name">{previewData.companyId}</div>
                <h1 className="doc-preview__title">Tender Response Proposal</h1>
                <p className="doc-preview__subtitle">In response to: {previewData.tenderName}</p>
                <div className="doc-preview__meta-row">
                  <span className="tag">Format: {getFormatSourceLabel(previewData.proposalMode)}</span>
                  <span className="tag">Sections: {previewData.sections.length}</span>
                  <span className="tag">Status: Draft</span>
                </div>
              </div>

              <div className="doc-preview__divider" />

              <div className="doc-preview__narrative">
                <p>{previewData.companyNarrative}</p>
              </div>

              {previewData.sections.slice(0, 4).map((section, i) => (
                <div key={i} className="doc-preview__section">
                  <h3 className="doc-preview__section-title">{section}</h3>
                  <div className="doc-preview__placeholder-lines">
                    <div className="doc-preview__line doc-preview__line--full" />
                    <div className="doc-preview__line doc-preview__line--full" />
                    <div className="doc-preview__line doc-preview__line--3q" />
                    <div className="doc-preview__line doc-preview__line--half" />
                  </div>
                </div>
              ))}

              {previewData.sections.length > 4 && (
                <div className="doc-preview__more">
                  + {previewData.sections.length - 4} more sections in the full document
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DashboardPage({ session, docState, proposalMode, guardedNavigate, proposalResult, orchestrationResult }) {
  const orchestrationSummary = orchestrationResult?.summary || {};
  const queue = [
    {
      name: docState?.fileName || 'New tender package',
      owner: session?.company_name || 'Workspace',
      stage: docState?.fileName ? 'Processing ready' : 'Awaiting upload',
      progress: proposalResult ? 'Draft available' : docState?.fileName ? 'Queued for generation' : 'No document',
      due: proposalResult ? 'Review next' : 'Upload required',
    },
    {
      name: 'Compliance review',
      owner: 'Review team',
      stage: 'Validation',
      progress: 'Needs review',
      due: 'Before export',
    },
    {
      name: 'Commercial annexures',
      owner: 'Negotiation agents',
      stage: 'Vendor sourcing',
      progress: orchestrationSummary.vendor_rfq_count ? `${orchestrationSummary.vendor_rfq_count} RFQs queued` : 'Awaiting RFQs',
      due: 'Quote comparison',
    },
    {
      name: 'Deadline orchestration',
      owner: 'Submission owner',
      stage: 'Reminder automation',
      progress: orchestrationSummary.deadline_alerts ? `${orchestrationSummary.deadline_alerts} alerts armed` : 'Deadline needed',
      due: 'Escalation path',
    },
  ];

  return (
    <main className="page-main page-section">
      <PageHead
        title="Workspace Dashboard"
        text="Operate the proposal workflow from one place: intake, generation, validation, and release."
        action={<button className="btn btn--primary" onClick={() => guardedNavigate('upload')}>New Tender</button>}
      />

      <section className="kpi-grid">
        <Metric label="Company" value={session?.company_name || 'Workspace'} text={session?.contact_email || 'No workspace email yet'} />
        <Metric label="Industry" value={session?.industry || 'Not set'} text={session?.contact_phone || 'Contact pending'} />
        <Metric label="Tender" value={docState?.fileName || 'No upload yet'} text={docState?.doc_id || 'Document ID pending'} />
        <Metric label="Format source" value={getFormatSourceLabel(proposalMode)} text={getProposalFormatStatus(docState)} />
        <Metric label="Compliance" value={`${Math.round(orchestrationSummary.average_compliance || 0)}%`} text="Post-generation clause coverage score" />
        <Metric label="Vendor RFQs" value={orchestrationSummary.vendor_rfq_count || 0} text="Supplier quote requests queued" />
      </section>

      <section className="dashboard-showcase">
        <article className="dashboard-main">
          <div className="dashboard-main__header">
            <div>
              <div className="stack-panel__eyebrow">Operations Queue</div>
              <h2 className="panel-title">Tender response tracking</h2>
            </div>
            <span className="status-pill status-pill--review">
              {proposalResult ? 'Draft available' : 'Waiting for generation'}
            </span>
          </div>

          <div className="progress-band">
            <ProgressStep title="Onboard" active />
            <ProgressStep title="Upload" active={Boolean(docState?.fileName)} />
            <ProgressStep title="Process" active={Boolean(proposalResult)} />
            <ProgressStep title="Orchestrate" active={Boolean(orchestrationResult)} />
            <ProgressStep title="Review" active={Boolean(orchestrationResult)} />
            <ProgressStep title="Export" />
          </div>

          <div className="dashboard-table">
            <div className="dashboard-table__head">
              <span>Workflow Item</span>
              <span>Owner</span>
              <span>Stage</span>
              <span>Status</span>
              <span>Next Move</span>
            </div>
            {queue.map((item) => (
              <div key={item.name} className="dashboard-table__row">
                <strong>{item.name}</strong>
                <span>{item.owner}</span>
                <span>{item.stage}</span>
                <StatusToken
                  tone={
                    item.progress.includes('Draft') ? 'done'
                    : item.progress.includes('Missing') ? 'danger'
                    : item.progress.includes('Needs') ? 'warning'
                    : 'review'
                  }
                  label={item.progress}
                />
                <span>{item.due}</span>
              </div>
            ))}
          </div>

          <div className="quick-grid">
            <QuickAction title="Upload tender" text="Bring in the latest tender document and choose the structure path." onClick={() => guardedNavigate('upload')} />
            <QuickAction title="Open draft" text="Review the draft workspace and continue refining the response." onClick={() => guardedNavigate('proposal')} />
            <QuickAction title="Run review" text="Inspect ready content, flagged sections, and missing inputs." onClick={() => guardedNavigate('review')} />
          </div>
        </article>

        <aside className="dashboard-aside">
          <div className="sidebar-card sidebar-card--accent">
            <div className="stack-panel__eyebrow">Primary Action</div>
            <h3>Move the current response forward</h3>
            <p>Use the next action below to continue the workflow without losing context.</p>
            <button className="btn btn--primary" onClick={() => guardedNavigate(docState?.fileName ? 'processing' : 'upload')}>
              {docState?.fileName ? 'Open Processing' : 'Start Intake'}
            </button>
          </div>
          <div className="sidebar-card">
            <div className="stack-panel__eyebrow">Active Procurement</div>
            <ul className="plain-list">
              <li>Negotiation agents split BOQ and requirement rows by category</li>
              <li>Supplier RFQs are queued with price, lead time, and compliance requests</li>
              <li>Best quote benchmarks feed back into commercial proposal review</li>
              <li>Deadline reminders escalate missing information to owners</li>
            </ul>
          </div>
          <div className="sidebar-card">
            <div className="stack-panel__eyebrow">Workspace Focus</div>
            <ul className="plain-list">
              <li>Keep workspace details current before each response cycle</li>
              <li>Use a consistent intake structure across tender submissions</li>
              <li>Review flagged sections before approving the draft</li>
              <li>Track export readiness and unresolved commercial inputs</li>
            </ul>
          </div>
        </aside>
      </section>
    </main>
  );
}

function ProposalPage({ proposalResult, docState, orchestrationResult, guardedNavigate }) {
  const outline = proposalResult?.sections?.length
    ? proposalResult.sections
    : ['Executive Summary', 'Eligibility And Compliance', 'Technical Approach', 'Past Performance', 'Commercial Inputs'];

  return (
    <main className="page-main page-section">
      <PageHead
        title="Draft Editor"
        text="Review the draft, refine key sections, and move the response toward approval."
      />

      <section className="proposal-workspace">
        <aside className="proposal-sidebar">
          <div className="sidebar-card">
            <div className="stack-panel__eyebrow">Draft outline</div>
            <div className="outline-list">
              {outline.map((item, i) => (
                <div key={i} className="outline-link outline-link--numbered">
                  <span className="outline-link__num">{String(i + 1).padStart(2, '0')}</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="sidebar-card">
            <div className="stack-panel__eyebrow">Draft metadata</div>
            <PreviewItem label="Tender" value={docState?.fileName || 'Not uploaded'} />
            <PreviewItem label="Draft state" value={proposalResult ? 'Draft ready' : 'Awaiting generation'} />
            <PreviewItem label="Compliance score" value={`${Math.round(orchestrationResult?.summary?.average_compliance || 0)}%`} />
            <PreviewItem label="RFQs queued" value={orchestrationResult?.summary?.vendor_rfq_count || 0} />
            {proposalResult?.downloadUrl && (
              <button
                className="btn btn--ghost"
                style={{ marginTop: '0.5rem', width: '100%' }}
                onClick={() => {
                  const link = document.createElement('a');
                  link.href = proposalResult.downloadUrl;
                  link.download = proposalResult.filename || 'generated_proposal.docx';
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                }}
              >
                ↓ Download .docx
              </button>
            )}
          </div>
          <div className="sidebar-card">
            <div className="stack-panel__eyebrow">Procurement Agents</div>
            <div className="outline-list">
              {(orchestrationResult?.multi_agent_negotiation || []).slice(0, 5).map((item, i) => (
                <div key={`${item.requirement_id}-${i}`} className="outline-link">
                  <span>{item.agent}</span>
                  <StatusToken label={item.status.replaceAll('_', ' ')} tone={item.status.includes('dispatched') ? 'done' : 'warning'} />
                </div>
              ))}
              {!orchestrationResult && <div className="muted">Generate a proposal to activate supplier orchestration.</div>}
            </div>
          </div>
        </aside>

        <article className="editor-card editor-card--rich">
          <div className="proposal-banner">
            <div>
              <div className="stack-panel__eyebrow">Proposal Draft</div>
              <h2 className="panel-title">Refine sections, confirm content quality, and prepare for release</h2>
            </div>
            <div className="inline-actions">
              <button className="btn btn--ghost" onClick={() => guardedNavigate('review')}>Open Review</button>
              <button className="btn btn--primary" onClick={() => guardedNavigate('export')}>Approve Draft</button>
            </div>
          </div>

          <div className="doc-content">
            <section className="content-block">
              <h3>Executive Summary</h3>
              <p>{proposalResult?.companyNarrative || 'Generate a draft to populate this section.'}</p>
              <div className="suggestion">
                Suggested insertion: tailor the executive summary to the tender owner, delivery horizon, and differentiators.
              </div>
            </section>

            <section className="content-block">
              <h3>Eligibility And Compliance</h3>
              <div className="callout">
                Compliance-aligned content is grouped here so reviewers can verify requirements quickly.
              </div>
            </section>

            <section className="content-block">
              <h3>Technical Approach</h3>
              <p>
                Use this workspace to shape delivery approach, methodology, and staffing into a more polished final response,
                while keeping review and approval close at hand.
              </p>
            </section>

            <section className="content-block">
              <h3>Commercial Inputs</h3>
              <div className="review-block">
                Missing-value placeholders should remain clearly visible so the reviewer knows what still needs manual input.
              </div>
            </section>
          </div>
        </article>
      </section>
    </main>
  );
}

function ReviewPage({ orchestrationResult, guardedNavigate }) {
  const [filter, setFilter] = useState('all');
  const complianceItems = (orchestrationResult?.compliance_scoring?.sections || []).slice(0, 12).map((item, index) => ({
    id: `compliance-${index}`,
    tone: item.status === 'compliant' ? 'done' : item.status === 'gap' ? 'danger' : 'warning',
    category: item.status === 'compliant' ? 'high' : item.status === 'gap' ? 'missing' : 'review',
    title: item.section_title || `Requirement ${index + 1}`,
    text: `${item.score}% compliance - ${item.recommendation}`,
    status: item.status.replaceAll('_', ' '),
  }));
  const reviewItems = complianceItems.length ? complianceItems : REVIEW_ITEMS;
  const filtered = reviewItems.filter((item) => filter === 'all' || item.category === filter);

  return (
    <main className="page-main page-section">
      <PageHead
        title="Review And Approval"
        text="Separate approved content, flagged sections, and missing inputs before release."
      />

      <section className="review-shell">
        <div className="review-filter-row">
          <FilterButton label="All" active={filter === 'all'} onClick={() => setFilter('all')} />
          <FilterButton label="High confidence" active={filter === 'high'} onClick={() => setFilter('high')} />
          <FilterButton label="Needs review" active={filter === 'review'} onClick={() => setFilter('review')} />
          <FilterButton label="Missing info" active={filter === 'missing'} onClick={() => setFilter('missing')} />
        </div>

        <div className="review-grid review-grid--full">
          {filtered.map((item) => (
            <article key={item.id} className="review-card">
              <div className="review-card__head">
                <h3>{item.title}</h3>
                <span className={`status-pill status-pill--${item.tone}`}>{item.status}</span>
              </div>
              <div className={`issue-strip issue-strip--${item.tone === 'danger' ? 'critical' : item.tone === 'done' ? 'ok' : 'warning'}`}>
                {item.text}
              </div>
            </article>
          ))}
        </div>

        <section className="approval-band">
          <div>
            <div className="stack-panel__eyebrow">Approval</div>
            <h2 className="panel-title">Confirm the draft, request revisions, or move directly to export.</h2>
          </div>
          <div className="inline-actions">
            <button className="btn btn--ghost" onClick={() => guardedNavigate('proposal')}>Request Changes</button>
            <button className="btn btn--primary" onClick={() => guardedNavigate('export')}>Approve And Continue</button>
          </div>
        </section>
      </section>
    </main>
  );
}

function ExportPage({ feedback, saveFeedback, guardedNavigate, proposalResult }) {
  const [message, setMessage] = useState(
    Object.keys(feedback || {}).length ? 'Saved feedback is available below.' : 'Feedback has not been saved yet.'
  );

  function handleFeedback(event) {
    event.preventDefault();
    const nextFeedback = Object.fromEntries(new FormData(event.currentTarget).entries());
    saveFeedback(nextFeedback);
    setMessage('Feedback saved successfully.');
    event.currentTarget.reset();
  }

  return (
    <main className="page-main page-section">
      <PageHead
        title="Export And Feedback"
        text="Prepare the submission package and capture notes that improve the next response cycle."
      />

      <section className="export-grid export-grid--wide">
        <article className="export-card">
          <div className="stack-panel__eyebrow">Export</div>
          <h2 className="panel-title">Download editable proposal package</h2>
          <div className="export-hero">
            <div className="export-hero__card">
              <strong>Download Editable Proposal</strong>
              <span>Word (.docx), Excel (.xlsx), and final submission bundle</span>
            </div>
            <div className="tag-row">
              <span className="tag">Word (.docx)</span>
              <span className="tag">Excel (.xlsx)</span>
              <span className="tag">Version history saved</span>
            </div>
          </div>
          <div className="inline-actions">
            <button className="btn btn--ghost" onClick={() => guardedNavigate('proposal')}>Back To Draft</button>
            <button
              className="btn btn--primary"
              onClick={() => {
                if (proposalResult?.downloadUrl) {
                  const link = document.createElement('a');
                  link.href = proposalResult.downloadUrl;
                  link.download = proposalResult.filename || 'generated_proposal.docx';
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                }
              }}
              disabled={!proposalResult?.downloadUrl}
            >
              {proposalResult?.downloadUrl ? 'Download Proposal' : 'No proposal generated yet'}
            </button>
          </div>
        </article>

        <article className="export-card">
          <div className="stack-panel__eyebrow">Feedback</div>
          <h2 className="panel-title">Capture edits and improve the next response cycle</h2>
          <div className="learning-ladder">
            <div className="learning-step">Reviewer notes are recorded</div>
            <div className="learning-step">Draft patterns are refined</div>
            <div className="learning-step">Future responses become faster and cleaner</div>
          </div>
          <form className="auth-form" onSubmit={handleFeedback}>
            <TextField label="What needed manual work?" name="manual_work_area" placeholder="Financial tables, annexures, reviewer comments…" />
            <div className="field">
              <label>
                What should improve next time?
                <textarea name="feedback_notes" placeholder="Add notes for the next response cycle…" />
              </label>
            </div>
            <button className="btn btn--primary" type="submit">Save Feedback</button>
          </form>
          <div className="info-note">{message}</div>
        </article>
      </section>
    </main>
  );
}

/* ── Shared UI primitives ── */

function PageHead({ title, text, action }) {
  return (
    <div className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        <p className="page-subtitle">{text}</p>
      </div>
      {action}
    </div>
  );
}

function TextField({ label, name, type = 'text', placeholder }) {
  return (
    <div className="field">
      <label>
        {label}
        <input name={name} type={type} placeholder={placeholder} required />
      </label>
    </div>
  );
}

/* FIX: FileField now accepts an onChange prop to capture the File object */
function FileField({ label, name, onChange }) {
  return (
    <div className="field">
      <label>
        {label}
        <input
          name={name}
          type="file"
          required
          onChange={onChange ? (e) => onChange(e.target.files?.[0] || null) : undefined}
        />
      </label>
    </div>
  );
}

function MiniMetric({ label, value }) {
  return (
    <div className="mini-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function FlowPill({ title, subtitle, tone, badge }) {
  return (
    <div className={`flow-pill flow-pill--${tone}`}>
      <div className="flow-pill__top">
        <strong>{title}</strong>
        {badge ? <span className="flow-pill__badge">{badge}</span> : null}
      </div>
      <span>{subtitle}</span>
    </div>
  );
}

function StatusToken({ label, tone = 'review' }) {
  return <span className={`status-token status-token--${tone}`}>{label}</span>;
}

function StepCard({ index, title, text, active = false }) {
  return (
    <div className={`step ${active ? 'is-active' : ''}`}>
      <div className="step__index">{index}</div>
      <strong>{title}</strong>
      <p className="muted">{text}</p>
    </div>
  );
}

function PreviewItem({ label, value }) {
  return (
    <div className="preview-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProcessNode({ title, text }) {
  return (
    <div className="process-node">
      <div className="process-node__accent" />
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </div>
  );
}

function ConfidenceChip({ title, tone }) {
  return <div className={`confidence-chip confidence-chip--${tone}`}>{title}</div>;
}

function Metric({ label, value, text }) {
  return (
    <article className="metric-card">
      <div className="metric-icon">#</div>
      <div>
        <div className="kpi-label">{label}</div>
        <div className="kpi-number">{value}</div>
        <p>{text}</p>
      </div>
    </article>
  );
}

function ProgressStep({ title, active = false }) {
  return (
    <div className={`progress-step ${active ? 'is-active' : ''}`}>
      <span className="progress-step__dot" />
      <strong>{title}</strong>
    </div>
  );
}

function QuickAction({ title, text, onClick }) {
  return (
    <button className="quick-link quick-link--block" onClick={onClick}>
      <span>
        <strong>{title}</strong>
        <span className="muted quick-link__text">{text}</span>
      </span>
    </button>
  );
}

function FilterButton({ label, active, onClick }) {
  return (
    <button className={`review-filter ${active ? 'is-active' : ''}`} onClick={onClick}>
      {label}
    </button>
  );
}

createRoot(document.getElementById('root')).render(<App />);

