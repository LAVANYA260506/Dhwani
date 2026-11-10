# DHWANI
### Turning complex education-loan applications into guided conversations.

**The Problem**

For many students, applying for an education loan is not just a form-filling exercise. It involves navigating unfamiliar financial terminology, understanding documentation requirements, overcoming language barriers, and ensuring that every detail is entered correctly. A single misunderstanding or inconsistent entry can create friction in an already stressful process.

**The Vision**

What if students could complete an education-loan application simply by having a conversation?

**Dhwani** is a multilingual, voice-first Agentic AI assistant that transforms a conventional education-loan application into an interactive, guided experience. Supporting Kannada and English, Dhwani doesn't merely answer questions — it understands the application context, interacts with its underlying workflow, validates information, and helps applicants resolve discrepancies while keeping them in control.

**How Dhwani Works**

1. **Conversational Understanding:** Applicants interact naturally in Kannada or English through voice or text. Dhwani explains unfamiliar fields using a verified knowledge base.
2. **Agentic Form Completion:** Through predefined backend tools, the agent captures responses, updates application fields, and maintains application context.
3. **Intelligent Validation:** A deterministic validation engine checks entries in real time, identifying invalid formats, incorrect field inputs, and missing information before they progress.
4. **Document Intelligence:** Using LlamaParse, Dhwani extracts structured information from uploaded academic marks cards and compares it against the applicant's entered details.
5. **Human-in-the-Loop Resolution:** When conflicting information is detected, Dhwani presents both values and asks the applicant to clarify. It never silently overrides applicant-provided information.
6. **Application Readiness:** Once the applicant reviews the completed information, Dhwani generates a readiness summary and demonstrates a mock submission with a unique reference ID.

**Technical Architecture**

Next.js frontend → FastAPI backend → Agent orchestration and predefined tools → Application state and deterministic validation.

Gnani powers the multilingual speech interface, an LLM interprets conversational intent and coordinates approved actions, and LlamaParse handles document extraction. The validation and comparison layers independently enforce data consistency.

**Measuring Success**

The prototype will be evaluated on:
- Form-field completion accuracy and end-to-end task completion rate.
- Validation accuracy across valid and deliberately incorrect inputs.
- Document extraction and form-to-document discrepancy detection.
- Kannada and English interaction quality, including successful clarification handling.

These measurements will help assess whether Dhwani makes the application process more understandable, accurate, and accessible.

**The Impact**

Dhwani shifts the interaction model from *applicants adapting to complicated digital forms* to *digital applications adapting to applicants*.

By combining multilingual voice interaction, agentic workflow execution, document intelligence, and human-controlled validation, Dhwani demonstrates how AI can make essential digital services more approachable without taking decision-making authority away from the people using them.

**Prototype Scope:** A fictional bank's education-loan application workflow with simulated submission. No real banking integration, loan approval, or financial eligibility decisions are performed.
