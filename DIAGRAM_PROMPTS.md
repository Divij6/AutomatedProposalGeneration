# Gemini Diagram Prompts

## 1. User Flow Diagram Prompt

Create a clean, modern user flow diagram for an AI Tender Proposal and Active Procurement Orchestration platform. Use the first reference image as the visual style: wide landscape layout, soft off-white background, purple primary action nodes, pale lavender secondary nodes, rounded rectangles, diamond decision nodes, thin grey connectors, clear arrows, subtle shadows, and a centered title.

Title: "AI Tender Proposal Orchestrator - User Flow"

Flow content:
- Start with "User" under "Login / Onboard".
- Decision diamond: "Existing user?"
- YES path: "Log in" -> "Dashboard".
- NO path: "Sign up" -> "Verify email" -> "Company onboarding".
- Company onboarding includes "Upload company knowledge base" and "Upload proposal template" -> "Dashboard".
- From Dashboard branch into:
  1. "Upload Tender" -> "Parse PDF / DOCX" -> "Extract clauses, BOQ, annexures" -> "Detect proposal format" -> decision "Tender has response format?"
     - YES: "Use tender format"
     - NO: "Use company template"
     - both connect to "Generate proposal draft"
  2. "Review proposal" -> "Compliance scoring" -> decision "Compliance >= threshold?"
     - YES: "Approve draft"
     - NO: "Revise flagged sections"
  3. "Active procurement orchestration" -> "Split BOQ requirements" -> "Trigger vendor RFQs" -> "Compare quotes" -> "Feed best prices into proposal"
  4. "Deadline orchestration" -> "Send reminders" -> "Escalate missing inputs"
- Final path: "Export DOCX / submission bundle" -> "Submit to portal" -> "Capture win/loss feedback" -> "Reuse intelligence for future tenders".

Keep the diagram easy to read, aligned in columns, with no decorative clutter. Use icons only if they are simple and professional.

## 2. System Architecture Diagram Prompt

Create a professional system architecture diagram using the second reference image as the style: horizontal pipeline, labelled vertical columns, light grey background, blue highlighted central AI/RAG/multi-agent region, bold uppercase section headings, blue arrows, simple enterprise icons, and clean white component cards.

Title: "SYSTEM ARCHITECTURE: AI-POWERED TENDER PROPOSAL AND PROCUREMENT ORCHESTRATION"

Columns from left to right:
1. INPUT
   - Tender documents: PDF, DOCX, RFPs, BOQs, specifications
   - Company knowledge base
   - Proposal template
   - Vendor directory and supplier catalog
2. DOCUMENT PROCESSING
   - FastAPI upload API
   - Docling + PyMuPDF parsing
   - Table extraction
   - Section normalization
   - Proposal format extraction
3. LLM ANALYSIS
   - Groq / local Ollama LLM
   - Proposal format detector
   - Requirement and clause understanding
   - BOQ line-item interpretation
4. RETRIEVAL LAYER
   - Cohere multilingual embeddings
   - Qdrant vector database
   - Tender chunks collection
   - Company knowledge collection
   - Similar tender memory / win-loss intelligence
5. MULTI-AGENT LAYER
   - LangGraph orchestrator
   - Section generation agent
   - Compliance scoring agent
   - Vendor negotiation agents per BOQ item
   - Deadline and escalation agent
   - Quote comparison and synthesizer agent
6. PROPOSAL GENERATION
   - DOCX compiler
   - Table-preserving response builder
   - Best quote feedback into commercial sections
   - Draft proposal package
7. REVIEW, PROCUREMENT, AND SUBMISSION
   - Human-in-the-loop review
   - Compliance % dashboard
   - Supplier RFQ tracking
   - Deadline reminders
   - Export and submit to portal

Show data stores below the pipeline: Supabase database and storage, Qdrant vector DB, local orchestration run store, generated proposal artifacts. Show arrows for feedback loops from review and win/loss results back into similarity reuse intelligence. Make it industry-ready, not cartoonish.

## 3. Industry-Level UML Diagram Prompt

Create an industry-level UML diagram for an AI Tender Proposal and Procurement Orchestration system. Use a clean enterprise UML style with packages, classes, interfaces, service boundaries, dependencies, and multiplicities. The diagram should be detailed but readable, suitable for a software architecture presentation.

Diagram type: UML component + class hybrid diagram.

Include these packages:
- Frontend
- API Layer
- Document Pipeline
- Retrieval and Vector Search
- Proposal Generation Agents
- Active Procurement Orchestration
- Persistence and External Services

Classes/components to include:
- ReactApp
- ApiClient
- FastAPIApp
- AuthController
- CompanyController
- TenderController
- ProposalController
- ProcurementOrchestrationController
- ParsingPipeline
- DoclingParser
- Normaliser
- ChunkingPipeline
- EmbeddingPipeline
- QdrantStore
- RetrievalService
- ProposalFormatDetector
- ProposalJsonBuilder
- LangGraphProposalWorkflow
- LoadSectionsNode
- ValidateSectionNode
- GenerateSectionNode
- CompileProposalNode
- ProcurementOrchestrationEngine
- RequirementExtractor
- VendorDirectory
- NegotiationAgent
- QuoteComparator
- ComplianceScoringEngine
- TenderReuseIntelligence
- DeadlineOrchestrationAgent
- SupabaseClient
- QdrantClient
- LLMClient
- CohereEmbedder
- GeneratedProposalArtifact
- OrchestrationRun

Show relationships:
- ReactApp uses ApiClient.
- ApiClient calls FastAPIApp endpoints.
- FastAPIApp delegates to controllers.
- TenderController uses ParsingPipeline, ChunkingPipeline, EmbeddingPipeline, ProposalFormatDetector, ProposalJsonBuilder.
- ProposalController invokes LangGraphProposalWorkflow and then triggers ProcurementOrchestrationEngine.
- LangGraphProposalWorkflow composes LoadSectionsNode, ValidateSectionNode, GenerateSectionNode, CompileProposalNode.
- GenerateSectionNode depends on RetrievalService and LLMClient.
- RetrievalService depends on QdrantStore and CohereEmbedder.
- ProcurementOrchestrationEngine composes RequirementExtractor, VendorDirectory, NegotiationAgent, QuoteComparator, ComplianceScoringEngine, TenderReuseIntelligence, DeadlineOrchestrationAgent.
- NegotiationAgent creates many supplier RFQ dispatches and compares many quotes.
- ComplianceScoringEngine scores many generated sections against many tender requirements.
- DeadlineOrchestrationAgent creates reminders and escalation events.
- SupabaseClient stores companies, tenders, proposal metadata, and files.
- QdrantClient stores tender chunks and company knowledge embeddings.
- OrchestrationRun persists the post-generation procurement workflow.

Use UML notations:
- Packages as grouped containers.
- Interfaces for LLMClient, VectorStore, StorageClient, NotificationGateway.
- Composition diamonds where workflow owns nodes and orchestration engine owns agents.
- Dependency arrows for API/service calls.
- Multiplicities such as 1..*, 0..*, 1.
- Add stereotypes like <<controller>>, <<service>>, <<agent>>, <<external>>, <<datastore>>, <<artifact>>.

Make the output landscape, high resolution, monochrome/blue enterprise palette, with no decorative icons except small UML-style component symbols.

## 4. Proposed Framework / Methodology Diagram Prompt

Create a polished academic methodology diagram for a research project titled "AI-Powered Tender Proposal Generation and Procurement Orchestration". This diagram must show the proposed research framework, not low-level implementation details. Use a layered architecture layout, top-to-bottom or left-to-right, with clean academic styling, light background, sharp labels, subtle blue/teal enterprise palette, and professional spacing.

Title: "Proposed Framework / Research Methodology"

Show the framework in clearly separated layers:

Layer 1: Input Knowledge Layer
- Tender documents
- BOQ and annexures
- Company knowledge base
- Proposal templates
- Vendor database
- Historical bid memory

Layer 2: Document Understanding Layer
- Parsing and extraction
- Section detection
- Table and BOQ extraction
- Proposal format detection
- Requirement normalization

Layer 3: Intelligence Layer
- LLM-based clause understanding
- Retrieval-augmented generation
- Tender similarity and reuse intelligence
- Semantic compliance scoring
- Deadline-aware reasoning

Layer 4: Multi-Agent Decision Layer
- Proposal generation agent
- Validation agent
- Negotiation agents
- Compliance agent
- Deadline orchestration agent
- Synthesis/orchestrator agent

Layer 5: Action and Output Layer
- Draft proposal generation
- Vendor RFQ dispatch
- Quote intake
- Compliance review dashboard
- Final proposal export
- Submission readiness

Show feedback loops:
- Reviewer feedback back into historical bid memory
- Quote and compliance results back into proposal refinement
- Win/loss outcomes back into reuse intelligence

Make the diagram look publication-ready for a thesis or conference paper. Keep it conceptual and methodology-focused, not software-box heavy.

## 5. LangGraph Workflow Diagram Prompt

Create a clean agent workflow diagram showing the exact LangGraph state machine for tender proposal generation. Style it as a professional technical flowchart with white background, blue and grey node colors, rounded process boxes, decision diamonds, directional arrows, and clear labels.

Title: "LangGraph Agent Workflow for Proposal Generation"

Nodes to include exactly in this order:
- Start
- Load Sections Node
- Process Section Node
- Validate Section Node
- Decision: Skip or Generate?
- Generate Section Node
- Decision: More Sections?
- Compile Proposal Node
- End

Flow logic:
- Start -> Load Sections Node
- Load Sections Node -> Process Section Node
- Process Section Node -> Validate Section Node
- Validate Section Node -> decision diamond "Skip or Generate?"
- If Skip -> back to Process Section Node for next section
- If Generate -> Generate Section Node
- Generate Section Node -> decision diamond "More Sections?"
- If Yes -> back to Process Section Node
- If No -> Compile Proposal Node
- Compile Proposal Node -> End

Annotate the main nodes with small subtitles:
- Load Sections Node: loads proposal_json sections or table rows
- Process Section Node: selects current section
- Validate Section Node: checks if section should be skipped
- Generate Section Node: retrieves context and drafts content
- Compile Proposal Node: writes final DOCX

Make it explicit that this is the agentic workflow inside LangGraph. The diagram should feel like an architecture review artifact, not a generic classroom flowchart.

## 6. Procurement Orchestration Flow Prompt

Create a professional process diagram focused only on the procurement orchestration novelty of the system. Use a horizontal pipeline layout, clean enterprise styling, muted blue/green palette, and modern icon-supported boxes. This diagram must look like a research contribution figure.

Title: "Procurement Orchestration Flow After Proposal Generation"

Flow steps:
- Proposal Generated
- Requirements Extracted
- BOQ / Specification Rows Identified
- Vendor Matched from Supplier Database
- RFQ Dispatched via Email
- Pending Quote Created in Supabase
- Vendor Quote Submitted
- Quotes Compared
- Best Commercial Option Selected
- Compliance Scored
- Proposal / Review Dashboard Updated

Add side annotations:
- Requirement extraction from proposal sections and tables
- Vendor matching based on category and rating
- RFQ email contains quote reference ID
- Vendor quote is stored in structured database
- Compliance scoring uses semantic similarity
- Results feed back into proposal review

Add two feedback arrows:
- Quote comparison -> proposal commercial refinement
- Compliance scored -> reviewer action / revision path

Make this diagram clearly distinct from the main system architecture. It should emphasize business orchestration and automation flow.

## 7. Compliance Scoring Pipeline Prompt

Create a crisp linear pipeline diagram for the compliance scoring subsystem in an AI tender proposal platform. Use a minimal academic-tech style with clean boxes, arrows, and one highlighted model box. Keep it simple, elegant, and easy to understand.

Title: "Semantic Compliance Scoring Pipeline"

Pipeline steps:
- Tender Requirement Text
- Generated Proposal Section Text
- Candidate Match Selection
- Cohere Rerank Model
- Relevance Score (0 to 1)
- Score Scaling to 0 to 100
- Compliance Classification

Show the final classification outcomes as three separate labeled outputs:
- Compliant
- Needs Review
- Gap

Add short annotations:
- Input query: requirement text
- Input candidate: generated section text
- Model: rerank-multilingual-v3.0
- Output score mapped to compliance percentage
- Threshold logic:
  - 80 to 100 = Compliant
  - 55 to 79 = Needs Review
  - 0 to 54 = Gap

Use a modern research-paper visual style. The Cohere rerank model box should be slightly emphasized so the semantic scoring innovation is visually clear.
