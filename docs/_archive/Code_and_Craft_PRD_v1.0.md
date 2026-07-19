





PRODUCT REQUIREMENTS 
DOCUMENT
Code&Craft
Autonomous AI-Powered Creative Digital Agency


Version 1.0  |  February 19, 2026
Owner: Sukaimi  |  Classification: Internal / Investor
?
Document Control
Field
Detail
Document Title
Code&Craft Product Requirements Document (PRD)
Version
1.1
Status
Draft (Restructured)
Owner
Sukaimi (Founder)
Date Created
February 19, 2026
Last Updated
February 19, 2026
Classification
Internal / Investor
Platform
OpenClaw v2026.2.9
Infrastructure
Hostinger VPS KVM 1 (Ubuntu 24.04 LTS)

Revision History
Version
Date
Author
Changes
1.0
February 19, 2026
Sukaimi
Initial PRD creation
1.1
February 19, 2026
Sukaimi
Agency restructure: ISO 9001 + 
ITIL 5 alignment. CEO renamed 
to Account Director. SecOps 
renamed to Studio Manager 
(content editor role). New 
Incident Manager agent added 
with cron health checks. Quality 
review streamlined to one-pass 
with 4 checks.

?
Executive Summary
Code&Craft is an autonomous AI-powered creative digital agency, built on the OpenClaw multi-
agent orchestration platform. It is a sister company to Code&Canvas (Sukaimi's main company). 
Code&Craft operates as a fully autonomous AI agency where a CEO agent receives client 
requests via Telegram, delegates work to specialist sub-agents, reviews outputs, and delivers 
final work back to the client Ñ all without human intervention.
The system currently runs on a Hostinger VPS (KVM 1, 1 CPU, 4GB RAM, 50GB disk) located 
in Malaysia (Kuala Lumpur), running Ubuntu 24.04 LTS with OpenClaw v2026.2.9. It uses 
Google Gemini 2.0 Flash as the primary LLM for the CEO agent, with Anthropic Claude Sonnet 
4.5 as fallback and for specialist agents requiring higher reasoning capability.
This PRD documents the current system architecture, service offerings, known limitations, and a 
roadmap for scaling the agent team and improving reliability. It serves as both a technical 
reference for system maintenance and a strategic overview for stakeholders and potential 
investors.

Problem Statement
Small and medium businesses need creative digital services (social media content, blog writing, 
SEO research, brand graphics, security audits) but face three key barriers: high agency costs, 
slow turnaround times, and inconsistent quality from freelancers. Traditional agencies charge 
premium rates with multi-day delivery cycles. Freelancer marketplaces offer lower costs but 
require significant management overhead and quality control.
Code&Craft solves this by deploying autonomous AI agents that can deliver creative digital 
services at a fraction of the cost and time. A client sends a request via Telegram, and the AI 
agency handles the entire workflow Ñ from task decomposition and delegation to content 
generation and delivery Ñ within minutes, not days.

Target Users & Personas
Primary: SMB Owners & Marketing Managers
Business owners and marketing managers at small-to-medium businesses who need ongoing 
creative digital content but lack the budget for a full-service agency or in-house creative team. 
They value speed, affordability, and convenience over bespoke creative direction.
Secondary: Solopreneurs & Personal Brands
Individual entrepreneurs, coaches, consultants, and content creators who need professional-
quality social media graphics, blog posts, and SEO-optimized content on a recurring basis.
Tertiary: Investors & Strategic Partners
Stakeholders evaluating Code&Craft as a scalable AI-native agency model. This audience 
needs to understand the technical architecture, unit economics, and growth trajectory.

Product Overview & Architecture
System Architecture
Code&Craft is built on OpenClaw v2026.2.9, a multi-agent orchestration platform that manages 
agent lifecycles, inter-agent communication, and external integrations. The system follows a 
hub-and-spoke delegation model where the CEO agent acts as the central hub.
Component
Technology
Details
Platform
OpenClaw v2026.2.9
Multi-agent orchestration with 
sessions_spawn delegation
Infrastructure
Hostinger VPS KVM 1
1 CPU, 4GB RAM, 50GB disk, Ubuntu 24.04 
LTS
Location
Malaysia (Kuala Lumpur)
IP: 76.13.179.220
Gateway
Port 18789 (loopback)
Token-based auth, local mode
Primary LLM
Google Gemini 2.0 Flash
CEO agent default; cost-efficient, fast 
inference
Fallback LLM
Anthropic Claude Sonnet 4.5
Higher reasoning; used by Creative Director & 
Strategist
Image Generation
Gemini 3 Pro (nano-banana-
pro)
AI image generation skill with 1K/2K/4K 
resolution
Client Interface
Telegram Bot
Primary client communication channel
File Delivery
telegram-send-file CLI
Delivers images, reports, and files to 
Telegram
Networking
Tailscale (disabled)
Available but currently off

Agent Architecture
The system employs a hierarchical multi-agent architecture with one orchestrator (CEO) and 
four specialist agents. The CEO receives all inbound requests, determines which agent(s) to 
delegate to, reviews outputs, and delivers consolidated results to the client.
Agent ID
Display Name
Model
Role & Capabilities
main
Account Director
Gemini 2.0 Flash 
(default)
Orchestrator. Operations Lead 
& Client Liaison. Receives 
client briefs via Telegram, 
acknowledges with witty one-
liner, delegates to specialists, 
routes output through Studio 
Manager, delivers to client. 
Three operating modes: 
Personal Assistant, CEO 
Advisor, Account Director.
creative-director
Creative Director
Claude Sonnet 4.5
AI image generation (via nano-
banana-pro/Gemini 3 Pro), social 
media graphics, brand mood 
boards, visual direction, wireframe 
descriptions, typography 
guidance.
content-writer
Content Writer
Gemini 2.0 Flash 
(default)
Blog posts (SEO-optimized), 
website copywriting, social media 
captions, email newsletters, 
proofreading, content repurposing.
strategist
Strategist
Claude Sonnet 4.5
SEO keyword research, 
competitor analysis, content 
calendar planning, market 
research, target audience profiling, 
digital marketing strategy.
cybersecurity
Studio Manager
Gemini 2.0 Flash
Content Editor & Quality Polish. 
One-pass review of all 
deliverables before client 
delivery. Checks: language 
quality, factual accuracy, brand 
fit, platform compliance. Default 
disposition: APPROVE.
incident-manager
Incident Manager
Gemini 2.0 Flash
Error Detection, Recovery & 
System Health (ITIL 5 Aligned). 
Activated by cron job (every 30 
min, 8am-10pm SGT) or on-
demand by Account Director. 
Classifies incidents P1/P2/P3. 
Reads gateway logs and 
reports issues.

Delegation Flow
Client request flow (ISO 9001 PDCA): (1) Client sends brief via Telegram. (2) Account Director 
acknowledges with a witty one-liner and delegates to specialist(s) in the same turn. (3) 
Specialist agent(s) execute the task autonomously. (4) Specialist returns output to Account 
Director. (5) Account Director routes ALL output through Studio Manager (cybersecurity agent) 
for a one-pass quality polish. (6) Studio Manager returns APPROVED or REVISION NEEDED. 
(7) If approved, Account Director delivers consolidated output to client via Telegram. (8) If 
revision needed, specialist fixes and content goes straight to delivery (no second review). (9) If 
any agent fails, Account Director delegates to Incident Manager for diagnosis.
Critical configuration: The CEO agent must have subagents.allowAgents configured in its per-agent 
config within openclaw.json. Without this, sessions_spawn returns "agentId is not allowed for 
sessions_spawn (allowed: none)" and delegation fails silently. This is configured at 
agents.list[0].subagents.allowAgents (not agents.defaults.subagents due to schema bug #10031 in 
v2026.2.9).

Service Offerings
Code&Craft currently offers 10 services, each mapped to one or more specialist agents:
#
Service
Primary Agent
Support Agent(s)
Delivery Format
1
Social Media Content (copy + 
graphics)
Content Writer
Creative Director
Text + PNG via 
Telegram
2
Blog Writing (SEO-optimized)
Content Writer
Strategist 
(keywords)
Text via Telegram
3
SEO Keyword Research
Strategist
Ñ
Text report via 
Telegram
4
Website Copywriting
Content Writer
Ñ
Text via Telegram
5
Competitor Analysis
Strategist
Ñ
Text report via 
Telegram
6
Website Security Audit
SecOps
Ñ
Security report via 
Telegram
7
Email Security Check 
(SPF/DKIM/DMARC)
SecOps
Ñ
Security report via 
Telegram
8
Password & Access Policy 
Review
SecOps
Ñ
Security report via 
Telegram
9
Phishing Awareness Report
SecOps
Ñ
Security report via 
Telegram
10
SSL/Domain Health Check
SecOps
Ñ
Security report via 
Telegram


Functional Requirements
P0 Ñ Must-Have (Current)
*	FR-001: Task Delegation Ñ CEO agent receives client messages via Telegram and 
delegates to the correct specialist agent(s) using sessions_spawn.
*	FR-002: Image Generation & Delivery Ñ Creative Director generates AI images using 
nano-banana-pro (Gemini 3 Pro) and delivers via telegram-send-file.
*	FR-003: Content Generation Ñ Content Writer produces SEO-optimized blog posts, social 
media copy, and website content on first response without asking for clarification.
*	FR-004: Strategy & Research Ñ Strategist performs SEO keyword research, competitor 
analysis, and market research using web search and delivers structured reports.
*	FR-005: Security Auditing Ñ SecOps performs passive security reconnaissance (SSL, 
DNS, headers, SPF/DKIM/DMARC) without requiring explicit permission for public checks.
*	FR-006: Output Consolidation Ñ CEO consolidates all agent outputs into a single 
message with actual deliverable text (not summaries) and delivers to client via Telegram.
*	FR-007: No-Loop Operation Ñ All agents operate under a "no loops" policy: make 
reasonable assumptions, deliver on first response, accept feedback and refine.
P1 Ñ Nice-to-Have (Next Phase)
*	FR-008: CEO Model Reliability Ñ Upgrade CEO model from Gemini 2.0 Flash to a more 
reliable model to eliminate empty response failures.
*	FR-009: Multi-Channel Delivery Ñ Add multi-channel delivery beyond Telegram (email, 
WhatsApp, web dashboard).
*	FR-010: Revision Workflow Ñ Implement client feedback loop where clients can request 
revisions and agents iterate.
*	FR-011: Agent Expansion Ñ Add new specialist agents: Account Manager, Web 
Developer, Video Editor, Data Analyst.
P2 Ñ Future Considerations
*	FR-012: Client Portal Ñ Client self-service portal with request history, revision tracking, 
and billing.
*	FR-013: Monitoring Dashboard Ñ Agent performance monitoring dashboard with success 
rates, response times, and error logs.
*	FR-014: White-Label Ñ White-label capability for partners to deploy their own branded AI 
agency instances.

Configuration Reference
This section documents the current OpenClaw configuration as deployed on the production 
VPS. It serves as both a technical reference and a baseline for future changes.
openclaw.json Ñ Key Settings
Config Path
Value
Notes
meta.lastTouchedVersion
2026.2.9
Current OpenClaw version
auth.profiles.anthropic:default
provider: anthropic, mode: 
api_key
Anthropic API access
auth.profiles.google:default
provider: google, mode: 
api_key
Google API access
agents.defaults.model.primary
google/gemini-2.0-flash
Default model for all agents
agents.defaults.model.fallbacks
["anthropic/claude-sonnet-4-
5"]
Fallback if primary fails
agents.defaults.maxConcurrent
4
Max concurrent agent 
sessions
agents.defaults.subagents.maxConcurrent
8
Max concurrent sub-agent 
sessions
agents.defaults.compaction.mode
safeguard
Context compaction strategy
agents.list[0].subagents.allowAgents
["creative-director", "content-
writer", "strategist", 
"cybersecurity"]
CRITICAL: Per-agent 
allowlist for sessions_spawn
plugins.entries.telegram
enabled: true
Telegram bot integration
nodes.denyCommands
camera.snap, camera.clip, 
screen.record, calendar.add, 
contacts.add, reminders.add
Blocked device commands

Agent Workspace Structure
Agent
Workspace Path
Key Files
CEO (main)
/root/.openclaw/workspace/
AGENTS.md (system prompt with 
delegation instructions, service list, 
operating modes, delivery format)
Creative Director
/root/.openclaw/workspace-creative-
director/
AGENTS.md (image generation via 
nano-banana-pro, telegram-send-file 
delivery, creative standards)
Content Writer
/root/.openclaw/workspace-content-
writer/
AGENTS.md (blog writing, 
copywriting, SEO content, writing 
standards, no-loop policy)
Strategist
/root/.openclaw/workspace-strategist/
AGENTS.md (SEO research, 
competitor analysis, market research, 
output standards)
SecOps 
(cybersecurity)
Studio Manager
Gemini 2.0 Flash


Known Issues & Technical Debt
Risk
Severity
Likelihood
Mitigation
Gemini Flash empty 
responses: CEO agent 
(Gemini 2.0 Flash) 
intermittently returns 
empty content arrays, 
causing delegation to fail 
on first attempt. This is an 
LLM inference issue, not 
a config issue.
High
Intermittent
Consider upgrading 
CEO to Gemini 2.5 Pro 
or adding retry logic. 
Monitor OpenRouter for 
model stability updates.
RESOLVED: Agent 
naming mismatch. All 
agents now have 
consistent names: 
Account Director, 
Studio Manager, 
Content Writer, 
Creative Director, 
Strategist, Incident 
Manager.
Low
Confirmed
Align naming across 
identity.md, 
AGENTS.md, and 
openclaw.json. Choose 
one name.
Schema bug #10031: 
subagents.allowAgents 
cannot be set at 
agents.defaults.subagents 
level due to schema 
validation bug in 
v2026.2.9. Must use per-
agent config instead.
Medium
Confirmed
Fixed in PR #10197 
(not yet in v2026.2.9). 
When upgrading 
OpenClaw, can move 
to agents.defaults path.
Identity.md files: Some 
agent identity.md files 
may be empty or 
inconsistent. These files 
define agent metadata but 
are not always populated.
Low
Needs Audit
Audit all identity.md 
files and populate with 
consistent metadata.
Single point of failure: 
VPS is a single KVM 1 
instance with no 
redundancy. If VPS goes 
down, entire agency is 
offline.
High
Latent
Consider backup VPS, 
snapshot automation, 
or container-based 
deployment for failover.
No monitoring: No 
visibility into agent 
success/failure rates, 
response times, or error 
patterns. Debugging 
requires manual log 
inspection.
Medium
Confirmed
Implement logging and 
monitoring. Consider 
integration with 
Grafana, Prometheus, 
or custom dashboard.
Disk usage at 70.6%: 
VPS disk is 33GB/50GB 
used. Image generation 
and session logs will 
consume additional space 
over time.
Medium
Confirmed
Implement session 
cleanup automation. 
Consider larger disk or 
log rotation policy.
Gemini Flash empty 
responses on 
delegation
High
Intermittent
Account Director 
occasionally stops 
after 
acknowledgment 
without delegating. 
Mitigated by explicit 
prompt instructions 
requiring delegation 
in same turn as 
acknowledgment.
Gemini 3 Pro image 
API 503 errors
Medium
Intermittent
Image generation 
API occasionally 
returns 503 
(overloaded). 
Creative Director 
retries automatically. 
External dependency 
on Google API 
availability.
Security services need 
reallocation
Medium
Confirmed
Services 6-10 
(security audits) need 
a dedicated security 
agent since 
cybersecurity agent 
is now Studio 
Manager (content 
editor role). Planned 
for Phase 2.


Success Metrics & KPIs
Leading Indicators (Short-Term)
Metric
Target
Measurement Method
Task delegation success rate
³95% (sessions_spawn 
accepted)
Parse session JSONL files for 
sessions_spawn status
Agent first-response delivery 
rate
³90% deliver on first attempt
Track agent responses for deliverable 
content vs empty/error
CEO empty response rate
<5% of total requests
Monitor Gemini Flash response 
content arrays
Image generation + delivery 
success
³90% end-to-end
Track nano-banana-pro execution + 
telegram-send-file delivery
Average response time
<3 minutes for simple tasks
Timestamp from client message to 
CEO final delivery

Lagging Indicators (Long-Term)
Metric
Target (6 months)
Measurement Method
Active recurring clients
³10 clients
Unique Telegram users with >3 
requests/month
Monthly requests processed
³100 requests/month
Session count in OpenClaw
Client satisfaction (feedback)
³4/5 average rating
Post-delivery feedback prompt (to be 
implemented)
Revenue per client
Defined by pricing model
To be determined based on service 
tiers
System uptime
³99.5%
VPS uptime monitoring


Non-Goals (Explicitly Out of Scope)
*	Software Development: Code&Craft is a creative digital agency, not a software 
development shop. No custom software, app development, or engineering services.
*	Active Security Testing: Active penetration testing, vulnerability exploitation, or any 
security work that goes beyond passive reconnaissance requires explicit client permission 
and is not offered as a standard service.
*	Human-in-the-Loop Operations: This PRD covers the autonomous agent system. Human-
in-the-loop creative review, account management, or manual quality control is not currently 
in scope.
*	Real-Time Collaboration: Real-time streaming, video calls, or live collaboration features 
are not in scope. All interaction is asynchronous via Telegram.
*	Platform-as-a-Service: Building a general-purpose AI agent platform for external 
customers is not the goal. Code&Craft uses OpenClaw as infrastructure, not as a product to 
sell.

Assumptions & Constraints
Assumptions
*	Clients are comfortable interacting with an AI agency via Telegram messaging.
*	Gemini 2.0 Flash will remain available and cost-effective on OpenRouter.
*	Claude Sonnet 4.5 will continue to be available via Anthropic API for specialist agents.
*	The current VPS capacity (1 CPU, 4GB RAM) is sufficient for the initial client load.
*	OpenClaw v2026.2.9 will remain stable until an upgrade path is validated.
Constraints
*	Infrastructure: Single VPS with no redundancy or auto-scaling.
*	Image Generation: Image generation depends on Gemini 3 Pro availability via Google API.
*	Security: Passive security reconnaissance only; no active scanning without explicit 
permission.
*	Cost: LLM API costs scale linearly with request volume. Cost optimization is critical.
*	Platform Bugs: Schema bug #10031 in v2026.2.9 requires per-agent config workarounds.

Risks & Dependencies
External Dependencies
Dependency
Type
Risk if Unavailable
OpenRouter / Google Gemini API
LLM Provider
CEO agent cannot process requests; 
entire system halts
Anthropic Claude API
LLM Provider
Creative Director and Strategist 
agents cannot function
Google Gemini 3 Pro (nano-banana-
pro)
Image Generation
No image generation capability
Telegram Bot API
Client Interface
No client communication channel
Hostinger VPS
Infrastructure
Complete system outage
OpenClaw Platform
Orchestration
Agent management and delegation 
fails


Roadmap & Phasing
Phase 1: Stabilize (Current Ñ Weeks 1Ð4)
*	Fix cybersecurity agent naming mismatch (SecOps vs SecBot)
*	Audit and populate all identity.md files
*	Evaluate Gemini 2.5 Pro or alternative CEO model for reliability
*	Implement session log rotation and disk cleanup automation
*	Run 20+ end-to-end tests across all 10 services and document success rates
Phase 2: Scale Agents (Weeks 5Ð12)
*	Add new agents (e.g., Account Manager, Web Developer) with proper allowAgents config
*	Implement agent performance monitoring
*	Add multi-agent collaboration (e.g., Content Writer + Strategist for SEO blog packages)
*	Develop pricing model and service tiers
Phase 3: Scale Clients (Weeks 13Ð24)
*	Launch client onboarding flow via Telegram
*	Add revision/feedback workflow
*	Implement client request history and tracking
*	Explore additional delivery channels (WhatsApp, email, web)
Phase 4: Enterprise (Weeks 25+)
*	Client self-service portal
*	White-label capability
*	Redundant infrastructure (backup VPS or container deployment)
*	Upgrade OpenClaw when schema bug #10031 fix is available in stable release

Open Questions
#
Question
Owner
Priority
1
Should the CEO model be upgraded to Gemini 
2.5 Pro or switched to Claude? Need 
cost/reliability tradeoff analysis.
Sukaimi (Founder)
High
2
What is the pricing model for Code&Craft 
services? Per-request, subscription, or tiered?
Sukaimi (Founder)
High
3
Should the cybersecurity agent be named 
SecOps or SecBot? Needs brand alignment 
decision.
Sukaimi (Founder)
Low
4
What new agents should be prioritized for Phase 
2? (Account Manager, Web Dev, Video Editor, 
Data Analyst)
Sukaimi (Founder)
Medium
5
Is the current VPS plan sufficient for 10+ 
concurrent clients, or does infrastructure need 
upgrading?
Engineering
Medium
6
Should Code&Craft support multi-language 
content generation?
Sukaimi (Founder)
Low
7
What is the disaster recovery plan if the VPS 
goes down?
Engineering
High


Appendix
A. Agent Configuration Checklist (for adding new agents)
*	Create agent entry in agents.list[] in openclaw.json with id, name, workspace, agentDir, 
model (if different from default), and identity.
*	Add agent ID to the CEO's subagents.allowAgents array in 
agents.list[0].subagents.allowAgents.
*	Create workspace directory (e.g., /root/.openclaw/workspace-<agent-name>/).
*	Create AGENTS.md in the workspace with identity, skills, workflow, no-loops policy, output 
standards, and rules.
*	Create identity.md with consistent naming matching AGENTS.md and openclaw.json.
*	Restart gateway: systemctl --user restart openclaw-gateway.
*	Clear sessions: echo '{}' > /root/.openclaw/agents/main/sessions/sessions.json.
*	Test delegation via Telegram: send a task matching the new agent's skills.
*	Verify in session JSONL that sessions_spawn returns status: "accepted".
B. Key File Paths
File
Path
Purpose
Main config
/root/.openclaw/openclaw.json
All agent definitions, 
models, plugins, auth
CEO prompt
/root/.openclaw/workspace/AGENTS.md
CEO system prompt with 
delegation logic
Session metadata
/root/.openclaw/agents/main/sessions/sessions.json
Active session routing info
Session transcripts
/root/.openclaw/agents/main/sessions/*.jsonl
Per-session message logs
Gateway service
~/.config/systemd/user/openclaw-gateway.service
systemd user service

C. Resolved Issues (for reference)
Issue
Root Cause
Fix Applied
Date
sessions_spawn returns 
"forbidden"
subagents.allowAgents not 
configured; default is "none"
Added allowAgents to 
agents.list[0].subagents 
(per-agent, not defaults 
due to schema bug 
#10031)
February 19, 
2026
Gateway crash on config 
change
allowAgents placed in 
agents.defaults.subagents 
(schema rejects it in 
v2026.2.9)
Moved to per-agent config 
at agents.list[0].subagents
February 19, 
2026
Wrong 
tools.elevated.allowFrom 
config
tools.elevated.allowFrom 
populated with tool names 
instead of sender IDs; does 
not control sessions_spawn
Removed 
tools.elevated.allowFrom 
entirely
February 19, 
2026
Agency restructure: 
CEO ? Account 
Director
Restructure brief required 
renaming and new role 
assignment
Updated IDENTITY.md, 
AGENTS.md, and 
openclaw.json for all 
agents
February 19, 
2026
Agency restructure: 
SecOps ? Studio 
Manager
Cybersecurity agent 
repurposed from security 
auditing to content editing
New IDENTITY.md and 
AGENTS.md with 
narrowed 4-check 
scope. Model changed 
to Gemini Flash.
February 19, 
2026
New agent: Incident 
Manager
No system health 
monitoring existed
Added incident-manager 
agent with cron health 
check (*/30 8-22 * * * 
Asia/Singapore)
February 19, 
2026
Quality review over-
blocking
Quality Guard was 
blocking creative content 
over hypothetical safety 
concerns
Renamed to Studio 
Manager. Scope 
narrowed to 4 checks. 
One-pass only. Default: 
APPROVE.
February 19, 
2026

