# MVP Blueprint for Self-Healing Web Agent

**Project Name:** Self-Healing Web Agent  
**Goal:** Develop a Minimum Viable Product (MVP) of an autonomous web scraping agent that can detect and adapt to changes in website structure, ensuring continuous data extraction, with a focus on user-friendly integration and human-in-the-loop control for codebase modifications.

## 1. Core Functionality (MVP Scope)

The MVP focuses on demonstrating the core self-healing mechanism for a single, well-defined web scraping task, integrated into a user-facing platform.

### 1.1. Target Website & Data Point
- **Target:** A publicly accessible e-commerce product page (e.g., a specific product on a well-known online retailer).
- **Data Point:** Extracting the product price (e.g., $19.99).

### 1.2. Key Features to Implement
1. **Initial Data Extraction:** Successfully navigate to the target URL and extract the product price using a predefined CSS selector.
2. **Simulated Selector Failure:** Introduce a mechanism to simulate a selector failure (e.g., by intentionally breaking the initial selector or by changing the target HTML in a test environment).
3. **Change Detection:** The agent must detect that the initial selector has failed to return the expected data.
4. **Autonomous Healing Process:**
   - **Screenshot Capture:** Capture a screenshot of the webpage at the point of failure.
   - **Visual Analysis (via Agentic AI):** Use a vision-capable LLM (e.g., Gemini 1.5 Flash/Pro) to analyze the screenshot and the webpage HTML to identify the new location of the product price.
   - **New Selector Generation:** The LLM should propose a new, valid CSS selector for the product price.
   - **Selector Update (Internal):** The agent updates its internal configuration with the new selector.
5. **Re-extraction & Verification:** Attempt to extract the product price again using the newly generated selector. Verify that the extraction is successful.
6. **Persistence (Basic):** Store the successfully healed selector locally (e.g., in a simple JSON file) so that the agent uses it for subsequent runs.
7. **24/7 Monitoring:** The agent continuously monitors the target website for changes and data integrity.
8. **Human-in-the-Loop Codebase Update:** Crucially, before any proposed change is applied to the user's actual codebase, the system must present the proposed change to the user for explicit permission/authorization. This ensures full control and trust.

## 2. Platform & Integration Model (MVP)

The MVP establishes the foundation for a user-friendly platform and integration methods.

### 2.1. Web-Based Platform (MVP)
A simple web interface where users can:
- Input target website/app links for monitoring.
- View the status of their agents (monitoring, healing, pending approval).
- Review and approve/reject proposed codebase updates.

### 2.2. Integration Methods (MVP)
- **Direct Link Input:** Users can provide a website or app URL directly to the platform.
- **Browser Extension:** A basic browser extension that, once installed and authorized, allows the agent to monitor the user's active web sessions and propose changes. For MVP, focus on the authorization flow and basic communication.
- **Authorization:** A clear, secure, and easy-to-use authorization flow for both direct link and extension integration, ensuring the agent has the necessary permissions to monitor and propose changes.

## 3. Technical Requirements & Agentic AI Integration

This MVP is built using an Agentic AI platform to orchestrate the autonomous behaviors.

- **Agent Orchestration:** The main `SelfHealingWebAgent` manages sub-tasks and interacts with the web platform.
- **Browser Control:** Utilize browser automation (Playwright) for navigation and interaction.
- **LLM Integration:** Integrate with vision-capable LLMs (Gemini) for visual analysis and selector generation.
- **Artifacts:** Generate and manage artifacts for:
  - *Failure Report:* Screenshot of the page when the selector fails.
  - *Adaptation Plan:* The proposed new selector and reasoning.
  - *Verification Report:* Screenshot and extracted data after successful healing.
  - *Proposed Codebase Changes:* A diff or clear representation of the code update for user review.
- **Language:** Python (for backend agent logic) and JavaScript/HTML/CSS for the web platform and browser extension.
