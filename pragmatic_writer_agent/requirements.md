## 🎯 Architecture Requirements: Pragmatic Content Factory (PCF)

This document describes the architecture requirements for a system that generates highly personalized and strategically aligned content. The system is built on the principle of an **agent ecosystem** with prioritization of authenticity, engineering pragmatism, and alignment with the brand DNA (Grigory Sharkov, "The Pragmatic Architect") and target audience ("LangChain Survivor").



### I. Agents (The Crew)

The system must consist of five specialized agents. All agents must work with the target audience's "Tribal Language" and adhere to the "Confident Pragmatist" / "Engineering Stand-up" tone.

| ID | Agent | Role and Description | Key Task |
| :--- | :--- | :--- | :--- |
| **1.** | **Deep Analyst** (The Extractor) | Receives raw ideas (transcriptions, links) and **deconstructs** them, identifying the key insight, "Social Currency," and direct references to target audience "pain points" (e.g., "Latency", "Debugging Nightmare"). | Creating a structured **Content Brief** (set of talking points) from raw material. |
| **2.** | **Voice Architect** (The Ghostwriter) | Generates content drafts (YouTube scripts, LinkedIn posts) based on the Content Brief. | Strict adherence to **Speech Style** (mixing jargon with tech slang) and applying dramaturgical formulas (e.g., "MLOps Blueprint", "Secret Value"). |
| **3.** | **Ruthless Critic** (The Quality Gate) | Functions as the "Internal Editor" and **"Grigory Simulator"**. | Verifying the draft for 100% compliance with **RAG (Constitutional Layer)**: absence of "hype", no emotional emojis, use of "functional" emojis (e.g., ⬇️, →), and application of "Transformation Language" (e.g., "Pure Python", "Reduced latency"). |
| **4.** | **Atomizer** (The Distributor) | Takes the final, approved content and adapts it for different platforms. | Generating **50 headline variants** for YouTube/Reels, creating "editing sheets", and structuring text for posts. |
| **5.** | **The Librarian** (Memory Manager) | **Manages all data stores** and updates the system's "brain" based on external feedback (Managed Learning Loop). | Implementing **Corrections** (e.g., a new "Taboo term") into RAG indices and updating **Worldview** (stance on a tool) in the Knowledge Graph. |

### II. Memory and Knowledge Base (The Brain)

The system must use a two-layer memory architecture, where each layer performs its critical function.

#### 1. RAG: Constitutional Layer (Style and Rules)
* **Purpose:** Storing and retrieving data that defines voice, tone, and rules.
* **Contents:**
    * **Static (Read-Only):** `brand_passport.pdf`, `reader_card.pdf`, `speech_code.pdf`. (Immutable DNA).
    * **Dynamic (Managed by Librarian):** Documents with constantly updated constraints.
        * `taboo_list.md`: List of prohibited phrases, clichés, and "hype" terms.
        * `style_adjustments.md`: Log of tone changes.
* **Interaction:** **Voice Architect** and **Ruthless Critic** must query this layer to verify each generated phrase for voice compliance.

#### 2. Knowledge Graph: Worldview Layer (Topics and Stances)
* **Purpose:** Storing structured relationships between technical concepts, problems, and your stance on them (Worldview).
* **Architecture:** A graph consisting of:
    * **Nodes (Entities):** `LangChain`, `Docker`, `Latency`, `MLOps`, `Business Impact`, `Hype`.
    * **Edges (Relationships):**
        * `[LangChain] --(causes)--> [Debugging Nightmare]`
        * `[Docker] --(is_solution_to)--> [Reproducibility]`
        * `[Grigory] --(hates)--> [Hype]`
* **Interaction:**
    * **Deep Analyst** uses it to contextualize new topics: if a new tool is mentioned in the raw material, Analyst must check if a relationship `[Grigory] --(is_skeptical_of)--> [Tool]` already exists.
    * **Librarian** updates this graph when you change your opinion (e.g., due to a new case study).

### III. Architectural Connections and Loops

#### 1. Main Pipeline
* **Sequence:** `Input` → `Analyst` → `Writer` ↔ `Critic` → `Final Script` → `Atomizer` → `Social Posts`.
* **Requirement:** **Writer** cannot receive approval until **Critic** marks **Pass** on all key metrics (Tonal Score, Hype-Level, Latency-Check).

#### 2. Learning Loop (The Learning Loop)
* **Trigger Source:** User feedback (`User / Grigory`).
* **Path:** `User Feedback` → **Librarian** → `RAG (Dynamic Docs)` + `Knowledge Graph`.
* **Requirement:** **Librarian** must have a prioritization mechanism: manual "Taboo" corrections have the highest priority and immediately enter RAG for immediate use by **Critic** in the next cycle.

#### 3. Formatting and Code
* **Language:** The main code must be written in Python.
* **Immutability:** Source documents must be accessible for reading but not for writing (Immutability). Only **Librarian** can make changes to derived dynamic documents (`taboo_list.md`) and the Knowledge Graph.