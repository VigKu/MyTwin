---
title: MyVirtualTwin
emoji: 🐨
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: 6.26.0
python_version: '3.13'
app_file: app.py
pinned: false
license: apache-2.0
short_description: Career related twin
---

------------------------------
## My AI Twin Deployment with Semantic LRU Caching & Guardrails

This project deploys an AI Digital Twin designed to interact with visitors, potential recruiters, and future employers. The system is built using Gradio, OpenAI LLMs, and Hugging Face Hub for cloud context storage.
To deliver production-grade responsiveness and safety, the application includes a multi-tiered Semantic & Lexical LRU Cache, strict PII/State Guardrails, and an automated Human-in-the-Loop context resolution workflow.

This project is based on Ed Donner's agentic course on Udemy.
------------------------------
## 🏗️ Architecture & Workflow Overview

                        +----------------------------+

                        |  User Query (Gradio App)   |
                        +--------------+-------------+
                                       |
                                       v
                        +--------------+-------------+

                        |  Lexical & Semantic Cache  |
                        +--------------+-------------+
                                       |
                    +------------------+------------------+

                    |                                     |
                    v Cache Hit                           v Cache Miss
        +-----------+-----------+             +-----------+-----------+

        | Return Cached Response |             | Execute RAG Tool:     |
        +-----------------------+             | query_add_knowledge() |
                                              +-----------+-----------+
                                                          |
                                                          v
                                              +-----------+-----------+

                                              | Pull knowledge_gap.txt|
                                              | From Hugging Face Hub |
                                              +-----------+-----------+
                                                          |
                                                          v
                                              +-----------+-----------+

                                              | Append Extra Context  |
                                              | To OpenAI LLM Inputs  |
                                              +-----------+-----------+
                                                          |
                                                          v
                                              +-----------+-----------+

                                              |   Invoke OpenAI LLM   |
                                              |    (gpt-5.4-nano)     |
                                              +-----------+-----------+
                                                          |
                                                          v
                                              +-----------+-----------+

                                              | Apply Guardrail Checks|
                                              +-----------+-----------+
                                                          |
                                    +---------------------+---------------------+

                                    |                                           |
                                    v Passes Checks                             v Triggers Guardrail
                        +-----------+-----------+                   +-----------+-----------+

                        | Save to LRU Cache     |                   |  Skip Cache Save      |
                        +-----------------------+                   +-----------+-----------+
                                                                                |
                                                                                v
                                                                    +-----------+-----------+

                                                                    | Append Knowledge Gap  |
                                                                    |   (Hugging Face)      |
                                                                    +-----------------------+


   1. User Submits Query: The input message is captured via the Gradio interface.
   2. Cache Verification: The system queries a global Least Recently Used (LRU) Semantic Prompt Cache using a multi-tiered similarity pipeline.
   3. RAG Context Enrichment (Cache Miss): On a cache miss, the agent executes query_additional_knowledge. This downloads knowledge_gap.txt from Hugging Face and appends its contents as enriched reference context into the prompt stream sent to the OpenAI LLM.
   4. LLM Invocation: The OpenAI model (gpt-5.4-nano) processes the combined context (Resume + Summary + Appended Knowledge Gap) to generate a highly accurate response.
   5. Guardrail Evaluation & Storage: The final response text is parsed through PII and "Unknown Answer" evaluation engines. Safe pairs are cached, while missing answers are securely written back up to Hugging Face as a new knowledge gap entry.

------------------------------
## ⚡ Multi-Tiered LRU Cache Concept
To keep computational latency low and limit API expenses, queries are routed through a customized Least Recently Used (LRU) Semantic Prompt Cache (LRUSemanticPromptCache) with a maximum capacity of 15 elements.
The cache uses a two-tier matching strategy to guarantee high-precision hits:

| Match Tier | Technology Used | Strategy Details |
|---|---|---|
| Tier 1: Lexical Match | rapidfuzz | Scans structural layout using token-based text similarity. Captures exact structural duplicates or inverted word orders quickly without embedding lookup overhead. |
| Tier 2: Semantic Match | sentence-transformers (all-MiniLM-L6-v2) | Generates a normalized text vector and measures the geometric angle via Cosine Similarity against stored entries. Hits are triggered if the similarity exceeds the configured threshold (0.7). |

## LRU Eviction & Re-ordering Logic
The cache tracks interactions using ordered lists:

* Cache Hits: When a query hits either the lexical or semantic cache, the targeted entry is popped from its current position and appended to the very end of the tracking list. This tags it as the Most Recently Used (MRU) entry.
* Cache Evictions: When new data is added and the cache is full (>= max_size), the element at index 0 (the coldest, Least Recently Used entry) is deleted to make room for the new record.

------------------------------
## 🛡️ Guardrails & Safety Processing
Every model response undergoes a strict evaluation filter before it is allowed to enter the long-term cache memory:

* PII Redaction Guardrail (contains_pii): Regular expressions evaluate inputs for email addresses, telephone variations, or explicit self-identifying statements (e.g., "My name is..."). If triggered, caching is bypassed to protect user privacy.
* Uncertainty Guardrail (is_unknown_response): If the model responds with any variation of uncertainty (e.g., "do not have details", "insufficient information", "I don't know"), the response is prevented from being saved to the cache. This prevents the agent from permanently remembering unhelpful or empty states.

------------------------------
## 👥 Human-in-the-Loop Offline Knowledge Workflow
When the digital twin encounters a career-related question that isn't answered in its primary resume context, it follows a structured offline loop to learn the answer:

[Agent Misses Answer] -> [Appends to knowledge_gap.txt] -> [Human Edits File Offline] -> [Agent Pulls via Tool as RAG]

## 1. Automated Detection & Storage
When the Uncertainty Guardrail catches an "I don't know" state, it automatically runs save_knowledge_gap(). This function downloads the current knowledge_gap.txt file from a Hugging Face Dataset repository (Vikool/MyData), appends the raw question along with the agent's uncertain response, and pushes the updated file back to the repository.
## 2. Offline Human Intervention
The human owner logs into Hugging Face or edits the repository file offline. The human modifies the appended entry by replacing the uncertain response with the true, verified factual background:

# BEFORE (Automated Upload)
Prompt: Did you manage Kubernetes clusters at your last job?
Answer: I don't have that information. Please contact my human self.

# AFTER (Human Correction Offline)
Prompt: Did you manage Kubernetes clusters at your last job?
Answer: Yes, I managed production EKS clusters, configured Helm charts, and optimized auto-scaling profiles.

## 3. RAG Injection at Runtime
Because the retrieved knowledge is injected straight into the LLM's workspace via RAG, the digital twin reads these human-corrected QA pairs like an extension of its resume. It gains the ability to reason over these previously unanswerable topics and phrase intelligent responses dynamically.
------------------------------




