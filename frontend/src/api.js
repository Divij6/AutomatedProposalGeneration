const env = import.meta.env;

export const config = {
  backendBaseUrl: trimTrailingSlash(env.VITE_BACKEND_BASE_URL || ''),
  generateProposalBaseUrl: trimTrailingSlash(env.VITE_GENERATE_PROPOSAL_BASE_URL || env.VITE_BACKEND_BASE_URL || ''),
  endpoints: {
    login: env.VITE_LOGIN_ENDPOINT || '/login',
    onboardCompany: env.VITE_ONBOARD_COMPANY_ENDPOINT || '/onboard-company',
    uploadPdf: env.VITE_UPLOAD_PDF_ENDPOINT || '/upload-pdf',
    generateProposal: env.VITE_GENERATE_PROPOSAL_ENDPOINT || '/generate-proposal',
    checkProposalFormat: env.VITE_CHECK_PROPOSAL_FORMAT_ENDPOINT || '/check-proposal-format',
  },
};

function trimTrailingSlash(value) {
  return String(value || '').replace(/\/+$/, '');
}

function isAbsoluteUrl(value) {
  return /^https?:\/\//i.test(String(value || ''));
}

function buildUrl(endpoint, baseUrl = config.backendBaseUrl) {
  if (isAbsoluteUrl(endpoint)) {
    return endpoint;
  }

  if (!baseUrl) {
    throw new Error('Backend base URL is missing. Update frontend/.env.');
  }

  return `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
}

async function readResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string'
      ? payload
      : payload?.detail || payload?.message || 'Request failed.';
    throw new Error(message);
  }

  return payload;
}

export async function loginCompany({ email, password }) {
  const formData = new FormData();
  formData.append('email', email);
  formData.append('password', password);

  const response = await fetch(buildUrl(config.endpoints.login), {
    method: 'POST',
    body: formData,
  });

  return readResponse(response);
}

export async function onboardCompany(values) {
  const formData = new FormData();
  formData.append('company_name', values.company_name || '');
  formData.append('industry', values.industry || '');
  formData.append('contact_email', values.contact_email || '');
  formData.append('contact_phone', values.contact_phone || '');
  formData.append('password', values.password || '');

  if (!values.knowledge_base) {
    throw new Error('Knowledge base file is required.');
  }

  if (!values.proposal_template) {
    throw new Error('Proposal template file is required.');
  }

  formData.append('knowledge_base', values.knowledge_base);
  formData.append('proposal_template', values.proposal_template);

  const response = await fetch(buildUrl(config.endpoints.onboardCompany), {
    method: 'POST',
    body: formData,
  });

  return readResponse(response);
}

export async function uploadPdf({ companyId, file }) {
  const formData = new FormData();
  formData.append('company_id', companyId);
  formData.append('file', file);

  const response = await fetch(buildUrl(config.endpoints.uploadPdf), {
    method: 'POST',
    body: formData,
  });

  return readResponse(response);
}

export async function checkProposalFormat({ docId }) {
  const params = new URLSearchParams({ doc_id: docId });
  const response = await fetch(buildUrl(`${config.endpoints.checkProposalFormat}?${params}`), {
    method: 'GET',
  });

  return readResponse(response);
}

export async function generateProposal({ companyId, docId, formatSource }) {
  const formData = new FormData();
  formData.append('company_id', companyId);
  formData.append('doc_id', docId);
  formData.append('format_source', formatSource === 'tender' ? 'tender' : 'template');

  const response = await fetch(buildUrl(
    config.endpoints.generateProposal,
    config.generateProposalBaseUrl,
  ), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    await readResponse(response);
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get('content-disposition') || '';
  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);

  return {
    blob,
    filename: filenameMatch?.[1] || 'generated_proposal.docx',
    downloadUrl: URL.createObjectURL(blob),
  };
}

export function normalizeCompanySession(payload, fallback = {}) {
  const source = typeof payload === 'object' && payload !== null ? payload : {};

  return {
    company_id: source.company_id || source.id || fallback.company_id || '',
    company_name: source.company_name || fallback.company_name || '',
    contact_email: source.contact_email || fallback.contact_email || '',
    raw: payload,
  };
}
